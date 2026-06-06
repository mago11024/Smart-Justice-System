/* axios 实例，baseURL + 拦截器 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (!err.config?.silent) {
      const msg = err.response?.data?.detail || err.message || '请求失败'
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  }
)

export default api
