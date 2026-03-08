'use client'

import { useState, useEffect } from 'react'
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
  InputNumber,
  DatePicker,
  Switch,
  message,
  Popconfirm,
  Tooltip,
  Badge,
  Avatar,
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
  VideoCameraOutlined,
  BookOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Header, Content } = Layout
const { Title, Text } = Typography // Destructured Title and Text
const { Search } = Input
const { Option } = Select

interface Course {
  id: number
  title: string
  description: string
  thumbnail_url: string
  language: string
  level: string
  duration: number
  is_published: boolean
  created_at: string
  updated_at: string
  author: {
    id: number
    name: string
    avatar_url: string
  }
  tags: string[]
  knowledge_points_count: number
  videos_count: number
}

export default function CoursesPage() {
  const [searchText, setSearchText] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCourse, setEditingCourse] = useState<Course | null>(null)
  const [form] = Form.useForm()
  const queryClient = useQueryClient()

  // 获取课程列表
  const { data: coursesData, isLoading, refetch } = useQuery({
    queryKey: ['courses', searchText],
    queryFn: () => api.courses.getCourses({ search: searchText }),
  })

  const courses = coursesData?.data?.items || []

  // 创建/更新课程
  const mutation = useMutation({
    mutationFn: (data: any) =>
      editingCourse
        ? api.courses.updateCourse(editingCourse.id, data)
        : api.courses.createCourse(data),
    onSuccess: () => {
      message.success(editingCourse ? '课程更新成功' : '课程创建成功')
      queryClient.invalidateQueries({ queryKey: ['courses'] })
      handleCancel()
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '操作失败')
    },
  })

  // 删除课程
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.courses.deleteCourse(id),
    onSuccess: () => {
      message.success('课程删除成功')
      queryClient.invalidateQueries({ queryKey: ['courses'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '删除失败')
    },
  })

  const handleSearch = (value: string) => {
    setSearchText(value)
  }

  const handleAdd = () => {
    setEditingCourse(null)
    form.resetFields()
    setIsModalOpen(true)
  }

  const handleEdit = (course: Course) => {
    setEditingCourse(course)
    form.setFieldsValue({
      ...course,
      tags: course.tags || [],
    })
    setIsModalOpen(true)
  }

  const handleDelete = (id: number) => {
    deleteMutation.mutate(id)
  }

  const handleCancel = () => {
    setIsModalOpen(false)
    setEditingCourse(null)
    form.resetFields()
  }

  const handleSubmit = () => {
    form.validateFields().then(values => {
      mutation.mutate(values)
    })
  }

  const columns: ColumnsType<Course> = [
    {
      title: '课程封面',
      dataIndex: 'thumbnail_url',
      key: 'thumbnail',
      width: 140,
      render: (url, record) => (
        <div className="relative group cursor-pointer overflow-hidden rounded-xl shadow-md border border-slate-100 w-28 h-[72px] bg-slate-50 flex items-center justify-center">
          <img
            src={url || '/default-course.svg'}
            alt={record.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700 ease-out"
          />
          {/* 装饰性罩层 */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent opacity-60 group-hover:opacity-40 transition-opacity duration-300" />
        </div>
      ),
    },
    {
      title: '课程信息',
      dataIndex: 'title',
      key: 'title',
      render: (text, record) => (
        <div className="max-w-md">
          <div className="font-bold text-slate-800 text-base mb-1 line-clamp-1">{text}</div>
          <div className="text-xs text-slate-500 line-clamp-2">
            {record.description || '暂无描述信息'}
          </div>
        </div>
      ),
    },
    {
      title: '教研作者',
      dataIndex: 'author',
      key: 'author',
      width: 150,
      render: (author) => (
        <div className="flex items-center space-x-2 bg-slate-50/50 p-1.5 pr-3 rounded-full border border-slate-100 inline-flex">
          <Avatar size={24} src={author?.avatar_url} icon={<UserOutlined />} className="shadow-sm" />
          <span className="text-xs font-bold text-slate-700">{author?.name || '资深讲师'}</span>
        </div>
      ),
    },
    {
      title: '核心标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags) => (
        <div className="flex flex-wrap gap-1.5">
          {tags?.slice(0, 3).map((tag: string) => (
            <span key={tag} className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-500 uppercase tracking-wider">
              {tag}
            </span>
          ))}
          {tags && tags.length > 3 && (
            <span className="text-[10px] text-slate-400 font-bold">+{tags.length - 3}</span>
          )}
        </div>
      ),
    },
    {
      title: '发布状态',
      dataIndex: 'is_published',
      key: 'status',
      width: 120,
      render: (published) => (
        <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-black uppercase tracking-widest ${published ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'}`}>
          <Badge status={published ? 'success' : 'default'} className="mr-2" />
          {published ? 'Published' : 'Draft'}
        </div>
      ),
    },
    {
      title: '资源概览',
      key: 'stats',
      width: 160,
      render: (_, record) => (
        <div className="flex items-center space-x-4">
          <Tooltip title="关联知识点">
            <div className="flex items-center space-x-1.5">
              <BookOutlined className="text-violet-400" />
              <span className="font-black text-sm text-slate-700">{record.knowledge_points_count || 0}</span>
            </div>
          </Tooltip>
          <div className="w-[1px] h-4 bg-slate-200"></div>
          <Tooltip title="关联视频课">
            <div className="flex items-center space-x-1.5">
              <VideoCameraOutlined className="text-indigo-400" />
              <span className="font-black text-sm text-slate-700">{record.videos_count || 0}</span>
            </div>
          </Tooltip>
        </div>
      ),
    },
    {
      title: '最后修改',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 120,
      render: (date) => <span className="text-xs text-slate-400 font-medium">{dayjs(date).format('YYYY-MM-DD')}</span>,
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => (
        <div className="flex items-center space-x-1">
          <Tooltip title="编辑课程">
            <Button
              type="text"
              icon={<EditOutlined className="text-slate-400 hover:text-indigo-500" />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="查看成果">
            <Button
              type="text"
              icon={<EyeOutlined className="text-slate-400 hover:text-emerald-500" />}
              onClick={() => window.open(`/courses/${record.id}`, '_blank')}
            />
          </Tooltip>
          <Popconfirm
            title="确认删除课程"
            description="关联的教学资产将同步失效，请谨慎操作。"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="彻底移除">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined className="opacity-50 hover:opacity-100" />}
              />
            </Tooltip>
          </Popconfirm>
        </div>
      ),
    },
  ]

  return (
    <>
      <Header className="flex-none z-10 h-24 flex items-center justify-between px-10 bg-white/70 backdrop-blur-xl border-b border-white/20">
        <div>
          <Title level={3} className="!m-0 !font-bold text-slate-900">课程资产管理</Title>
          <Text type="secondary" className="text-xs">构建结构化知识体系，赋能智能化教学体验</Text>
        </div>
        <Space size="middle">
          <Search
            placeholder="搜索课程资源..."
            allowClear
            onSearch={handleSearch}
            className="w-72"
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()} />
          <Button type="primary" size="large" icon={<PlusOutlined />} onClick={handleAdd} className="shadow-lg shadow-indigo-100">
            新建课程
          </Button>
        </Space>
      </Header>

      <Content className="flex-1 overflow-y-auto p-10">
        <Card className="border-none shadow-sm overflow-hidden">
          <Table
            columns={columns}
            dataSource={courses}
            rowKey="id"
            loading={isLoading}
            className="premium-table"
            pagination={{
              total: coursesData?.data?.total || courses.length,
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => <span className="text-slate-400 text-xs font-medium">总计发现 {total} 门专业课程</span>,
            }}
          />
        </Card>
      </Content>

      <Modal
        title={<div className="text-lg font-black pb-4 border-b">配置课程资产</div>}
        open={isModalOpen}
        onCancel={handleCancel}
        onOk={handleSubmit}
        confirmLoading={mutation.isPending}
        width={600}
        centered
        className="premium-modal"
      >
        <Form
          form={form}
          layout="vertical"
          className="pt-6"
          initialValues={{
            language: 'zh-CN',
            level: 'beginner',
            is_published: false,
          }}
        >
          <Form.Item
            name="title"
            label={<span className="font-bold text-slate-700">课程标题</span>}
            rules={[{ required: true, message: '请输入课程标题' }]}
          >
            <Input placeholder="输入精准且具有吸引力的标题" />
          </Form.Item>

          <Form.Item
            name="description"
            label={<span className="font-bold text-slate-700">教学大纲/简介</span>}
            rules={[{ required: true, message: '请输入课程描述' }]}
          >
            <Input.TextArea placeholder="详细描述本课程的教学目标与核心价值" rows={4} />
          </Form.Item>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              name="language"
              label={<span className="font-bold text-slate-700">教学语言</span>}
              rules={[{ required: true, message: '请选择语言' }]}
            >
              <Select placeholder="选择主要语言">
                <Option value="zh-CN">简体中文</Option>
                <Option value="en-US">English</Option>
                <Option value="ja-JP">日本語</Option>
                <Option value="ko-KR">한국어</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="level"
              label={<span className="font-bold text-slate-700">难度评级</span>}
              rules={[{ required: true, message: '请选择难度等级' }]}
            >
              <Select placeholder="设定准入门槛">
                <Option value="beginner">初级 (Beginner)</Option>
                <Option value="intermediate">中级 (Intermediate)</Option>
                <Option value="advanced">高级 (Advanced)</Option>
                <Option value="expert">专家 (Expert)</Option>
              </Select>
            </Form.Item>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              name="duration"
              label={<span className="font-bold text-slate-700">预计时长 (Min)</span>}
            >
              <InputNumber min={0} className="w-full" placeholder="评估总学习时长" />
            </Form.Item>

            <Form.Item
              name="tags"
              label={<span className="font-bold text-slate-700">检索关键词</span>}
            >
              <Select mode="tags" placeholder="输入后按回车" className="w-full" />
            </Form.Item>
          </div>

          <Form.Item
            name="is_published"
            label={<span className="font-bold text-slate-700">发布决策</span>}
            valuePropName="checked"
          >
            <Switch checkedChildren="正式发布" unCheckedChildren="暂存草稿" className="!bg-emerald-500" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}