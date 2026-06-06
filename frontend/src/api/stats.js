import api from './index'

export function getStats() {
  return api.get('/stats')
}
