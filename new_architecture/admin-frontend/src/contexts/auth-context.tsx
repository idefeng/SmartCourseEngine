'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { message } from 'antd'
import { api } from '../services/api'

// 用户类型定义
export interface User {
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
  TOKEN: 'token',
  REFRESH_TOKEN: 'refresh_token',
  USER: 'smartcourse_user',
  REMEMBER: 'smartcourse_remember'
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    isAuthenticated: false
  })
  const [messageApi, contextHolder] = message.useMessage()
  const router = useRouter()

  // 初始化检查登录状态
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem(STORAGE_KEYS.TOKEN)
      if (token) {
        try {
          // 验证Token并获取用户信息
          const user = (await api.auth.getCurrentUser()) as any
          setState({
            user,
            token,
            isLoading: false,
            isAuthenticated: true
          })
        } catch (error) {
          console.error('Token invalid or expired', error)
          // 清除无效Token
          localStorage.removeItem(STORAGE_KEYS.TOKEN)
          localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
          setState({
            user: null,
            token: null,
            isLoading: false,
            isAuthenticated: false
          })
        }
      } else {
        setState({
          user: null,
          token: null,
          isLoading: false,
          isAuthenticated: false
        })
      }
    }

    initAuth()
  }, [])

  // 登录
  const login = async (credentials: LoginCredentials) => {
    try {
      setState(prev => ({ ...prev, isLoading: true }))
      
      const response = await api.auth.login({
        email: credentials.email,
        password: credentials.password
      })
      
      const { access_token, refresh_token, user } = response as any
      
      // 存储Token
      localStorage.setItem(STORAGE_KEYS.TOKEN, access_token)
      if (refresh_token) {
        localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refresh_token)
      }
      
      // 如果选择了记住我，可以存储相关标记（可选）
      if (credentials.remember) {
        localStorage.setItem(STORAGE_KEYS.REMEMBER, 'true')
      }

      setState({
        user,
        token: access_token,
        isLoading: false,
        isAuthenticated: true
      })
      
      messageApi.success('登录成功')
      
      // 根据角色跳转
      if (user.role === 'admin') {
        router.push('/dashboard') 
      } else {
        router.push('/dashboard')
      }
      
    } catch (error: any) {
      setState(prev => ({ ...prev, isLoading: false }))
      const msg = error.message || '登录失败'
      messageApi.error(msg)
      throw error
    }
  }

  // 注册
  const register = async (data: RegisterData) => {
    try {
      setState(prev => ({ ...prev, isLoading: true }))
      
      const response = await api.auth.register(data)
      const { access_token, refresh_token, user } = response as any
      
      localStorage.setItem(STORAGE_KEYS.TOKEN, access_token)
      if (refresh_token) {
        localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refresh_token)
      }
      
      setState({
        user,
        token: access_token,
        isLoading: false,
        isAuthenticated: true
      })
      
      messageApi.success('注册成功')
      router.push('/dashboard')
      
    } catch (error: any) {
      setState(prev => ({ ...prev, isLoading: false }))
      const msg = error.message || '注册失败'
      messageApi.error(msg)
      throw error
    }
  }

  // 登出
  const logout = () => {
    // 调用API logout只是为了清理本地，也可以调用后端注销
    api.auth.logout() 
    setState({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false
    })
  }

  // 更新用户信息
  const updateUser = (userData: Partial<User>) => {
    setState(prev => {
        if (!prev.user) return prev;
        return {
            ...prev,
            user: { ...prev.user, ...userData } as User
        }
    })
  }

  // 手动刷新Token (API拦截器已自动处理)
  const refreshToken = async () => {
      console.warn('refreshToken is handled automatically by api interceptors')
  }

  return (
    <AuthContext.Provider value={{ 
      ...state, 
      login, 
      logout, 
      register, 
      updateUser,
      refreshToken 
    }}>
      {contextHolder}
      {children}
    </AuthContext.Provider>
  )
}

// Hook
export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
