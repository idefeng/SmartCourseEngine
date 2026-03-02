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
      width: 80,
      render: (url) => (
        <Avatar 
          shape="square" 
          size="large" 
          src={url || '/default-course.png'}
          icon={<BookOutlined />}
        />
      ),
    },
    {
      title: '课程标题',
      dataIndex: 'title',
      key: 'title',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <div style={{ fontSize: 12, color: '#666' }}>
            {record.description?.substring(0, 50)}...
          </div>
        </div>
      ),
    },
    {
      title: '作者',
      dataIndex: 'author',
      key: 'author',
      render: (author) => (
        <Space>
          <Avatar size="small" src={author?.avatar_url} icon={<UserOutlined />} />
          <span>{author?.name}</span>
        </Space>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags) => (
        <Space size={[0, 4]} wrap>
          {tags?.slice(0, 3).map((tag: string) => (
            <Tag key={tag} color="blue">{tag}</Tag>
          ))}
          {tags && tags.length > 3 && (
            <Tag>+{tags.length - 3}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_published',
      key: 'status',
      width: 100,
      render: (published) => (
        <Badge 
          status={published ? 'success' : 'default'} 
          text={published ? '已发布' : '草稿'} 
        />
      ),
    },
    {
      title: '统计',
      key: 'stats',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title="知识点数量">
            <Tag icon={<BookOutlined />} color="green">
              {record.knowledge_points_count || 0}
            </Tag>
          </Tooltip>
          <Tooltip title="视频数量">
            <Tag icon={<VideoCameraOutlined />} color="blue">
              {record.videos_count || 0}
            </Tag>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              onClick={() => window.open(`/courses/${record.id}`, '_blank')}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个课程吗？"
            description="删除后无法恢复，课程相关的视频和知识点也会被删除。"
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
          <h2 style={{ margin: 0 }}>课程管理</h2>
          <p style={{ margin: 0, color: '#666', fontSize: 14 }}>
            管理所有课程内容，包括创建、编辑、发布和删除课程
          </p>
        </div>
        <Space>
          <Search
            placeholder="搜索课程标题或描述"
            allowClear
            enterButton={<SearchOutlined />}
            onSearch={handleSearch}
            style={{ width: 300 }}
          />
          <Button icon={<FilterOutlined />}>筛选</Button>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新建课程
          </Button>
        </Space>
      </Header>
      <Content style={{ margin: '24px' }}>
        <Card>
          <Table
            columns={columns}
            dataSource={courses}
            rowKey="id"
            loading={isLoading}
            pagination={{
              total: coursesData?.data?.total || 0,
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条记录`,
            }}
          />
        </Card>
      </Content>

      {/* 课程编辑/创建模态框 */}
      <Modal
        title={editingCourse ? '编辑课程' : '新建课程'}
        open={isModalOpen}
        onCancel={handleCancel}
        onOk={handleSubmit}
        confirmLoading={mutation.isPending}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            language: 'zh-CN',
            level: 'beginner',
            is_published: false,
          }}
        >
          <Form.Item
            name="title"
            label="课程标题"
            rules={[{ required: true, message: '请输入课程标题' }]}
          >
            <Input placeholder="请输入课程标题" />
          </Form.Item>

          <Form.Item
            name="description"
            label="课程描述"
            rules={[{ required: true, message: '请输入课程描述' }]}
          >
            <Input.TextArea 
              placeholder="请输入课程描述" 
              rows={4}
            />
          </Form.Item>

          <Form.Item
            name="thumbnail_url"
            label="封面图片URL"
          >
            <Input placeholder="请输入封面图片URL" />
          </Form.Item>

          <Form.Item
            name="language"
            label="语言"
            rules={[{ required: true, message: '请选择语言' }]}
          >
            <Select placeholder="请选择语言">
              <Option value="zh-CN">中文</Option>
              <Option value="en-US">英文</Option>
              <Option value="ja-JP">日文</Option>
              <Option value="ko-KR">韩文</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="level"
            label="难度等级"
            rules={[{ required: true, message: '请选择难度等级' }]}
          >
            <Select placeholder="请选择难度等级">
              <Option value="beginner">初级</Option>
              <Option value="intermediate">中级</Option>
              <Option value="advanced">高级</Option>
              <Option value="expert">专家</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="duration"
            label="预计学习时长（分钟）"
          >
            <InputNumber 
              min={0} 
              style={{ width: '100%' }} 
              placeholder="请输入预计学习时长"
            />
          </Form.Item>

          <Form.Item
            name="tags"
            label="标签"
          >
            <Select
              mode="tags"
              placeholder="请输入标签，按回车添加"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name="is_published"
            label="发布状态"
            valuePropName="checked"
          >
            <Switch checkedChildren="已发布" unCheckedChildren="草稿" />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}