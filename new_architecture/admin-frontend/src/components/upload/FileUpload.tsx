'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Upload as AntUpload,
  Button,
  Card,
  Progress,
  Space,
  Typography,
  Alert,
  List,
  Tag,
  Modal,
  message,
} from 'antd';
import {
  UploadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CloseCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  FileOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { useAuth } from '@/contexts/auth-context';
import { useUpload, UploadTask, UploadStatus, UploadEventType } from '@/services/upload';

const { Title, Text } = Typography;

interface FileUploadProps {
  onUploadComplete?: (task: UploadTask) => void;
  onUploadError?: (error: Error) => void;
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // MB
}

const FileUpload: React.FC<FileUploadProps> = ({
  onUploadComplete,
  onUploadError,
  accept = '.mp4,.avi,.mov,.wmv,.flv,.mkv,.webm,.m4v,.mp3,.wav,.ogg,.flac,.aac,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.bmp,.webp,.txt,.md,.json,.xml,.csv',
  multiple = false,
  maxSize = 10240, // 10GB in MB
}) => {
  const { user, isLoading, isAuthenticated } = useAuth();
  const {
    uploadFile,
    getTasks,
    getTask,
    cancelUpload,
    on,
    off,
  } = useUpload();

  const [uploading, setUploading] = useState(false);
  const [tasks, setTasks] = useState<UploadTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<UploadTask | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 加载任务列表
  useEffect(() => {
    loadTasks();
    
    // 订阅上传事件
    const handleProgress = (event: any) => {
      const { task } = event;
      updateTask(task);
    };

    const handleCompleted = (event: any) => {
      const { task } = event;
      updateTask(task);
      message.success(`文件上传完成: ${task.file_name}`);
      if (onUploadComplete) {
        onUploadComplete(task);
      }
    };

    const handleFailed = (event: any) => {
      const { task, data } = event;
      updateTask(task);
      message.error(`文件上传失败: ${task.file_name}`);
      if (onUploadError && data?.error) {
        onUploadError(data.error);
      }
    };

    const handleCancelled = (event: any) => {
      const { task } = event;
      removeTask(task.upload_id);
      message.info(`上传已取消: ${task.file_name}`);
    };

    on(UploadEventType.PROGRESS, handleProgress);
    on(UploadEventType.COMPLETED, handleCompleted);
    on(UploadEventType.FAILED, handleFailed);
    on(UploadEventType.CANCELLED, handleCancelled);

    return () => {
      off(UploadEventType.PROGRESS, handleProgress);
      off(UploadEventType.COMPLETED, handleCompleted);
      off(UploadEventType.FAILED, handleFailed);
      off(UploadEventType.CANCELLED, handleCancelled);
    };
  }, []);

  // 加载任务
  const loadTasks = () => {
    const allTasks = getTasks();
    setTasks(allTasks);
  };

  // 更新任务
  const updateTask = (task: UploadTask) => {
    setTasks(prev => {
      const index = prev.findIndex(t => t.upload_id === task.upload_id);
      if (index >= 0) {
        const newTasks = [...prev];
        newTasks[index] = task;
        return newTasks;
      } else {
        return [...prev, task];
      }
    });
  };

  // 移除任务
  const removeTask = (uploadId: string) => {
    setTasks(prev => prev.filter(task => task.upload_id !== uploadId));
  };

  // 处理文件选择
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    if (isLoading) {
      message.warning('正在校验登录状态，请稍后重试');
      return;
    }

    if (!isAuthenticated || !user?.id) {
      message.error('请先登录后再上传文件');
      return;
    }

    setUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // 验证文件大小
        if (file.size > maxSize * 1024 * 1024) {
          message.error(`文件 ${file.name} 超过大小限制 (${maxSize}MB)`);
          continue;
        }

        // 开始上传
        const task = await uploadFile(file, user.id, {
          description: `上传于 ${new Date().toLocaleString()}`,
        });

        updateTask(task);
      }
    } catch (error: any) {
      message.error(`上传失败: ${error.message}`);
      if (onUploadError) {
        onUploadError(error);
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // 取消上传
  const handleCancelUpload = async (task: UploadTask) => {
    Modal.confirm({
      title: '确认取消上传',
      content: `确定要取消上传 "${task.file_name}" 吗？`,
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await cancelUpload(task.upload_id);
          removeTask(task.upload_id);
        } catch (error: any) {
          message.error(`取消上传失败: ${error.message}`);
        }
      },
    });
  };

  // 查看任务详情
  const handleViewDetails = (task: UploadTask) => {
    setSelectedTask(task);
    setModalVisible(true);
  };

  // 获取状态标签
  const getStatusTag = (status: UploadStatus) => {
    switch (status) {
      case UploadStatus.PENDING:
        return <Tag color="default">等待中</Tag>;
      case UploadStatus.UPLOADING:
        return <Tag color="processing">上传中</Tag>;
      case UploadStatus.PROCESSING:
        return <Tag color="processing">处理中</Tag>;
      case UploadStatus.COMPLETED:
        return <Tag color="success">已完成</Tag>;
      case UploadStatus.FAILED:
        return <Tag color="error">失败</Tag>;
      case UploadStatus.CANCELLED:
        return <Tag color="default">已取消</Tag>;
      default:
        return <Tag color="default">未知</Tag>;
    }
  };

  // 获取文件图标
  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v'].includes(ext || '')) {
      return <VideoCameraOutlined style={{ fontSize: 20, color: '#1890ff' }} />;
    }
    return <FileOutlined style={{ fontSize: 20, color: '#666' }} />;
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 格式化时间
  const formatTime = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
  };

  return (
    <div className="file-upload-container">
      <Card
        title={
          <Space>
            <UploadOutlined />
            <span>文件上传</span>
          </Space>
        }
        extra={
          <Space>
            <input
              ref={fileInputRef}
              type="file"
              accept={accept}
              multiple={multiple}
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <Button
              type="primary"
              icon={<UploadOutlined />}
              loading={uploading}
              disabled={isLoading || !isAuthenticated}
              onClick={() => fileInputRef.current?.click()}
            >
              选择文件
            </Button>
          </Space>
        }
      >
        {/* 上传提示 */}
        <Alert
          message="上传说明"
          description={
            <div>
              <Text type="secondary">
                支持上传视频、音频、图片、文档等文件，单个文件最大 {maxSize}MB。
                <br />
                支持断点续传，上传过程中可以暂停和恢复。
              </Text>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {/* 任务列表 */}
        {tasks.length > 0 ? (
          <List
            dataSource={tasks}
            renderItem={(task) => (
              <List.Item
                actions={[
                  task.status === UploadStatus.UPLOADING && (
                    <Button
                      key="cancel"
                      type="text"
                      danger
                      icon={<CloseCircleOutlined />}
                      onClick={() => handleCancelUpload(task)}
                    >
                      取消
                    </Button>
                  ),
                  <Button
                    key="details"
                    type="text"
                    onClick={() => handleViewDetails(task)}
                  >
                    详情
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  avatar={getFileIcon(task.file_name)}
                  title={
                    <Space>
                      <Text strong>{task.file_name}</Text>
                      {getStatusTag(task.status)}
                    </Space>
                  }
                  description={
                    <div>
                      <Space direction="vertical" size={2} style={{ width: '100%' }}>
                        <div>
                          <Text type="secondary">
                            大小: {formatFileSize(task.file_size)} | 
                            分片: {task.uploaded_chunks?.length || 0}/{task.total_chunks} | 
                            创建: {formatTime(task.created_at)}
                          </Text>
                        </div>
                        {task.status === UploadStatus.UPLOADING && (
                          <Progress
                            percent={task.progress || 0}
                            size="small"
                            status="active"
                            strokeColor={{
                              '0%': '#108ee9',
                              '100%': '#87d068',
                            }}
                          />
                        )}
                        {task.status === UploadStatus.PROCESSING && (
                          <Progress
                            percent={task.progress || 0}
                            size="small"
                            status="active"
                            strokeColor={{
                              '0%': '#108ee9',
                              '100%': '#87d068',
                            }}
                          />
                        )}
                      </Space>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <UploadOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
            <Text type="secondary">暂无上传任务，点击上方按钮选择文件开始上传</Text>
          </div>
        )}
      </Card>

      {/* 任务详情模态框 */}
      <Modal
        title="上传任务详情"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedTask && (
          <div>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              {/* 基本信息 */}
              <div>
                <Title level={5}>基本信息</Title>
                <Space direction="vertical" size={8}>
                  <div>
                    <Text strong>文件名: </Text>
                    <Text>{selectedTask.file_name}</Text>
                  </div>
                  <div>
                    <Text strong>文件大小: </Text>
                    <Text>{formatFileSize(selectedTask.file_size)}</Text>
                  </div>
                  <div>
                    <Text strong>文件类型: </Text>
                    <Text>{selectedTask.file_type || '未知'}</Text>
                  </div>
                  <div>
                    <Text strong>状态: </Text>
                    {getStatusTag(selectedTask.status)}
                  </div>
                  <div>
                    <Text strong>创建时间: </Text>
                    <Text>{formatTime(selectedTask.created_at)}</Text>
                  </div>
                  <div>
                    <Text strong>更新时间: </Text>
                    <Text>{formatTime(selectedTask.updated_at)}</Text>
                  </div>
                </Space>
              </div>

              {/* 上传进度 */}
              {(selectedTask.status === UploadStatus.UPLOADING || 
                selectedTask.status === UploadStatus.PROCESSING) && (
                <div>
                  <Title level={5}>上传进度</Title>
                  <Progress
                    percent={selectedTask.progress || 0}
                    status="active"
                    strokeColor={{
                      '0%': '#108ee9',
                      '100%': '#87d068',
                    }}
                  />
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">
                      分片进度: {selectedTask.uploaded_chunks?.length || 0}/{selectedTask.total_chunks}
                    </Text>
                  </div>
                </div>
              )}

              {/* 分片信息 */}
              {selectedTask.total_chunks > 0 && (
                <div>
                  <Title level={5}>分片信息</Title>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {Array.from({ length: selectedTask.total_chunks }, (_, i) => i).map((chunkIndex) => (
                      <Tag
                        key={chunkIndex}
                        color={selectedTask.uploaded_chunks?.includes(chunkIndex) ? 'success' : 'default'}
                        style={{ margin: 2 }}
                      >
                        {chunkIndex + 1}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* 元数据 */}
              {selectedTask.metadata && Object.keys(selectedTask.metadata).length > 0 && (
                <div>
                  <Title level={5}>元数据</Title>
                  <pre style={{ 
                    background: '#f6f6f6', 
                    padding: 12, 
                    borderRadius: 4,
                    maxHeight: 200,
                    overflow: 'auto'
                  }}>
                    {JSON.stringify(selectedTask.metadata, null, 2)}
                  </pre>
                </div>
              )}

              {/* 文件路径 */}
              {selectedTask.file_path && (
                <div>
                  <Title level={5}>文件路径</Title>
                  <Text code>{selectedTask.file_path}</Text>
                </div>
              )}
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default FileUpload;
