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
  Tree,
  message,
  Popconfirm,
  Tooltip,
  Badge,
  Avatar,
  Row,
  Col,
  Statistic,
  Descriptions,
  Timeline,
  Progress,
} from 'antd'
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
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
  HistoryOutlined,
  StarOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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

export default function KnowledgePage() {
  const [searchText, setSearchText] = useState('')
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  const [isGraphModalOpen, setIsGraphModalOpen] = useState(false)
  const [selectedPoint, setSelectedPoint] = useState<KnowledgePoint | null>(null)
  const [knowledgeGraph, setKnowledgeGraph] = useState<KnowledgeGraph | null>(null)
  const [activeTab, setActiveTab] = useState('list')
  const queryClient = useQueryClient()

  // 获取知识点列表
  const { data: knowledgeData, isLoading, refetch } = useQuery({
    queryKey: ['knowledge', searchText],
    queryFn: () => api.knowledge.getKnowledgePoints({ search: searchText }),
  })

  const knowledgePoints: KnowledgePoint[] = knowledgeData?.data?.items || []

  // 获取知识图谱
  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: ['knowledge-graph'],
    queryFn: () => {
      // 模拟知识图谱数据
      return Promise.resolve({
        success: true,
        message: '知识图谱获取成功',
        data: {
          nodes: [
            { id: 'kp_1', type: 'knowledge_point', name: '变量声明', category: '编程基础', importance: 3 },
            { id: 'kp_2', type: 'knowledge_point', name: '数据类型', category: '编程基础', importance: 4 },
            { id: 'kp_3', type: 'knowledge_point', name: '条件语句', category: '控制流', importance: 4 },
            { id: 'kp_4', type: 'knowledge_point', name: '循环语句', category: '控制流', importance: 4 },
            { id: 'concept_变量', type: 'concept', name: '变量', category: '编程基础' },
            { id: 'concept_赋值', type: 'concept', name: '赋值', category: '编程基础' },
            { id: 'concept_数据类型', type: 'concept', name: '数据类型', category: '编程基础' },
            { id: 'concept_if语句', type: 'concept', name: 'if语句', category: '控制流' },
            { id: 'concept_循环', type: 'concept', name: '循环', category: '控制流' },
          ],
          edges: [
            { source: 'kp_1', target: 'concept_变量', type: 'contains', weight: 0.9 },
            { source: 'kp_1', target: 'concept_赋值', type: 'contains', weight: 0.8 },
            { source: 'kp_2', target: 'concept_数据类型', type: 'contains', weight: 0.9 },
            { source: 'kp_3', target: 'concept_if语句', type: 'contains', weight: 0.85 },
            { source: 'kp_4', target: 'concept_循环', type: 'contains', weight: 0.85 },
            { source: 'kp_1', target: 'kp_2', type: 'precedes', weight: 0.8 },
            { source: 'kp_2', target: 'kp_3', type: 'precedes', weight: 0.7 },
            { source: 'kp_3', target: 'kp_4', type: 'precedes', weight: 0.7 },
          ],
          metadata: {
            total_nodes: 9,
            total_edges: 8,
            knowledge_points: 4,
            generated_at: '2026-03-01T20:37:00Z',
          },
        },
      })
    },
  })

  // 删除知识点
  const deleteMutation = useMutation({
    mutationFn: (id: number) => {
      // 模拟删除API
      return Promise.resolve({ success: true, message: '删除成功' })
    },
    onSuccess: () => {
      message.success('知识点删除成功')
      queryClient.invalidateQueries({ queryKey: ['knowledge'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '删除失败')
    },
  })

  const handleSearch = (value: string) => {
    setSearchText(value)
  }

  const handleViewDetails = (point: KnowledgePoint) => {
    setSelectedPoint(point)
    setIsDetailModalOpen(true)
  }

  const handleViewGraph = () => {
    setKnowledgeGraph(graphData?.data || null)
    setIsGraphModalOpen(true)
  }

  const handleDelete = (id: number) => {
    deleteMutation.mutate(id)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getImportanceColor = (importance: number) => {
    switch (importance) {
      case 1: return 'green'
      case 2: return 'blue'
      case 3: return 'orange'
      case 4: return 'red'
      case 5: return 'purple'
      default: return 'default'
    }
  }

  const getImportanceText = (importance: number) => {
    switch (importance) {
      case 1: return '低'
      case 2: return '中'
      case 3: return '高'
      case 4: return '重要'
      case 5: return '核心'
      default: return '未知'
    }
  }

  const columns: ColumnsType<KnowledgePoint> = [
    {
      title: '知识点',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500, marginBottom: 4 }}>{text}</div>
          <div style={{ fontSize: 12, color: '#666' }}>
            {record.description?.substring(0, 60)}...
          </div>
        </div>
      ),
    },
    {
      title: '所属课程',
      dataIndex: 'course',
      key: 'course',
      width: 120,
      render: (course) => (
        course ? (
          <Space>
            <Avatar size="small" src={course.thumbnail_url} icon={<BookOutlined />} />
            <span>{course.title}</span>
          </Space>
        ) : (
          <Tag color="default">未关联</Tag>
        )
      ),
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category) => (
        <Tag color="blue">{category}</Tag>
      ),
    },
    {
      title: '重要性',
      dataIndex: 'importance',
      key: 'importance',
      width: 100,
      render: (importance) => (
        <Badge 
          color={getImportanceColor(importance)} 
          text={getImportanceText(importance)}
        />
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 100,
      render: (confidence) => (
        <Progress 
          percent={Math.round(confidence * 100)} 
          size="small" 
          strokeColor={confidence > 0.8 ? '#52c41a' : confidence > 0.6 ? '#faad14' : '#f5222d'}
        />
      ),
    },
    {
      title: '时间范围',
      key: 'time_range',
      width: 120,
      render: (_, record) => (
        <div style={{ fontSize: 12 }}>
          {formatTime(record.start_time)} - {formatTime(record.end_time)}
        </div>
      ),
    },
    {
      title: '概念',
      dataIndex: 'concepts',
      key: 'concepts',
      render: (concepts) => (
        <Space size={[0, 4]} wrap>
          {concepts?.slice(0, 3).map((concept: string) => (
            <Tag key={concept} color="green">{concept}</Tag>
          ))}
          {concepts && concepts.length > 3 && (
            <Tag>+{concepts.length - 3}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 100,
      render: (date) => dayjs(date).format('MM-DD'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个知识点吗？"
            description="删除后无法恢复。"
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

  const knowledgeStats = {
    total: knowledgePoints.length,
    categories: Array.from(new Set(knowledgePoints.map(kp => kp.category))).length,
    concepts: knowledgePoints.reduce((acc, kp) => acc + (kp.concepts?.length || 0), 0),
    highImportance: knowledgePoints.filter(kp => kp.importance >= 4).length,
  }

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
          <h2 style={{ margin: 0 }}>知识管理</h2>
          <p style={{ margin: 0, color: '#666', fontSize: 14 }}>
            管理所有知识点，查看知识图谱，进行知识搜索和关联
          </p>
        </div>
        <Space>
          <Search
            placeholder="搜索知识点名称或描述"
            allowClear
            enterButton={<SearchOutlined />}
            onSearch={handleSearch}
            style={{ width: 300 }}
          />
          <Button icon={<FilterOutlined />}>筛选</Button>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
          <Button 
            type="primary" 
            icon={<ClusterOutlined />}
            onClick={handleViewGraph}
          >
            查看知识图谱
          </Button>
        </Space>
      </Header>
      <Content style={{ margin: '24px' }}>
        {/* 统计卡片 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="知识点总数"
                value={knowledgeStats.total}
                prefix={<BookOutlined />}
                valueStyle={{ color: '#3b82f6' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="知识类别"
                value={knowledgeStats.categories}
                prefix={<NodeIndexOutlined />}
                valueStyle={{ color: '#10b981' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="概念数量"
                value={knowledgeStats.concepts}
                prefix={<LinkOutlined />}
                valueStyle={{ color: '#8b5cf6' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="重要知识点"
                value={knowledgeStats.highImportance}
                prefix={<StarOutlined />}
                valueStyle={{ color: '#f59e0b' }}
              />
            </Card>
          </Col>
        </Row>

        <Card
          tabList={[
            { key: 'list', tab: '知识点列表' },
            { key: 'tree', tab: '知识树' },
            { key: 'search', tab: '高级搜索' },
          ]}
          activeTabKey={activeTab}
          onTabChange={setActiveTab}
        >
          {activeTab === 'list' && (
            <Table
              columns={columns}
              dataSource={knowledgePoints}
              rowKey="id"
              loading={isLoading}
              pagination={{
                total: knowledgeData?.data?.total || 0,
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
            />
          )}
          
          {activeTab === 'tree' && (
            <div style={{ padding: 24, textAlign: 'center' }}>
              <Tree
                showLine
                defaultExpandedKeys={['root']}
                treeData={[
                  {
                    title: '编程基础',
                    key: 'programming',
                    children: [
                      {
                        title: '变量和数据类型',
                        key: 'variables',
                        children: [
                          { title: '变量声明', key: 'var-declaration' },
                          { title: '数据类型', key: 'data-types' },
                          { title: '类型转换', key: 'type-conversion' },
                        ],
                      },
                      {
                        title: '运算符',
                        key: 'operators',
                        children: [
                          { title: '算术运算符', key: 'arithmetic' },
                          { title: '比较运算符', key: 'comparison' },
                          { title: '逻辑运算符', key: 'logical' },
                        ],
                      },
                    ],
                  },
                  {
                    title: '控制流',
                    key: 'control-flow',
                    children: [
                      {
                        title: '条件语句',
                        key: 'conditionals',
                        children: [
                          { title: 'if语句', key: 'if-statement' },
                          { title: 'else语句', key: 'else-statement' },
                          { title: 'switch语句', key: 'switch-statement' },
                        ],
                      },
                      {
                        title: '循环语句',
                        key: 'loops',
                        children: [
                          { title: 'for循环', key: 'for-loop' },
                          { title: 'while循环', key: 'while-loop' },
                          { title: 'do-while循环', key: 'do-while-loop' },
                        ],
                      },
                    ],
                  },
                ]}
              />
            </div>
          )}
          
          {activeTab === 'search' && (
            <div style={{ padding: 24 }}>
              <Form layout="vertical">
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="关键词搜索">
                      <Input placeholder="输入关键词" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="知识类别">
                      <Select placeholder="选择知识类别" mode="multiple">
                        <Option value="programming">编程基础</Option>
                        <Option value="control-flow">控制流</Option>
                        <Option value="functions">函数</Option>
                        <Option value="oop">面向对象</Option>
                        <Option value="data-structures">数据结构</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>
                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item label="重要性">
                      <Select placeholder="选择重要性" mode="multiple">
                        <Option value={1}>低</Option>
                        <Option value={2}>中</Option>
                        <Option value={3}>高</Option>
                        <Option value={4}>重要</Option>
                        <Option value={5}>核心</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item label="置信度阈值">
                      <InputNumber 
                        min={0} 
                        max={1} 
                        step={0.1}
                        placeholder="0.0-1.0"
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item label="时间范围">
                      <Input placeholder="开始时间-结束时间" />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item>
                  <Button type="primary" icon={<FileSearchOutlined />}>
                    开始搜索
                  </Button>
                </Form.Item>
              </Form>
            </div>
          )}
        </Card>
      </Content>

      {/* 知识点详情模态框 */}
      <Modal
        title="知识点详情"
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={null}
        width={700}
      >
        {selectedPoint && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="知识点名称" span={2}>
                <div style={{ fontSize: 16, fontWeight: 500 }}>
                  {selectedPoint.name}
                </div>
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedPoint.description}
              </Descriptions.Item>
              <Descriptions.Item label="所属课程">
                {selectedPoint.course ? (
                  <Space>
                    <Avatar size="small" src={selectedPoint.course.thumbnail_url} />
                    <span>{selectedPoint.course.title}</span>
                  </Space>
                ) : (
                  '未关联'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="知识类别">
                <Tag color="blue">{selectedPoint.category}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="重要性">
                <Badge 
                  color={getImportanceColor(selectedPoint.importance)} 
                  text={getImportanceText(selectedPoint.importance)}
                />
              </Descriptions.Item>
              <Descriptions.Item label="置信度">
                <Progress 
                  percent={Math.round(selectedPoint.confidence * 100)} 
                  size="small" 
                  strokeColor={selectedPoint.confidence > 0.8 ? '#52c41a' : selectedPoint.confidence > 0.6 ? '#faad14' : '#f5222d'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="时间范围">
                {formatTime(selectedPoint.start_time)} - {formatTime(selectedPoint.end_time)}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedPoint.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {dayjs(selectedPoint.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="关联概念" span={2}>
                <Space size={[4, 8]} wrap>
                  {selectedPoint.concepts?.map((concept) => (
                    <Tag key={concept} color="green">{concept}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Card title="时间线" style={{ marginTop: 16 }}>
              <Timeline>
                <Timeline.Item color="green">
                  <p>知识点创建</p>
                  <p style={{ fontSize: 12, color: '#666' }}>
                    {dayjs(selectedPoint.created_at).format('YYYY-MM-DD HH:mm:ss')}
                  </p>
                </Timeline.Item>
                <Timeline.Item color="blue">
                  <p>知识点更新</p>
                  <p style={{ fontSize: 12, color: '#666' }}>
                    {dayjs(selectedPoint.updated_at).format('YYYY-MM-DD HH:mm:ss')}
                  </p>
                </Timeline.Item>
                <Timeline.Item color="orange">
                  <p>嵌入向量生成</p>
                  <p style={{ fontSize: 12, color: '#666' }}>
                    维度: {selectedPoint.embedding?.length || 0}
                  </p>
                </Timeline.Item>
              </Timeline>
            </Card>
          </div>
        )}
      </Modal>

      {/* 知识图谱模态框 */}
      <Modal
        title="知识图谱"
        open={isGraphModalOpen}
        onCancel={() => setIsGraphModalOpen(false)}
        footer={null}
        width={900}
      >
        {knowledgeGraph && (
          <div>
            <Descriptions bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="节点总数">
                {knowledgeGraph.metadata.total_nodes}
              </Descriptions.Item>
              <Descriptions.Item label="边总数">
                {knowledgeGraph.metadata.total_edges}
              </Descriptions.Item>
              <Descriptions.Item label="知识点数量">
                {knowledgeGraph.metadata.knowledge_points}
              </Descriptions.Item>
              <Descriptions.Item label="生成时间">
                {dayjs(knowledgeGraph.metadata.generated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ 
              border: '1px solid #d9d9d9', 
              borderRadius: 8, 
              padding: 24,
              minHeight: 400,
              background: '#fafafa',
              textAlign: 'center',
            }}>
              <ClusterOutlined style={{ fontSize: 48, color: '#3b82f6', marginBottom: 16 }} />
              <h3>知识图谱可视化</h3>
              <p style={{ color: '#666', marginBottom: 24 }}>
                这是一个模拟的知识图谱可视化界面。在实际部署中，这里会显示交互式的知识图谱。
              </p>
              
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Card title="节点类型" size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{ width: 12, height: 12, background: '#3b82f6', borderRadius: '50%', marginRight: 8 }} />
                        <span>知识点节点 ({knowledgeGraph.nodes.filter(n => n.type === 'knowledge_point').length})</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{ width: 12, height: 12, background: '#10b981', borderRadius: '50%', marginRight: 8 }} />
                        <span>概念节点 ({knowledgeGraph.nodes.filter(n => n.type === 'concept').length})</span>
                      </div>
                    </Space>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="关系类型" size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{ width: 20, height: 2, background: '#8b5cf6', marginRight: 8 }} />
                        <span>包含关系 ({knowledgeGraph.edges.filter(e => e.type === 'contains').length})</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{ width: 20, height: 2, background: '#f59e0b', marginRight: 8 }} />
                        <span>先后关系 ({knowledgeGraph.edges.filter(e => e.type === 'precedes').length})</span>
                      </div>
                    </Space>
                  </Card>
                </Col>
              </Row>

              <div style={{ marginTop: 24 }}>
                <h4>知识图谱数据</h4>
                <div style={{ 
                  maxHeight: 200, 
                  overflowY: 'auto', 
                  border: '1px solid #d9d9d9',
                  borderRadius: 4,
                  padding: 8,
                  background: '#fff',
                  fontSize: 12,
                }}>
                  <pre>{JSON.stringify(knowledgeGraph, null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </Layout>
  )
}
