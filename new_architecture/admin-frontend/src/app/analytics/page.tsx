'use client'

import { useState } from 'react'
import {
    Layout,
    Card,
    Row,
    Col,
    Statistic,
    Progress,
    Typography,
    Space,
    Button,
    DatePicker,
    Select,
    Table,
    Badge,
} from 'antd'
import {
    LineChartOutlined,
    BarChartOutlined,
    PieChartOutlined,
    RiseOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
    ReloadOutlined,
    DownloadOutlined,
    FilterOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import dayjs from 'dayjs'

const { Header, Content } = Layout
const { Title, Text } = Typography
const { RangePicker } = DatePicker
const { Option } = Select

export default function AnalyticsPage() {
    const [dateRange, setDateRange] = useState<any>(null)

    // 获取概览数据
    const { data: overviewData, isLoading: isOverviewLoading, refetch: refetchOverview } = useQuery({
        queryKey: ['analytics-overview'],
        queryFn: () => api.analytics.getOverview(),
    })

    // 获取动态趋势
    const { data: trendsData, isLoading: isTrendsLoading } = useQuery({
        queryKey: ['analytics-trends'],
        queryFn: () => api.analytics.getLearningTrends(),
    })

    const stats = [
        {
            title: '总学习时长',
            value: '2,840',
            suffix: 'Hrs',
            trend: '+12.5%',
            isUp: true,
            color: 'text-indigo-600',
            bg: 'bg-indigo-50',
        },
        {
            title: '知识点覆盖率',
            value: '84',
            suffix: '%',
            trend: '+4.2%',
            isUp: true,
            color: 'text-emerald-600',
            bg: 'bg-emerald-50',
        },
        {
            title: '活跃用户数',
            value: '1,248',
            suffix: 'Ppl',
            trend: '-2.1%',
            isUp: false,
            color: 'text-rose-600',
            bg: 'bg-rose-50',
        },
        {
            title: '课程完成率',
            value: '68',
            suffix: '%',
            trend: '+8.1%',
            isUp: true,
            color: 'text-violet-600',
            bg: 'bg-violet-50',
        },
    ]

    const courseColumns = [
        {
            title: '热门课程',
            dataIndex: 'title',
            key: 'title',
            render: (text: string) => <Text strong className="text-slate-700">{text}</Text>,
        },
        {
            title: '订阅用户',
            dataIndex: 'users',
            key: 'users',
            render: (users: number) => <Badge count={users} overflowCount={9999} style={{ backgroundColor: '#f1f5f9', color: '#64748b', fontWeight: 'bold' }} />,
        },
        {
            title: '完成度平衡',
            dataIndex: 'completion',
            key: 'completion',
            render: (percent: number) => (
                <Progress
                    percent={percent}
                    size="small"
                    strokeColor={percent > 80 ? '#10b981' : '#6366f1'}
                />
            ),
        },
        {
            title: '平均分',
            dataIndex: 'score',
            key: 'score',
            render: (score: number) => (
                <Space size={4}>
                    <RiseOutlined className="text-emerald-500" />
                    <Text strong>{score}</Text>
                </Space>
            ),
        },
    ]

    const mockCourseData = [
        { key: '1', title: '深度学习中的微积分基础', users: 1240, completion: 85, score: 92 },
        { key: '2', title: 'Python 异步编程实战', users: 890, completion: 72, score: 88 },
        { key: '3', title: '多模态 AI 架构设计', users: 2100, completion: 45, score: 95 },
        { key: '4', title: '分布式渲染技术', users: 560, completion: 90, score: 84 },
    ]

    return (
        <>
            <Header className="flex-none z-10 h-24 flex items-center justify-between px-10 bg-white/70 backdrop-blur-xl border-b border-white/20">
                <div>
                    <Title level={4} className="!m-0 !font-black uppercase tracking-tight">数据引擎</Title>
                    <Text type="secondary" className="text-[10px] font-bold uppercase tracking-widest opacity-60">Analytics & Intelligent Insights</Text>
                </div>

                <div className="flex items-center space-x-4">
                    <RangePicker
                        className="rounded-xl border-none shadow-sm bg-slate-50"
                        onChange={(dates) => setDateRange(dates)}
                    />
                    <Select defaultValue="all" className="w-32" variant="borderless">
                        <Option value="all">全域流量</Option>
                        <Option value="web">Web 端</Option>
                        <Option value="mobile">移动端</Option>
                    </Select>
                    <Button icon={<ReloadOutlined />} onClick={() => refetchOverview()} />
                    <Button type="primary" icon={<DownloadOutlined />} className="bg-slate-900 border-none rounded-xl">导出报告</Button>
                </div>
            </Header>

            <Content className="flex-1 overflow-y-auto p-10 space-y-8">
                {/* 指标面板 */}
                <Row gutter={[24, 24]}>
                    {stats.map((stat, idx) => (
                        <Col xs={24} sm={12} lg={6} key={idx}>
                            <Card className="hover:shadow-xl transition-all border-none shadow-sm relative overflow-hidden group">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <Text type="secondary" className="text-[10px] font-black uppercase tracking-widest block mb-2 opacity-50">{stat.title}</Text>
                                        <div className="flex items-baseline space-x-2">
                                            <Title level={2} className="!m-0 !font-black tracking-tighter">{stat.value}</Title>
                                            <Text className="text-xs font-bold text-slate-400">{stat.suffix}</Text>
                                        </div>
                                    </div>
                                    <div className={`p-3 rounded-2xl ${stat.bg} ${stat.color} text-xl shadow-inner`}>
                                        {idx % 2 === 0 ? <LineChartOutlined /> : <BarChartOutlined />}
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <div className={`flex items-center px-2 py-0.5 rounded-full text-[10px] font-black ${stat.isUp ? 'bg-emerald-50 text-emerald-500' : 'bg-rose-50 text-rose-500'}`}>
                                        {stat.isUp ? <ArrowUpOutlined className="mr-1" /> : <ArrowDownOutlined className="mr-1" />}
                                        {stat.trend}
                                    </div>
                                    <Text type="secondary" className="text-[10px] font-medium italic opacity-40">vs last period</Text>
                                </div>
                                {/* 装饰性背景 */}
                                <div className="absolute -right-2 -bottom-2 opacity-[0.03] text-6xl rotate-12 group-hover:scale-110 transition-transform">
                                    <RiseOutlined />
                                </div>
                            </Card>
                        </Col>
                    ))}
                </Row>

                <Row gutter={[24, 24]}>
                    {/* 学习趋势图 (Mock Placeholder) */}
                    <Col span={16}>
                        <Card
                            title={<span className="font-black italic uppercase text-xs tracking-widest text-slate-400">Knowledge Acquisition Pulse</span>}
                            className="border-none shadow-sm h-full"
                            extra={<Button type="text" icon={<FilterOutlined />} size="small" />}
                        >
                            <div className="py-10 flex flex-col items-center justify-center bg-slate-50/50 rounded-3xl border border-dashed border-slate-200 min-h-[400px]">
                                <div className="relative w-full max-w-md aspect-video bg-white rounded-2xl shadow-2xl p-6 flex flex-col justify-between overflow-hidden">
                                    <div className="flex justify-between">
                                        <div className="space-y-1">
                                            <div className="w-20 h-2 bg-slate-100 rounded"></div>
                                            <div className="w-12 h-2 bg-slate-50 rounded"></div>
                                        </div>
                                        <div className="flex space-x-2">
                                            <div className="w-6 h-6 rounded-lg bg-indigo-50"></div>
                                            <div className="w-6 h-6 rounded-lg bg-violet-50"></div>
                                        </div>
                                    </div>
                                    {/* Mock Line Chart */}
                                    <div className="relative h-32 w-full mt-4 flex items-end justify-between px-2">
                                        {[40, 70, 45, 90, 65, 80, 50, 95, 75, 100].map((h, i) => (
                                            <div key={i} className="w-1.5 bg-gradient-to-t from-indigo-500 to-violet-400 rounded-full animate-pulse" style={{ height: `${h}%`, animationDelay: `${i * 0.1}s` }}></div>
                                        ))}
                                    </div>
                                    <div className="mt-4 pt-4 border-t border-slate-50 flex justify-between">
                                        <div className="w-1/3 h-2 bg-slate-100 rounded"></div>
                                        <div className="w-1/4 h-2 bg-slate-50 rounded"></div>
                                    </div>
                                    {/* 装饰光效 */}
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-[80px] rounded-full"></div>
                                </div>
                                <Title level={5} className="mt-8 !text-slate-400 italic">正在实时计算全域知识点消费链路...</Title>
                            </div>
                        </Card>
                    </Col>

                    {/* 右侧分布 */}
                    <Col span={8}>
                        <Card
                            title={<span className="font-black italic uppercase text-xs tracking-widest text-slate-400">Learning Distribution</span>}
                            className="border-none shadow-sm h-full"
                        >
                            <div className="space-y-8">
                                <div>
                                    <div className="flex justify-between mb-2">
                                        <Text className="text-xs font-bold text-slate-600">Video Content Analysis</Text>
                                        <Text className="text-xs font-black text-indigo-500">42%</Text>
                                    </div>
                                    <Progress percent={42} showInfo={false} strokeColor="#6366f1" size={{ height: 12 }} />
                                </div>
                                <div>
                                    <div className="flex justify-between mb-2">
                                        <Text className="text-xs font-bold text-slate-600">Interactive Knowledge Points</Text>
                                        <Text className="text-xs font-black text-emerald-500">28%</Text>
                                    </div>
                                    <Progress percent={28} showInfo={false} strokeColor="#10b981" size={{ height: 12 }} />
                                </div>
                                <div>
                                    <div className="flex justify-between mb-2">
                                        <Text className="text-xs font-bold text-slate-600">Synthetic Assessments</Text>
                                        <Text className="text-xs font-black text-violet-500">15%</Text>
                                    </div>
                                    <Progress percent={15} showInfo={false} strokeColor="#a855f7" size={{ height: 12 }} />
                                </div>
                                <div>
                                    <div className="flex justify-between mb-2">
                                        <Text className="text-xs font-bold text-slate-600">Social Collaboration</Text>
                                        <Text className="text-xs font-black text-orange-500">15%</Text>
                                    </div>
                                    <Progress percent={15} showInfo={false} strokeColor="#f59e0b" size={{ height: 12 }} />
                                </div>
                            </div>

                            <div className="mt-12 p-6 rounded-3xl bg-slate-900 text-white relative overflow-hidden">
                                <div className="relative z-10">
                                    <div className="text-[9px] font-black opacity-40 uppercase tracking-widest mb-1">AI Recommendation</div>
                                    <Title level={4} className="!text-white !m-0 !tracking-tight">Optimized Path Found</Title>
                                    <Text className="text-[10px] text-slate-400 mt-2 block italic leading-relaxed">
                                        基于当前学习密度分析，建议下周增加“多模态AI”相关的内容权重以提高用户留存。
                                    </Text>
                                </div>
                                <PieChartOutlined className="absolute -bottom-6 -right-6 text-8xl opacity-10 rotate-12" />
                            </div>
                        </Card>
                    </Col>
                </Row>

                {/* 热门课程排行 */}
                <Card className="border-none shadow-sm premium-card">
                    <div className="flex items-center justify-between mb-6">
                        <Title level={5} className="!m-0 italic uppercase tracking-tighter">Top Performing Assets</Title>
                        <Button type="link" size="small" className="text-indigo-500 font-bold">查看全部</Button>
                    </div>
                    <Table
                        columns={courseColumns}
                        dataSource={mockCourseData}
                        pagination={false}
                        className="premium-table-minimal"
                    />
                </Card>
            </Content>
        </>
    )
}
