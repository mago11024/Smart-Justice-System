<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getNotifications } from '@/api/notifications'
import {
  DataAnalysis,
  Bell,
  Search,
  MagicStick,
  UserFilled,
  Setting,
  List,
} from '@element-plus/icons-vue'
import GlobalDropZone from '@/components/ai/GlobalDropZone.vue'
import { getIngestTaskCount } from '@/api/documents'
import { useEventStream } from '@/composables/useEventStream'

defineProps({
  collapsed: { type: Boolean, default: false },
})

const route = useRoute()
const router = useRouter()

const unreadCount = ref(0)
const taskCount = ref(0)

const navItems = computed(() => [
  { path: '/', icon: DataAnalysis, label: '案件总览' },
  { path: '/reminders', icon: Bell, label: '提醒中心', badge: unreadCount.value },
  { path: '/tasks', icon: List, label: '任务中心', badge: taskCount.value },
  { path: '/search', icon: Search, label: '知识搜索' },
  { path: '/ai', icon: MagicStick, label: 'AI 能力' },
  { path: '/lawyers', icon: UserFilled, label: '律师工作负载' },
])

const currentPath = computed(() => route.path)

function navigate(path) {
  router.push(path)
}

async function fetchUnread() {
  try {
    const res = await getNotifications(true, { silent: true })
    unreadCount.value = res.data.length
  } catch {}
}

async function fetchTaskCount() {
  try {
    const res = await getIngestTaskCount({ silent: true })
    taskCount.value = res.data.active
  } catch {}
}

const { notificationVersion, taskVersion } = useEventStream()

onMounted(() => { fetchUnread(); fetchTaskCount() })
watch(notificationVersion, () => { fetchUnread() })
watch(taskVersion, () => { fetchTaskCount() })
</script>

<template>
  <aside :class="['sidebar', { collapsed }]">
    <div class="sb-head">
      <div class="sb-icon">律</div>
      <span v-show="!collapsed" class="sb-title">案件驾驶舱</span>
      <span v-show="!collapsed" class="sb-version">v1.0</span>
    </div>
    <nav class="sb-nav">
      <button
        v-for="item in navItems"
        :key="item.path"
        :class="['sb-item', { active: (item.path === '/' ? currentPath === '/' : currentPath.startsWith(item.path)) }]"
        :title="collapsed ? item.label : ''"
        @click="navigate(item.path)"
      >
        <component :is="item.icon" class="icon" />
        <span v-show="!collapsed" class="label">{{ item.label }}</span>
        <span v-if="item.badge > 0" :class="['badge', { 'badge-collapsed': collapsed }]">
          <template v-if="collapsed">●</template>
          <template v-else>{{ unreadCount }}</template>
        </span>
      </button>
    </nav>
    <div v-if="!collapsed" class="sb-secondary">
      <button
        :class="['sb-item', { active: currentPath === '/settings' }]"
        title="设置"
        @click="navigate('/settings')"
      >
        <component :is="Setting" class="icon" />
        <span v-show="!collapsed" class="label">设置</span>
      </button>
    </div>
    <GlobalDropZone v-if="!collapsed" />
    <div class="sb-foot">
      <div class="sb-user">
        <span class="sb-av">张</span>
        <div v-show="!collapsed">
          <div class="sb-un">张明</div>
          <div class="sb-ur">主任</div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 240px; background: var(--surface); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; flex-shrink: 0;
  transition: width 0.2s ease;
  overflow: hidden;
}
.sidebar.collapsed { width: 64px; }

.sb-head { display: flex; align-items: center; gap: 10px; padding: 20px 20px 16px; }
.collapsed .sb-head { padding: 20px 16px 16px; justify-content: center; }
.sb-icon {
  width: 32px; height: 32px; border-radius: 8px;
  background: linear-gradient(135deg, var(--accent), #8B5CF6);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 14px; font-weight: 700;
  flex-shrink: 0;
}
html.dark .sb-icon { background: linear-gradient(135deg, var(--accent), #5B3CC4); }
.sb-title { font-size: 15px; font-weight: 700; letter-spacing: -0.02em; white-space: nowrap; }
.sb-version {
  font-size: 10px; color: var(--text-tertiary); font-weight: 500;
  padding: 2px 6px; border-radius: 4px; background: var(--border);
  margin-left: auto; margin-top: 2px; white-space: nowrap;
}

.sb-nav { flex: 1; padding: 8px 12px; display: flex; flex-direction: column; gap: 2px; }
.collapsed .sb-nav { padding: 8px; }

.sb-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  border-radius: var(--radius-sm); cursor: pointer; font-size: 13px; font-weight: 500;
  color: var(--text-secondary); transition: all 0.12s;
  border: none; background: none; font-family: inherit; text-align: left; width: 100%;
  position: relative;
}
.collapsed .sb-item {
  justify-content: center; padding: 10px 0;
}
.sb-item:hover { color: var(--text); background: var(--bg); }
.sb-item.active { color: var(--accent); background: var(--accent-soft); }
.label { white-space: nowrap; }
.sb-item .badge {
  margin-left: auto; background: var(--red-soft); color: var(--red);
  font-size: 10px; font-weight: 600; padding: 1px 7px; border-radius: 10px;
}
.badge-collapsed {
  position: absolute; top: 4px; right: 4px; margin-left: 0 !important;
  font-size: 8px !important; padding: 0 !important; background: transparent !important;
  color: var(--red) !important;
}

.icon { font-size: 15px; width: 20px; text-align: center; flex-shrink: 0; }

.sb-foot { padding: 12px; border-top: 1px solid var(--border); }
.collapsed .sb-foot { padding: 8px; }
.sb-user { display: flex; align-items: center; gap: 10px; padding: 8px; }
.collapsed .sb-user { justify-content: center; }
.sb-av {
  width: 28px; height: 28px; border-radius: 50%; background: var(--accent-soft);
  color: var(--accent); display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.sb-un { font-size: 12px; font-weight: 600; white-space: nowrap; }
.sb-ur { font-size: 11px; color: var(--text-tertiary); white-space: nowrap; }

.sb-secondary { padding: 4px 12px 8px; border-top: 1px solid var(--border); }
</style>
