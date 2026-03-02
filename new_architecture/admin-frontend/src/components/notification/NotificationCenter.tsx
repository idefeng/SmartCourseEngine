'use client';

import React, { useState, useEffect } from 'react';
import {
  Badge,
  Button,
  Card,
  List,
  Typography,
  Space,
  Tag,
  Dropdown,
  MenuProps,
  Popover,
  Empty,
  Divider,
} from 'antd';
import {
  BellOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { useWebSocket, MessageType } from '@/services/websocket';

const { Title, Text } = Typography;

// 通知类型
export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error',
  SYSTEM = 'system',
  UPLOAD = 'upload',
  ANALYSIS = 'analysis',
}

// 通知接口
export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  data?: Record<string, any>;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface NotificationCenterProps {
  maxNotifications?: number;
  autoClear?: boolean;
  autoClearDelay?: number; // 毫秒
}

const NotificationCenter: React.FC<NotificationCenterProps> = ({
  maxNotifications = 50,
  autoClear = true,
  autoClearDelay = 10000, // 10秒
}) => {
  const wsClient = useWebSocket();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [visible, setVisible] = useState(false);

  // 初始化WebSocket监听器
  useEffect(() => {
    // 系统通知
    const handleSystemNotification = (message: any) => {
      const { title, message: msg, level } = message.data;
      addNotification({
        type: level === 'error' ? NotificationType.ERROR : 
              level === 'warning' ? NotificationType.WARNING : 
              level === 'success' ? NotificationType.SUCCESS : 
              NotificationType.INFO,
        title: title || '系统通知',
        message: msg,
        data: message.data,
      });
    };

    // 任务完成
    const handleTaskCompleted = (message: any) => {
      const { task_id, task_type, result } = message.data;
      addNotification({
        type: NotificationType.SUCCESS,
        title: '任务完成',
        message: `${task_type === 'video_analysis' ? '视频分析' : '任务'}已完成`,
        data: message.data,
        action: {
          label: '查看详情',
          onClick: () => {
            console.log('查看任务详情:', task_id);
            // 这里可以跳转到任务详情页面
          },
        },
      });
    };

    // 任务失败
    const handleTaskFailed = (message: any) => {
      const { task_id, task_type, error } = message.data;
      addNotification({
        type: NotificationType.ERROR,
        title: '任务失败',
        message: `${task_type === 'video_analysis' ? '视频分析' : '任务'}失败: ${error}`,
        data: message.data,
        action: {
          label: '重试',
          onClick: () => {
            console.log('重试任务:', task_id);
            // 这里可以触发重试逻辑
          },
        },
      });
    };

    // 视频上传进度
    const handleVideoUploadProgress = (message: any) => {
      const { task_id, progress, file_name } = message.data;
      if (progress === 100) {
        addNotification({
          type: NotificationType.SUCCESS,
          title: '上传完成',
          message: `文件 "${file_name}" 上传完成`,
          data: message.data,
        });
      }
    };

    // 视频分析开始
    const handleVideoAnalysisStarted = (message: any) => {
      const { task_id, video_id } = message.data;
      addNotification({
        type: NotificationType.INFO,
        title: '分析开始',
        message: '视频分析任务已开始',
        data: message.data,
      });
    };

    // 知识图谱更新
    const handleKnowledgeGraphUpdated = (message: any) => {
      const { graph_id, node_count, edge_count } = message.data;
      addNotification({
        type: NotificationType.SUCCESS,
        title: '知识图谱更新',
        message: `知识图谱已更新，包含 ${node_count} 个节点和 ${edge_count} 条关系`,
        data: message.data,
      });
    };

    // 注册监听器
    wsClient.on(MessageType.SYSTEM_NOTIFICATION, handleSystemNotification);
    wsClient.on(MessageType.TASK_COMPLETED, handleTaskCompleted);
    wsClient.on(MessageType.TASK_FAILED, handleTaskFailed);
    wsClient.on(MessageType.VIDEO_UPLOAD_PROGRESS, handleVideoUploadProgress);
    wsClient.on(MessageType.VIDEO_ANALYSIS_STARTED, handleVideoAnalysisStarted);
    wsClient.on(MessageType.KNOWLEDGE_GRAPH_UPDATED, handleKnowledgeGraphUpdated);

    return () => {
      wsClient.off(MessageType.SYSTEM_NOTIFICATION, handleSystemNotification);
      wsClient.off(MessageType.TASK_COMPLETED, handleTaskCompleted);
      wsClient.off(MessageType.TASK_FAILED, handleTaskFailed);
      wsClient.off(MessageType.VIDEO_UPLOAD_PROGRESS, handleVideoUploadProgress);
      wsClient.off(MessageType.VIDEO_ANALYSIS_STARTED, handleVideoAnalysisStarted);
      wsClient.off(MessageType.KNOWLEDGE_GRAPH_UPDATED, handleKnowledgeGraphUpdated);
    };
  }, []);

  // 自动清理通知
  useEffect(() => {
    if (!autoClear || notifications.length === 0) return;

    const timer = setInterval(() => {
      setNotifications(prev => {
        const now = Date.now();
        return prev.filter(notification => {
          const notificationTime = new Date(notification.timestamp).getTime();
          return now - notificationTime < autoClearDelay;
        });
      });
    }, 1000); // 每秒检查一次

    return () => clearInterval(timer);
  }, [notifications, autoClear, autoClearDelay]);

  // 更新未读计数
  useEffect(() => {
    const unread = notifications.filter(n => !n.read).length;
    setUnreadCount(unread);
  }, [notifications]);

  // 添加通知
  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      read: false,
    };

    setNotifications(prev => {
      const updated = [newNotification, ...prev];
      // 限制通知数量
      if (updated.length > maxNotifications) {
        return updated.slice(0, maxNotifications);
      }
      return updated;
    });
  };

  // 标记为已读
  const markAsRead = (id: string) => {
    setNotifications(prev =>
      prev.map(notification =>
        notification.id === id ? { ...notification, read: true } : notification
      )
    );
  };

  // 标记所有为已读
  const markAllAsRead = () => {
    setNotifications(prev =>
      prev.map(notification => ({ ...notification, read: true }))
    );
  };

  // 删除通知
  const deleteNotification = (id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  };

  // 清空所有通知
  const clearAllNotifications = () => {
    setNotifications([]);
  };

  // 获取通知图标
  const getNotificationIcon = (type: NotificationType) => {
    switch (type) {
      case NotificationType.SUCCESS:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case NotificationType.ERROR:
        return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
      case NotificationType.WARNING:
        return <WarningOutlined style={{ color: '#fa8c16' }} />;
      case NotificationType.INFO:
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
      case NotificationType.UPLOAD:
        return <CheckCircleOutlined style={{ color: '#1890ff' }} />;
      case NotificationType.ANALYSIS:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#666' }} />;
    }
  };

  // 获取通知标签颜色
  const getNotificationTagColor = (type: NotificationType) => {
    switch (type) {
      case NotificationType.SUCCESS:
        return 'success';
      case NotificationType.ERROR:
        return 'error';
      case NotificationType.WARNING:
        return 'warning';
      case NotificationType.INFO:
        return 'processing';
      case NotificationType.UPLOAD:
        return 'blue';
      case NotificationType.ANALYSIS:
        return 'green';
      default:
        return 'default';
    }
  };

  // 格式化时间
  const formatTime = (timestamp: string) => {
    const now = Date.now();
    const notificationTime = new Date(timestamp).getTime();
    const diff = now - notificationTime;

    if (diff < 60000) {
      return '刚刚';
    } else if (diff < 3600000) {
      return `${Math.floor(diff / 60000)}分钟前`;
    } else if (diff < 86400000) {
      return `${Math.floor(diff / 3600000)}小时前`;
    } else {
      return new Date(timestamp).toLocaleDateString('zh-CN');
    }
  };

  // 下拉菜单项
  const dropdownItems: MenuProps['items'] = [
    {
      key: 'mark-all-read',
      icon: <CheckOutlined />,
      label: '标记所有为已读',
      onClick: markAllAsRead,
      disabled: unreadCount === 0,
    },
    {
      key: 'clear-all',
      icon: <DeleteOutlined />,
      label: '清空所有通知',
      onClick: clearAllNotifications,
      disabled: notifications.length === 0,
    },
    {
      type: 'divider',
    },
    ...notifications.slice(0, 5).map((notification, index) => ({
      key: `notification-${index}`,
      label: (
        <Space direction="vertical" size={2} style={{ width: 250 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {getNotificationIcon(notification.type)}
            <Text strong style={{ flex: 1 }}>{notification.title}</Text>
            {!notification.read && (
              <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#1890ff' }} />
            )}
          </div>
          <Text type="secondary" ellipsis style={{ fontSize: 12 }}>
            {notification.message}
          </Text>
          <Text type="secondary" style={{ fontSize: 10 }}>
            {formatTime(notification.timestamp)}
          </Text>
        </Space>
      ),
      onClick: () => markAsRead(notification.id),
    })),
    notifications.length > 5 && {
      key: 'view-all',
      label: (
        <div style={{ textAlign: 'center', padding: '8px 0' }}>
          <Text type="secondary">查看全部 ({notifications.length})</Text>
        </div>
      ),
      onClick: () => setVisible(true),
    },
  ].filter(Boolean) as MenuProps['items'];

  // 通知内容
  const notificationContent = (
    <Card
      size="small"
      style={{ width: 400, maxHeight: 500, overflow: 'auto' }}
      title={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text strong>通知中心</Text>
          <Space>
            <Button
              type="text"
              size="small"
              onClick={markAllAsRead}
              disabled={unreadCount === 0}
            >
              全部已读
            </Button>
            <Button
              type="text"
              size="small"
              danger
              onClick={clearAllNotifications}
              disabled={notifications.length === 0}
            >
              清空
            </Button>
          </Space>
        </Space>
      }
    >
      {notifications.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无通知"
          style={{ margin: '40px 0' }}
        />
      ) : (
        <List
          size="small"
          dataSource={notifications}
          renderItem={(notification) => (
            <List.Item
              style={{
                backgroundColor: notification.read ? 'transparent' : '#f6ffed',
                padding: '12px',
                borderRadius: 4,
                marginBottom: 8,
              }}
              actions={[
                <Button
                  key="read"
                  type="text"
                  size="small"
                  onClick={() => markAsRead(notification.id)}
                  disabled={notification.read}
                >
                  已读
                </Button>,
                <Button
                  key="delete"
                  type="text"
                  size="small"
                  danger
                  onClick={() => deleteNotification(notification.id)}
                >
                  删除
                </Button>,
              ]}
            >
              <List.Item.Meta
                avatar={getNotificationIcon(notification.type)}
                title={
                  <Space>
                    <Text strong>{notification.title}</Text>
                    <Tag color={getNotificationTagColor(notification.type)} size="small">
                      {notification.type}
                    </Tag>
                    {!notification.read && (
                      <Tag color="blue" size="small">
                        未读
                      </Tag>
                    )}
                  </Space>
                }
                description={
                  <Space direction="vertical" size={4} style={{ width: '100%' }}>
                    <Text>{notification.message}</Text>
                    <Space>
                      <ClockCircleOutlined style={{ fontSize: 12 }} />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {formatTime(notification.timestamp)}
                      </Text>
                    </Space>
                    {notification.action && (
                      <Button
                        type="link"
                        size="small"
                        onClick={notification.action.onClick}
                        style={{ padding: 0 }}
                      >
                        {notification.action.label}
                      </Button>
                    )}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );

  return (
    <div className="notification-center">
      <Popover
        content={notificationContent}
        title={null}
        trigger="click"
        open={visible}
        onOpenChange={setVisible}
        placement="bottomRight"
        overlayStyle={{ padding: 0 }}
      >
        <Badge count={unreadCount} overflowCount={99}>
          <Button
            type="text"
            icon={<BellOutlined />}
            style={{ fontSize: 18 }}
          />
        </Badge>
      </Popover>

      {/* 也可以使用Dropdown，但Popover提供更好的自定义 */}
      {/* <Dropdown
        menu={{ items: dropdownItems }}
        trigger={['click']}
        placement="bottomRight"
        overlayStyle={{ width: 300 }}
      >
        <Badge count={unreadCount} overflowCount={99}>
          <Button
            type="text"
            icon={<BellOutlined />}
            style={{ fontSize: 18 }}
          />
        </Badge>
      </Dropdown> */}
    </div>
  );
};

export default NotificationCenter;