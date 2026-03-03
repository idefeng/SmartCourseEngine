'use client'

import { useState, useEffect } from 'react'
import { 
  Layout, 
  Card, 
  Input, 
  Button, 
  Space, 
  Select, 
  Tag, 
  List, 
  Avatar, 
  Typography, 
  Divider,
  Radio,
  Slider,
  Switch,
  Row,
  Col,
  Statistic,
  Progress,
  Empty,
  Spin,
  Alert,
  Badge,
} from 'antd'
import { 
  SearchOutlined, 
  FilterOutlined,
  ReloadOutlined,
  StarOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  BookOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  NodeIndexOutlined,
  HistoryOutlined,
  FireOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import dayjs from 'dayjs'

const { Header, Content } = Layout
const { Search } = Input
const { Title, Text, Paragraph } = Typography
const { Option } = Select

interface SearchResult {
  id: string
  type: 'course' | 'knowledge_point' | 'document' | 'video' | 'semantic_match'
  title: string
  description: string
  relevance: number
  score: number
  similarity?: number
  metadata: any
  search_type?: string
  weighted_score?: number
}

interface SearchResponse {
  success: boolean
  data: {
    results: SearchResult[]
    total: number
    search_type?: string
    search_time?: string
  }
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState('hybrid')
  const [searchLimit, setSearchLimit] = useState(10)
  const [weights, setWeights] = useState({
    text: 0.4,
    vector: 0.4,
    semantic: 0.2,
  })
  const [filters, setFilters] = useState({
    type: [] as string[],
    category: [] as string[],
    minRelevance: 0.5,
  })
  const [searchHistory, setSearchHistory] = useState<string[]>([])
  const [showFilters, setShowFilters] = useState(false)

  // 搜索查询
  const { data: searchData, isLoading, refetch, isFetching } = useQuery<SearchResponse>({
    queryKey: ['search', query, searchType, searchLimit, weights],
    queryFn: () => {
      if (!query.trim()) {
        return Promise.resolve({ success: true, data: { results: [], total: 0 } })
      }
      
      if (searchType === 'hybrid') {
        return api.search.hybridSearch(query, weights, searchLimit).then((res) => res.data as SearchResponse)
      } else if (searchType === 'semantic') {
        return api.search.semanticSearch(query, searchLimit).then((res) => res.data as SearchResponse)
      } else {
        return api.search.search(query, searchType, searchLimit).then((res) => res.data as SearchResponse)
      }
    },
    enabled: false,
  })

  const searchResults: SearchResult[] = searchData?.data?.results || []
  const searchStats = searchData?.data || { results: [], total: 0 }

  const handleSearch = (value: string) => {
    if (!value.trim()) return
    
    setQuery(value)
    
    // 添加到搜索历史
    if (!searchHistory.includes(value)) {
      setSearchHistory(prev => [value, ...prev.slice(0, 9)])
    }
    
    // 触发搜索
    setTimeout(() => {
      refetch()
    }, 100)
  }

  const handleSearchTypeChange = (type: string) => {
    setSearchType(type)
    if (query) {
      refetch()
    }
  }

  const handleWeightChange = (key: string, value: number) => {
    setWeights(prev => ({
      ...prev,
      [key]: value,
    }))
  }

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
    }))
  }

  const handleClearFilters = () => {
    setFilters({
      type: [],
      category: [],
      minRelevance: 0.5,
    })
  }

  const handleHistoryClick = (historyQuery: string) => {
    setQuery(historyQuery)
    setTimeout(() => {
      refetch()
    }, 100)
  }

  const getResultIcon = (type: string) => {
    switch (type) {
      case 'course':
        return <BookOutlined style={{ color: '#3b82f6' }} />
      case 'knowledge_point':
        return <NodeIndexOutlined style={{ color: '#10b981' }} />
      case 'video':
        return <VideoCameraOutlined style={{ color: '#8b5cf6' }} />
      case 'document':
        return <FileTextOutlined style={{ color: '#f59e0b' }} />
      case 'semantic_match':
        return <ThunderboltOutlined style={{ color: '#ef4444' }} />
      default:
        return <SearchOutlined />
    }
  }

  const getResultColor = (type: string) => {
    switch (type) {
      case 'course': return 'blue'
      case 'knowledge_point': return 'green'
      case 'video': return 'purple'
      case 'document': return 'orange'
      case 'semantic_match': return 'red'
      default: return 'default'
    }
  }

  const getResultTypeText = (type: string) => {
    switch (type) {
      case 'course': return '课程'
      case 'knowledge_point': return '知识点'
      case 'video': return '视频'
      case 'document': return '文档'
      case 'semantic_match': return '语义匹配'
      default: return type
    }
  }

  const filteredResults = searchResults.filter(result => {
    // 类型筛选
    if (filters.type.length > 0 && !filters.type.includes(result.type)) {
      return false
    }
    
    // 相关性筛选
    if (result.relevance < filters.minRelevance) {
      return false
    }
    
    // 类别筛选（如果存在）
    if (filters.category.length > 0 && result.metadata?.category) {
      if (!filters.category.includes(result.metadata.category)) {
        return false
      }
    }
    
    return true
  })

  const searchTypes = [
    { value: 'hybrid', label: '混合搜索', icon: <FireOutlined /> },
    { value: 'text', label: '文本搜索', icon: <FileTextOutlined /> },
    { value: 'vector', label: '向量搜索', icon: <NodeIndexOutlined /> },
    { value: 'semantic', label: '语义搜索', icon: <ThunderboltOutlined /> },
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
          <h2 style={{ margin: 0 }}>智能搜索</h2>
          <p style={{ margin: 0, color: '#666', fontSize: 14 }}>
            支持多种搜索方式，快速找到您需要的课程和知识点
          </p>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
        </Space>
      </Header>
      <Content style={{ margin: '24px' }}>
        {/* 搜索框区域 */}
        <Card style={{ marginBottom: 24 }}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Title level={3}>智能知识搜索</Title>
            <Text type="secondary">
              输入关键词，使用AI技术快速找到相关课程、知识点和视频
            </Text>
          </div>

          <Search
            placeholder="输入您要搜索的内容，例如：Python变量声明、机器学习基础、条件语句等"
            enterButton={
              <Button type="primary" icon={<SearchOutlined />} loading={isFetching}>
                搜索
              </Button>
            }
            size="large"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onSearch={handleSearch}
            style={{ marginBottom: 16 }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text strong>搜索类型：</Text>
              <Radio.Group 
                value={searchType} 
                onChange={(e) => handleSearchTypeChange(e.target.value)}
                buttonStyle="solid"
              >
                {searchTypes.map(type => (
                  <Radio.Button key={type.value} value={type.value}>
                    <Space size={4}>
                      {type.icon}
                      {type.label}
                    </Space>
                  </Radio.Button>
                ))}
              </Radio.Group>
            </Space>

            <Button 
              type="text" 
              icon={<FilterOutlined />}
              onClick={() => setShowFilters(!showFilters)}
            >
              {showFilters ? '隐藏筛选' : '显示筛选'}
            </Button>
          </div>

          {/* 高级筛选 */}
          {showFilters && (
            <Card style={{ marginTop: 16 }}>
              <Row gutter={[16, 16]}>
                <Col span={8}>
                  <div>
                    <Text strong>结果类型：</Text>
                    <Select
                      mode="multiple"
                      placeholder="选择结果类型"
                      value={filters.type}
                      onChange={(value) => handleFilterChange('type', value)}
                      style={{ width: '100%', marginTop: 8 }}
                    >
                      <Option value="course">课程</Option>
                      <Option value="knowledge_point">知识点</Option>
                      <Option value="video">视频</Option>
                      <Option value="document">文档</Option>
                      <Option value="semantic_match">语义匹配</Option>
                    </Select>
                  </div>
                </Col>
                <Col span={8}>
                  <div>
                    <Text strong>知识类别：</Text>
                    <Select
                      mode="multiple"
                      placeholder="选择知识类别"
                      value={filters.category}
                      onChange={(value) => handleFilterChange('category', value)}
                      style={{ width: '100%', marginTop: 8 }}
                    >
                      <Option value="编程基础">编程基础</Option>
                      <Option value="控制流">控制流</Option>
                      <Option value="函数">函数</Option>
                      <Option value="面向对象">面向对象</Option>
                      <Option value="数据结构">数据结构</Option>
                    </Select>
                  </div>
                </Col>
                <Col span={8}>
                  <div>
                    <Text strong>最小相关性：{filters.minRelevance.toFixed(1)}</Text>
                    <Slider
                      min={0}
                      max={1}
                      step={0.1}
                      value={filters.minRelevance}
                      onChange={(value) => handleFilterChange('minRelevance', value)}
                      style={{ marginTop: 8 }}
                    />
                  </div>
                </Col>
              </Row>
              
              {searchType === 'hybrid' && (
                <div style={{ marginTop: 16 }}>
                  <Text strong>搜索权重：</Text>
                  <Row gutter={[16, 8]} style={{ marginTop: 8 }}>
                    <Col span={8}>
                      <div>
                        <Text>文本搜索：{weights.text}</Text>
                        <Slider
                          min={0}
                          max={1}
                          step={0.1}
                          value={weights.text}
                          onChange={(value) => handleWeightChange('text', value)}
                        />
                      </div>
                    </Col>
                    <Col span={8}>
                      <div>
                        <Text>向量搜索：{weights.vector}</Text>
                        <Slider
                          min={0}
                          max={1}
                          step={0.1}
                          value={weights.vector}
                          onChange={(value) => handleWeightChange('vector', value)}
                        />
                      </div>
                    </Col>
                    <Col span={8}>
                      <div>
                        <Text>语义搜索：{weights.semantic}</Text>
                        <Slider
                          min={0}
                          max={1}
                          step={0.1}
                          value={weights.semantic}
                          onChange={(value) => handleWeightChange('semantic', value)}
                        />
                      </div>
                    </Col>
                  </Row>
                </div>
              )}

              <div style={{ marginTop: 16, textAlign: 'right' }}>
                <Button onClick={handleClearFilters}>清除筛选</Button>
              </div>
            </Card>
          )}
        </Card>

        {/* 搜索结果区域 */}
        <Row gutter={[16, 16]}>
          <Col span={18}>
            <Card
              title={
                <Space>
                  <span>搜索结果</span>
                  {query && (
                    <Tag color="blue">
                      搜索词：{query}
                    </Tag>
                  )}
                  {searchStats.search_type && (
                    <Tag color="green">
                      搜索类型：{searchStats.search_type}
                    </Tag>
                  )}
                </Space>
              }
              extra={
                <Space>
                  <Text type="secondary">
                    找到 {filteredResults.length} 个结果
                  </Text>
                  <Switch
                    checkedChildren="实时更新"
                    unCheckedChildren="手动更新"
                  />
                </Space>
              }
            >
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 16 }}>正在搜索中...</div>
                </div>
              ) : !query ? (
                <Empty
                  description="请输入搜索内容"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ) : filteredResults.length === 0 ? (
                <Empty
                  description="没有找到相关结果"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ) : (
                <List
                  itemLayout="vertical"
                  dataSource={filteredResults}
                  renderItem={(result, index) => (
                    <List.Item
                      key={result.id}
                      actions={[
                        <Space key="relevance">
                          <Text type="secondary">相关性：</Text>
                          <Progress 
                            percent={Math.round(result.relevance * 100)} 
                            size="small" 
                            strokeColor={
                              result.relevance > 0.8 ? '#52c41a' : 
                              result.relevance > 0.6 ? '#faad14' : '#f5222d'
                            }
                            style={{ width: 100 }}
                          />
                        </Space>,
                        <Space key="score">
                          <Text type="secondary">评分：</Text>
                          <Badge 
                            count={result.score.toFixed(2)} 
                            style={{ backgroundColor: '#3b82f6' }}
                          />
                        </Space>,
                        <Button 
                          key="view" 
                          type="text" 
                          icon={<EyeOutlined />}
                          onClick={() => {
                            // 根据类型跳转到不同页面
                            if (result.type === 'course') {
                              window.open(`/courses/${result.metadata?.course_id}`, '_blank')
                            } else if (result.type === 'video') {
                              window.open(result.metadata?.file_path, '_blank')
                            }
                          }}
                        >
                          查看
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        avatar={
                          <Avatar 
                            size="large" 
                            icon={getResultIcon(result.type)}
                            style={{ backgroundColor: 'transparent' }}
                          />
                        }
                        title={
                          <Space>
                            <Tag color={getResultColor(result.type)}>
                              {getResultTypeText(result.type)}
                            </Tag>
                            <Title level={5} style={{ margin: 0 }}>
                              {result.title}
                            </Title>
                            {result.search_type && (
                              <Tag color="cyan">
                                {result.search_type}
                              </Tag>
                            )}
                          </Space>
                        }
                        description={
                          <div>
                            <Paragraph ellipsis={{ rows: 2 }}>
                              {result.description}
                            </Paragraph>
                            {result.metadata && (
                              <Space size={[8, 4]} wrap style={{ marginTop: 8 }}>
                                {result.metadata.category && (
                                  <Tag color="blue">{result.metadata.category}</Tag>
                                )}
                                {result.metadata.language && (
                                  <Tag color="green">{result.metadata.language}</Tag>
                                )}
                                {result.metadata.duration && (
                                  <Tag icon={<ClockCircleOutlined />}>
                                    {result.metadata.duration}分钟
                                  </Tag>
                                )}
                                {result.metadata.author && (
                                  <Tag icon={<UserOutlined />}>
                                    {result.metadata.author}
                                  </Tag>
                                )}
                              </Space>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Col>

          <Col span={6}>
            {/* 搜索统计 */}
            <Card title="搜索统计" style={{ marginBottom: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic 
                  title="总结果数" 
                  value={searchStats.total || 0}
                  prefix={<SearchOutlined />}
                />
                <Statistic 
                  title="搜索类型" 
                  value={searchStats.search_type || '未搜索'}
                />
                {searchStats.search_time && (
                  <Statistic 
                    title="搜索时间" 
                    value={dayjs(searchStats.search_time).format('HH:mm:ss')}
                  />
                )}
              </Space>
            </Card>

            {/* 搜索历史 */}
            <Card 
              title={
                <Space>
                  <HistoryOutlined />
                  <span>搜索历史</span>
                </Space>
              }
              extra={
                <Button 
                  type="text" 
                  size="small"
                  onClick={() => setSearchHistory([])}
                >
                  清空
                </Button>
              }
            >
              {searchHistory.length === 0 ? (
                <Empty
                  description="暂无搜索历史"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  style={{ margin: 0 }}
                />
              ) : (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {searchHistory.map((historyQuery, index) => (
                    <Card 
                      key={index}
                      size="small"
                      hoverable
                      onClick={() => handleHistoryClick(historyQuery)}
                      style={{ cursor: 'pointer' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <SearchOutlined style={{ marginRight: 8, color: '#666' }} />
                        <Text ellipsis style={{ flex: 1 }}>
                          {historyQuery}
                        </Text>
                      </div>
                    </Card>
                  ))}
                </Space>
              )}
            </Card>

            {/* 热门搜索 */}
            <Card 
              title={
                <Space>
                  <FireOutlined />
                  <span>热门搜索</span>
                </Space>
              }
              style={{ marginTop: 16 }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {[
                  'Python编程入门',
                  '机器学习基础',
                  '深度学习实战',
                  '数据结构与算法',
                  'Web开发教程',
                  '人工智能应用',
                  '数据分析方法',
                  '云计算技术',
                ].map((hotQuery, index) => (
                  <Card 
                    key={index}
                    size="small"
                    hoverable
                    onClick={() => handleHistoryClick(hotQuery)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <Badge 
                        count={index + 1} 
                        style={{ 
                          backgroundColor: index < 3 ? '#ef4444' : '#6b7280',
                          marginRight: 8,
                        }} 
                      />
                      <Text ellipsis style={{ flex: 1 }}>
                        {hotQuery}
                      </Text>
                    </div>
                  </Card>
                ))}
              </Space>
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  )
}
