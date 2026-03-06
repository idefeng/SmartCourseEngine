'use client'

import { useState } from 'react'
import { Layout, Menu, Button, Card, Row, Col, Statistic, Typography, Space, Alert, Dropdown, Avatar } from 'antd'
import {
  DashboardOutlined,
  VideoCameraOutlined,
  BookOutlined,
  SearchOutlined,
  UserOutlined,
  SettingOutlined,
  UploadOutlined,
  LineChartOutlined,
  TeamOutlined,
  LogoutOutlined,
  ProfileOutlined,
  KeyOutlined,
} from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/auth-context'
import NotificationCenter from '@/components/notification/NotificationCenter'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'

const { Header, Sider, Content } = Layout
const { Title, Text } = Typography

export default function HomePage() {
  const router = useRouter()
  const { user, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)

  const getTotal = (value: any, paths: string[][]) => {
    for (const path of paths) {
      let current = value
      for (const key of path) {
        current = current?.[key]
      }
      const num = Number(current)
      if (Number.isFinite(num)) {
        return num
      }
    }
    return 0
  }

  const { data: statsData, isLoading: loading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const [coursesRes, videosRes, knowledgeRes] = await Promise.allSettled([
        api.courses.getCourses({ page: 1, page_size: 1 }),
        api.videos.getVideos({ page: 1, page_size: 1 }),
        api.knowledge.getKnowledgePoints({ page: 1, page_size: 1 }),
      ])

      const coursesValue = coursesRes.status === 'fulfilled' ? coursesRes.value : null
      const videosValue = videosRes.status === 'fulfilled' ? videosRes.value : null
      const knowledgeValue = knowledgeRes.status === 'fulfilled' ? knowledgeRes.value : null

      return {
        courses: getTotal(coursesValue, [['pagination', 'total'], ['total']]),
        videos: getTotal(videosValue, [['total'], ['pagination', 'total']]),
        knowledgePoints: getTotal(knowledgeValue, [['total'], ['pagination', 'total']]),
        users: 0,
      }
    },
  })

  const stats = statsData || {
    courses: 0,
    videos: 0,
    knowledgePoints: 0,
    users: 0,
  }

  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
      onClick: () => router.push('/'),
    },
    {
      key: 'courses',
      icon: <BookOutlined />,
      label: '课程管理',
      onClick: () => router.push('/courses'),
    },
    {
      key: 'videos',
      icon: <VideoCameraOutlined />,
      label: '视频管理',
      onClick: () => router.push('/videos'),
    },
    {
      key: 'knowledge',
      icon: <SearchOutlined />,
      label: '知识管理',
      onClick: () => router.push('/knowledge'),
    },
    {
      key: 'users',
      icon: <UserOutlined />,
      label: '用户管理',
      onClick: () => router.push('/users'),
    },
    {
      key: 'analytics',
      icon: <LineChartOutlined />,
      label: '数据分析',
      onClick: () => router.push('/analytics'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      onClick: () => router.push('/settings'),
    },
  ]

  const quickActions = [
    {
      title: '上传视频',
      description: '上传新视频并开始分析',
      icon: <UploadOutlined />,
      color: '#3b82f6',
      action: () => router.push('/videos/upload'),
    },
    {
      title: '创建课程',
      description: '创建新的在线课程',
      icon: <BookOutlined />,
      color: '#10b981',
      action: () => router.push('/courses/new'),
    },
    {
      title: '知识图谱',
      description: '查看和编辑知识图谱',
      icon: <SearchOutlined />,
      color: '#8b5cf6',
      action: () => router.push('/knowledge/graph'),
    },
    {
      title: '用户分析',
      description: '查看用户学习数据',
      icon: <TeamOutlined />,
      color: '#f59e0b',
      action: () => router.push('/analytics/users'),
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          boxShadow: '2px 0 8px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ padding: '24px 16px', textAlign: 'center' }}>
          <Title level={3} style={{ margin: 0, color: '#3b82f6' }}>
            {collapsed ? 'SCE' : 'SmartCourse'}
          </Title>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            智能课程引擎
          </Text>
        </div>
        <Menu
          mode="inline"
          defaultSelectedKeys={['dashboard']}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header style={{ 
          background: '#fff', 
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
          position: 'sticky',
          top: 0,
          zIndex: 1000,
        }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              欢迎使用 SmartCourseEngine
            </Title>
            <Text type="secondary">
              基于AI的智能课程知识库管理系统
            </Text>
          </div>
          <Space>
            <Button type="primary" onClick={() => router.push('/videos/upload')}>
              <UploadOutlined /> 上传视频
            </Button>
            
            {/* 通知中心 */}
            {user && <NotificationCenter />}
            
            {user ? (
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'profile',
                      icon: <ProfileOutlined />,
                      label: '个人资料',
                      onClick: () => router.push('/profile')
                    },
                    {
                      key: 'settings',
                      icon: <SettingOutlined />,
                      label: '系统设置',
                      onClick: () => router.push('/settings')
                    },
                    {
                      key: 'change-password',
                      icon: <KeyOutlined />,
                      label: '修改密码',
                      onClick: () => router.push('/change-password')
                    },
                    { type: 'divider' },
                    {
                      key: 'logout',
                      icon: <LogoutOutlined />,
                      label: '退出登录',
                      danger: true,
                      onClick: () => logout()
                    }
                  ]
                }}
                placement="bottomRight"
              >
                <Space style={{ cursor: 'pointer', padding: '8px 12px', borderRadius: 6, border: '1px solid #f0f0f0' }}>
                  <Avatar 
                    size="small" 
                    src={user.avatar_url} 
                    icon={<UserOutlined />}
                    style={{ backgroundColor: user.role === 'admin' ? '#f5222d' : '#1890ff' }}
                  />
                  <div>
                    <div style={{ fontWeight: 500, fontSize: 14 }}>
                      {user.full_name || user.username}
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      {user.role === 'admin' ? '管理员' : 
                       user.role === 'teacher' ? '教师' : 
                       user.role === 'student' ? '学生' : '用户'}
                    </div>
                  </div>
                </Space>
              </Dropdown>
            ) : (
              <Button onClick={() => router.push('/login')}>
                <UserOutlined /> 登录
              </Button>
            )}
          </Space>
        </Header>
        <Content style={{ margin: '24px 16px', overflow: 'initial' }}>
          <div style={{ padding: 24, background: '#fff', borderRadius: 8 }}>
            <Alert
              message="欢迎使用 SmartCourseEngine 管理后台"
              description="这是一个基于AI的智能课程知识库管理系统，支持视频分析、知识提取、智能搜索等功能。"
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Title level={3} style={{ marginBottom: 24 }}>
              系统概览
            </Title>

            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={24} sm={12} lg={6}>
                <Card loading={loading}>
                  <Statistic
                    title="课程数量"
                    value={stats.courses}
                    prefix={<BookOutlined />}
                    valueStyle={{ color: '#3b82f6' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card loading={loading}>
                  <Statistic
                    title="视频数量"
                    value={stats.videos}
                    prefix={<VideoCameraOutlined />}
                    valueStyle={{ color: '#10b981' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card loading={loading}>
                  <Statistic
                    title="知识点"
                    value={stats.knowledgePoints}
                    prefix={<SearchOutlined />}
                    valueStyle={{ color: '#8b5cf6' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card loading={loading}>
                  <Statistic
                    title="用户数量"
                    value={stats.users}
                    prefix={<UserOutlined />}
                    valueStyle={{ color: '#f59e0b' }}
                  />
                </Card>
              </Col>
            </Row>

            <Title level={3} style={{ marginBottom: 24 }}>
              快速操作
            </Title>

            <Row gutter={[16, 16]}>
              {quickActions.map((action, index) => (
                <Col xs={24} sm={12} lg={6} key={index}>
                  <Card
                    hoverable
                    onClick={action.action}
                    style={{ textAlign: 'center', cursor: 'pointer' }}
                  >
                    <div style={{ fontSize: 32, color: action.color, marginBottom: 16 }}>
                      {action.icon}
                    </div>
                    <Title level={5} style={{ marginBottom: 8 }}>
                      {action.title}
                    </Title>
                    <Text type="secondary">{action.description}</Text>
                  </Card>
                </Col>
              ))}
            </Row>

            <Title level={3} style={{ marginTop: 32, marginBottom: 24 }}>
              系统功能
            </Title>

            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <Card title="视频分析" variant="borderless">
                  <ul style={{ paddingLeft: 20 }}>
                    <li>支持多种视频格式上传</li>
                    <li>自动语音识别（支持中文）</li>
                    <li>关键帧提取和场景检测</li>
                    <li>智能知识点提取</li>
                  </ul>
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card title="知识管理" variant="borderless">
                  <ul style={{ paddingLeft: 20 }}>
                    <li>结构化知识点提取</li>
                    <li>知识图谱可视化</li>
                    <li>向量搜索和语义搜索</li>
                    <li>智能推荐和关联</li>
                  </ul>
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card title="学习管理" variant="borderless">
                  <ul style={{ paddingLeft: 20 }}>
                    <li>个性化学习路径</li>
                    <li>学习进度跟踪</li>
                    <li>智能练习和测试</li>
                    <li>学习效果分析</li>
                  </ul>
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card title="系统管理" variant="borderless">
                  <ul style={{ paddingLeft: 20 }}>
                    <li>多用户权限管理</li>
                    <li>数据备份和恢复</li>
                    <li>系统监控和告警</li>
                    <li>API接口管理</li>
                  </ul>
                </Card>
              </Col>
            </Row>

            <div style={{ marginTop: 32, textAlign: 'center' }}>
              <Text type="secondary">
                版本: 1.0.0 | 最后更新: 2026-03-01 | 技术支持: SmartCourseEngine Team
              </Text>
            </div>
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
