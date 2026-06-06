<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Fold, Expand, Sunny, Moon, Search } from '@element-plus/icons-vue'
import { exportCasesCsv } from '@/api/cases'
import { inject } from 'vue'

const props = defineProps({
  sidebarCollapsed: { type: Boolean, default: false },
  isDark: { type: Boolean, default: false },
})

const emit = defineEmits(['toggleSidebar', 'toggleTheme'])

const router = useRouter()
const searchText = ref('')

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
</style>
