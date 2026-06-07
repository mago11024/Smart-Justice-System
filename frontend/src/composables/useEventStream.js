import { ref, readonly } from 'vue'

// ---- 模块级单例状态 ----
const notificationVersion = ref(0)
const taskVersion = ref(0)
const lastTaskEvent = ref(null)
const connected = ref(false)

let eventSource = null
let reconnectTimer = null

function connect() {
  if (eventSource) {
    eventSource.close()
  }

  eventSource = new EventSource('/api/events')

  eventSource.onopen = () => {
    connected.value = true
    // 重连后递增版本号，驱动组件重新拉取断线期间可能错过的数据
    notificationVersion.value++
    taskVersion.value++
  }

  eventSource.onerror = () => {
    connected.value = false
    // EventSource 自带指数退避重连，这里加硬兜底
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(connect, 5000)
  }

  eventSource.addEventListener('notification_changed', () => {
    notificationVersion.value++
  })

  eventSource.addEventListener('task_changed', (event) => {
    taskVersion.value++
    try {
      lastTaskEvent.value = { ...JSON.parse(event.data || '{}'), receivedAt: Date.now() }
    } catch {
      lastTaskEvent.value = { receivedAt: Date.now() }
    }
  })

  // 心跳事件仅保活，不处理
  eventSource.addEventListener('heartbeat', () => {})
}

function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  connected.value = false
}

// ---- 公开组合式函数 ----
export function useEventStream() {
  return {
    notificationVersion: readonly(notificationVersion),
    taskVersion: readonly(taskVersion),
    lastTaskEvent: readonly(lastTaskEvent),
    connected: readonly(connected),
    connect,
    disconnect,
  }
}
