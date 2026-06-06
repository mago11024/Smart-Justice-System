<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Fold, Expand, Sunny, Moon, Search, SwitchButton, User } from '@element-plus/icons-vue'
import { exportCasesCsv } from '@/api/cases'
import api from '@/api'

const props = defineProps({
  sidebarCollapsed: { type: Boolean, default: false },
  isDark: { type: Boolean, default: false },
})

const emit = defineEmits(['toggleSidebar', 'toggleTheme'])

const router = useRouter()
const searchText = ref('')
const currentUser = ref(readAuthUser())

function readAuthUser() {
  try {
    return JSON.parse(localStorage.getItem('auth_user') || '{}')
  } catch {
    return {}
  }
}

function onSearch() {
  const q = searchText.value.trim()
  if (q) {
    router.push('/search')
  }
}

async function doExport() {
  try {
    const res = await exportCasesCsv()
    const blob = new Blob([res.data], { type: 'text/csv; charset=utf-8-sig' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `案件导出_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已导出')
  } catch {
    ElMessage.error('导出失败')
  }
}

function goLogin() {
  window.location.href = '/login.html'
}

async function logout() {
  try {
    await api.post('/auth/logout', null, { silent: true })
  } catch {
    // Local logout still clears the token when the server is unavailable.
  } finally {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    window.location.href = '/login.html'
  }
}
</script>

<template>
  <div class="topbar">
    <el-button
      class="tb-toggle"
      :icon="sidebarCollapsed ? Expand : Fold"
      text
      @click="emit('toggleSidebar')"
      :title="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
    />
    <div class="tb-search">
      <el-input
        v-model="searchText"
        placeholder="搜索案号、当事人、案由…"
        :prefix-icon="Search"
        clearable
        @keyup.enter="onSearch"
      />
    </div>
    <div class="tb-spacer"></div>
    <div class="tb-actions">
      <el-button
        :icon="isDark ? Sunny : Moon"
        text
        @click="emit('toggleTheme')"
        :title="isDark ? '切换亮色' : '切换暗色'"
      />
      <el-button @click="doExport">导出</el-button>
      <el-button @click="router.push('/case/create')" type="primary">+ 新建案件</el-button>
      <div class="tb-user" v-if="currentUser.username">
        <el-icon><User /></el-icon>
        <span>{{ currentUser.username }}</span>
      </div>
      <el-button v-if="currentUser.username" :icon="SwitchButton" @click="logout">退出</el-button>
      <el-button v-else :icon="User" @click="goLogin">登录</el-button>
    </div>
  </div>
</template>

<style scoped>
.topbar {
  height: 56px; display: flex; align-items: center;
  padding: 0 20px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.tb-toggle { margin-right: 4px; font-size: 18px; }
.tb-search { width: 320px; }
.tb-spacer { flex: 1; }
.tb-actions { display: flex; align-items: center; gap: 8px; }
.tb-user {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 13px;
  white-space: nowrap;
}
</style>
