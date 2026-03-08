'use client'

import { useState } from 'react'
import { Layout, Menu, Typography } from 'antd'
import {
    DashboardOutlined,
    VideoCameraOutlined,
    BookOutlined,
    SearchOutlined,
    UserOutlined,
    LineChartOutlined,
    SettingOutlined,
} from '@ant-design/icons'
import { useRouter, usePathname } from 'next/navigation'

const { Sider } = Layout
const { Title, Text } = Typography

export default function AppSidebar() {
    const router = useRouter()
    const pathname = usePathname()
    const [collapsed, setCollapsed] = useState(false)

    // Map route paths to menu keys for default selection
    const getSelectedKey = () => {
        if (pathname.startsWith('/courses')) return 'courses'
        if (pathname.startsWith('/videos')) return 'videos'
        if (pathname.startsWith('/knowledge')) return 'knowledge'
        if (pathname.startsWith('/users')) return 'users'
        if (pathname.startsWith('/analytics')) return 'analytics'
        if (pathname.startsWith('/settings')) return 'settings'
        return 'dashboard'
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
            label: '知识中枢',
            onClick: () => router.push('/knowledge'),
        },
        {
            key: 'users',
            icon: <UserOutlined className="text-lg" />,
            label: '用户洞察',
            onClick: () => router.push('/users'),
        },
        {
            key: 'analytics',
            icon: <LineChartOutlined className="text-lg" />,
            label: '数据引擎',
            onClick: () => router.push('/analytics'),
        },
        {
            key: 'settings',
            icon: <SettingOutlined className="text-lg" />,
            label: '全局配置',
            onClick: () => router.push('/settings'),
        },
    ]

    return (
        <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={setCollapsed}
            theme="light"
            width={240}
            className="glass-sidebar hidden md:block border-r border-slate-100 h-full overflow-y-auto"
            style={{
                boxShadow: '2px 0 8px 0 rgba(29,35,41,.05)',
            }}
        >
            <div className="p-6 mb-4 flex flex-col items-center justify-center space-y-3">
                <div className="w-14 h-14 rounded-[20px] bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-indigo-200 shadow-2xl animate-float relative overflow-hidden group hover:scale-105 transition-transform cursor-pointer" onClick={() => router.push('/')}>
                    <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <Title level={3} className="!m-0 !text-white !font-black !tracking-tighter">
                        {collapsed ? 'S' : 'SC'}
                    </Title>
                </div>
                {!collapsed && (
                    <div className="text-center animate-fadeIn">
                        <Title level={4} className="!m-0 premium-gradient-text !text-lg !tracking-tight">
                            SmartCourse
                        </Title>
                        <Text type="secondary" className="text-[9px] uppercase tracking-widest font-black opacity-60 bg-clip-text text-transparent bg-gradient-to-r from-slate-400 to-slate-500">
                            AI Powered Engine
                        </Text>
                    </div>
                )}
            </div>
            <div className="px-3 pb-6">
                <Menu
                    mode="inline"
                    selectedKeys={[getSelectedKey()]}
                    items={menuItems}
                    className="bg-transparent border-none premium-menu space-y-1"
                />
            </div>
        </Sider>
    )
}
