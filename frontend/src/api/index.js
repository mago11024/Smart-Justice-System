/* axios 实例，baseURL + 拦截器 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      if (window.location.pathname !== '/login.html') {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.replace(`/login.html?redirect=${redirect}`)
      }
      return Promise.reject(err)
    }
    if (!err.config?.silent) {
      const msg = err.response?.data?.detail || err.message || '请求失败'
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  }
)

export default api
