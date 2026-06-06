import { ref, onBeforeUnmount } from 'vue'

/**
 * 延迟 loading 显示：API 在 delay ms 内返回就不显示遮罩，避免"闪一下"
 * 模板中用 v-loading="showLoading"
 *
 * 安全机制：
 * - 并发调用 run() 时，前一个 timer 会被清除
 * - 组件卸载时自动清除 timer 并隐藏 loading，防止永久卡住
 * - 硬超时兜底：超过 maxWait 秒后强制关闭 loading
 */
export function useDeferredLoading(delay = 200, maxWait = 30_000) {
  const showLoading = ref(false)

  let timer = null
  let hardTimer = null

  function clearTimers() {
    if (timer) { clearTimeout(timer); timer = null }
    if (hardTimer) { clearTimeout(hardTimer); hardTimer = null }
  }

  async function run(fn) {
    // 清除之前的 timer（防止并发调用时旧 timer 泄漏）
    clearTimers()
    showLoading.value = false

    timer = setTimeout(() => { showLoading.value = true }, delay)
    // 硬超时兜底：超过 maxWait 后强制关闭 loading，防止任何意外导致永久 loading
    hardTimer = setTimeout(() => { showLoading.value = false }, delay + maxWait)

    try {
      return await fn()
    } finally {
      clearTimers()
      showLoading.value = false
    }
  }

  onBeforeUnmount(() => {
    clearTimers()
    showLoading.value = false
  })

  return { showLoading, run }
}
