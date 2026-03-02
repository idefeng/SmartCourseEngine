/**
 * WebSocket客户端服务
 * 
 * 提供WebSocket连接管理、消息处理、事件订阅功能
 */

import { useEffect } from 'react';
import { useAuth } from '@/contexts/auth-context';

// WebSocket消息类型
export enum MessageType {
  // 系统消息
  CONNECT = 'connect',
  DISCONNECT = 'disconnect',
  PING = 'ping',
  PONG = 'pong',
  ERROR = 'error',
  
  // 用户消息
  USER_ONLINE = 'user_online',
  USER_OFFLINE = 'user_offline',
  USER_TYPING = 'user_typing',
  USER_MESSAGE = 'user_message',
  
  // 视频处理
  VIDEO_UPLOAD_PROGRESS = 'video_upload_progress',
  VIDEO_ANALYSIS_STARTED = 'video_analysis_started',
  VIDEO_ANALYSIS_PROGRESS = 'video_analysis_progress',
  VIDEO_ANALYSIS_COMPLETED = 'video_analysis_completed',
  VIDEO_ANALYSIS_FAILED = 'video_analysis_failed',
  
  // 知识处理
  KNOWLEDGE_EXTRACTION_STARTED = 'knowledge_extraction_started',
  KNOWLEDGE_EXTRACTION_PROGRESS = 'knowledge_extraction_progress',
  KNOWLEDGE_EXTRACTION_COMPLETED = 'knowledge_extraction_completed',
  KNOWLEDGE_GRAPH_UPDATED = 'knowledge_graph_updated',
  
  // 系统通知
  SYSTEM_NOTIFICATION = 'system_notification',
  TASK_COMPLETED = 'task_completed',
  TASK_FAILED = 'task_failed',
}

// WebSocket消息接口
export interface WebSocketMessage {
  type: MessageType;
  data: Record<string, any>;
  timestamp: string;
  message_id?: string;
  user_id?: number;
}

// 事件监听器类型
type EventListener = (message: WebSocketMessage) => void;

// WebSocket配置
interface WebSocketConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
}

// 默认配置
const DEFAULT_CONFIG: WebSocketConfig = {
  url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001/ws',
  reconnectInterval: 3000, // 3秒重连间隔
  maxReconnectAttempts: 5, // 最大重连次数
  pingInterval: 30000, // 30秒发送一次ping
};

/**
 * WebSocket客户端类
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private pingTimer: NodeJS.Timeout | null = null;
  private eventListeners: Map<MessageType, EventListener[]> = new Map();
  private connectionListeners: Array<(connected: boolean) => void> = [];
  private isConnected = false;
  private userId: number | null = null;

  constructor(config: Partial<WebSocketConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 连接到WebSocket服务器
   */
  connect(userId: number): void {
    if (this.ws && this.isConnected) {
      console.log('WebSocket已经连接');
      return;
    }

    this.userId = userId;
    const url = `${this.config.url}?user_id=${userId}`;
    
    try {
      this.ws = new WebSocket(url);
      this.setupEventHandlers();
    } catch (error) {
      console.error('WebSocket连接失败:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * 断开WebSocket连接
   */
  disconnect(): void {
    // 清理定时器
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }

    // 关闭连接
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.notifyConnectionChange(false);
  }

  /**
   * 发送消息
   */
  send(type: MessageType, data: Record<string, any> = {}): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接，无法发送消息');
      return;
    }

    const message: WebSocketMessage = {
      type,
      data,
      timestamp: new Date().toISOString(),
    };

    this.ws.send(JSON.stringify(message));
  }

  /**
   * 发送ping消息
   */
  sendPing(): void {
    this.send(MessageType.PING, { timestamp: new Date().toISOString() });
  }

  /**
   * 订阅消息事件
   */
  on(type: MessageType, listener: EventListener): void {
    if (!this.eventListeners.has(type)) {
      this.eventListeners.set(type, []);
    }
    this.eventListeners.get(type)!.push(listener);
  }

  /**
   * 取消订阅消息事件
   */
  off(type: MessageType, listener: EventListener): void {
    const listeners = this.eventListeners.get(type);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  /**
   * 订阅连接状态变化
   */
  onConnectionChange(listener: (connected: boolean) => void): void {
    this.connectionListeners.push(listener);
  }

  /**
   * 取消订阅连接状态变化
   */
  offConnectionChange(listener: (connected: boolean) => void): void {
    const index = this.connectionListeners.indexOf(listener);
    if (index > -1) {
      this.connectionListeners.splice(index, 1);
    }
  }

  /**
   * 获取连接状态
   */
  getConnected(): boolean {
    return this.isConnected;
  }

  /**
   * 获取用户ID
   */
  getUserId(): number | null {
    return this.userId;
  }

  /**
   * 设置事件处理器
   */
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket连接成功');
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.notifyConnectionChange(true);
      this.startPingTimer();
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket连接关闭:', event.code, event.reason);
      this.isConnected = false;
      this.notifyConnectionChange(false);
      this.stopPingTimer();
      
      // 如果不是正常关闭，尝试重连
      if (event.code !== 1000) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      this.isConnected = false;
      this.notifyConnectionChange(false);
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('消息解析失败:', error, event.data);
      }
    };
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: WebSocketMessage): void {
    // 触发对应类型的监听器
    const listeners = this.eventListeners.get(message.type);
    if (listeners) {
      listeners.forEach(listener => listener(message));
    }

    // 特殊处理ping消息
    if (message.type === MessageType.PING) {
      this.send(MessageType.PONG, { timestamp: new Date().toISOString() });
    }
  }

  /**
   * 开始ping定时器
   */
  private startPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
    }

    this.pingTimer = setInterval(() => {
      this.sendPing();
    }, this.config.pingInterval);
  }

  /**
   * 停止ping定时器
   */
  private stopPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  /**
   * 安排重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts!) {
      console.error('达到最大重连次数，停止重连');
      return;
    }

    this.reconnectAttempts++;
    console.log(`尝试重连 (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})...`);

    setTimeout(() => {
      if (this.userId) {
        this.connect(this.userId);
      }
    }, this.config.reconnectInterval);
  }

  /**
   * 通知连接状态变化
   */
  private notifyConnectionChange(connected: boolean): void {
    this.connectionListeners.forEach(listener => listener(connected));
  }
}

// 全局WebSocket客户端实例
let globalWebSocketClient: WebSocketClient | null = null;

/**
 * 获取WebSocket客户端实例（单例模式）
 */
export function getWebSocketClient(): WebSocketClient {
  if (!globalWebSocketClient) {
    globalWebSocketClient = new WebSocketClient();
  }
  return globalWebSocketClient;
}

/**
 * 初始化WebSocket连接
 */
export function initWebSocket(userId: number): WebSocketClient {
  const client = getWebSocketClient();
  client.connect(userId);
  return client;
}

/**
 * 断开WebSocket连接
 */
export function disconnectWebSocket(): void {
  if (globalWebSocketClient) {
    globalWebSocketClient.disconnect();
  }
}

/**
 * React Hook: 使用WebSocket
 */
export function useWebSocket() {
  const { user } = useAuth();
  const client = getWebSocketClient();

  // 当用户登录状态变化时，自动连接/断开WebSocket
  useEffect(() => {
    if (user?.id) {
      getWebSocketClient().connect(user.id);
    } else {
      getWebSocketClient().disconnect();
    }

    return () => {
      // 组件卸载时不自动断开，由应用统一管理
    };
  }, [user?.id]);

  return client;
}

// 导出常用消息类型
export const WSMessageType = MessageType;