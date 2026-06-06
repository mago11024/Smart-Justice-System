import api from './index'

export function getLawyers() {
  return api.get('/lawyers')
}

export function getLawyerCases(lawyerId) {
  return api.get(`/lawyers/${lawyerId}/cases`)
}
