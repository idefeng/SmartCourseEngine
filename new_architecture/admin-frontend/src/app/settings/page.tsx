'use client'

import { useState } from 'react'
import {
    Layout,
    Typography,
    Card,
    Row,
    Col,
    Space,
    Button,
    Form,
    Input,
    Switch,
    Select,
    Divider,
    Badge,
    Tabs,
    InputNumber,
    message,
    App,
    Tooltip,
} from 'antd'
import {
    SettingOutlined,
    CloudServerOutlined,
    RobotOutlined,
    BellOutlined,
    SafetyCertificateOutlined,
    SaveOutlined,
    ReloadOutlined,
    DatabaseOutlined,
    InfoCircleOutlined,
    CheckCircleOutlined,
} from '@ant-design/icons'

const { Header, Content } = Layout
const { Title, Text } = Typography
const { Option } = Select

export default function SettingsPage() {
    const { message: antdMessage } = App.useApp()
    const [loading, setLoading] = useState(false)
    const [form] = Form.useForm()

    const handleSave = async (values: any) => {
        setLoading(true)
        try {
            // 模拟保存操作
            await new Promise(resolve => setTimeout(resolve, 1500))
            antdMessage.success('系统全局配置已更新成功')
        } catch (error) {
            antdMessage.error('保存设置失败，请稍后重试')
        } finally {
            setLoading(false)
        }
    }

    const systemInfo = [
        { label: '核心版本', value: 'v2.0.4-premium', status: 'success' },
        { label: '网关负载', value: '14.2%', status: 'processing' },
        { label: '数据库节点', value: 'Cluster 01 (Online)', status: 'success' },
        { label: 'AI 算力池', value: 'GPU-RTX-4090 (Available)', status: 'warning' },
    ]

    return (
        <div className="flex flex-col h-full bg-slate-50/50">
            <Header className="flex-none z-10 !h-24 flex items-center justify-between px-10 bg-white/70 backdrop-blur-xl border-b border-white/20">
                <div className="flex flex-col">
                    <Title level={3} className="!m-0 !font-bold text-slate-900 flex items-center gap-2">
                        <SettingOutlined className="text-indigo-600" />
                        全局配置
                    </Title>
                    <Text type="secondary" className="text-xs font-medium opacity-60">定义系统核心参数，调度 AI 算力与存储策略</Text>
                </div>

                <div className="flex items-center space-x-3">
                    <Button icon={<ReloadOutlined />} />
                    <Button
                        type="primary"
                        icon={<SaveOutlined />}
                        loading={loading}
                        onClick={() => form.submit()}
                        className="bg-indigo-600 hover:bg-indigo-700 h-10 px-6 rounded-xl font-bold"
                    >
                        保存更改
                    </Button>
                </div>
            </Header>

            <Content className="flex-1 overflow-y-auto p-10">
                <div className="max-w-6xl mx-auto space-y-8">
                    {/* 状态看板 */}
                    <Row gutter={24}>
                        {systemInfo.map((info, idx) => (
                            <Col span={6} key={idx}>
                                <Card className="hover:shadow-lg transition-all border-none shadow-sm">
                                    <div className="text-[10px] uppercase tracking-widest font-black text-slate-400 mb-2">{info.label}</div>
                                    <div className="flex items-baseline space-x-2">
                                        <span className="text-sm font-bold text-slate-800">{info.value}</span>
                                        <Badge status={info.status as any} />
                                    </div>
                                </Card>
                            </Col>
                        ))}
                    </Row>

                    <Form
                        form={form}
                        layout="vertical"
                        onFinish={handleSave}
                        initialValues={{
                            whisper_model: 'medium',
                            enable_keyframes: true,
                            enable_scenes: true,
                            max_upload_size: 2048,
                            storage_path: '/app/data/storage',
                            api_timeout: 3600,
                            notification_email: true,
                            notification_system: true,
                            enable_auto_analysis: true,
                        }}
                        className="space-y-8"
                    >
                        <Tabs
                            defaultActiveKey="1"
                            type="card"
                            className="premium-tabs"
                            items={[
                                {
                                    key: '1',
                                    label: <Space><RobotOutlined />AI 核心引擎</Space>,
                                    children: (
                                        <Card className="border-none shadow-sm rounded-2xl overflow-hidden mt-4">
                                            <Row gutter={48}>
                                                <Col span={12}>
                                                    <Form.Item
                                                        name="whisper_model"
                                                        label={<span className="font-bold text-slate-700">语音识别模型 (Whisper)</span>}
                                                        tooltip="指定视频音频转录所使用的模型规模。较大模型精度更高但耗时更久。"
                                                    >
                                                        <Select size="large" className="w-full">
                                                            <Option value="tiny">Tiny (超轻量 / 极速)</Option>
                                                            <Option value="base">Base (基础 / 快速)</Option>
                                                            <Option value="small">Small (精简 / 平衡)</Option>
                                                            <Option value="medium">Medium (进阶 / 高精度)</Option>
                                                            <Option value="large-v3">Large v3 (顶级 / 专家级精度)</Option>
                                                        </Select>
                                                    </Form.Item>
                                                    <Form.Item
                                                        name="enable_auto_analysis"
                                                        label={<span className="font-bold text-slate-700">上传后自动启动分析</span>}
                                                        valuePropName="checked"
                                                    >
                                                        <Switch />
                                                    </Form.Item>
                                                </Col>
                                                <Col span={12}>
                                                    <Form.Item
                                                        name="enable_keyframes"
                                                        label={<span className="font-bold text-slate-700">视觉关键帧提取</span>}
                                                        valuePropName="checked"
                                                        tooltip="如果关闭，知识提取将仅基于语音文本，不参考视觉场景。"
                                                    >
                                                        <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                                                    </Form.Item>
                                                    <Form.Item
                                                        name="enable_scenes"
                                                        label={<span className="font-bold text-slate-700">场景深度分割</span>}
                                                        valuePropName="checked"
                                                        tooltip="利用 OpenCV 算法检测视频画面剧烈变化，辅助知识点定位。"
                                                    >
                                                        <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                                                    </Form.Item>
                                                </Col>
                                            </Row>
                                            <Divider />
                                            <div className="bg-indigo-50/50 p-6 rounded-2xl border border-indigo-100/50">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <InfoCircleOutlined className="text-indigo-500" />
                                                    <span className="font-bold text-indigo-900">算力调度提示</span>
                                                </div>
                                                <p className="text-xs text-indigo-700 leading-relaxed m-0">
                                                    当前系统检测到本地搭载了 NVIDIA CUDA 硬件加速。Medium 级以上模型将优先分配至 GPU 处理。视频转录预计将提升约 8-12 倍性能。
                                                </p>
                                            </div>
                                        </Card>
                                    ),
                                },
                                {
                                    key: '2',
                                    label: <Space><DatabaseOutlined />存储与架构</Space>,
                                    children: (
                                        <Card className="border-none shadow-sm rounded-2xl mt-4">
                                            <Row gutter={48}>
                                                <Col span={12}>
                                                    <Form.Item
                                                        name="max_upload_size"
                                                        label={<span className="font-bold text-slate-700">单文件最大限制 (MB)</span>}
                                                    >
                                                        <InputNumber min={1} max={10240} className="w-full" size="large" addonAfter="MB" />
                                                    </Form.Item>
                                                    <Form.Item
                                                        name="api_timeout"
                                                        label={<span className="font-bold text-slate-700">全局接口超时时间 (秒)</span>}
                                                    >
                                                        <InputNumber min={60} max={86400} className="w-full" size="large" addonAfter="Seconds" />
                                                    </Form.Item>
                                                </Col>
                                                <Col span={12}>
                                                    <Form.Item
                                                        name="storage_path"
                                                        label={<span className="font-bold text-slate-700">资源磁盘挂载点</span>}
                                                    >
                                                        <Input size="large" prefix={<CloudServerOutlined className="text-slate-400" />} />
                                                    </Form.Item>
                                                </Col>
                                            </Row>
                                        </Card>
                                    ),
                                },
                                {
                                    key: '3',
                                    label: <Space><SafetyCertificateOutlined />安全与凭据</Space>,
                                    children: (
                                        <Card className="border-none shadow-sm rounded-2xl mt-4">
                                            <div className="space-y-6">
                                                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100">
                                                    <div>
                                                        <div className="font-bold text-slate-800">API 网关访问密钥 (Master Key)</div>
                                                        <div className="text-xs text-slate-500 font-mono mt-1">************************-SCM-2026</div>
                                                    </div>
                                                    <Button type="link">重置密钥</Button>
                                                </div>
                                                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100">
                                                    <div>
                                                        <div className="font-bold text-slate-800">外部 OCR 服务凭证 (Azure/Google)</div>
                                                        <div className="text-xs text-slate-500 mt-1 italic">未配置 - 当前优先使用本地模型</div>
                                                    </div>
                                                    <Button type="primary" ghost size="small">立即配置</Button>
                                                </div>
                                            </div>
                                        </Card>
                                    ),
                                },
                                {
                                    key: '4',
                                    label: <Space><BellOutlined />消息通知</Space>,
                                    children: (
                                        <Card className="border-none shadow-sm rounded-2xl mt-4">
                                            <Row gutter={[48, 24]}>
                                                <Col span={12}>
                                                    <div className="flex items-center justify-between p-4 rounded-xl hover:bg-slate-50 transition-colors">
                                                        <div>
                                                            <div className="font-bold text-slate-800">系统内部弹窗通知</div>
                                                            <Text type="secondary" className="text-xs">分析完成或任务失败时在网页顶部弹出</Text>
                                                        </div>
                                                        <Form.Item name="notification_system" valuePropName="checked" noStyle>
                                                            <Switch />
                                                        </Form.Item>
                                                    </div>
                                                </Col>
                                                <Col span={12}>
                                                    <div className="flex items-center justify-between p-4 rounded-xl hover:bg-slate-50 transition-colors">
                                                        <div>
                                                            <div className="font-bold text-slate-800">邮件实时报告推送</div>
                                                            <Text type="secondary" className="text-xs">将知识点提取报告发送至管理员邮箱</Text>
                                                        </div>
                                                        <Form.Item name="notification_email" valuePropName="checked" noStyle>
                                                            <Switch />
                                                        </Form.Item>
                                                    </div>
                                                </Col>
                                            </Row>
                                        </Card>
                                    ),
                                },
                            ]}
                        />
                    </Form>

                    {/* 底部声明 */}
                    <div className="text-center pt-8 opacity-40">
                        <Text type="secondary" className="text-[10px] uppercase font-bold tracking-widest">
                            SmartCourseEngine Configuration Protocol Module v2.0
                        </Text>
                    </div>
                </div>
            </Content>
        </div>
    )
}
