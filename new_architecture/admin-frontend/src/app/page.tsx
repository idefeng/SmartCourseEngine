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
      icon: <DashboardOutlined className="text-lg" />,
      label: '仪表盘',
      onClick: () => router.push('/'),
    },
    {
      key: 'courses',
      icon: <BookOutlined className="text-lg" />,
      label: '课程管理',
      onClick: () => router.push('/courses'),
    },
    {
      key: 'videos',
      icon: <VideoCameraOutlined className="text-lg" />,
      label: '视频管理',
      onClick: () => router.push('/videos'),
    },
    {
      key: 'knowledge',
      icon: <SearchOutlined className="text-lg" />,
      label: '知识管理',
      onClick: () => router.push('/knowledge'),
    },
    {
      key: 'users',
      icon: <UserOutlined className="text-lg" />,
      label: '用户管理',
      onClick: () => router.push('/users'),
    },
    {
      key: 'analytics',
      icon: <LineChartOutlined className="text-lg" />,
      label: '数据分析',
      onClick: () => router.push('/analytics'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined className="text-lg" />,
      label: '系统设置',
      onClick: () => router.push('/settings'),
    },
  ]

  const quickActions = [
    {
      title: '上传视频',
      description: '上传新视频并开始分析',
      icon: <UploadOutlined />,
      gradient: 'from-blue-500 to-indigo-600',
      action: () => router.push('/videos/upload'),
    },
    {
      title: '创建课程',
      description: '创建新的在线课程',
      icon: <BookOutlined />,
      gradient: 'from-emerald-500 to-teal-600',
      action: () => router.push('/courses'),
    },
    {
      title: '知识图谱',
      description: '查看和编辑知识图谱',
      icon: <SearchOutlined />,
      gradient: 'from-violet-500 to-purple-600',
      action: () => router.push('/knowledge'),
    },
    {
      title: '用户分析',
      description: '查看用户学习数据',
      icon: <TeamOutlined />,
      gradient: 'from-orange-500 to-amber-600',
      action: () => router.push('/users'),
    },
  ]

  return (
    <>
      <Header className="flex-none z-10 h-20 md:h-24 flex items-center justify-between px-6 md:px-10 bg-white/70 backdrop-blur-xl border-b border-white/20">
        <div className="flex flex-col">
          <Title level={3} className="!m-0 !text-slate-900 !font-bold">
            仪表盘
          </Title>
          <Text type="secondary" className="text-sm">
            欢迎回来，管理并优化您的智能课程库
          </Text>
        </div>

        <Space size="large">
          <Button
            type="primary"
            size="large"
            icon={<UploadOutlined />}
            onClick={() => router.push('/videos/upload')}
            className="hidden lg:flex items-center"
          >
            上传视频
          </Button>

          <div className="flex items-center space-x-4">
            {user && <NotificationCenter />}

            {user ? (
              <Dropdown
                menu={{
                  className: "w-56 p-2 rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100/50",
                  items: [
                    {
                      key: 'header',
                      label: (
                        <div className="px-2 py-2 border-b border-slate-100 mb-1 flex flex-col">
                          <span className="font-bold text-slate-800 text-sm truncate">{user.full_name || user.username}</span>
                          <span className="text-xs text-slate-400 truncate mt-0.5">{user.email || 'user@example.com'}</span>
                        </div>
                      ),
                      disabled: true,
                      style: { cursor: 'default' }
                    },
                    { key: 'profile', icon: <ProfileOutlined className="text-indigo-500" />, label: '个人资料', onClick: () => router.push('/profile') },
                    { key: 'settings', icon: <SettingOutlined className="text-slate-500" />, label: '全局设置', onClick: () => router.push('/settings') },
                    { key: 'change-password', icon: <KeyOutlined className="text-slate-500" />, label: '安全组', onClick: () => router.push('/change-password') },
                    { type: 'divider' },
                    { key: 'logout', icon: <LogoutOutlined className="text-red-500" />, label: <span className="text-red-500 font-bold">退出登录</span>, onClick: () => logout() }
                  ]
                }}
                placement="bottomRight"
                trigger={['hover']}
              >
                <div className="flex items-center space-x-2.5 cursor-pointer p-1 pr-4 rounded-full bg-white/60 backdrop-blur-md border border-slate-200/80 shadow-sm hover:bg-white hover:shadow-md hover:-translate-y-0.5 transition-all duration-300">
                  <Avatar
                    size={38}
                    src={user.avatar_url}
                    icon={<UserOutlined />}
                    className="border-2 border-white shadow-sm"
                    style={{
                      background: user.role === 'admin' ? 'linear-gradient(135deg, #f43f5e 0%, #e11d48 100%)' : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                    }}
                  />
                  <div className="hidden sm:flex flex-col items-start justify-center">
                    <div className="font-black text-[13px] text-slate-800 leading-none mb-1">
                      {user.full_name || user.username}
                    </div>
                    <div className="text-[9px] text-slate-400 font-black uppercase tracking-widest leading-none">
                      {user.role === 'admin' ? 'Administrator' :
                        user.role === 'teacher' ? 'Instructor' :
                          user.role === 'student' ? 'Student' : 'User'}
                    </div>
                  </div>
                </div>
              </Dropdown>
            ) : (
              <Button shape="round" icon={<UserOutlined />} onClick={() => router.push('/login')}>
                登录
              </Button>
            )}
          </div>
        </Space>
      </Header>

      <Content className="flex-1 overflow-y-auto p-6 md:p-10">
        <div className="max-w-7xl mx-auto space-y-10">
          {/* 统计指标 */}
          <section>
            <div className="flex items-center justify-between mb-6">
              <Title level={4} className="!m-0 flex items-center space-x-2">
                <span className="w-1.5 h-6 bg-indigo-600 rounded-full inline-block"></span>
                <span>核心指标</span>
              </Title>
            </div>
            <Row gutter={[24, 24]}>
              {[
                { title: '课程数量', value: stats.courses, icon: <BookOutlined />, color: 'text-blue-600', bg: 'bg-blue-50' },
                { title: '视频数量', value: stats.videos, icon: <VideoCameraOutlined />, color: 'text-emerald-600', bg: 'bg-emerald-50' },
                { title: '提取知识点', value: stats.knowledgePoints, icon: <SearchOutlined />, color: 'text-violet-600', bg: 'bg-violet-50' },
                { title: '活跃用户', value: stats.users, icon: <UserOutlined />, color: 'text-orange-600', bg: 'bg-orange-50' },
              ].map((item, idx) => (
                <Col xs={24} sm={12} lg={6} key={idx}>
                  <Card className="hover:shadow-xl group" loading={loading}>
                    <div className="flex items-start justify-between">
                      <div>
                        <Text type="secondary" className="text-xs font-bold uppercase tracking-widest block mb-1">
                          {item.title}
                        </Text>
                        <Title level={2} className="!m-0 !font-black !text-slate-900 group-hover:scale-105 transition-transform duration-300 origin-left">
                          {item.value || 0}
                        </Title>
                      </div>
                      <div className={`p-3 rounded-2xl ${item.bg} ${item.color} text-2xl animate-float`} style={{ animationDelay: `${idx * 0.2}s` }}>
                        {item.icon}
                      </div>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          </section>

          {/* 快速入门 & 操作 */}
          <section>
            <Title level={4} className="!mb-6 flex items-center space-x-2">
              <span className="w-1.5 h-6 bg-indigo-600 rounded-full inline-block"></span>
              <span>快速操作</span>
            </Title>
            <Row gutter={[24, 24]}>
              {quickActions.map((action, index) => (
                <Col xs={24} sm={12} lg={6} key={index}>
                  <Card
                    hoverable
                    onClick={action.action}
                    className="group overflow-hidden border-none h-full shadow-sm hover:shadow-md transition-all duration-300"
                    styles={{
                      body: {
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        textAlign: 'center',
                        padding: '32px 24px',
                      }
                    }}
                  >
                    <div className={`w-16 h-16 rounded-3xl bg-gradient-to-br ${action.gradient} text-white text-3xl flex items-center justify-center mb-6 shadow-lg group-hover:rotate-6 transition-all duration-300`}>
                      {action.icon}
                    </div>
                    <Title level={5} className="!mb-2 !font-bold">
                      {action.title}
                    </Title>
                    <Text type="secondary" className="text-xs">
                      {action.description}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>
          </section>

          {/* 功能模块展示 */}
          <section>
            <Title level={4} className="!mb-6 flex items-center space-x-2">
              <span className="w-1.5 h-6 bg-indigo-600 rounded-full inline-block"></span>
              <span>平台功能总览</span>
            </Title>
            <Row gutter={[24, 24]}>
              {[
                { title: '视频深度分析', desc: '采用先进集成语音识别与视觉模型，深度解析教学内容', items: ['多格式支持', '自动ASR识别', '关键帧提取', '场景检测'] },
                { title: '智能知识管理', desc: '构建多维知识图谱，实现教学资源的智能化分类与联想', items: ['结构化提取', '知识图谱可视化', '向量语义搜索', '智能推荐'] },
                { title: '自适应学习流', desc: '基于学习者特征实时调整教学路径，提供沉浸式学习体验', items: ['个性化路径', '进度实时追踪', '智能课后练习', '效果多维评估'] },
                { title: '企业级系统管控', desc: '全面保障平台稳定运行，支持大规模高并发教学场景', items: ['多级权限管理', '数据容灾备份', '实时系统监控', 'OpenAPI支持'] },
              ].map((mod, i) => (
                <Col xs={24} md={12} key={i}>
                  <Card className="h-full border border-slate-100 hover:border-indigo-100 bg-white/50">
                    <Title level={4} className="!mb-2">{mod.title}</Title>
                    <Text type="secondary" className="block mb-6 h-10">{mod.desc}</Text>
                    <div className="grid grid-cols-2 gap-3">
                      {mod.items.map((item, j) => (
                        <div key={j} className="flex items-center space-x-2 text-slate-600 text-sm">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                          <span>{item}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          </section>

          <footer className="pt-10 pb-6 text-center">
            <div className="w-10 h-1 bg-slate-200 mx-auto mb-6 rounded-full opacity-50"></div>
            <Text type="secondary" className="text-xs font-medium tracking-wide opacity-60">
              SCM ENGINE VERSION 2.0.0 PREMIUM EDITION
            </Text>
            <div className="mt-2 text-[10px] text-slate-400 font-bold uppercase tracking-tighter">
              &copy; 2026 SmartCourseEngine Team. All rights reserved.
            </div>
          </footer>
        </div>
      </Content>
    </>
  )
}

