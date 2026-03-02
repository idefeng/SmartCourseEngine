import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

// API配置 - 使用统一API网关
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001'

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 添加请求时间戳
    config.headers['X-Request-Timestamp'] = new Date().toISOString()
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 统一处理API响应格式
    const data = response.data
    
    if (data.success === false) {
      // 如果API返回错误，抛出异常
      const error = new Error(data.message || '请求失败')
      ;(error as any).response = response
      ;(error as any).code = data.error_code
      ;(error as any).details = data.details
      return Promise.reject(error)
    }
    
    // 返回数据部分
    return data.data
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response
      
      // 处理统一API响应格式的错误
      if (data && data.success === false) {
        const apiError = new Error(data.message || 'API请求失败')
        ;(apiError as any).code = data.error_code
        ;(apiError as any).details = data.details
        ;(apiError as any).timestamp = data.timestamp
        
        // 根据错误代码进行特殊处理
        switch (data.error_code) {
          case '0004': // 权限不足
            if (typeof window !== 'undefined') {
              window.location.href = '/login'
            }
            break
          case '0005': // 资源不存在
            console.error('资源不存在:', data.message)
            break
          case '0001': // 参数验证失败
            console.error('参数验证失败:', data.details?.errors)
            break
        }
        
        return Promise.reject(apiError)
      }
      
      // 处理HTTP状态码错误
      switch (status) {
        case 401:
          // 未授权，跳转到登录页
          if (typeof window !== 'undefined') {
            window.location.href = '/login'
          }
          break
        case 403:
          console.error('权限不足:', data?.message)
          break
        case 404:
          console.error('资源不存在:', data?.message)
          break
        case 422:
          console.error('参数验证失败:', data?.errors)
          break
        case 500:
          console.error('服务器错误:', data?.message)
          break
        default:
          console.error('请求错误:', data?.message)
      }
    } else if (error.request) {
      console.error('网络错误，请检查网络连接')
    } else {
      console.error('请求配置错误:', error.message)
    }
    
    return Promise.reject(error)
  }
)

// API接口定义
export const api = {
  // 课程相关
  courses: {
    // 获取课程列表
    getCourses: (params?: any) => 
      apiClient.get('/api/v1/courses', { params }),
    
    // 获取课程详情
    getCourse: (id: number | string) => 
      apiClient.get(`/api/v1/courses/${id}`),
    
    // 创建课程
    createCourse: (data: any) => 
      apiClient.post('/api/v1/courses', data),
    
    // 更新课程
    updateCourse: (id: number | string, data: any) => 
      apiClient.put(`/api/v1/courses/${id}`, data),
    
    // 删除课程
    deleteCourse: (id: number | string) => 
      apiClient.delete(`/api/v1/courses/${id}`),
    
    // 搜索课程
    searchCourses: (query: string, params?: any) => 
      apiClient.get('/api/v1/courses/search', { 
        params: { query, ...params } 
      }),
  },

  // 视频相关
  videos: {
    // 上传视频
    uploadVideo: (formData: FormData, onProgress?: (progress: number) => void) => {
      const config: AxiosRequestConfig = {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
      
      if (onProgress) {
        config.onUploadProgress = (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / (progressEvent.total || 1)
          )
          onProgress(percentCompleted)
        }
      }
      
      return apiClient.post('/api/v1/videos/upload', formData, config)
    },
    
    // 分析视频
    analyzeVideo: (videoId: string, options?: any) => 
      apiClient.post(`/api/v1/videos/${videoId}/analyze`, options),
    
    // 获取视频列表
    getVideos: (params?: any) => 
      apiClient.get('/api/v1/videos', { params }),
    
    // 获取视频详情
    getVideo: (id: string) => 
      apiClient.get(`/api/v1/videos/${id}`),
    
    // 删除视频
    deleteVideo: (id: string) => 
      apiClient.delete(`/api/v1/videos/${id}`),
  },

  // 知识点相关
  knowledge: {
    // 提取知识点
    extractKnowledge: (transcript: any, courseId?: number) => 
      apiClient.post('/api/v1/knowledge/extract', { transcript, course_id: courseId }),
    
    // 构建知识图谱
    buildKnowledgeGraph: (knowledgePoints: any[]) => 
      apiClient.post('/api/v1/knowledge/graph', { knowledge_points: knowledgePoints }),
    
    // 处理视频分析
    processVideoAnalysis: (videoAnalysis: any, courseId?: number) => 
      apiClient.post('/api/v1/knowledge/process', { video_analysis: videoAnalysis, course_id: courseId }),
    
    // 获取知识点列表
    getKnowledgePoints: (params?: any) => 
      apiClient.get('/api/v1/knowledge/points', { params }),
    
    // 搜索知识点
    searchKnowledge: (query: string, params?: any) => 
      apiClient.get('/api/v1/knowledge/search', { params: { query, ...params } }),
  },

  // 搜索相关
  search: {
    // 通用搜索
    search: (query: string, searchType: string = 'hybrid', limit: number = 10) => 
      apiClient.get('/api/v1/search', { 
        params: { query, search_type: searchType, limit } 
      }),
    
    // 知识点搜索
    searchKnowledge: (query: string, params?: any) => 
      apiClient.get('/api/v1/search/knowledge', { 
        params: { query, ...params } 
      }),
    
    // 课程搜索
    searchCourses: (query: string, params?: any) => 
      apiClient.get('/api/v1/search/courses', { 
        params: { query, ...params } 
      }),
    
    // 语义搜索
    semanticSearch: (query: string, limit: number = 10) => 
      apiClient.get('/api/v1/search/semantic', { 
        params: { query, limit } 
      }),
    
    // 混合搜索
    hybridSearch: (query: string, weights?: any, limit: number = 10) => 
      apiClient.get('/api/v1/search/hybrid', { 
        params: { query, weights: JSON.stringify(weights), limit } 
      }),
  },

  // 用户相关
  users: {
    // 获取用户列表
    getUsers: (params?: any) => 
      apiClient.get('/api/v1/users', { params }),
    
    // 获取用户详情
    getUser: (id: number | string) => 
      apiClient.get(`/api/v1/users/${id}`),
    
    // 创建用户
    createUser: (data: any) => 
      apiClient.post('/api/v1/users', data),
    
    // 更新用户
    updateUser: (id: number | string, data: any) => 
      apiClient.put(`/api/v1/users/${id}`, data),
    
    // 删除用户
    deleteUser: (id: number | string) => 
      apiClient.delete(`/api/v1/users/${id}`),
  },

  // 系统相关
  system: {
    // 健康检查
    health: () => 
      apiClient.get('/health'),
    
    // 系统状态
    status: () => 
      apiClient.get('/api/v1/system/status'),
    
    // 统计信息
    stats: () => 
      apiClient.get('/api/v1/system/stats'),
  },
}

// 导出类型
export type ApiResponse<T = any> = {
  success: boolean
  message: string
  data: T
  timestamp: string
}

export type PaginatedResponse<T = any> = ApiResponse<{
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}>

export default apiClient