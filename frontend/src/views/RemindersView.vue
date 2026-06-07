<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell, Calendar, Check, Clock, Document, Refresh, Search, Star, StarFilled, View, Warning } from '@element-plus/icons-vue'
import { getNotifications, getNotificationStats, markRead, markUnread, pinNotification, readAll, unpinNotification } from '@/api/notifications'
import { useDeferredLoading } from '@/composables/useDeferredLoading'
import { useEventStream } from '@/composables/useEventStream'

const router = useRouter()
const notifications = ref([])
const nstats = ref({ total_unread: 0, total_all: 0, overdue_count: 0, due_soon_count: 0, court_count: 0, analysis_count: 0 })
const activeGroup = ref('all')
const unreadOnly = ref(false)
const keyword = ref('')
const sortMode = ref('latest')
const detailVisible = ref(false)
const currentNotification = ref(null)
const { showLoading, run } = useDeferredLoading()
const { notificationVersion } = useEventStream()

async function fetchAll() {
  try {
    await run(async () => {
      const [notifRes, statsRes] = await Promise.all([
        getNotifications(),
        getNotificationStats(),
      ])
      notifications.value = notifRes.data
      nstats.value = { ...nstats.value, ...statsRes.data }
    })
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '提醒加载失败')
  }
}

const groups = computed(() => {
  return [
    { key: 'all', label: '全部', count: nstats.value.total_all || notifications.value.length, icon: Bell },
    { key: 'unread', label: '未读', count: nstats.value.total_unread, icon: View },
    { key: 'pinned', label: '置顶', count: pinnedCount.value, icon: StarFilled },
    { key: 'overdue', label: '超期预警', count: nstats.value.overdue_count, icon: Warning },
    { key: 'due_soon', label: '即将到期', count: nstats.value.due_soon_count, icon: Clock },
    { key: 'court_tomorrow', label: '开庭提醒', count: nstats.value.court_count, icon: Calendar },
    { key: 'analysis_complete', label: 'AI 分析', count: nstats.value.analysis_count, icon: Document },
  ]
})

const filteredNotifs = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  let list = [...notifications.value]

  if (activeGroup.value === 'unread') {
    list = list.filter(n => !n.is_read)
  } else if (activeGroup.value === 'pinned') {
    list = list.filter(n => n.is_pinned)
  } else if (activeGroup.value !== 'all') {
    list = list.filter(n => n.type === activeGroup.value)
  }

  if (unreadOnly.value) {
    list = list.filter(n => !n.is_read)
  }

  if (query) {
    list = list.filter((n) => {
      return [
        n.message,
        n.case_name,
        n.case_number,
        n.document_filename,
        typeLabel(n.type),
      ].some(v => String(v || '').toLowerCase().includes(query))
    })
  }

  const severity = { overdue: 0, due_soon: 1, court_tomorrow: 2, analysis_complete: 3 }
  list.sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
    if (sortMode.value === 'unread') {
      if (a.is_read !== b.is_read) return a.is_read ? 1 : -1
    }
    if (sortMode.value === 'risk') {
      const rank = (severity[a.type] ?? 9) - (severity[b.type] ?? 9)
      if (rank !== 0) return rank
    }
    return new Date(b.created_at) - new Date(a.created_at)
  })

  return list
})

async function doMarkRead(id) {
  try {
    await markRead(id)
    await fetchAll()
    if (currentNotification.value?.id === id) {
      currentNotification.value = { ...currentNotification.value, is_read: true }
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '标记已读失败')
  }
}

async function doMarkUnread(id) {
  try {
    await markUnread(id)
    await fetchAll()
    if (currentNotification.value?.id === id) {
      currentNotification.value = { ...currentNotification.value, is_read: false }
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '标记未读失败')
  }
}

async function doTogglePin(n) {
  try {
    if (n.is_pinned) {
      await unpinNotification(n.id)
      ElMessage.success('已取消置顶')
    } else {
      await pinNotification(n.id)
      ElMessage.success('已置顶')
    }
    await fetchAll()
    if (currentNotification.value?.id === n.id) {
      currentNotification.value = { ...currentNotification.value, is_pinned: !n.is_pinned }
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '置顶操作失败')
  }
}

async function doReadAll() {
  try {
    await readAll()
    await fetchAll()
    ElMessage.success('已全部标为已读')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '批量处理失败')
  }
}

async function doReadFiltered() {
  const unreadIds = filteredNotifs.value.filter(n => !n.is_read).map(n => n.id)
  if (unreadIds.length === 0) return
  try {
    await Promise.all(unreadIds.map(id => markRead(id)))
    await fetchAll()
    ElMessage.success('当前筛选结果已标为已读')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '批量处理失败')
  }
}

function goCase(n) {
  if (!n?.case_id) {
    openDetail(n)
    return
  }
  const query = n.document_id ? { focus: 'documents', document_id: n.document_id } : {}
  router.push({ path: `/case/${n.case_id}`, query })
}

function typeLabel(type) {
  return {
    overdue: '超期',
    due_soon: '即将到期',
    court_tomorrow: '开庭',
    analysis_complete: 'AI 分析',
  }[type] || type
}

function typeTag(type) {
  return { overdue: 'danger', due_soon: 'warning', court_tomorrow: '', analysis_complete: 'success' }[type] || 'info'
}

function typeIcon(type) {
  return {
    overdue: Warning,
    due_soon: Clock,
    court_tomorrow: Calendar,
    analysis_complete: Document,
  }[type] || Bell
}

function typeClass(type) {
  return {
    overdue: 'overdue',
    due_soon: 'due-soon',
    court_tomorrow: 'court',
    analysis_complete: 'analysis',
  }[type] || 'normal'
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function openDetail(n) {
  currentNotification.value = n
  detailVisible.value = true
}

async function viewNotification(n) {
  if (!n.is_read) await doMarkRead(n.id)
  goCase(n)
}

const unreadInFilter = computed(() => filteredNotifs.value.filter(n => !n.is_read).length)
const pinnedCount = computed(() => notifications.value.filter(n => n.is_pinned).length)

const activeEmptyText = computed(() => {
  const current = groups.value.find(g => g.key === activeGroup.value)
  if (keyword.value.trim()) return '没有匹配的提醒'
  if (unreadOnly.value || activeGroup.value === 'unread') return '暂无未读提醒'
  return `暂无${current?.label || ''}提醒`
})

watch(notificationVersion, () => { fetchAll() })

function resetFilters() {
  activeGroup.value = 'all'
  unreadOnly.value = false
  keyword.value = ''
  sortMode.value = 'latest'
}

onMounted(fetchAll)
</script>

<template>
  <div v-loading="showLoading">
    <div class="header">
      <div>
        <h1>提醒中心</h1>
        <p>未读 {{ nstats.total_unread }} 条 · 置顶 {{ pinnedCount }} 条 · 超期 {{ nstats.overdue_count }} 件 · 即将到期 {{ nstats.due_soon_count }} 件 · 开庭 {{ nstats.court_count }} 件 · AI 分析 {{ nstats.analysis_count }} 条</p>
      </div>
      <el-button :icon="Refresh" @click="fetchAll">刷新</el-button>
    </div>

    <div class="stats-row">
      <div v-for="g in groups" :key="g.key" :class="['stat-chip', { active: activeGroup === g.key }]" @click="activeGroup = g.key">
        <el-icon class="chip-icon"><component :is="g.icon" /></el-icon>
        <span class="chip-label">{{ g.label }}</span>
        <span class="chip-n">{{ g.count }}</span>
      </div>
    </div>

    <div class="toolbar">
      <el-input
        v-model="keyword"
        :prefix-icon="Search"
        clearable
        placeholder="搜索案件、案号、文档或提醒内容"
        class="search-input"
      />
      <el-switch v-model="unreadOnly" active-text="只看未读" />
      <el-select v-model="sortMode" class="sort-select">
        <el-option label="最新优先" value="latest" />
        <el-option label="未读优先" value="unread" />
        <el-option label="风险优先" value="risk" />
      </el-select>
      <div class="toolbar-actions">
        <el-button v-if="unreadInFilter > 0" size="small" plain type="primary" :icon="Check" @click="doReadFiltered">
          当前筛选已读
        </el-button>
        <el-button v-if="nstats.total_unread > 0" size="small" type="primary" text @click="doReadAll">全部标为已读</el-button>
      </div>
    </div>

    <div v-if="filteredNotifs.length === 0" class="empty">
      <p>{{ activeEmptyText }}</p>
      <p class="sub">可以调整筛选条件或稍后刷新查看</p>
      <el-button v-if="keyword || unreadOnly || activeGroup !== 'all'" size="small" @click="resetFilters">清空筛选</el-button>
    </div>

    <div v-for="n in filteredNotifs" :key="n.id" :class="['notif', typeClass(n.type), { read: n.is_read, pinned: n.is_pinned }]">
      <div class="n-left" @click="openDetail(n)">
        <div class="n-type-icon">
          <el-icon><component :is="typeIcon(n.type)" /></el-icon>
        </div>
        <div class="n-body">
          <div class="n-msg">
            <el-tag v-if="n.is_pinned" size="small" type="warning" effect="dark" class="pin-badge">
              <el-icon><StarFilled /></el-icon>
              置顶
            </el-tag>
            <el-tag size="small" :type="typeTag(n.type)" effect="plain">
              {{ typeLabel(n.type) }}
            </el-tag>
            <span v-if="!n.is_read" class="unread-dot"></span>
            <span class="n-text">{{ n.message }}</span>
          </div>
          <div class="n-meta">
            <span v-if="n.case_id" class="n-case-name" @click.stop="goCase(n)">
              {{ n.case_number ? `${n.case_number} · ` : '' }}{{ n.case_name || '关联案件' }}
            </span>
            <span v-else class="n-case-empty">未关联案件</span>
            <span v-if="n.document_filename" class="n-document">{{ n.document_filename }}</span>
            <span class="n-time">{{ formatTime(n.created_at) }}</span>
          </div>
        </div>
      </div>
      <div class="n-actions">
        <el-button size="small" text :type="n.is_pinned ? 'warning' : 'info'" :icon="n.is_pinned ? StarFilled : Star" @click="doTogglePin(n)">
          {{ n.is_pinned ? '取消置顶' : '置顶' }}
        </el-button>
        <el-button size="small" text :icon="View" @click="openDetail(n)">查看</el-button>
        <el-button v-if="n.case_id" size="small" text type="primary" @click="viewNotification(n)">处理</el-button>
        <el-button v-if="!n.is_read" size="small" text type="primary" @click="doMarkRead(n.id)">已读</el-button>
        <el-button v-else size="small" text type="primary" @click="doMarkUnread(n.id)">未读</el-button>
      </div>
    </div>

    <el-drawer v-model="detailVisible" title="提醒详情" size="420px">
      <template v-if="currentNotification">
        <div :class="['detail-head', typeClass(currentNotification.type)]">
          <div class="detail-icon">
            <el-icon><component :is="typeIcon(currentNotification.type)" /></el-icon>
          </div>
          <div>
            <el-tag :type="typeTag(currentNotification.type)" effect="plain">{{ typeLabel(currentNotification.type) }}</el-tag>
            <h3>{{ currentNotification.message }}</h3>
            <p>{{ currentNotification.is_read ? '已读' : '未读' }} · {{ currentNotification.is_pinned ? '已置顶' : '未置顶' }} · {{ formatTime(currentNotification.created_at) }}</p>
          </div>
        </div>

        <el-descriptions :column="1" border size="small" class="detail-desc">
          <el-descriptions-item label="案件">
            {{ currentNotification.case_name || '未关联案件' }}
          </el-descriptions-item>
          <el-descriptions-item label="案号">
            {{ currentNotification.case_number || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="文档">
            {{ currentNotification.document_filename || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="生成时间">
            {{ formatTime(currentNotification.created_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="drawer-actions">
          <el-button v-if="currentNotification.case_id" type="primary" @click="viewNotification(currentNotification)">
            {{ currentNotification.document_id ? '查看文档分析' : '查看案件' }}
          </el-button>
          <el-button :type="currentNotification.is_pinned ? 'warning' : 'default'" @click="doTogglePin(currentNotification)">
            {{ currentNotification.is_pinned ? '取消置顶' : '置顶' }}
          </el-button>
          <el-button v-if="!currentNotification.is_read" @click="doMarkRead(currentNotification.id)">标为已读</el-button>
          <el-button v-else @click="doMarkUnread(currentNotification.id)">标为未读</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
.header h1 { font-size: 26px; font-weight: 700; letter-spacing: 0; }
.header p { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.stats-row { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.stat-chip {
  display: flex; align-items: center; gap: 6px;
  min-height: 38px; padding: 8px 14px; border-radius: 19px; border: 1px solid var(--border);
  background: var(--surface); cursor: pointer; transition: all 0.15s;
  font-size: 13px; font-weight: 500; color: var(--text-secondary);
}
.stat-chip:hover { border-color: var(--accent); color: var(--accent); }
.stat-chip.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.chip-icon { font-size: 14px; }
.chip-n {
  background: rgba(0,0,0,0.06); border-radius: 10px; padding: 1px 8px;
  font-size: 11px; font-weight: 600;
}
html.dark .chip-n { background: rgba(255,255,255,0.08); }
.stat-chip.active .chip-n { background: rgba(255,255,255,0.2); }

.toolbar {
  display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap;
  padding: 12px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm);
}
.search-input { width: min(420px, 100%); }
.sort-select { width: 128px; }
.toolbar-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }

.empty {
  text-align: center; padding: 60px 0; color: var(--text-tertiary);
  background: var(--surface); border: 1px dashed var(--border); border-radius: var(--radius-sm);
}
.empty p { font-size: 15px; font-weight: 500; }
.empty .sub { font-size: 12px; margin-top: 4px; margin-bottom: 14px; }

.notif {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; min-height: 86px; padding: 16px 18px; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); margin-bottom: 8px; transition: all 0.15s;
}
.notif:not(.read) { border-left-width: 4px; }
.notif.overdue:not(.read) { border-left-color: var(--red); }
.notif.due-soon:not(.read) { border-left-color: var(--orange); }
.notif.court:not(.read) { border-left-color: var(--blue); }
.notif.analysis:not(.read) { border-left-color: #10b981; }
.notif.pinned {
  border-color: rgba(245,158,11,0.45);
  box-shadow: 0 1px 0 rgba(245,158,11,0.1);
}
.notif:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.04); transform: translateY(-1px); }
html.dark .notif:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.25); }
.notif.read { opacity: 0.68; }
.n-left { display: flex; align-items: flex-start; gap: 12px; cursor: pointer; flex: 1; min-width: 0; }
.n-type-icon {
  width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0; display: grid; place-items: center;
  background: var(--accent-soft); color: var(--accent); margin-top: 1px;
}
.notif.overdue .n-type-icon { background: rgba(239,68,68,0.08); color: var(--red); }
.notif.due-soon .n-type-icon { background: rgba(245,158,11,0.1); color: var(--orange); }
.notif.court .n-type-icon { background: rgba(59,130,246,0.1); color: var(--blue); }
.notif.analysis .n-type-icon { background: rgba(16,185,129,0.1); color: #059669; }

.n-body { flex: 1; min-width: 0; }
.n-msg { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.pin-badge :deep(.el-tag__content) { display: inline-flex; align-items: center; gap: 3px; }
.unread-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
.n-text { font-size: 14px; line-height: 1.4; overflow-wrap: anywhere; }
.n-meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 12px; color: var(--text-tertiary); }
.n-case-name { color: var(--accent); cursor: pointer; }
.n-case-name:hover { text-decoration: underline; }
.n-case-empty, .n-document, .n-time { color: var(--text-tertiary); }
.n-document {
  max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.n-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

.detail-head {
  display: flex; gap: 12px; padding: 14px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: var(--surface); margin-bottom: 16px;
}
.detail-icon {
  width: 38px; height: 38px; display: grid; place-items: center; border-radius: 10px;
  background: var(--accent-soft); color: var(--accent); flex-shrink: 0;
}
.detail-head.overdue .detail-icon { background: rgba(239,68,68,0.08); color: var(--red); }
.detail-head.due-soon .detail-icon { background: rgba(245,158,11,0.1); color: var(--orange); }
.detail-head.court .detail-icon { background: rgba(59,130,246,0.1); color: var(--blue); }
.detail-head.analysis .detail-icon { background: rgba(16,185,129,0.1); color: #059669; }
.detail-head h3 { font-size: 15px; line-height: 1.5; margin: 8px 0 4px; overflow-wrap: anywhere; }
.detail-head p { font-size: 12px; color: var(--text-tertiary); }
.detail-desc { margin-bottom: 16px; }
.drawer-actions { display: flex; justify-content: flex-end; gap: 8px; }

@media (max-width: 768px) {
  .header { flex-direction: column; }
  .toolbar { align-items: stretch; }
  .search-input, .sort-select { width: 100%; }
  .toolbar-actions { margin-left: 0; justify-content: flex-start; flex-wrap: wrap; }
  .notif { align-items: flex-start; flex-direction: column; }
  .n-actions { align-self: flex-end; flex-wrap: wrap; justify-content: flex-end; }
  .n-document { max-width: 100%; }
}
</style>
