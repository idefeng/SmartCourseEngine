'use client'

import { useState, useEffect, useRef } from 'react'
import { 
  Layout, 
  Card, 
  Table, 
  Button, 
  Space, 
  Input, 
  Tag, 
  Modal, 
  Form, 
  Select, 
  Upload,
  Progress,
  message,
  Popconfirm,
  Tooltip,
  Badge,
  Avatar,
  Row,
  Col,
  Statistic,
  Timeline,
  Descriptions,
} from 'antd'
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  EyeOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  UploadOutlined,
  VideoCameraOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd/es/upload/interface'
import dayjs from 'dayjs'
import { useRouter } from 'next/navigation'

const { Header, Content } = Layout
const { Search } = Input
const { Option } = Select

interface Video {
  id: string
  title: string
  description: string
  file_path: string
  thumbnail_url: string
  duration: number
  file_size: number
  format: string
  status: 'uploading' | 'processing' | 'completed' | 'failed'
  progress: number
  course_id: number | null
  created_at: string
  updated_at: string
  analysis_result: any
  transcript: any
}

export default function VideosPage() {
  const router = useRouter()
  const [searchText, setSearchText] = useState('')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [form] = Form.useForm()
  const queryClient = useQueryClient()

  // 获取视频列表
  const { data: videosData, isLoading, refetch } = useQuery({
    queryKey: ['videos', searchText],
    queryFn: () => api.videos.getVideos({ search: searchText }),
  })

  const videos = videosData?.data?.items || []

  // 上传视频
  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => 
      api.videos.uploadVideo(formData, (progress) => {
        setUploadProgress(progress)
      }),
    onSuccess: () => {
      message.success('视频上传成功')
      queryClient.invalidateQueries({ queryKey: ['videos'] })
      handleUploadCancel()
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '上传失败')
      setUploadProgress(0)
    },
  })

  // 分析视频
  const analyzeMutation = useMutation({
    mutationFn: ({ videoId, options }: { videoId: string; options?: any }) => 
      api.videos.analyzeVideo(videoId, options),
    onSuccess: () => {
      message.success('视频分析任务已开始')
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '分析失败')
    },
  })

  // 删除视频
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.videos.deleteVideo(id),
    onSuccess: () => {
      message.success('视频删除成功')
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '删除失败')
    },
  })

  const handleSearch = (value: string) => {
    setSearchText(value)
  }

  const handleUpload = () => {
    setIsUploadModalOpen(true)
  }

  const handleUploadCancel = () => {
    setIsUploadModalOpen(false)
    setUploadProgress(0)
    setFileList([])
    form.resetFields()
  }

  const handleUploadSubmit = () => {
    if (fileList.length === 0) {
      message.warning('请选择要上传的视频文件')
      return
    }

    const formData = new FormData()
    const file = fileList[0].originFileObj
    
    if (!file) {
      message.error('文件无效')
      return
    }

    formData.append('video', file)
    
    const values = form.getFieldsValue()
    Object.keys(values).forEach(key => {
      if (values[key] !== undefined) {
        formData.append(key, values[key])
      }
    })

    uploadMutation.mutate(formData)
  }

  const handleAnalyze = (videoId: string) => {
    analyzeMutation.mutate({ videoId })
  }

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id)
  }

  const handleViewDetails = (video: Video) => {
    setSelectedVideo(video)
    setIsDetailModalOpen(true)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    } else {
      return `${minutes}:${secs.toString().padStart(2, '0')}`
    }
  }

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'uploading':
        return { color: 'blue', text: '上传中', icon: <LoadingOutlined /> }
      case 'processing':
        return { color: 'orange', text: '分析中', icon: <LoadingOutlined /> }
      case 'completed':
        return { color: 'green', text: '已完成', icon: <CheckCircleOutlined /> }
      case 'failed':
        return { color: 'red', text: '失败', icon: <CloseCircleOutlined /> }
      default:
        return { color: 'default', text: '未知', icon: null }
    }
  }

  const columns: ColumnsType<Video> = [
    {
      title: '视频',
      dataIndex: 'thumbnail_url',
      key: 'thumbnail',
      width: 100,
      render: (url, record) => (
        <div style={{ position: 'relative' }}>
          <Avatar 
            shape="square" 
            size={64} 
            src={url || '/default-video.png'}
            icon={<VideoCameraOutlined />}
          />
          {record.duration && (
            <div style={{
              position: 'absolute',
              bottom: 4,
              right: 4,
              background: 'rgba(0,0,0,0.7)',
              color: 'white',
              padding: '2px 4px',
              borderRadius: 4,
              fontSize: 10,
            }}>
              {formatDuration(record.duration)}
            </div>
          )}
        </div>
      ),
    },
    {
      title: '视频信息',
      dataIndex: 'title',
      key: 'title',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500, marginBottom: 4 }}>{text}</div>
          <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
            {record.description?.substring(0, 80)}...
          </div>
          <Space size={[4, 0]} wrap>
            <Tag icon={<ClockCircleOutlined />} size="small">
              {formatDuration(record.duration || 0)}
            </Tag>
            <Tag size="small">{record.format || 'mp4'}</Tag>
            <Tag size="small">{formatFileSize(record.file_size || 0)}</Tag>
          </Space>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status, record) => {
        const config = getStatusConfig(status)
        return (
          <div>
            <Badge 
              status={config.color as any} 
              text={config.text}
            />
            {record.progress !== undefined && record.progress < 100 && (
              <Progress 
                percent={record.progress} 
                size="small" 
                style={{ marginTop: 4 }}
              />
            )}
          </div>
        )
      },
    },
    {
      title: '关联课程',
      dataIndex: 'course_id',
      key: 'course',
      width: 100,
      render: (courseId) => (
        courseId ? (
          <Tag color="blue">课程 #{courseId}</Tag>
        ) : (
          <Tag color="default">未关联</Tag>
        )
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date) => dayjs(date).format('MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>
          {record.status === 'completed' && (
            <Tooltip title="播放视频">
              <Button 
                type="text" 
                icon={<PlayCircleOutlined />}
                onClick={() => window.open(record.file_path, '_blank')}
              />
            </Tooltip>
          )}
          {record.status === 'completed' && !record.analysis_result && (
            <Tooltip title="开始分析">
              <Button 
                type="text" 
                icon={<FileTextOutlined />}
                onClick={() => handleAnalyze(record.id)}
                loading={analyzeMutation.isPending}
              />
            </Tooltip>
          )}
          <Popconfirm
            title="确定要删除这个视频吗？"
            description="删除后无法恢复，相关的分析结果也会被删除。"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button 
                type="text" 
                danger 
                icon={<DeleteOutlined />} 
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const videoStats = {
    total: videos.length,
    uploading: videos.filter(v => v.status === 'uploading').length,
    processing: videos.filter(v => v.status === 'processing').length,
    completed: videos.filter(v => v.status === 'completed').length,
    failed: videos.filter(v => v.status === 'failed').length,
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ 
        background: '#fff', 
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
      }}>
        <div>
          <h2 style={{ margin: 0 }}>视频管理</h2>
          <p style={{ margin: 0, color: '#666', fontSize: 14 }}>
            管理所有视频文件，包括上传、分析和删除视频
          </p>
        </div>
        <Space>
          <Search
            placeholder="搜索视频标题或描述"
            allowClear
            enterButton={<SearchOutlined />}
            onSearch={handleSearch}
            style={{ width: 300 }}
          />
          <Button icon={<FilterOutlined />}>筛选</Button>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
          <Button 
            type="primary" 
            icon={<UploadOutlined />}
            onClick={() => router.push('/videos/upload')}
          >
            高级上传
          </Button>
          <Button 
            icon={<PlusOutlined />}
            onClick={handleUpload}
          >
            快速上传
          </Button>
        </Space>
      </Header>
      <Content style={{ margin: '24px' }}>
        {/* 统计卡片 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="视频总数"
                value={videoStats.total}
                prefix={<VideoCameraOutlined />}
                valueStyle={{ color: '#3b82f6' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="上传中"
                value={videoStats.uploading}
                prefix={<LoadingOutlined />}
                valueStyle={{ color: '#3b82f6' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="分析中"
                value={videoStats.processing}
                prefix={<LoadingOutlined />}
                valueStyle={{ color: '#f59e0b' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="已完成"
                value={videoStats.completed}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#10b981' }}
              />
            </Card>
          </Col>
        </Row>

        <Card>
          <Table
            columns={columns}
            dataSource={videos}
            rowKey="id"
            loading={isLoading}
            pagination={{
              total: videosData?.data?.total || 0,
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条记录`,
            }}
          />
        </Card>
      </Content>

      {/* 上传视频模态框 */}
      <Modal
        title="上传视频"
        open={isUploadModalOpen}
        onCancel={handleUploadCancel}
        onOk={handleUploadSubmit}
        confirmLoading={uploadMutation.isPending}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="title"
            label="视频标题"
            rules={[{ required: true, message: '请输入视频标题' }]}
          >
            <Input placeholder="请输入视频标题" />
          </Form.Item>

          <Form.Item
            name="description"
            label="视频描述"
          >
            <Input.TextArea 
              placeholder="请输入视频描述" 
              rows={3}
            />
          </Form.Item>

          <Form.Item
            name="course_id"
            label="关联课程"
          >
            <Select placeholder="请选择关联课程" allowClear>
              <Option value={1}>Python编程入门</Option>
              <Option value={2}>机器学习基础</Option>
              <Option value={3}>深度学习实战</Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="视频文件"
            required
          >
            <Upload
              fileList={fileList}
              beforeUpload={(file) => {
                setFileList([file])
                return false
              }}
              onRemove={() => {
                setFileList([])
              }}
              maxCount={1}
              accept="video/*"
            >
              <Button icon={<UploadOutlined />}>选择视频文件</Button>
            </Upload>
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              支持格式: MP4, AVI, MOV, WMV, FLV, MKV
            </div>
          </Form.Item>

          {uploadProgress > 0 && (
            <Form.Item label="上传进度">
              <Progress percent={uploadProgress} />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 视频详情模态框 */}
      <Modal
        title="视频详情"
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={null}
        width={800}
      >
        {selectedVideo && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="视频标题" span={2}>
                {selectedVideo.title}
              </Descriptions.Item>
              <Descriptions.Item label="视频描述">
                {selectedVideo.description}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge 
                  status={getStatusConfig(selectedVideo.status).color as any} 
                  text={getStatusConfig(selectedVideo.status).text}
                />
              </Descriptions.Item>
              <Descriptions.Item label="时长">
                {formatDuration(selectedVideo.duration || 0)}
              </Descriptions.Item>
              <Descriptions.Item label="文件大小">
                {formatFileSize(selectedVideo.file_size || 0)}
              </Descriptions.Item>
              <Descriptions.Item label="格式">
                {selectedVideo.format || 'mp4'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedVideo.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {dayjs(selectedVideo.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="文件路径" span={2}>
                {selectedVideo.file_path}
              </Descriptions.Item>
            </Descriptions>

            {selectedVideo.analysis_result && (
              <Card title="分析结果" style={{ marginTop: 16 }}>
                <Timeline>
                  <Timeline.Item color="green">
                    <p>语音识别完成</p>
                    <p style={{ fontSize: 12, color: '#666' }}>
                      识别时长: {selectedVideo.analysis_result.transcript?.duration || 0}秒
                    </p>
                  </Timeline.Item>
                  <Timeline.Item color="green">
                    <p>关键帧提取完成</p>
                    <p style={{ fontSize: 12, color: '#666' }}>
                      提取数量: {selectedVideo.analysis_result.keyframes?.length || 0}个
                    </p>
                  </Timeline.Item>
                  <Timeline.Item color="green">
                    <p>场景检测完成</p>
                    <p style={{ fontSize: 12, color: '#666' }}>
                      场景数量: {selectedVideo.analysis_result.scenes?.length || 0}个
                    </p>
                  </Timeline.Item>
                </Timeline>
              </Card>
            )}

            {selectedVideo.transcript && (
              <Card title="转录文本" style={{ marginTop: 16 }}>
                <div style={{ maxHeight: 200, overflowY: 'auto', padding: 8 }}>
                  {selectedVideo.transcript.text || '暂无转录文本'}
                </div>
              </Card>
            )}

            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Space>
                <Button 
                  type="primary" 
                  icon={<PlayCircleOutlined />}
                  onClick={() => window.open(selectedVideo.file_path, '_blank')}
                >
                  播放视频
                </Button>
                {!selectedVideo.analysis_result && (
                  <Button 
                    icon={<FileTextOutlined />}
                    onClick={() => {
                      handleAnalyze(selectedVideo.id)
                      setIsDetailModalOpen(false)
                    }}
                    loading={analyzeMutation.isPending}
                  >
                    开始分析
                  </Button>
                )}
              </Space>
            </div>
          </div>
        )}
      </Modal>
    </Layout>
  )
}
