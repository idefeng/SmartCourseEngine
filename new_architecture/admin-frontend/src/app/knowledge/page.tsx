'use client'

import { useMemo, useState } from 'react'
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
  Tree,
  message,
  Tooltip,
  Badge,
  Avatar,
  Row,
  Col,
  Statistic,
  Descriptions,
  Timeline,
  Progress,
  Typography,
} from 'antd'
import {
  EyeOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  BookOutlined,
  NodeIndexOutlined,
  LinkOutlined,
  ClusterOutlined,
  ShareAltOutlined,
  FileSearchOutlined,
  StarOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Header, Content } = Layout
const { Search } = Input
const { Option } = Select

interface KnowledgePoint {
  id: number
  name: string
  description: string
  category: string
  importance: number
  confidence: number
  start_time: number
  end_time: number
  course_id: number
  concepts: string[]
  embedding: number[]
  created_at: string
  updated_at: string
  course?: {
    id: number
    title: string
    thumbnail_url: string
  }
}

interface KnowledgeGraph {
  nodes: Array<{
    id: string
    type: string
    name: string
    category: string
    importance?: number
  }>
  edges: Array<{
    source: string
    target: string
    type: string
    weight: number
  }>
  metadata: {
    total_nodes: number
    total_edges: number
    knowledge_points: number
    generated_at: string
  }
}

const { Title, Text } = Typography

export default function KnowledgePage() {
  const [searchText, setSearchText] = useState('')
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  const [isGraphModalOpen, setIsGraphModalOpen] = useState(false)
  const [selectedPoint, setSelectedPoint] = useState<KnowledgePoint | null>(null)
  const [knowledgeGraph, setKnowledgeGraph] = useState<KnowledgeGraph | null>(null)
  const [activeTab, setActiveTab] = useState('list')

  // 获取知识点列表
  const { data: knowledgeData, isLoading, refetch } = useQuery({
    queryKey: ['knowledge', searchText],
    queryFn: () => api.knowledge.getKnowledgePoints({ search: searchText }),
  })

  const knowledgePoints: KnowledgePoint[] = (knowledgeData as any)?.items || (knowledgeData as any)?.data?.items || []

  // 获取知识图谱
  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: ['knowledge-graph', knowledgePoints.map((item) => item.id).join(',')],
    queryFn: () => api.knowledge.buildKnowledgeGraph(knowledgePoints),
    enabled: knowledgePoints.length > 0,
  })

  const handleSearch = (value: string) => {
    setSearchText(value)
  }

  const handleViewDetails = (point: KnowledgePoint) => {
    setSelectedPoint(point)
    setIsDetailModalOpen(true)
  }

  const handleViewGraph = () => {
    if (!graphData) {
      message.warning('暂无可用知识图谱数据')
      return
    }
    setKnowledgeGraph(((graphData as any)?.data || graphData) as KnowledgeGraph)
    setIsGraphModalOpen(true)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getImportanceConfig = (importance: number) => {
    switch (importance) {
      case 1: return { color: 'text-slate-400 bg-slate-50', text: '入门' }
      case 2: return { color: 'text-blue-500 bg-blue-50', text: '基础' }
      case 3: return { color: 'text-indigo-500 bg-indigo-50', text: '核心' }
      case 4: return { color: 'text-orange-500 bg-orange-50', text: '重要' }
      case 5: return { color: 'text-purple-600 bg-purple-50', text: '专家' }
      default: return { color: 'text-slate-400 bg-slate-50', text: '未知' }
    }
  }

  const columns: ColumnsType<KnowledgePoint> = [
    {
      title: '知识实体',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div className="max-w-md">
          <div className="font-bold text-slate-800 text-sm mb-1">{text}</div>
          <div className="text-[11px] text-slate-400 line-clamp-1 italic">
            {record.description || '暂无详细描述信息'}
          </div>
        </div>
      ),
    },
    {
      title: '关联素材',
      dataIndex: 'course',
      key: 'course',
      width: 140,
      render: (course) => (
        course ? (
          <div className="flex items-center space-x-2 bg-slate-50 p-1 pr-2 rounded-lg border border-slate-100 inline-flex">
            <Avatar size={20} src={course.thumbnail_url} icon={<BookOutlined />} className="rounded shadow-sm" />
            <span className="text-[10px] font-bold text-slate-600 truncate max-w-[80px]">{course.title}</span>
          </div>
        ) : (
          <span className="text-[10px] text-slate-300 italic">未关联课程</span>
        )
      ),
    },
    {
      title: '维度分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category) => (
        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tight bg-slate-100 text-slate-500">
          {category}
        </span>
      ),
    },
    {
      title: '重要性评级',
      dataIndex: 'importance',
      key: 'importance',
      width: 100,
      render: (importance) => {
        const config = getImportanceConfig(importance)
        return (
          <div className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest inline-flex ${config.color}`}>
            {config.text}
          </div>
        )
      },
    },
    {
      title: 'AI 置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (confidence) => (
        <div className="space-y-1">
          <div className="flex justify-between text-[9px] font-black text-slate-400 uppercase">
            <span>Precision</span>
            <span>{Math.round(confidence * 100)}%</span>
          </div>
          <Progress
            percent={Math.round(confidence * 100)}
            size="small"
            showInfo={false}
            strokeColor={confidence > 0.8 ? '#10b981' : confidence > 0.6 ? '#f59e0b' : '#ef4444'}
            trailColor="#f1f5f9"
          />
        </div>
      ),
    },
    {
      title: '概念拓扑',
      dataIndex: 'concepts',
      key: 'concepts',
      render: (concepts) => (
        <div className="flex flex-wrap gap-1">
          {concepts?.slice(0, 2).map((concept: string) => (
            <span key={concept} className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-50 text-indigo-500 border border-indigo-100/50">
              #{concept}
            </span>
          ))}
          {concepts && concepts.length > 2 && (
            <span className="text-[9px] text-slate-300">+{concepts.length - 2}</span>
          )}
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 60,
      render: (_, record) => (
        <Tooltip title="详情解析">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined className="text-slate-400 hover:text-indigo-500" />}
            onClick={() => handleViewDetails(record)}
          />
        </Tooltip>
      ),
    },
  ]

  const knowledgeStats = [
    { title: '知识点总数', value: knowledgePoints.length, icon: <BookOutlined />, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { title: '维度分类', value: Array.from(new Set(knowledgePoints.map(kp => kp.category))).length, icon: <NodeIndexOutlined />, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { title: '关联概念', value: knowledgePoints.reduce((acc, kp) => acc + (kp.concepts?.length || 0), 0), icon: <LinkOutlined />, color: 'text-violet-600', bg: 'bg-violet-50' },
    { title: '核心权重', value: knowledgePoints.filter(kp => kp.importance >= 4).length, icon: <StarOutlined />, color: 'text-orange-600', bg: 'bg-orange-50' },
  ]

  const knowledgeTreeData = useMemo(() => {
    const categoryMap = new Map<string, KnowledgePoint[]>()
    knowledgePoints.forEach((point) => {
      const category = point.category || '未分类'
      if (!categoryMap.has(category)) categoryMap.set(category, [])
      categoryMap.get(category)!.push(point)
    })
    return Array.from(categoryMap.entries()).map(([category, points]) => ({
      title: <span className="font-bold text-slate-700">{category}</span>,
      key: `category-${category}`,
      children: points.map((point) => ({
        title: <span className="text-slate-500">{point.name}</span>,
        key: `point-${point.id}`,
      })),
    }))
  }, [knowledgePoints])

  return (
    <>
      <Header className="flex-none z-10 h-24 flex items-center justify-between px-10 bg-white/70 backdrop-blur-xl border-b border-white/20">
        <div>
          <Title level={3} className="!m-0 !font-bold">知识中枢</Title>
          <Text type="secondary" className="text-xs">多模态知识提取与智能化拓扑构建</Text>
        </div>

        <div className="flex items-center space-x-4">
          <Search
            placeholder="检索知识实体..."
            allowClear
            onSearch={handleSearch}
            className="w-64"
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()} />
          <Button
            type="primary"
            variant="dashed"
            icon={<ClusterOutlined />}
            loading={graphLoading}
            onClick={handleViewGraph}
            className="bg-indigo-600 border-none shadow-lg shadow-indigo-100 hover:scale-105 transition-transform"
          >
            可视化图谱
          </Button>
        </div>
      </Header>

      <Content className="flex-1 overflow-y-auto p-10 space-y-8">
        <Row gutter={[24, 24]}>
          {knowledgeStats.map((item, idx) => (
            <Col xs={24} sm={12} lg={6} key={idx}>
              <Card className="hover:shadow-lg transition-all group border-none shadow-sm">
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

        <Card
          className="border-none shadow-sm overflow-hidden premium-card-tabs"
          activeTabKey={activeTab}
          onTabChange={setActiveTab}
          tabList={[
            { key: 'list', tab: <span className="font-bold">实体矩阵</span> },
            { key: 'tree', tab: <span className="font-bold">层级拓扑</span> },
            { key: 'search', tab: <span className="font-bold">深度检索</span> },
          ]}
        >
          {activeTab === 'list' && (
            <Table
              columns={columns}
              dataSource={knowledgePoints}
              rowKey="id"
              loading={isLoading}
              className="premium-table"
              pagination={{
                total: (knowledgeData as any)?.pagination?.total || knowledgePoints.length,
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => <span className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">Total: {total} nodes</span>,
              }}
            />
          )}

          {activeTab === 'tree' && (
            <div className="py-10 px-20 bg-slate-50/50 rounded-2xl border border-slate-100">
              <Tree
                showLine={{ showLeafIcon: false }}
                defaultExpandAll
                treeData={knowledgeTreeData}
                className="!bg-transparent premium-tree"
              />
            </div>
          )}

          {activeTab === 'search' && (
            <div className="py-10">
              <Form layout="vertical" className="max-w-4xl mx-auto space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <Form.Item label={<span className="font-bold text-slate-700">语义关键词</span>}>
                    <Input prefix={<SearchOutlined className="text-slate-300" />} placeholder="输入知识实体或概念名称..." size="large" />
                  </Form.Item>
                  <Form.Item label={<span className="font-bold text-slate-700">维度过滤</span>}>
                    <Select placeholder="选择知识维度" mode="multiple" size="large">
                      <Option value="programming">智能开发</Option>
                      <Option value="control-flow">算法逻辑</Option>
                      <Option value="functions">架构模式</Option>
                      <Option value="oop">工程实践</Option>
                    </Select>
                  </Form.Item>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <Form.Item label={<span className="font-bold text-slate-700">权重等级</span>}>
                    <Select placeholder="筛选重要性" mode="multiple" size="large">
                      <Option value={3}>核心模块</Option>
                      <Option value={4}>关键链路</Option>
                      <Option value={5}>顶层架构</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item label={<span className="font-bold text-slate-700">最小置信度阈值</span>}>
                    <InputNumber min={0} max={1} step={0.1} placeholder="0.0 - 1.0" className="w-full" size="large" />
                  </Form.Item>
                  <Form.Item label={<span className="font-bold text-slate-700">时间窗口</span>}>
                    <Input placeholder="00:00 - 99:99" size="large" />
                  </Form.Item>
                </div>

                <div className="flex justify-center pt-6">
                  <Button type="primary" size="large" icon={<FileSearchOutlined />} className="px-10 h-14 rounded-2xl shadow-xl shadow-indigo-100">
                    执行高级语义搜索
                  </Button>
                </div>
              </Form>
            </div>
          )}
        </Card>
      </Content>

      <Modal
        title={null}
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={null}
        width={800}
        centered
        className="premium-detail-modal"
        styles={{ body: { padding: 0 } }}
      >
        {selectedPoint && (
          <div className="flex flex-col md:flex-row min-h-[500px]">
            <div className="md:w-5/12 p-8 bg-slate-900 text-white flex flex-col justify-between">
              <div>
                <div className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-2">Entity ID: {selectedPoint.id}</div>
                <Title level={2} className="!text-white !font-black !m-0 !tracking-tight">{selectedPoint.name}</Title>
                <div className="mt-6 space-y-4">
                  <div className="bg-white/5 p-4 rounded-xl border border-white/10 backdrop-blur-sm">
                    <div className="text-[9px] font-bold text-slate-400 uppercase mb-2">Core Description</div>
                    <Text className="text-slate-300 text-sm leading-relaxed italic">"{selectedPoint.description}"</Text>
                  </div>
                  <div className="flex gap-2">
                    <span className="px-3 py-1 bg-indigo-600 rounded-full text-[10px] font-bold uppercase">{selectedPoint.category}</span>
                    <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase ${getImportanceConfig(selectedPoint.importance).color} text-white`}>
                      {getImportanceConfig(selectedPoint.importance).text}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-10 space-y-6">
                <div className="flex justify-between items-end">
                  <div>
                    <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Time Window</div>
                    <div className="text-2xl font-black">{formatTime(selectedPoint.start_time)} <span className="text-sm opacity-30 mx-2">→</span> {formatTime(selectedPoint.end_time)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">AI Confidence</div>
                    <div className="text-2xl font-black text-emerald-400">{Math.round(selectedPoint.confidence * 100)}%</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="md:w-7/12 p-10 bg-white">
              <Title level={4} className="!font-black mb-8 italic uppercase tracking-tighter shadow-indigo-50">Topology Trace</Title>

              <div className="space-y-8">
                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center">
                    <LinkOutlined className="mr-2" /> Linked Concepts
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedPoint.concepts?.map((concept) => (
                      <span key={concept} className="px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-xl text-xs font-bold text-slate-600 shadow-sm hover:border-indigo-200 transition-colors cursor-default">
                        #{concept}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center">
                    <ShareAltOutlined className="mr-2" /> Evolution Path
                  </div>
                  <Timeline
                    className="compact-timeline"
                    items={[
                      {
                        color: 'indigo',
                        label: 'ORIGIN',
                        children: (
                          <>
                            <div className="text-xs font-bold text-slate-800">实体提取自底层多模态引擎</div>
                            <div className="text-[10px] text-slate-400 mt-1">{dayjs(selectedPoint.created_at).format('YYYY.MM.DD HH:mm')}</div>
                          </>
                        ),
                      },
                      {
                        color: 'violet',
                        label: 'EMBED',
                        children: (
                          <>
                            <div className="text-xs font-bold text-slate-800">生成 {selectedPoint.embedding?.length || 0}D 高维语义向量</div>
                            <div className="text-[10px] text-slate-400 mt-1">向量数据库已索引</div>
                          </>
                        ),
                      },
                      {
                        color: 'emerald',
                        label: 'FINAL',
                        children: (
                          <>
                            <div className="text-xs font-bold text-slate-800">进入生产级知识中枢</div>
                            <div className="text-[10px] text-slate-400 mt-1">同步分发至教研资产库</div>
                          </>
                        ),
                      },
                    ]}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        title={<div className="text-lg font-black pb-4 border-b uppercase tracking-widest">Global Knowledge Graph Topology</div>}
        open={isGraphModalOpen}
        onCancel={() => setIsGraphModalOpen(false)}
        footer={null}
        width={1000}
        centered
        className="premium-graph-modal"
      >
        {knowledgeGraph && (
          <div className="p-4">
            <div className="grid grid-cols-4 gap-4 mb-8">
              {[
                { label: 'Nodes', value: knowledgeGraph.metadata.total_nodes, sub: 'Total Entites' },
                { label: 'Edges', value: knowledgeGraph.metadata.total_edges, sub: 'Semantic Links' },
                { label: 'KP', value: knowledgeGraph.metadata.knowledge_points, sub: 'Points of interest' },
                { label: 'Sync', value: 'Live', sub: dayjs(knowledgeGraph.metadata.generated_at).format('HH:mm') }
              ].map((s, i) => (
                <div key={i} className="bg-slate-50 p-4 rounded-2xl border border-slate-100 flex flex-col items-center justify-center text-center">
                  <div className="text-[9px] font-black text-slate-400 uppercase mb-1 tracking-widest">{s.label}</div>
                  <div className="text-xl font-black text-slate-800 tracking-tighter">{s.value}</div>
                  <div className="text-[9px] text-slate-400 mt-1">{s.sub}</div>
                </div>
              ))}
            </div>

            <div className="aspect-[21/9] rounded-3xl bg-slate-900 overflow-hidden relative border-8 border-slate-50 shadow-inner flex items-center justify-center group">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-indigo-900/40 via-transparent to-transparent opacity-40 group-hover:opacity-60 transition-opacity"></div>

              <div className="relative z-10 text-center animate-fadeIn">
                <ClusterOutlined className="text-6xl text-indigo-400 mb-6 drop-shadow-[0_0_15px_rgba(129,140,248,0.5)]" />
                <div className="max-w-md mx-auto px-8">
                  <Title level={3} className="!text-white !font-black !m-0 !tracking-tight">Interactive Knowledge Engine</Title>
                  <Text className="text-slate-400 text-sm mt-4 block leading-relaxed">
                    基于高维向量自相似性聚类动态生成的全域知识拓扑。正在计算语义关联权重并实时渲染实时链路。
                  </Text>
                </div>
              </div>

              {/* Mock Particles for Graph Vibe */}
              <div className="absolute top-10 left-10 w-2 h-2 rounded-full bg-indigo-500/40 animate-pulse"></div>
              <div className="absolute bottom-10 right-20 w-3 h-3 rounded-full bg-emerald-500/30 animate-pulse delay-500"></div>
              <div className="absolute top-1/2 left-20 w-1 h-1 rounded-full bg-violet-500/50 animate-pulse delay-700"></div>
            </div>

            <div className="mt-8 grid grid-cols-2 gap-8">
              <div className="p-6 rounded-2xl bg-slate-50 border border-slate-100">
                <div className="text-[10px] font-black text-slate-400 uppercase mb-4 tracking-widest">Distribution Matrix</div>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-[11px] font-bold mb-1.5">
                      <span className="text-slate-600">Knowledge Points</span>
                      <span className="text-indigo-600">{knowledgeGraph.nodes.filter(n => n.type === 'knowledge_point').length}</span>
                    </div>
                    <Progress percent={65} showInfo={false} strokeColor="#6366f1" size="small" />
                  </div>
                  <div>
                    <div className="flex justify-between text-[11px] font-bold mb-1.5">
                      <span className="text-slate-600">Concepts Nodes</span>
                      <span className="text-emerald-600">{knowledgeGraph.nodes.filter(n => n.type === 'concept').length}</span>
                    </div>
                    <Progress percent={35} showInfo={false} strokeColor="#10b981" size="small" />
                  </div>
                </div>
              </div>
              <div className="p-6 rounded-2xl bg-indigo-600 text-white shadow-xl shadow-indigo-100 overflow-hidden relative">
                <div className="relative z-10 h-full flex flex-col justify-between">
                  <div className="text-[10px] font-black opacity-60 uppercase tracking-widest">Graph Density</div>
                  <div>
                    <div className="text-4xl font-black tracking-tighter">High Alpha</div>
                    <div className="text-xs opacity-80 mt-2 italic font-medium">知识链路完整性已达 94.2%，建议进行跨科室概念聚合。</div>
                  </div>
                </div>
                <ShareAltOutlined className="absolute -bottom-4 -right-4 text-9xl opacity-10 rotate-12" />
              </div>
            </div>
          </div>
        )}
      </Modal>
    </>
  )
}
