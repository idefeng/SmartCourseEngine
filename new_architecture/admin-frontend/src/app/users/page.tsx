'use client'

import { useState } from 'react'
import {
    Layout,
    Card,
    Table,
    Button,
    Space,
    Input,
    Tag,
    Avatar,
    Row,
    Col,
    Statistic,
    Progress,
    Typography,
    Tooltip,
    Badge,
} from 'antd'
import {
    UserOutlined,
    SearchOutlined,
    ReloadOutlined,
    UserAddOutlined,
    MailOutlined,
    CheckCircleOutlined,
    CrownOutlined,
    HistoryOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Header, Content } = Layout
const { Search } = Input
const { Title, Text } = Typography

interface User {
    id: number
    username: string
    email: string
    role: string
    status: string
    last_login: string
    learning_progress: number
    enrolled_courses: number
    created_at: string
}

export default function UsersPage() {
    const [searchText, setSearchText] = useState('')

    // 获取用户列表
    const { data: userData, isLoading, refetch } = useQuery({
        queryKey: ['users', searchText],
        queryFn: () => api.users.getUsers({ search: searchText }),
    })

    const users: User[] = (userData as any)?.items || (userData as any)?.data?.items || []

    const handleSearch = (value: string) => {
        setSearchText(value)
    }

    const columns: ColumnsType<User> = [
        {
            title: '用户信息',
            dataIndex: 'username',
            key: 'username',
            render: (text, record) => (
                <div className="flex items-center space-x-3">
                    <Avatar
                        src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${record.username}`}
                        className="border-2 border-indigo-100 shadow-sm"
                    />
                    <div>
                        <div className="font-bold text-slate-800 text-sm">{text}</div>
                        <div className="text-[11px] text-slate-400 flex items-center">
                            <MailOutlined className="mr-1" /> {record.email}
                        </div>
                    </div>
                </div>
            ),
        },
        {
            title: '账户角色',
            dataIndex: 'role',
            key: 'role',
            width: 120,
            render: (role) => {
                const isMaster = role === 'admin' || role === 'master'
                return (
                    <Tag
                        icon={isMaster ? <CrownOutlined /> : <UserOutlined />}
                        color={isMaster ? 'gold' : 'blue'}
                        className="px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-widest border-none shadow-sm"
                    >
                        {role}
                    </Tag>
                )
            },
        },
        {
            title: '账户状态',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: (status) => (
                <Badge
                    status={status === 'active' ? 'success' : 'default'}
                    text={
                        <span className={`text-[10px] font-bold uppercase tracking-widest ${status === 'active' ? 'text-emerald-500' : 'text-slate-400'}`}>
                            {status}
                        </span>
                    }
                />
            ),
        },
        {
            title: '学习进度',
            dataIndex: 'learning_progress',
            key: 'learning_progress',
            width: 180,
            render: (progress) => (
                <div className="space-y-1">
                    <div className="flex justify-between text-[9px] font-black text-slate-400 uppercase">
                        <span>Overall Path</span>
                        <span>{progress}%</span>
                    </div>
                    <Progress
                        percent={progress}
                        size="small"
                        showInfo={false}
                        strokeColor={{
                            '0%': '#6366f1',
                            '100%': '#a855f7',
                        }}
                        trailColor="#f1f5f9"
                    />
                </div>
            ),
        },
        {
            title: '最近记录',
            dataIndex: 'last_login',
            key: 'last_login',
            render: (date) => (
                <div className="text-slate-500 text-[11px] flex items-center">
                    <HistoryOutlined className="mr-1 opacity-40" />
                    {date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '从未登录'}
                </div>
            ),
        },
        {
            title: '操作',
            key: 'action',
            width: 80,
            render: () => (
                <Space>
                    <Tooltip title="用户画像">
                        <Button
                            type="text"
                            size="small"
                            icon={<SearchOutlined className="text-slate-400 hover:text-indigo-500" />}
                        />
                    </Tooltip>
                </Space>
            ),
        },
    ]

    const userStats = [
        { title: '全站用户总数', value: 1248, icon: <UserOutlined />, color: 'text-indigo-600', bg: 'bg-indigo-50', suffix: 'Members' },
        { title: '今日活跃指标', value: 86, icon: <CheckCircleOutlined />, color: 'text-emerald-600', bg: 'bg-emerald-50', suffix: 'Active' },
        { title: '高转化用户', value: 342, icon: <CrownOutlined />, color: 'text-orange-600', bg: 'bg-orange-50', suffix: 'VIP' },
        { title: '本周新增入驻', value: 12, icon: <UserAddOutlined />, color: 'text-violet-600', bg: 'bg-violet-50', suffix: 'New' },
    ]

    return (
        <>
            <Header className="flex-none z-10 h-24 flex items-center justify-between px-10 bg-white/70 backdrop-blur-xl border-b border-white/20">
                <div>
                    <Title level={3} className="!m-0 !font-bold">用户洞察</Title>
                    <Text type="secondary" className="text-xs">智能学习画像分析与用户全生命周期管理</Text>
                </div>

                <div className="flex items-center space-x-4">
                    <Search
                        placeholder="搜索用户名或邮箱..."
                        allowClear
                        onSearch={handleSearch}
                        className="w-64"
                    />
                    <Button icon={<ReloadOutlined />} onClick={() => refetch()} />
                    <Button
                        type="primary"
                        icon={<UserAddOutlined />}
                        className="bg-indigo-600 border-none shadow-lg shadow-indigo-100"
                    >
                        添加用户
                    </Button>
                </div>
            </Header>

            <Content className="flex-1 overflow-y-auto p-10 space-y-8">
                <Row gutter={[24, 24]}>
                    {userStats.map((item, idx) => (
                        <Col xs={24} sm={12} lg={6} key={idx}>
                            <Card className="hover:shadow-lg transition-all group border-none shadow-sm overflow-hidden relative">
                                <div className="flex items-center justify-between relative z-10">
                                    <div>
                                        <Text type="secondary" className="text-[10px] font-bold uppercase tracking-widest block mb-1">{item.title}</Text>
                                        <div className="flex items-baseline space-x-2">
                                            <Title level={3} className="!m-0 !font-black !text-slate-900 group-hover:scale-105 transition-transform">{item.value}</Title>
                                            <span className="text-[9px] font-bold text-slate-400 uppercase">{item.suffix}</span>
                                        </div>
                                    </div>
                                    <div className={`p-3 rounded-2xl ${item.bg} ${item.color} text-2xl animate-float`} style={{ animationDelay: `${idx * 0.15}s` }}>
                                        {item.icon}
                                    </div>
                                </div>
                                {/* 装饰背景 */}
                                <div className={`absolute -right-4 -bottom-4 text-6xl opacity-[0.03] ${item.color} rotate-12`}>
                                    {item.icon}
                                </div>
                            </Card>
                        </Col>
                    ))}
                </Row>

                <Card className="border-none shadow-sm overflow-hidden premium-card">
                    <Table
                        columns={columns}
                        dataSource={users}
                        rowKey="id"
                        loading={isLoading}
                        className="premium-table"
                        pagination={{
                            total: (userData as any)?.total || users.length,
                            pageSize: 10,
                            showSizeChanger: true,
                            showTotal: (total) => <span className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">Global Atlas: {total} users</span>,
                        }}
                    />
                </Card>
            </Content>
        </>
    )
}
