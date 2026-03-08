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
  App,
  Popconfirm,
  Tooltip,
  Badge,
  Avatar,
  Row,
  Col,
  Statistic,
  Timeline,
  Descriptions,
  Typography,
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
const { Title, Text } = Typography

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
  pipeline_stage?: string
  knowledge_points_count?: number
}

export default function VideosPage() {
  const router = useRouter()
  const [searchText, setSearchText] = useState('')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null)
  const [isVideoPlayerOpen, setIsVideoPlayerOpen] = useState(false)
  const [currentVideoUrl, setCurrentVideoUrl] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [form] = Form.useForm()
  const queryClient = useQueryClient()
  const { message } = App.useApp()

  // 获取视频列表
  const { data: videosData, isLoading, refetch } = useQuery({
    queryKey: ['videos', searchText],
    queryFn: () => api.videos.getVideos({ search: searchText }),
    refetchInterval: 5000,
  })

  const videos: Video[] = (videosData as any)?.items || (videosData as any)?.data?.items || []

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
    const file = fileList[0].originFileObj || (fileList[0] as unknown as File)

    if (!file || !(file instanceof File)) {
      message.error('文件无效，请重新选择')
      return
    }

    // 检查文件大小 (2GB)
    const MAX_SIZE = 2 * 1024 * 1024 * 1024
    if (file.size > MAX_SIZE) {
      message.error(`视频文件大小 (${formatFileSize(file.size)}) 已超过 2GB 限制`)
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
        return { color: 'processing', text: '上传中', icon: <LoadingOutlined />, class: 'text-blue-600 bg-blue-50' }
      case 'processing':
        return { color: 'warning', text: '分析中', icon: <LoadingOutlined />, class: 'text-amber-600 bg-amber-50' }
      case 'completed':
        return { color: 'success', text: '已完成', icon: <CheckCircleOutlined />, class: 'text-emerald-600 bg-emerald-50' }
      case 'failed':
        return { color: 'error', text: '失败', icon: <CloseCircleOutlined />, class: 'text-red-600 bg-red-50' }
      default:
        return { color: 'default', text: '未知', icon: null, class: 'text-gray-600 bg-gray-50' }
    }
  }

  const getPipelineText = (video: Video) => {
    if (video.status === 'processing') {
      if (video.pipeline_stage === 'analyzing') return '视频转录中...'
      if (video.pipeline_stage === 'knowledge_processing') return '知识提取中...'
      if (video.pipeline_stage === 'knowledge_completed') return '知识提取完成'
      return '处理中'
    }
    if (video.status === 'completed') {
      const count = video.knowledge_points_count ?? video.analysis_result?.knowledge_points?.length ?? 0
      if (count > 0) return `知识点已生成（${count}）`
      return '分析已完成'
    }
    return ''
  }

  const columns: ColumnsType<Video> = [
    {
      title: '视频',
      dataIndex: 'thumbnail_url',
      key: 'thumbnail',
      width: 140,
      render: (url, record) => (
        <div className="relative group cursor-pointer overflow-hidden rounded-xl shadow-md border border-slate-100 w-28 h-[72px] bg-slate-50 flex items-center justify-center">
          <img
            src={url || '/default-video.svg'}
            alt={record.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700 ease-out"
          />
          {/* 装饰性罩层 */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-60 group-hover:opacity-40 transition-opacity duration-300" />

          <div className="absolute inset-0 bg-indigo-600/10 group-hover:bg-indigo-600/30 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100 duration-500">
            <PlayCircleOutlined className="text-white text-3xl drop-shadow-lg transform scale-90 group-hover:scale-100 transition-transform duration-300" />
          </div>

          {(record.duration || 0) > 0 && (
            <div className="absolute bottom-1.5 right-1.5 bg-black/80 backdrop-blur-sm text-white px-1.5 py-0.5 rounded-md text-[9px] font-black tracking-tight border border-white/10">
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
        <div className="max-w-md">
          <div className="font-bold text-slate-800 text-base mb-1 line-clamp-1">{text}</div>
          <div className="text-xs text-slate-500 mb-2 line-clamp-2">
            {record.description || '暂无描述'}
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600">
              <ClockCircleOutlined className="mr-1" /> {formatDuration(record.duration || 0)}
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-50 text-indigo-600 uppercase">
              {record.format || 'mp4'}
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600">
              {formatFileSize(record.file_size || 0)}
            </span>
          </div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 180,
      render: (status, record) => {
        const config = getStatusConfig(status)
        return (
          <div className="space-y-2">
            <Badge
              status={config.color as any}
              text={<span className="font-bold text-sm">{config.text}</span>}
            />
            {getPipelineText(record) && (
              <div className="text-[11px] text-slate-400 font-medium">
                {getPipelineText(record)}
              </div>
            )}
            {record.progress !== undefined && record.progress < 100 && (
              <Progress
                percent={record.progress}
                size="small"
                strokeColor="#6366f1"
                trailColor="#f1f5f9"
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
      width: 120,
      render: (courseId) => (
        courseId ? (
          <div className="inline-flex items-center px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 text-xs font-bold border border-blue-100">
            #{courseId} 课程
          </div>
        ) : (
          <div className="text-slate-300 text-xs italic">未关联</div>
        )
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      render: (date) => (
        <div className="text-slate-500 text-xs font-medium">
          {dayjs(date).format('YYYY-MM-DD')}<br />
          <span className="opacity-60">{dayjs(date).format('HH:mm:ss')}</span>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_, record) => (
        <div className="flex items-center space-x-1">
          <Tooltip title="查看详情">
            <Button
              type="text"
              size="large"
              icon={<EyeOutlined className="text-slate-400 hover:text-indigo-500" />}
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>
          {record.status === 'completed' && (
            <Tooltip title="播放视频">
              <Button
                type="text"
                size="large"
                icon={<PlayCircleOutlined className="text-slate-400 hover:text-emerald-500" />}
                onClick={() => {
                  const path = record.file_path;
                  const url = path.startsWith('http') ? path : `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001'}${path}`;
                  setCurrentVideoUrl(url);
                  setIsVideoPlayerOpen(true);
                }}
              />
            </Tooltip>
          )}
          {record.status === 'completed' && !record.analysis_result && (
            <Tooltip title="开始分析">
              <Button
                type="text"
                size="large"
                icon={<FileTextOutlined className="text-slate-400 hover:text-orange-500" />}
                onClick={() => handleAnalyze(record.id)}
                loading={analyzeMutation.isPending}
              />
            </Tooltip>
          )}
          <Popconfirm
            title="删除视频"
            description="确定要删除吗？分析结果也将不可恢复。"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除">
              <Button
                type="text"
                size="large"
                danger
                icon={<DeleteOutlined className="opacity-50 hover:opacity-100" />}
              />
            </Tooltip>
          </Popconfirm>
        </div>
      ),
    },
  ]

  const videoStats = [
    { title: '视频总数', value: videos.length, icon: <VideoCameraOutlined />, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { title: '上传中', value: videos.filter(v => v.status === 'uploading').length, icon: <LoadingOutlined />, color: 'text-blue-600', bg: 'bg-blue-50' },
    { title: '处理中', value: videos.filter(v => v.status === 'processing').length, icon: <LoadingOutlined />, color: 'text-orange-600', bg: 'bg-orange-50' },
    { title: '已完成', value: videos.filter(v => v.status === 'completed').length, icon: <CheckCircleOutlined />, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  ]

  return (
    <>
      <Header className="flex-none z-10 !h-24 flex items-center justify-between px-10 bg-white/70 backdrop-blur-xl border-b border-white/20">
        <div className="flex flex-col">
          <Title level={3} className="!m-0 !font-bold text-slate-900">视频管理</Title>
          <Text type="secondary" className="text-xs font-medium opacity-60">管理教学资源，深度挖掘视频知识价值</Text>
        </div>

        <div className="flex items-center space-x-4">
          <Search
            placeholder="搜索视频资源..."
            allowClear
            onSearch={handleSearch}
            className="w-64"
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()} className="hover:rotate-180 transition-transform duration-500" />
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
        </div>
      </Header>

      <Content className="flex-1 overflow-y-auto p-10 space-y-8">
        {/* 统计横廊 */}
        <Row gutter={[24, 24]}>
          {videoStats.map((item, idx) => (
            <Col xs={24} sm={12} lg={6} key={idx}>
              <Card className="hover:shadow-lg transition-all group">
                <div className="flex items-center justify-between">
                  <div>
                    <Text type="secondary" className="text-[10px] font-bold uppercase tracking-widest block mb-1">{item.title}</Text>
                    <Title level={3} className="!m-0 !font-black !text-slate-900 group-hover:scale-105 transition-transform">{item.value}</Title>
                  </div>
                  <div className={`p-3 rounded-2xl ${item.bg} ${item.color} text-2xl animate-float`} style={{ animationDelay: `${idx * 0.15}s` }}>
                    {item.icon}
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>

        <Card className="border-none shadow-sm overflow-hidden">
          <Table
            columns={columns}
            dataSource={videos}
            rowKey="id"
            loading={isLoading}
            className="premium-table"
            pagination={{
              total: (videosData as any)?.pagination?.total || videos.length,
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => <span className="text-slate-400 text-xs">共 {total} 个视频资源</span>,
            }}
          />
        </Card>
      </Content>

      {/* 快速上传模态框 */}
      <Modal
        title={<div className="text-lg font-bold pb-4 border-b">快速上传视频</div>}
        open={isUploadModalOpen}
        onCancel={handleUploadCancel}
        onOk={handleUploadSubmit}
        confirmLoading={uploadMutation.isPending}
        width={540}
        centered
        className="premium-modal"
      >
        <Form
          form={form}
          layout="vertical"
          className="pt-6"
        >
          <Form.Item
            name="title"
            label={<span className="font-bold text-slate-700">视频标题</span>}
            rules={[{ required: true, message: '请输入视频标题' }]}
          >
            <Input placeholder="输入具有辨识度的标题" />
          </Form.Item>

          <Form.Item
            name="description"
            label={<span className="font-bold text-slate-700">内容简介</span>}
          >
            <Input.TextArea placeholder="简要描述视频的核心教学内容" rows={3} />
          </Form.Item>

          <Form.Item
            label={<span className="font-bold text-slate-700">资源文件</span>}
            required
            tooltip="我们将自动提取视频中的知识点、关键帧并生成智能转录文本"
          >
            <Upload.Dragger
              fileList={fileList}
              beforeUpload={(file) => {
                // 检查文件大小 (2GB)
                const MAX_SIZE = 2 * 1024 * 1024 * 1024
                if (file.size > MAX_SIZE) {
                  message.error(`文件过大 (${formatFileSize(file.size)})，单个上传限制为 2GB`)
                  return Upload.LIST_IGNORE
                }
                setFileList([file])
                return false
              }}
              onRemove={() => setFileList([])}
              maxCount={1}
              accept="video/*"
              className="premium-dragger group !bg-slate-50/50 hover:!bg-white !border-slate-100 hover:!border-indigo-300 !border-2 !rounded-3xl !p-10 transition-all duration-500"
            >
              <div className="flex flex-col items-center justify-center py-6">
                <div className="w-20 h-20 rounded-3xl bg-white shadow-xl shadow-indigo-100 flex items-center justify-center text-indigo-500 text-3xl group-hover:scale-110 group-hover:rotate-12 transition-all duration-500 border border-indigo-50 mb-6">
                  <UploadOutlined className="animate-bounce" />
                </div>
                <div className="space-y-2 text-center">
                  <div className="text-base font-black text-slate-800 tracking-tight">点击或将视频文件拖拽至此</div>
                  <div className="text-[11px] text-slate-400 font-bold uppercase tracking-widest bg-slate-100 px-3 py-1 rounded-full inline-block">
                    MP4, MOV, MKV, AVI • MAX 2GB
                  </div>
                </div>
              </div>
            </Upload.Dragger>
          </Form.Item>

          {uploadProgress > 0 && (
            <div className="mt-4 p-4 bg-indigo-50 rounded-xl">
              <div className="flex justify-between mb-2">
                <span className="text-xs font-bold text-indigo-700 uppercase">正在上传...</span>
                <span className="text-xs font-black text-indigo-700">{uploadProgress}%</span>
              </div>
              <Progress percent={uploadProgress} showInfo={false} strokeColor="#6366f1" size={{ height: 8 }} />
            </div>
          )}
        </Form>
      </Modal>

      {/* 视频详情 - 沉浸式视图 */}
      <Modal
        title={null}
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={null}
        width={1000}
        centered
        className="detail-modal"
        styles={{ body: { padding: 0 } }}
      >
        {selectedVideo && (
          <div className="flex flex-col lg:flex-row min-h-[600px]">
            {/* 左侧：视频及核心信息 */}
            <div className="lg:w-7/12 p-8 bg-slate-900 text-white flex flex-col">
              <div className="aspect-video bg-black rounded-2xl overflow-hidden mb-8 relative group shadow-2xl">
                {selectedVideo.thumbnail_url ? (
                  <img src={selectedVideo.thumbnail_url} className="w-full h-full object-cover opacity-60" />
                ) : <div className="w-full h-full flex items-center justify-center text-slate-700 text-4xl"><VideoCameraOutlined /></div>}
                <div className="absolute inset-0 flex items-center justify-center">
                  <Button
                    type="primary"
                    shape="circle"
                    size="large"
                    icon={<PlayCircleOutlined />}
                    className="!w-20 !h-20 !text-3xl bg-indigo-600 hover:scale-110 !border-none"
                    onClick={() => {
                      const path = selectedVideo.file_path;
                      const url = path.startsWith('http') ? path : `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001'}${path}`;
                      setCurrentVideoUrl(url);
                      setIsVideoPlayerOpen(true);
                    }}
                  />
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <Title level={2} className="!m-0 !text-white !font-black !tracking-tight">{selectedVideo.title}</Title>
                  <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${getStatusConfig(selectedVideo.status).class}`}>
                    {selectedVideo.status}
                  </div>
                </div>
                <Text className="text-slate-400 text-base leading-relaxed">{selectedVideo.description || '无视频描述信息'}</Text>

                <div className="grid grid-cols-2 gap-6 pt-8 border-t border-slate-800">
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">文件大小</div>
                    <div className="text-lg font-black">{formatFileSize(selectedVideo.file_size || 0)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">视频格式</div>
                    <div className="text-lg font-black uppercase text-indigo-400">{selectedVideo.format || 'mp4'}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">视频时长</div>
                    <div className="text-lg font-black">{formatDuration(selectedVideo.duration || 0)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">创建时间</div>
                    <div className="text-sm font-bold">{dayjs(selectedVideo.created_at).format('YYYY-MM-DD HH:mm')}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* 右侧：分析面板 */}
            <div className="lg:w-5/12 p-8 bg-white overflow-y-auto max-h-[700px]">
              <div className="flex items-center justify-between mb-8">
                <Title level={4} className="!m-0">AI 分析报告</Title>
                {!selectedVideo.analysis_result && (
                  <Button
                    type="primary"
                    size="small"
                    icon={<FileTextOutlined />}
                    onClick={() => handleAnalyze(selectedVideo.id)}
                    loading={analyzeMutation.isPending}
                  >开始分析</Button>
                )}
              </div>

              {selectedVideo.analysis_result ? (
                <div className="space-y-8">
                  <Timeline
                    className="premium-timeline"
                    items={[
                      {
                        color: 'indigo',
                        label: 'STEP 1',
                        children: (
                          <>
                            <div className="font-bold text-slate-800">深度语音转录</div>
                            <div className="text-xs text-slate-500 mt-1">
                              识别精准度: 98% | 词汇量: {selectedVideo.analysis_result.transcript?.total_words || 0}
                            </div>
                          </>
                        ),
                      },
                      {
                        color: 'violet',
                        label: 'STEP 2',
                        children: (
                          <>
                            <div className="font-bold text-slate-800">关键帧视觉分析</div>
                            <div className="text-xs text-slate-500 mt-1">
                              提取关键样本: {selectedVideo.analysis_result.keyframes?.length || 0} 个场景快照
                            </div>
                          </>
                        ),
                      },
                      {
                        color: 'emerald',
                        label: 'STEP 3',
                        children: (
                          <>
                            <div className="font-bold text-slate-800">知识图谱构建</div>
                            <div className="text-xs text-slate-500 mt-1">
                              提取核心概念: {selectedVideo.analysis_result.knowledge_points?.length || 0} 个知识实体
                            </div>
                          </>
                        ),
                      },
                    ]}
                  />

                  {selectedVideo.transcript && (
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                      <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">转录文本摘要</div>
                      <div className="text-xs text-slate-600 leading-relaxed italic line-clamp-6">
                        "{selectedVideo.transcript.text}"
                      </div>
                    </div>
                  )}

                  <div className="p-4 rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-200">
                    <div className="text-xs font-bold opacity-80 mb-2 uppercase">分析耗时</div>
                    <div className="text-2xl font-black">2.4 <span className="text-sm opacity-60">minutes</span></div>
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-4 py-20">
                  <div className="w-20 h-20 rounded-full bg-slate-50 flex items-center justify-center text-4xl text-slate-200">
                    <FileTextOutlined />
                  </div>
                  <div>
                    <div className="font-bold text-slate-400">尚未进行深度分析</div>
                    <Text type="secondary" className="text-xs">点击上方按钮，让 AI 为您解读视频中的核心知识点</Text>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* 视频播放弹窗 */}
      <Modal
        title={null}
        open={isVideoPlayerOpen}
        onCancel={() => {
          setIsVideoPlayerOpen(false)
          setCurrentVideoUrl('')
        }}
        footer={null}
        width={800}
        centered
        destroyOnHidden
        className="video-player-modal"
        styles={{ body: { padding: 0 } }}
      >
        {currentVideoUrl && (
          <video
            src={currentVideoUrl}
            controls
            autoPlay
            className="w-full h-auto aspect-video bg-black rounded-lg"
          />
        )}
      </Modal>
    </>
  )
}
