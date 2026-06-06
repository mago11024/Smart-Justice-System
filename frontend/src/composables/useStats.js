import { ref } from 'vue'
import { getStats } from '@/api/stats'

export function useStats() {
  const stats = ref({
    total_active: 0, overdue_count: 0, due_soon_count: 0,
    by_stage: {}, this_week_court: 0
  })
  const loading = ref(false)

  async function fetchStats() {
    loading.value = true
    try {
      const res = await getStats()
      stats.value = res.data
    } finally {
      loading.value = false
    }
  }

  return { stats, loading, fetchStats }
}
