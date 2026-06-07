import api from './index'

export function getNotifications(unreadOnly = false, config = {}) {
  return api.get('/notifications', { params: { unread_only: unreadOnly }, ...config })
}

export function markRead(id) {
  return api.put(`/notifications/${id}/read`)
}

export function markUnread(id) {
  return api.put(`/notifications/${id}/unread`)
}

export function pinNotification(id) {
  return api.put(`/notifications/${id}/pin`)
}

export function unpinNotification(id) {
  return api.put(`/notifications/${id}/unpin`)
}

export function readAll() {
  return api.post('/notifications/read-all')
}

export function getNotificationStats() {
  return api.get('/notifications/stats')
}
