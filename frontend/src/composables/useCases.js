import { ref, reactive, computed } from 'vue'
import { getCases, advanceCase, batchAdvance, assignCase, batchAssign, deleteCase } from '@/api/cases'
import { ElMessage, ElMessageBox } from 'element-plus'

export function useCases() {
  const sections = ref([])       // flow view: grouped sections
  const flatList = ref([])       // flat view: array
  const loading = ref(false)
  const showLoading = ref(false)
  const selectedIds = ref(new Set())
  const filters = reactive({ search: '', view: 'flow' })

  const selectedCount = computed(() => selectedIds.value.size)

  async function fetchCases() {
    const timer = setTimeout(() => { showLoading.value = true }, 200)
    loading.value = true
    try {
      const res = await getCases({ view: 'flow' })
      sections.value = res.data
      const flat = []
      for (const sec of res.data) {
        for (const c of sec.cases) {
          flat.push(c)
        }
      }
      flatList.value = flat
    } finally {
      clearTimeout(timer)
      loading.value = false
      showLoading.value = false
    }
  }

  async function doAdvance(caseId) {
    await advanceCase(caseId)
    ElMessage.success('已推进')
    await fetchCases()
  }

  async function doBatchAdvance() {
    const ids = [...selectedIds.value]
    await batchAdvance(ids)
    ElMessage.success(`已推进 ${ids.length} 件`)
    selectedIds.value.clear()
    await fetchCases()
  }

  async function doAssign(caseId, lawyerId) {
    await assignCase(caseId, lawyerId)
    ElMessage.success('已指派')
    await fetchCases()
  }

  async function doBatchAssign(lawyerId) {
    const ids = [...selectedIds.value]
    await batchAssign(ids, lawyerId)
    ElMessage.success(`已指派 ${ids.length} 件`)
    selectedIds.value.clear()
    await fetchCases()
  }

  async function doDelete(caseId) {
    await ElMessageBox.confirm('确定删除此案件？', '确认', { type: 'warning' })
    await deleteCase(caseId)
    ElMessage.success('已删除')
    await fetchCases()
  }

  function toggleSelect(id) {
    const s = new Set(selectedIds.value)
    if (s.has(id)) s.delete(id)
    else s.add(id)
    selectedIds.value = s
  }

  function clearSelection() {
    selectedIds.value = new Set()
  }

  return {
    sections, flatList, loading, showLoading, filters, selectedIds, selectedCount,
    fetchCases, doAdvance, doBatchAdvance, doAssign, doBatchAssign, doDelete,
    toggleSelect, clearSelection
  }
}
