<script setup>
import { onMounted, onBeforeUnmount, onActivated, onDeactivated, computed, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import StatsCards from '@/components/dashboard/StatsCards.vue'
import ViewToggle from '@/components/dashboard/ViewToggle.vue'
import BatchBar from '@/components/dashboard/BatchBar.vue'
import FlowSection from '@/components/case/FlowSection.vue'
import FlatCaseItem from '@/components/case/FlatCaseItem.vue'
import FlatFilters from '@/components/case/FlatFilters.vue'
import { useCases } from '@/composables/useCases'
import { useStats } from '@/composables/useStats'
import { getLawyers } from '@/api/lawyers'
import { getCases } from '@/api/cases'

const router = useRouter()
const { sections, flatList, loading, showLoading, filters, selectedIds, selectedCount, fetchCases, doAdvance, doBatchAdvance, doAssign, doBatchAssign, toggleSelect, clearSelection } = useCases()
const { stats, fetchStats } = useStats()

const lawyers = ref([])
const flatFilter = ref('all')
const searchQuery = ref('')

let searchDebounce = null

// 高亮案件
const highlightedCaseId = ref(null)
let highlightTimer = null

function onHighlightCase(e) {
  const caseId = e.detail?.caseId
  if (!caseId) return
  highlightedCaseId.value = caseId
  // 切换到平铺视图便于定位
  filters.view = 'flat'
  flatFilter.value = 'all'
  // 滚动到高亮案件
  nextTick(() => {
    const el = document.querySelector(`[data-case-id="${caseId}"]`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
  // 5s 后自动清除高亮
  if (highlightTimer) clearTimeout(highlightTimer)
  highlightTimer = setTimeout(() => { highlightedCaseId.value = null }, 5000)
}

function refreshList() {
  fetchCases()
  fetchStats()
}

function onSearch(val) {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(async () => {
    if (!val.trim()) {
      await fetchCases()
      return
    }
    loading.value = true
    try {
      const res = await getCases({ search: val, view: 'flat' })
      flatList.value = res.data || []
    } finally {
      loading.value = false
    }
  }, 300)
}

const filteredFlat = computed(() => {
  let list = flatList.value
  if (searchQuery.value.trim()) return list
  if (flatFilter.value === 'all') return list
  if (flatFilter.value === 'overdue') return list.filter((c) => c.overdue_status === 'overdue')
  if (flatFilter.value === 'due_3') return list.filter((c) => c.overdue_status === 'overdue' && c.overdue_days <= 3)
  if (flatFilter.value === 'due_7') return list.filter((c) => c.overdue_status === 'due_soon')
  return list.filter((c) => c.stage === flatFilter.value)
})

function itemSelected(id) {
  return selectedIds.value.has(id)
}

function goDetail(id) {
  router.push(`/case/${id}`)
}

async function batchAdvance() {
  await doBatchAdvance()
  fetchStats()
}

async function batchAssign() {
  try {
    const res = await getLawyers()
    lawyers.value = res.data
  } catch {}
  const { value } = await ElMessageBox.prompt('请输入律师姓名关键词或选择第一个律师', '指派律师', {
    inputPattern: /.*/,
    inputErrorMessage: '',
  })
  const l = lawyers.value[0]
  if (l) await doBatchAssign(l.id)
  fetchStats()
}

function onStatFilter(key) {
  flatFilter.value = key
  filters.view = 'flat'
}

function attachListeners() {
  window.addEventListener('smart-ingest-confirmed', refreshList)
  window.addEventListener('highlight-case', onHighlightCase)
}

function detachListeners() {
  window.removeEventListener('smart-ingest-confirmed', refreshList)
  window.removeEventListener('highlight-case', onHighlightCase)
  if (highlightTimer) clearTimeout(highlightTimer)
}

onMounted(() => {
  fetchCases()
  fetchStats()
  attachListeners()
})

onBeforeUnmount(() => {
  detachListeners()
})

// keep-alive 生命周期
onActivated(() => {
  attachListeners()
})

onDeactivated(() => {
  detachListeners()
})
</script>

<template>
  <div>
    <div class="header">
      <h1>案件总览</h1>
      <div class="header-meta">
        <span>共 {{ stats.total_active }} 件进行中</span>
        <span class="hm-dot"></span>
        <span>超期 <span class="hm-alert">{{ stats.overdue_count }}</span></span>
        <span class="hm-dot"></span>
        <span>本周开庭 {{ stats.this_week_court }}</span>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="search-box">
      <el-input
        v-model="searchQuery"
        placeholder="搜索案号、当事人、案由…"
        :prefix-icon="Search"
        clearable
        @input="onSearch"
        @clear="fetchCases"
      />
    </div>

    <StatsCards :stats="stats" @filter="onStatFilter" />

    <!-- Controls -->
    <div class="vrow">
      <ViewToggle v-model:view="filters.view" />
      <BatchBar
        :selected-count="selectedCount"
        @advance="batchAdvance"
        @assign="batchAssign"
        @clear="clearSelection"
      />
      <div class="vi">显示 {{ filteredFlat.length }} 件</div>
    </div>

    <!-- Flow View -->
    <div v-if="filters.view === 'flow' && !searchQuery.trim()" v-loading="showLoading" class="flow">
      <FlowSection
        v-for="sec in sections"
        :key="sec.stage"
        :section="sec"
        :item-selected="itemSelected"
        :highlighted-case-id="highlightedCaseId"
        @toggle="toggleSelect"
        @advance="(id) => { doAdvance(id); fetchStats() }"
        @detail="goDetail"
      />
    </div>

    <!-- Flat View -->
    <div v-else v-loading="showLoading" class="flat">
      <FlatFilters :stats="stats" :active-filter="flatFilter" @update:active-filter="flatFilter = $event" />
      <FlatCaseItem
        v-for="item in filteredFlat"
        :key="item.id"
        :item="item"
        :selected="itemSelected(item.id)"
        :highlighted="highlightedCaseId === item.id"
        @toggle="toggleSelect"
        @detail="goDetail"
      />
      <div v-if="filteredFlat.length === 0" class="empty">没有符合条件的案件</div>
    </div>
  </div>
</template>

<style scoped>
.header { margin-bottom: 20px; }
.header h1 { font-size: 26px; font-weight: 700; letter-spacing: -0.03em; color: var(--text); }
.header-meta { display: flex; align-items: center; gap: 16px; margin-top: 6px; }
.header-meta span { font-size: 13px; color: var(--text-secondary); }
.hm-dot { width: 4px; height: 4px; border-radius: 50%; background: var(--text-tertiary); }
.hm-alert { color: var(--red); font-weight: 500; }

.search-box { margin-bottom: 20px; max-width: 520px; }
.search-box :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--border) inset; border-radius: var(--radius-sm);
}
.search-box :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px var(--accent) inset; }
.search-box :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--accent-soft), 0 0 0 1px var(--accent) inset;
}

.vrow { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.vi { font-size: 12px; color: var(--text-tertiary); margin-left: auto; }
.flow { display: flex; flex-direction: column; }
.flat { display: flex; flex-direction: column; }
.empty { text-align: center; padding: 60px 0; color: var(--text-tertiary); font-size: 14px; }
</style>
