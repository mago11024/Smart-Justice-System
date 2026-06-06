<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotifications, getNotificationStats, markRead, readAll } from '@/api/notifications'
import { useDeferredLoading } from '@/composables/useDeferredLoading'

const router = useRouter()
const notifications = ref([])
const nstats = ref({ total_unread: 0, overdue_count: 0, due_soon_count: 0, court_count: 0 })
const activeGroup = ref('all')
const { showLoading, run } = useDeferredLoading()

async function fetchAll() {
  await run(async () => {
    const [notifRes, statsRes] = await Promise.all([
      getNotifications(),
      getNotificationStats(),
    ])
    notifications.value = notifRes.data
    nstats.value = statsRes.data
  })
}

const groups = computed(() => {
  return [
    { key: 'all', label: '全部', count: nstats.value.total_unread, color: '' },
    { key: 'overdue', label: '超期预警', count: nstats.value.overdue_count, color: 'var(--red)', icon: '🔴' },
    { key: 'due_soon', label: '即将到期', count: nstats.value.due_soon_count, color: 'var(--orange)', icon: '🟠' },
    { key: 'court_tomorrow', label: '开庭提醒', count: nstats.value.court_count, color: 'var(--blue)', icon: '🔵' },
  ]
})

const filteredNotifs = computed(() => {
  if (activeGroup.value === 'all') return notifications.value
  if (activeGroup.value === 'unread') return notifications.value.filter(n => !n.is_read)
  return notifications.value.filter(n => n.type === activeGroup.value)
})

async function doMarkRead(id) {
  await markRead(id)
  fetchAll()
}

async function doReadAll() {
  await readAll()
  fetchAll()
}

function goCase(id) {
  router.push(`/case/${id}`)
}

function typeLabel(type) {
  return { overdue: '超期', due_soon: '即将到期', court_tomorrow: '开庭' }[type] || type
}

function typeTag(type) {
  return { overdue: 'danger', due_soon: 'warning', court_tomorrow: '' }[type] || 'info'
}

onMounted(fetchAll)
</script>

<template>
  <div v-loading="showLoading">
    <div class="header">
      <h1>提醒中心</h1>
      <p>超期 {{ nstats.overdue_count }} 件 · 即将到期 {{ nstats.due_soon_count }} 件 · 开庭 {{ nstats.court_count }} 件</p>
    </div>

    <!-- 统计卡 -->
    <div class="stats-row">
      <div v-for="g in groups" :key="g.key" :class="['stat-chip', { active: activeGroup === g.key }]" @click="activeGroup = g.key">
        <span v-if="g.icon" class="chip-icon">{{ g.icon }}</span>
        <span class="chip-label">{{ g.label }}</span>
        <span class="chip-n">{{ g.count }}</span>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="toolbar">
      <span v-if="nstats.total_unread > 0" class="unread-info">{{ nstats.total_unread }} 条未读</span>
      <el-button v-if="nstats.total_unread > 0" size="small" type="primary" text @click="doReadAll">全部标为已读</el-button>
    </div>

    <!-- 通知列表 -->
    <div v-if="filteredNotifs.length === 0" class="empty">
      <p>暂无提醒</p>
      <p class="sub">一切正常，继续保持</p>
    </div>

    <div v-for="n in filteredNotifs" :key="n.id" :class="['notif', { read: n.is_read }]">
      <div class="n-left" @click="goCase(n.case_id)">
        <div :class="['n-dot', n.type]"></div>
        <div class="n-body">
          <div class="n-msg">
            <el-tag size="small" :type="typeTag(n.type)" effect="plain">
              {{ typeLabel(n.type) }}
            </el-tag>
            <span class="n-text">{{ n.message }}</span>
          </div>
          <div class="n-meta">
            <span class="n-case-name" @click.stop="goCase(n.case_id)">
              {{ n.case_number ? `${n.case_number} · ` : '' }}{{ n.case_name }}
            </span>
            <span class="n-time">{{ new Date(n.created_at).toLocaleString('zh-CN') }}</span>
          </div>
        </div>
      </div>
      <el-button v-if="!n.is_read" size="small" text type="primary" @click="doMarkRead(n.id)">已读</el-button>
    </div>
  </div>
</template>

<style scoped>
.header { margin-bottom: 20px; }
.header h1 { font-size: 26px; font-weight: 700; letter-spacing: -0.03em; }
.header p { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.stats-row { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.stat-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 20px; border: 1px solid var(--border);
  background: var(--surface); cursor: pointer; transition: all 0.15s;
  font-size: 13px; font-weight: 500; color: var(--text-secondary);
}
.stat-chip:hover { border-color: var(--accent); color: var(--accent); }
.stat-chip.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.chip-icon { font-size: 11px; }
.chip-n {
  background: rgba(0,0,0,0.06); border-radius: 10px; padding: 1px 8px;
  font-size: 11px; font-weight: 600;
}
html.dark .chip-n { background: rgba(255,255,255,0.08); }
.stat-chip.active .chip-n { background: rgba(255,255,255,0.2); }

.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.unread-info { font-size: 12px; color: var(--text-tertiary); }

.empty { text-align: center; padding: 60px 0; color: var(--text-tertiary); }
.empty p { font-size: 15px; font-weight: 500; }
.empty .sub { font-size: 12px; margin-top: 4px; }

.notif {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); margin-bottom: 8px; transition: all 0.15s;
}
.notif:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
html.dark .notif:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.25); }
.notif.read { opacity: 0.45; }
.n-left { display: flex; align-items: flex-start; gap: 12px; cursor: pointer; flex: 1; min-width: 0; }
.n-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 6px;
}
.n-dot.overdue { background: var(--red); }
.n-dot.due_soon { background: var(--orange); }
.n-dot.court_tomorrow { background: var(--blue); }

.n-body { flex: 1; min-width: 0; }
.n-msg { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.n-text { font-size: 14px; line-height: 1.4; }
.n-meta { display: flex; align-items: center; gap: 16px; font-size: 12px; color: var(--text-tertiary); }
.n-case-name { color: var(--accent); cursor: pointer; }
.n-case-name:hover { text-decoration: underline; }
</style>
