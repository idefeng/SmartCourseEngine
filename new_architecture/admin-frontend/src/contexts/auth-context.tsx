'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { message } from 'antd'

// 用户类型定义
interface User {
  id: number
  email: string
  username: string
  full_name?: string
  avatar_url?: string
  role: 'admin' | 'teacher' | 'student' | 'user'
  is_active: boolean
  created_at: string
  updated_at: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
}

interface LoginCredentials {
  email: string
  password: string
  remember?: boolean
}

interface RegisterData {
  email: string
  username: string
  password: string
  full_name?: string
}

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  register: (data: RegisterData) => Promise<void>
  updateUser: (user: Partial<User>) => void
  refreshToken: () => Promise<void>
}

// 创建Context
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// 存储键名
const STORAGE_KEYS = {
  TOKEN: 'smartcourse_token',
  USER: 'smartcourse_user',
  REMEMBER: 'smartcourse_remember'
}

// 模拟API函数
const mockAuthAPI = {
  login: async (credentials: LoginCredentials): Promise<{ user: User; token: string }> => {
    // 模拟API延迟
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟验证
    if (credentials.email === 'admin@smartcourse.com' && credentials.password === 'Admin@123') {
      return {
        user: {
          id: 1,
          email: 'admin@smartcourse.com',
          username: 'admin',
          full_name: '系统管理员',
          role: 'admin',
          is_active: true,
          created_at: '2026-03-01T00:00:00Z',
          updated_at: '2026-03-01T00:00:00Z'
        },
        token: 'mock-jwt-token-1234567890'
      }
    }
    
    throw new Error('邮箱或密码不正确')
  },
  
  register: async (data: RegisterData): Promise<{ user: User; token: string }> => {
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    return {
      user: {
        id: 2,
        email: data.email,
        username: data.username,
        full_name: data.full_name,
        role: 'user',
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      token: 'mock-jwt-token-new-user'
    }
  },
  
  refreshToken: async (token: string): Promise<{ user: User; token: string }> => {
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 模拟刷新令牌
    return {
      user: {
        id: 1,
        email: 'admin@smartcourse.com',
        username: 'admin',
        full_name: '系统管理员',
        role: 'admin',
        is_active: true,
        created_at: '2026-03-01T00:00:00Z',
        updated_at: '2026-03-01T00:00:00Z'
      },
      token: 'mock-jwt-token-refreshed'
    }
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    isAuthenticated: false
  })

  // 初始化认证状态
  useEffect(() => {
    const initAuth = () => {
      try {
        const token = localStorage.getItem(STORAGE_KEYS.TOKEN)
        const userStr = localStorage.getItem(STORAGE_KEYS.USER)
        
        if (token && userStr) {
          const user = JSON.parse(userStr)
          setAuthState({
            user,
            token,
            isLoading: false,
            isAuthenticated: true
          })
        } else {
          setAuthState(prev => ({ ...prev, isLoading: false }))
        }
      } catch (error) {
        console.error('初始化认证状态失败:', error)
        setAuthState({
          user: null,
          token: null,
          isLoading: false,
          isAuthenticated: false
        })
      }
    }

    initAuth()
  }, [])

  // 登录函数
  const login = async (credentials: LoginCredentials) => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }))
      
      const response = await mockAuthAPI.login(credentials)
      
      // 保存到本地存储
      localStorage.setItem(STORAGE_KEYS.TOKEN, response.token)
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(response.user))
      
      if (credentials.remember) {
        localStorage.setItem(STORAGE_KEYS.REMEMBER, 'true')
      }
      
      // 更新状态
      setAuthState({
        user: response.user,
        token: response.token,
        isLoading: false,
        isAuthenticated: true
      })
      
      message.success('登录成功')
      router.push('/')
      
    } catch (error: any) {
      setAuthState(prev => ({ ...prev, isLoading: false }))
      message.error(error.message || '登录失败')
      throw error
    }
  }

  // 注册函数
  const register = async (data: RegisterData) => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }))
      
      const response = await mockAuthAPI.register(data)
      
      // 保存到本地存储
      localStorage.setItem(STORAGE_KEYS.TOKEN, response.token)
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(response.user))
      
      // 更新状态
      setAuthState({
        user: response.user,
        token: response.token,
        isLoading: false,
        isAuthenticated: true
      })
      
      message.success('注册成功')
      router.push('/')
      
    } catch (error: any) {
      setAuthState(prev => ({ ...prev, isLoading: false }))
      message.error(error.message || '注册失败')
      throw error
    }
  }

  // 登出函数
  const logout = () => {
    // 清除本地存储
    localStorage.removeItem(STORAGE_KEYS.TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER)
    localStorage.removeItem(STORAGE_KEYS.REMEMBER)
    
    // 更新状态
    setAuthState({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false
    })
    
    message.success('已退出登录')
    router.push('/login')
  }

  // 更新用户信息
  const updateUser = (userData: Partial<User>) => {
    if (authState.user) {
      const updatedUser = { ...authState.user, ...userData }
      
      // 更新本地存储
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(updatedUser))
      
      // 更新状态
      setAuthState(prev => ({
        ...prev,
        user: updatedUser
      }))
      
      message.success('用户信息已更新')
    }
  }

  // 刷新令牌
  const refreshToken = async () => {
    if (!authState.token) return
    
    try {
      const response = await mockAuthAPI.refreshToken(authState.token)
      
      // 更新本地存储
      localStorage.setItem(STORAGE_KEYS.TOKEN, response.token)
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(response.user))
      
      // 更新状态
      setAuthState({
        user: response.user,
        token: response.token,
        isLoading: false,
        isAuthenticated: true
      })
      
    } catch (error) {
      console.error('刷新令牌失败:', error)
      logout() // 刷新失败则退出登录
    }
  }

  // 自动刷新令牌（每30分钟）
  useEffect(() => {
    if (!authState.isAuthenticated) return
    
    const interval = setInterval(() => {
      refreshToken()
    }, 30 * 60 * 1000) // 30分钟
    
    return () => clearInterval(interval)
  }, [authState.isAuthenticated])

  const value: AuthContextType = {
    ...authState,
    login,
    logout,
    register,
    updateUser,
    refreshToken
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

// 自定义Hook
export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth必须在AuthProvider内使用')
  }
  return context
}

// 权限检查Hook
export function usePermission() {
  const { user } = useAuth()
  
  const hasPermission = (requiredRole: User['role']) => {
    if (!user) return false
    
    const roleHierarchy = {
      'admin': 4,
      'teacher': 3,
      'student': 2,
      'user': 1
    }
    
    const userLevel = roleHierarchy[user.role] || 0
    const requiredLevel = roleHierarchy[requiredRole] || 0
    
    return userLevel >= requiredLevel
  }
  
  const isAdmin = () => hasPermission('admin')
  const isTeacher = () => hasPermission('teacher')
  const isStudent = () => hasPermission('student')
  
  return {
    hasPermission,
    isAdmin,
    isTeacher,
    isStudent,
    userRole: user?.role
  }
}

// 保护路由组件
export function ProtectedRoute({ children, requiredRole }: { 
  children: ReactNode
  requiredRole?: User['role']
}) {
  const { isAuthenticated, isLoading } = useAuth()
  const { hasPermission } = usePermission()
  const router = useRouter()
  
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
    
    if (!isLoading && isAuthenticated && requiredRole && !hasPermission(requiredRole)) {
      message.error('权限不足')
      router.push('/')
    }
  }, [isAuthenticated, isLoading, requiredRole, hasPermission, router])
  
  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <div>加载中...</div>
      </div>
    )
  }
  
  if (!isAuthenticated) {
    return null
  }
  
  if (requiredRole && !hasPermission(requiredRole)) {
    return null
  }
  
  return <>{children}</>
}