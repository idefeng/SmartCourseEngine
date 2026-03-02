/**
 * 文件上传服务
 * 
 * 提供分片上传、断点续传、进度跟踪功能
 */

import apiClient from './api';
import { getWebSocketClient, MessageType } from './websocket';

// 上传状态
export enum UploadStatus {
  PENDING = 'pending',
  UPLOADING = 'uploading',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

// 上传任务接口
export interface UploadTask {
  upload_id: string;
  file_name: string;
  file_size: number;
  file_hash: string;
  chunk_size: number;
  total_chunks: number;
  uploaded_chunks: number[];
  status: UploadStatus;
  user_id: number;
  created_at: string;
  updated_at: string;
  file_path?: string;
  file_type?: string;
  metadata?: Record<string, any>;
  progress?: number;
}

// 上传配置
export interface UploadConfig {
  chunkSize?: number; // 分片大小（字节）
  maxRetries?: number; // 最大重试次数
  retryDelay?: number; // 重试延迟（毫秒）
  concurrentUploads?: number; // 并发上传数
  timeout?: number; // 超时时间（毫秒）
}

// 默认配置
const DEFAULT_CONFIG: UploadConfig = {
  chunkSize: 10 * 1024 * 1024, // 10MB
  maxRetries: 3,
  retryDelay: 1000,
  concurrentUploads: 3,
  timeout: 30000,
};

// 上传事件类型
export enum UploadEventType {
  INITIALIZED = 'initialized',
  PROGRESS = 'progress',
  CHUNK_UPLOADED = 'chunk_uploaded',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

// 上传事件接口
export interface UploadEvent {
  type: UploadEventType;
  task: UploadTask;
  data?: any;
}

// 事件监听器类型
type UploadEventListener = (event: UploadEvent) => void;

/**
 * 文件上传管理器
 */
export class FileUploadManager {
  private tasks: Map<string, UploadTask> = new Map();
  private eventListeners: Map<UploadEventType, UploadEventListener[]> = new Map();
  private config: UploadConfig;
  private wsClient = getWebSocketClient();

  constructor(config: Partial<UploadConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.setupWebSocketListeners();
  }

  /**
   * 初始化上传任务
   */
  async initUpload(
    file: File,
    userId: number,
    metadata: Record<string, any> = {}
  ): Promise<UploadTask> {
    try {
      // 验证文件
      this.validateFile(file);

      // 计算分片数量
      const chunkSize = this.config.chunkSize!;
      const totalChunks = Math.ceil(file.size / chunkSize);

      // 调用API初始化上传
      const response = await apiClient.post('/upload/init', {
        file_name: file.name,
        file_size: file.size,
        chunk_size: chunkSize,
        user_id: userId,
        metadata,
      }, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const uploadData = response.data;
      const task: UploadTask = {
        ...uploadData.metadata,
        progress: 0,
      };

      // 保存任务
      this.tasks.set(task.upload_id, task);

      // 触发初始化事件
      this.emitEvent(UploadEventType.INITIALIZED, task);

      return task;
    } catch (error) {
      console.error('初始化上传失败:', error);
      throw error;
    }
  }

  /**
   * 开始上传文件
   */
  async uploadFile(
    file: File,
    userId: number,
    metadata: Record<string, any> = {}
  ): Promise<UploadTask> {
    // 初始化上传任务
    const task = await this.initUpload(file, userId, metadata);

    try {
      // 分片上传
      await this.uploadChunks(file, task);

      // 完成上传
      const completedTask = await this.completeUpload(task.upload_id);
      
      // 触发完成事件
      this.emitEvent(UploadEventType.COMPLETED, completedTask);

      return completedTask;
    } catch (error) {
      console.error('文件上传失败:', error);
      
      // 更新任务状态
      const failedTask = await this.getUploadStatus(task.upload_id);
      this.emitEvent(UploadEventType.FAILED, failedTask, { error });
      
      throw error;
    }
  }

  /**
   * 上传分片
   */
  private async uploadChunks(file: File, task: UploadTask): Promise<void> {
    const chunkSize = this.config.chunkSize!;
    const totalChunks = task.total_chunks;
    const uploadedChunks = new Set(task.uploaded_chunks);

    // 创建分片上传队列
    const chunksToUpload = Array.from({ length: totalChunks }, (_, i) => i)
      .filter(i => !uploadedChunks.has(i));

    // 并发上传分片
    const concurrentUploads = this.config.concurrentUploads!;
    const chunksQueue = [...chunksToUpload];

    while (chunksQueue.length > 0) {
      const currentChunks = chunksQueue.splice(0, concurrentUploads);
      await Promise.all(
        currentChunks.map(chunkIndex => this.uploadChunk(file, task, chunkIndex))
      );
    }
  }

  /**
   * 上传单个分片
   */
  private async uploadChunk(file: File, task: UploadTask, chunkIndex: number): Promise<void> {
    const chunkSize = this.config.chunkSize!;
    const start = chunkIndex * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    const chunk = file.slice(start, end);

    let retries = 0;
    const maxRetries = this.config.maxRetries!;

    while (retries <= maxRetries) {
      try {
        // 创建FormData
        const formData = new FormData();
        formData.append('chunk_file', chunk, `chunk_${chunkIndex}`);

        // 上传分片
        await apiClient.post(
          `/upload/chunk/${task.upload_id}/${chunkIndex}`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            timeout: this.config.timeout,
          }
        );

        // 更新任务进度
        const updatedTask = await this.getUploadStatus(task.upload_id);
        this.tasks.set(task.upload_id, updatedTask);

        // 触发分片上传事件
        this.emitEvent(UploadEventType.CHUNK_UPLOADED, updatedTask, { chunkIndex });

        // 触发进度事件
        this.emitEvent(UploadEventType.PROGRESS, updatedTask);

        return;
      } catch (error) {
        retries++;
        if (retries > maxRetries) {
          throw new Error(`分片 ${chunkIndex} 上传失败: ${error}`);
        }

        // 等待重试
        await new Promise(resolve => 
          setTimeout(resolve, this.config.retryDelay! * retries)
        );
      }
    }
  }

  /**
   * 完成上传
   */
  async completeUpload(uploadId: string): Promise<UploadTask> {
    try {
      const response = await apiClient.post(`/upload/complete/${uploadId}`);
      const task = response.data.metadata;
      
      this.tasks.set(uploadId, task);
      return task;
    } catch (error) {
      console.error('完成上传失败:', error);
      throw error;
    }
  }

  /**
   * 取消上传
   */
  async cancelUpload(uploadId: string): Promise<UploadTask> {
    try {
      const response = await apiClient.post(`/upload/cancel/${uploadId}`);
      const task = response.data.metadata;
      
      this.tasks.delete(uploadId);
      this.emitEvent(UploadEventType.CANCELLED, task);
      
      return task;
    } catch (error) {
      console.error('取消上传失败:', error);
      throw error;
    }
  }

  /**
   * 获取上传状态
   */
  async getUploadStatus(uploadId: string): Promise<UploadTask> {
    try {
      const response = await apiClient.get(`/upload/status/${uploadId}`);
      return response.data.metadata;
    } catch (error) {
      console.error('获取上传状态失败:', error);
      throw error;
    }
  }

  /**
   * 获取用户的上传任务
   */
  async getUserUploads(userId: number): Promise<UploadTask[]> {
    try {
      const response = await apiClient.get(`/upload/user/${userId}`);
      return response.data.uploads;
    } catch (error) {
      console.error('获取用户上传任务失败:', error);
      throw error;
    }
  }

  /**
   * 获取所有任务
   */
  getTasks(): UploadTask[] {
    return Array.from(this.tasks.values());
  }

  /**
   * 获取任务
   */
  getTask(uploadId: string): UploadTask | undefined {
    return this.tasks.get(uploadId);
  }

  /**
   * 订阅上传事件
   */
  on(type: UploadEventType, listener: UploadEventListener): void {
    if (!this.eventListeners.has(type)) {
      this.eventListeners.set(type, []);
    }
    this.eventListeners.get(type)!.push(listener);
  }

  /**
   * 取消订阅上传事件
   */
  off(type: UploadEventType, listener: UploadEventListener): void {
    const listeners = this.eventListeners.get(type);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  /**
   * 设置WebSocket监听器
   */
  private setupWebSocketListeners(): void {
    // 监听上传进度消息
    this.wsClient.on(MessageType.VIDEO_UPLOAD_PROGRESS, (message) => {
      const { task_id, progress, file_name } = message.data;
      const task = this.tasks.get(task_id);
      
      if (task) {
        const updatedTask = { ...task, progress };
        this.tasks.set(task_id, updatedTask);
        this.emitEvent(UploadEventType.PROGRESS, updatedTask);
      }
    });

    // 监听视频分析开始消息
    this.wsClient.on(MessageType.VIDEO_ANALYSIS_STARTED, (message) => {
      const { task_id, video_id } = message.data;
      const task = this.tasks.get(task_id);
      
      if (task) {
        console.log(`视频分析开始: ${task.file_name} (${video_id})`);
      }
    });

    // 监听视频分析进度消息
    this.wsClient.on(MessageType.VIDEO_ANALYSIS_PROGRESS, (message) => {
      const { task_id, progress, message: statusMessage } = message.data;
      const task = this.tasks.get(task_id);
      
      if (task) {
        console.log(`视频分析进度: ${task.file_name} - ${progress}% - ${statusMessage}`);
      }
    });

    // 监听任务完成消息
    this.wsClient.on(MessageType.TASK_COMPLETED, (message) => {
      const { task_id, task_type, result } = message.data;
      const task = this.tasks.get(task_id);
      
      if (task) {
        const updatedTask = { ...task, status: UploadStatus.COMPLETED };
        this.tasks.set(task_id, updatedTask);
        this.emitEvent(UploadEventType.COMPLETED, updatedTask, { result });
      }
    });

    // 监听任务失败消息
    this.wsClient.on(MessageType.TASK_FAILED, (message) => {
      const { task_id, task_type, error } = message.data;
      const task = this.tasks.get(task_id);
      
      if (task) {
        const updatedTask = { ...task, status: UploadStatus.FAILED };
        this.tasks.set(task_id, updatedTask);
        this.emitEvent(UploadEventType.FAILED, updatedTask, { error });
      }
    });
  }

  /**
   * 触发事件
   */
  private emitEvent(type: UploadEventType, task: UploadTask, data?: any): void {
    const listeners = this.eventListeners.get(type);
    if (listeners) {
      const event: UploadEvent = { type, task, data };
      listeners.forEach(listener => listener(event));
    }
  }

  /**
   * 验证文件
   */
  private validateFile(file: File): void {
    // 检查文件大小
    const maxSize = 10 * 1024 * 1024 * 1024; // 10GB
    if (file.size > maxSize) {
      throw new Error(`文件大小超过限制: ${file.size} > ${maxSize}`);
    }

    // 检查文件类型
    const allowedExtensions = [
      // 视频文件
      'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v',
      // 音频文件
      'mp3', 'wav', 'ogg', 'flac', 'aac',
      // 文档文件
      'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
      // 图片文件
      'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
      // 其他
      'txt', 'md', 'json', 'xml', 'csv'
    ];

    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!extension || !allowedExtensions.includes(extension)) {
      throw new Error(`不支持的文件类型: ${file.name}`);
    }
  }
}

// 全局文件上传管理器实例
let globalUploadManager: FileUploadManager | null = null;

/**
 * 获取文件上传管理器实例（单例模式）
 */
export function getUploadManager(): FileUploadManager {
  if (!globalUploadManager) {
    globalUploadManager = new FileUploadManager();
  }
  return globalUploadManager;
}

/**
 * React Hook: 使用文件上传
 */
export function useUpload() {
  const uploadManager = getUploadManager();

  return {
    // 上传方法
    uploadFile: uploadManager.uploadFile.bind(uploadManager),
    initUpload: uploadManager.initUpload.bind(uploadManager),
    completeUpload: uploadManager.completeUpload.bind(uploadManager),
    cancelUpload: uploadManager.cancelUpload.bind(uploadManager),
    
    // 查询方法
    getUploadStatus: uploadManager.getUploadStatus.bind(uploadManager),
    getUserUploads: uploadManager.getUserUploads.bind(uploadManager),
    getTasks: uploadManager.getTasks.bind(uploadManager),
    getTask: uploadManager.getTask.bind(uploadManager),
    
    // 事件订阅
    on: uploadManager.on.bind(uploadManager),
    off: uploadManager.off.bind(uploadManager),
  };
}

// 导出常用类型和枚举
export {
  UploadStatus as UploadStatusEnum,
  UploadEventType as UploadEventTypeEnum,
};