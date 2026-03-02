'use client';

import React, { useState, useEffect } from 'react';
import {
  Card,
  Progress,
  Typography,
  Space,
  Tag,
  Timeline,
  Alert,
  Button,
  List,
  Badge,
  Tooltip,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  FileOutlined,
  VideoCameraOutlined,
  SoundOutlined,
  PictureOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useUpload, UploadTask, UploadStatus } from '@/services/upload';
import { useWebSocket, MessageType } from '@/services/websocket';

const { Title, Text } = Typography;

interface ProgressDisplayProps {
  taskId?: string;
  showDetails?: boolean;
  compact?: boolean;
}

const ProgressDisplay: React.FC<ProgressDisplayProps> = ({
  taskId,
  showDetails = true,
  compact = false,
}) => {
  const { getTask, getTasks } = useUpload();
  const wsClient = useWebSocket();

  const [tasks, setTasks] = useState<UploadTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<UploadTask | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<Record<string, any>>({});

  // 加载任务
  useEffect(() => {
    loadTasks();
    
    // 监听WebSocket消息
    const handleVideoProgress = (message: any) => {
      const { task_id, progress, message: statusMessage } = message.data;
      setAnalysisProgress(prev => ({
        ...prev,
        [task_id]: { progress, message: statusMessage },
      }));
    };

    const handleTaskCompleted = (message: any) => {
      const { task_id } = message.data;
      setAnalysisProgress(prev => ({
        ...prev,
        [task_id]: { progress: 100, message: '分析完成' },
      }));
      loadTasks(); // 重新加载任务
    };

    const handleTaskFailed = (message: any) => {
      const { task_id, error } = message.data;
      setAnalysisProgress(prev => ({
        ...prev,
        [task_id]: { progress: 0, message: `分析失败: ${error}`, error: true },
      }));
    };

    wsClient.on(MessageType.VIDEO_ANALYSIS_PROGRESS, handleVideoProgress);
    wsClient.on(MessageType.TASK_COMPLETED, handleTaskCompleted);
    wsClient.on(MessageType.TASK_FAILED, handleTaskFailed);

    return () => {
      wsClient.off(MessageType.VIDEO_ANALYSIS_PROGRESS, handleVideoProgress);
      wsClient.off(MessageType.TASK_COMPLETED, handleTaskCompleted);
      wsClient.off(MessageType.TASK_FAILED, handleTaskFailed);
    };
  }, []);

  // 如果有taskId，只显示特定任务
  useEffect(() => {
    if (taskId) {
      const task = getTask(taskId);
      setSelectedTask(task || null);
    }
  }, [taskId]);

  // 加载任务
  const loadTasks = () => {
    const allTasks = getTasks();
    setTasks(allTasks);
    
    if (!taskId && allTasks.length > 0) {
      setSelectedTask(allTasks[0]);
    }
  };

  // 获取状态图标
  const getStatusIcon = (status: UploadStatus) => {
    switch (status) {
      case UploadStatus.PENDING:
        return <LoadingOutlined style={{ color: '#d9d9d9' }} />;
      case UploadStatus.UPLOADING:
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case UploadStatus.PROCESSING:
        return <LoadingOutlined style={{ color: '#52c41a' }} />;
      case UploadStatus.COMPLETED:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case UploadStatus.FAILED:
        return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
      case UploadStatus.CANCELLED:
        return <CloseCircleOutlined style={{ color: '#d9d9d9' }} />;
      default:
        return <LoadingOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: UploadStatus) => {
    switch (status) {
      case UploadStatus.PENDING:
        return 'default';
      case UploadStatus.UPLOADING:
        return 'processing';
      case UploadStatus.PROCESSING:
        return 'processing';
      case UploadStatus.COMPLETED:
        return 'success';
      case UploadStatus.FAILED:
        return 'error';
      case UploadStatus.CANCELLED:
        return 'default';
      default:
        return 'default';
    }
  };

  // 获取状态文本
  const getStatusText = (status: UploadStatus) => {
    switch (status) {
      case UploadStatus.PENDING:
        return '等待中';
      case UploadStatus.UPLOADING:
        return '上传中';
      case UploadStatus.PROCESSING:
        return '处理中';
      case UploadStatus.COMPLETED:
        return '已完成';
      case UploadStatus.FAILED:
        return '失败';
      case UploadStatus.CANCELLED:
        return '已取消';
      default:
        return '未知';
    }
  };

  // 获取文件图标
  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v'].includes(ext || '')) {
      return <VideoCameraOutlined style={{ fontSize: 20, color: '#1890ff' }} />;
    }
    if (['mp3', 'wav', 'ogg', 'flac', 'aac'].includes(ext || '')) {
      return <SoundOutlined style={{ fontSize: 20, color: '#52c41a' }} />;
    }
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext || '')) {
      return <PictureOutlined style={{ fontSize: 20, color: '#f5222d' }} />;
    }
    if (['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'].includes(ext || '')) {
      return <FileTextOutlined style={{ fontSize: 20, color: '#fa8c16' }} />;
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

  // 获取分析进度
  const getAnalysisProgress = (taskId: string) => {
    return analysisProgress[taskId] || { progress: 0, message: '等待分析...' };
  };

  // 渲染任务进度
  const renderTaskProgress = (task: UploadTask) => {
    const analysis = getAnalysisProgress(task.upload_id);
    
    return (
      <div style={{ width: '100%' }}>
        {/* 上传进度 */}
        {task.status === UploadStatus.UPLOADING && (
          <div style={{ marginBottom: 16 }}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary">上传进度</Text>
                <Text strong>{task.progress || 0}%</Text>
              </div>
              <Progress
                percent={task.progress || 0}
                status="active"
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            </Space>
          </div>
        )}

        {/* 分析进度 */}
        {(task.status === UploadStatus.PROCESSING || analysis.progress > 0) && (
          <div style={{ marginBottom: 16 }}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary">分析进度</Text>
                <Text strong>{analysis.progress}%</Text>
              </div>
              <Progress
                percent={analysis.progress}
                status={analysis.error ? 'exception' : 'active'}
                strokeColor={analysis.error ? undefined : {
                  '0%': '#52c41a',
                  '100%': '#87d068',
                }}
              />
              {analysis.message && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {analysis.message}
                </Text>
              )}
            </Space>
          </div>
        )}

        {/* 分片信息 */}
        {showDetails && task.total_chunks > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              分片进度: {task.uploaded_chunks?.length || 0}/{task.total_chunks}
            </Text>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              {Array.from({ length: task.total_chunks }, (_, i) => i).map((chunkIndex) => (
                <Tooltip key={chunkIndex} title={`分片 ${chunkIndex + 1}`}>
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 2,
                      backgroundColor: task.uploaded_chunks?.includes(chunkIndex)
                        ? '#52c41a'
                        : '#f0f0f0',
                      margin: 1,
                    }}
                  />
                </Tooltip>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // 紧凑模式
  if (compact && selectedTask) {
    return (
      <Card size="small" style={{ width: '100%' }}>
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {getFileIcon(selectedTask.file_name)}
            <Text ellipsis style={{ flex: 1 }}>
              {selectedTask.file_name}
            </Text>
            <Tag color={getStatusColor(selectedTask.status)} size="small">
              {getStatusText(selectedTask.status)}
            </Tag>
          </div>
          {renderTaskProgress(selectedTask)}
        </Space>
      </Card>
    );
  }

  // 完整模式
  return (
    <div className="progress-display-container">
      <Card
        title={
          <Space>
            <PlayCircleOutlined />
            <span>任务进度</span>
            <Badge
              count={tasks.filter(t => 
                t.status === UploadStatus.UPLOADING || 
                t.status === UploadStatus.PROCESSING
              ).length}
              style={{ backgroundColor: '#52c41a' }}
            />
          </Space>
        }
      >
        {tasks.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <PlayCircleOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
            <Text type="secondary">暂无进行中的任务</Text>
          </div>
        ) : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {/* 任务选择 */}
            {tasks.length > 1 && (
              <div>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>
                  选择任务:
                </Text>
                <Space wrap>
                  {tasks.map(task => (
                    <Button
                      key={task.upload_id}
                      type={selectedTask?.upload_id === task.upload_id ? 'primary' : 'default'}
                      size="small"
                      onClick={() => setSelectedTask(task)}
                      icon={getStatusIcon(task.status)}
                    >
                      {task.file_name}
                    </Button>
                  ))}
                </Space>
              </div>
            )}

            {/* 当前任务详情 */}
            {selectedTask && (
              <Card size="small">
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  {/* 任务头部 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {getFileIcon(selectedTask.file_name)}
                    <div style={{ flex: 1 }}>
                      <Text strong style={{ display: 'block' }}>
                        {selectedTask.file_name}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        大小: {formatFileSize(selectedTask.file_size)} | 
                        创建: {new Date(selectedTask.created_at).toLocaleString('zh-CN')}
                      </Text>
                    </div>
                    <Tag color={getStatusColor(selectedTask.status)}>
                      {getStatusIcon(selectedTask.status)} {getStatusText(selectedTask.status)}
                    </Tag>
                  </div>

                  {/* 进度显示 */}
                  {renderTaskProgress(selectedTask)}

                  {/* 时间线 */}
                  {showDetails && (
                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        处理流程:
                      </Text>
                      <Timeline
                        items={[
                          {
                            color: selectedTask.status !== UploadStatus.PENDING ? 'green' : 'gray',
                            children: '上传准备',
                          },
                          {
                            color: selectedTask.uploaded_chunks?.length > 0 ? 'green' : 'gray',
                            children: `分片上传 (${selectedTask.uploaded_chunks?.length || 0}/${selectedTask.total_chunks})`,
                          },
                          {
                            color: selectedTask.status === UploadStatus.PROCESSING ? 'blue' : 
                                  selectedTask.status === UploadStatus.COMPLETED ? 'green' : 'gray',
                            children: '视频分析',
                          },
                          {
                            color: selectedTask.status === UploadStatus.COMPLETED ? 'green' : 'gray',
                            children: '知识提取',
                          },
                          {
                            color: selectedTask.status === UploadStatus.COMPLETED ? 'green' : 'gray',
                            children: '完成处理',
                          },
                        ]}
                      />
                    </div>
                  )}
                </Space>
              </Card>
            )}

            {/* 所有任务概览 */}
            {showDetails && tasks.length > 1 && (
              <div>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>
                  所有任务:
                </Text>
                <List
                  size="small"
                  dataSource={tasks}
                  renderItem={task => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={getFileIcon(task.file_name)}
                        title={
                          <Space>
                            <Text>{task.file_name}</Text>
                            <Tag color={getStatusColor(task.status)} size="small">
                              {getStatusText(task.status)}
                            </Tag>
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size={2}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              进度: {task.progress || 0}% | 
                              大小: {formatFileSize(task.file_size)}
                            </Text>
                            {task.status === UploadStatus.UPLOADING && (
                              <Progress
                                percent={task.progress || 0}
                                size="small"
                                showInfo={false}
                              />
                            )}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </div>
            )}
          </Space>
        )}
      </Card>
    </div>
  );
};

export default ProgressDisplay;