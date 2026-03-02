'use client'

import { useState } from 'react'
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Typography, 
  Space, 
  Alert, 
  Divider,
  Checkbox,
  Row,
  Col,
} from 'antd'
import { 
  UserOutlined, 
  LockOutlined, 
  MailOutlined,
  EyeInvisibleOutlined,
  EyeTwoTone,
  GoogleOutlined,
  GithubOutlined,
} from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/services/api'

const { Title, Text, Paragraph } = Typography

export default function LoginPage() {
  const [form] = Form.useForm()
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loginType, setLoginType] = useState<'email' | 'username'>('email')

  const handleLogin = async (values: any) => {
    setLoading(true)
    setError(null)
    
    try {
      // 这里应该调用实际的登录API
      // 为了演示，我们使用模拟登录
      if (values.email === 'admin@smartcourse.com' && values.password === 'Admin@123') {
        // 模拟成功登录
        localStorage.setItem('token', 'mock-jwt-token')
        localStorage.setItem('user', JSON.stringify({
          id: 1,
          email: 'admin@smartcourse.com',
          username: 'admin',
          full_name: '系统管理员',
          role: 'admin',
          avatar_url: null
        }))
        
        // 跳转到仪表盘
        router.push('/')
      } else {
        setError('邮箱或密码不正确')
      }
    } catch (err: any) {
      setError(err.message || '登录失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleSocialLogin = (provider: 'google' | 'github') => {
    setError(null)
    // 这里应该处理第三方登录
    setError(`${provider}登录功能正在开发中`)
  }

  const handleForgotPassword = () => {
    // 这里应该跳转到忘记密码页面
    setError('忘记密码功能正在开发中')
  }

  return (
    <div style={{ 
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      <Card 
        style={{ 
          width: '100%',
          maxWidth: 480,
          borderRadius: 12,
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
        }}
        bodyStyle={{ padding: 40 }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ marginBottom: 8, color: '#1890ff' }}>
            SmartCourseEngine
          </Title>
          <Text type="secondary" style={{ fontSize: 16 }}>
            智能课程管理系统
          </Text>
        </div>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            closable
            onClose={() => setError(null)}
            style={{ marginBottom: 24 }}
          />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleLogin}
          initialValues={{ remember: true }}
        >
          <Form.Item
            name="email"
            label="邮箱地址"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' }
            ]}
          >
            <Input 
              prefix={<MailOutlined />} 
              placeholder="请输入邮箱地址"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码长度至少8位' }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="请输入密码"
              size="large"
              iconRender={(visible) => 
                visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
              }
            />
          </Form.Item>

          <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
            <Col>
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>记住我</Checkbox>
              </Form.Item>
            </Col>
            <Col>
              <Button type="link" onClick={handleForgotPassword} style={{ padding: 0 }}>
                忘记密码？
              </Button>
            </Col>
          </Row>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              size="large"
              block
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <Divider plain>或使用以下方式登录</Divider>

        <Space direction="vertical" style={{ width: '100%' }}>
          <Button 
            icon={<GoogleOutlined />}
            size="large"
            block
            onClick={() => handleSocialLogin('google')}
            style={{ 
              background: '#fff',
              color: '#757575',
              borderColor: '#ddd'
            }}
          >
            使用 Google 登录
          </Button>
          
          <Button 
            icon={<GithubOutlined />}
            size="large"
            block
            onClick={() => handleSocialLogin('github')}
            style={{ 
              background: '#24292e',
              color: '#fff',
              borderColor: '#24292e'
            }}
          >
            使用 GitHub 登录
          </Button>
        </Space>

        <div style={{ marginTop: 32, textAlign: 'center' }}>
          <Text type="secondary">
            还没有账户？{' '}
            <Link href="/register" style={{ color: '#1890ff' }}>
              立即注册
            </Link>
          </Text>
        </div>

        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Paragraph type="secondary" style={{ fontSize: 12 }}>
            登录即表示您同意我们的
            <Link href="/terms" style={{ margin: '0 4px' }}>服务条款</Link>
            和
            <Link href="/privacy" style={{ marginLeft: 4 }}>隐私政策</Link>
          </Paragraph>
        </div>
      </Card>

      {/* 演示账户提示 */}
      <div style={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        background: 'rgba(0,0,0,0.8)',
        color: 'white',
        padding: '12px 20px',
        borderRadius: 8,
        fontSize: 14,
        maxWidth: 300
      }}>
        <Text style={{ color: 'white' }}>
          <strong>演示账户：</strong><br />
          邮箱: admin@smartcourse.com<br />
          密码: Admin@123
        </Text>
      </div>
    </div>
  )
}