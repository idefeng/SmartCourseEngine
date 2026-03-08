'use client';

import React, { useState } from 'react';
import {
  Layout,
  Card,
  Typography,
  Space,
  Tabs,
  Alert,
  Row,
  Col,
  Button,
  Steps,
  Descriptions,
  Tag,
} from 'antd';
import {
  UploadOutlined,
  VideoCameraOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import FileUpload from '@/components/upload/FileUpload';
import ProgressDisplay from '@/components/upload/ProgressDisplay';

const { Title, Text } = Typography;
const { Header, Content } = Layout;
const { Step } = Steps;

export default function VideoUploadPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('upload');
  const [currentStep, setCurrentStep] = useState(0);
  const [analysisCompleted, setAnalysisCompleted] = useState(false);

  // 上传完成回调
  const handleUploadComplete = (task: any) => {
    console.log('上传完成:', task);
    setAnalysisCompleted(false);
    setCurrentStep(1); // 进入分析步骤
    setActiveTab('progress');
  };

  const handleAnalysisCompleted = (taskId: string) => {
    if (!analysisCompleted) {
      setCurrentStep(2);
      setAnalysisCompleted(true);
      setActiveTab('progress');
      console.log('分析流水线最终完成:', taskId);
    }
  };

  // 上传错误回调
  const handleUploadError = (error: Error) => {
    console.error('上传错误:', error);
  };

  // 步骤配置
  const steps = [
    {
      title: '上传视频',
      description: '选择并上传视频文件',
      icon: <CloudUploadOutlined />,
    },
    {
      title: '分析处理',
      description: 'AI自动分析视频内容',
      icon: <VideoCameraOutlined />,
    },
    {
      title: '完成',
      description: '生成知识库内容',
      icon: <CheckCircleOutlined />,
    },
  ];

  return (
    <>
      <Header className="flex-none z-10 !h-24 flex items-center justify-between px-10 bg-white/70 backdrop-blur-xl border-b border-white/20">
        <Space>
          <Button type="text" onClick={() => router.push('/videos')}>
            返回视频列表
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            <VideoCameraOutlined /> 视频上传与分析
          </Title>
        </Space>
      </Header>

      <Content className="flex-1 overflow-y-auto" style={{ padding: '24px' }}>
        <Space direction="vertical" size={24} style={{ width: '100%' }}>
          {/* 步骤指示器 */}
          <Card>
            <Steps current={currentStep} size="small">
              {steps.map((step, index) => (
                <Step
                  key={index}
                  title={step.title}
                  description={step.description}
                  icon={step.icon}
                />
              ))}
            </Steps>
          </Card>

          {/* 主内容区域 */}
          <Row gutter={24}>
            {/* 左侧：上传和进度 */}
            <Col span={16}>
              <Card>
                <Tabs
                  activeKey={activeTab}
                  onChange={setActiveTab}
                  items={[
                    {
                      key: 'upload',
                      label: (
                        <Space>
                          <CloudUploadOutlined />
                          <span>上传视频</span>
                        </Space>
                      ),
                      children: (
                        <div style={{ padding: '24px 0' }}>
                          <FileUpload
                            onUploadComplete={handleUploadComplete}
                            onUploadError={handleUploadError}
                            accept=".mp4,.avi,.mov,.wmv,.flv,.mkv,.webm,.m4v"
                            maxSize={10240} // 10GB
                          />
                        </div>
                      ),
                    },
                    {
                      key: 'progress',
                      label: (
                        <Space>
                          <VideoCameraOutlined />
                          <span>分析进度</span>
                        </Space>
                      ),
                      children: (
                        <div style={{ padding: '24px 0' }}>
                          <ProgressDisplay
                            showDetails={true}
                            onAnalysisCompleted={handleAnalysisCompleted}
                          />
                        </div>
                      ),
                    },
                  ]}
                />
                {analysisCompleted && (
                  <Alert
                    message="分析已完成"
                    description={
                      <Space>
                        <Button onClick={() => router.push('/videos')}>
                          返回视频列表
                        </Button>
                        <Button type="primary" onClick={() => router.push('/knowledge')}>
                          查看知识库
                        </Button>
                      </Space>
                    }
                    type="success"
                    showIcon
                    style={{ marginTop: 16 }}
                  />
                )}
              </Card>
            </Col>

            {/* 右侧：说明和统计 */}
            <Col span={8}>
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                {/* 上传说明 */}
                <Card
                  title={
                    <Space>
                      <InfoCircleOutlined />
                      <span>上传说明</span>
                    </Space>
                  }
                >
                  <Space direction="vertical" size={12}>
                    <Alert
                      message="支持格式"
                      description="MP4, AVI, MOV, WMV, FLV, MKV, WebM, M4V"
                      type="info"
                      showIcon
                    />
                    <Alert
                      message="大小限制"
                      description="单个文件最大 10GB"
                      type="info"
                      showIcon
                    />
                    <Alert
                      message="网络要求"
                      description="建议在稳定的网络环境下上传大文件"
                      type="warning"
                      showIcon
                    />
                    <Alert
                      message="断点续传"
                      description="支持上传中断后继续上传"
                      type="success"
                      showIcon
                    />
                  </Space>
                </Card>

                {/* 分析流程说明 */}
                <Card
                  title={
                    <Space>
                      <VideoCameraOutlined />
                      <span>分析流程</span>
                    </Space>
                  }
                >
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="1. 语音识别">
                      <Tag color="blue">Whisper AI</Tag>
                      提取视频中的语音内容
                    </Descriptions.Item>
                    <Descriptions.Item label="2. 关键帧提取">
                      <Tag color="green">OpenCV</Tag>
                      提取代表性画面
                    </Descriptions.Item>
                    <Descriptions.Item label="3. 场景检测">
                      <Tag color="orange">场景分析</Tag>
                      识别场景变化
                    </Descriptions.Item>
                    <Descriptions.Item label="4. 知识提取">
                      <Tag color="purple">NLP</Tag>
                      提取结构化知识点
                    </Descriptions.Item>
                    <Descriptions.Item label="5. 图谱构建">
                      <Tag color="red">知识图谱</Tag>
                      构建知识关联关系
                    </Descriptions.Item>
                  </Descriptions>
                </Card>

                {/* 实时统计 */}
                <Card
                  title={
                    <Space>
                      <LineChartOutlined />
                      <span>实时统计</span>
                    </Space>
                  }
                >
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Card size="small">
                        <Statistic
                          title="上传中"
                          value={0}
                          suffix="个"
                          valueStyle={{ color: '#1890ff' }}
                        />
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card size="small">
                        <Statistic
                          title="分析中"
                          value={0}
                          suffix="个"
                          valueStyle={{ color: '#52c41a' }}
                        />
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card size="small">
                        <Statistic
                          title="今日上传"
                          value={0}
                          suffix="个"
                        />
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card size="small">
                        <Statistic
                          title="总大小"
                          value={0}
                          suffix="GB"
                        />
                      </Card>
                    </Col>
                  </Row>
                </Card>
              </Space>
            </Col>
          </Row>

          {/* 底部提示 */}
          <Alert
            message="提示"
            description={
              <div>
                <Text>
                  1. 上传过程中请不要关闭页面，否则需要重新上传
                  <br />
                  2. 分析过程可能需要较长时间，请耐心等待
                  <br />
                  3. 分析结果会自动保存到知识库中
                  <br />
                  4. 可以通过通知中心查看实时进度
                </Text>
              </div>
            }
            type="info"
            showIcon
          />
        </Space>
      </Content>
    </>
  );
}

// 临时Statistic组件（因为antd的Statistic需要单独导入）
const Statistic = ({ title, value, suffix, valueStyle }: any) => (
  <div style={{ textAlign: 'center' }}>
    <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>{title}</div>
    <div style={{ fontSize: 24, fontWeight: 'bold', ...valueStyle }}>
      {value}
      {suffix && <span style={{ fontSize: 14, marginLeft: 2 }}>{suffix}</span>}
    </div>
  </div>
);

const LineChartOutlined = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z" />
  </svg>
);
