<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { searchDocuments } from '@/api/documents'
import { getCases } from '@/api/cases'

const router = useRouter()
const query = ref('')
const loading = ref(false)
const activeTab = ref('docs')
const docResults = ref([])
const caseResults = ref([])

let debounceTimer = null

function doSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(async () => {
    const q = query.value.trim()
    if (!q) {
      docResults.value = []
      caseResults.value = []
      return
    }
    loading.value = true
    try {
      const [docRes, caseRes] = await Promise.all([
        searchDocuments(q),
        getCases({ search: q, view: 'flat' }),
      ])
      docResults.value = docRes.data || []
      caseResults.value = caseRes.data || []
    } catch {}
    finally { loading.value = false }
  }, 300)
}

watch(query, doSearch)

function goCase(id) {
  router.push(`/case/${id}`)
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN')
}

const STAGE_MAP = {
  consultation: '咨询/待定',
  document_prep: '文书准备',
  court_appearance: '出庭应诉',
  awaiting_result: '等候结果',
  closed: '已结/归档',
}
</script>

<template>
  <div>
    <div class="header">
      <h1>知识搜索</h1>
      <p>搜索全所代理词、判决书、法律意见书及案件信息</p>
    </div>

    <div class="search-box">
      <el-input
        v-model="query"
        placeholder="搜索案号、当事人、案由、文书关键词…"
        :prefix-icon="Search"
        size="large"
        clearable
        class="search-input"
      />
    </div>

    <div v-if="!query.trim()" class="empty-hint">
      <span class="empty-icon">◈</span>
      <p>输入关键词开始搜索</p>
      <p class="sub">支持按当事人名称、案号、案由、文书内容进行检索</p>
    </div>

    <div v-else v-loading="loading" class="results-area">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="`案件 (${caseResults.length})`" name="cases">
          <div v-if="caseResults.length === 0" class="no-results">无匹配案件</div>
          <div v-for="c in caseResults" :key="c.id" class="result-card case" @click="goCase(c.id)">
            <div class="rc-hd">
              <span class="rc-name">{{ c.case_name }}</span>
              <el-tag size="small">{{ STAGE_MAP[c.stage] || c.stage }}</el-tag>
            </div>
            <div class="rc-body">
              <span v-if="c.case_number" class="rc-num">{{ c.case_number }}</span>
              <span v-if="c.plaintiff || c.defendant">{{ c.plaintiff || '?' }} → {{ c.defendant || '?' }}</span>
              <span v-if="c.cause_of_action" class="rc-cause">{{ c.cause_of_action }}</span>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="`文书 (${docResults.length})`" name="docs">
          <div v-if="docResults.length === 0" class="no-results">无匹配文书</div>
          <div v-for="d in docResults" :key="d.id" class="result-card doc" @click="goCase(d.case_id)">
            <div class="rc-hd">
              <span class="rc-name">{{ d.filename }}</span>
              <el-tag size="small" type="info">{{ d.file_type?.toUpperCase() }}</el-tag>
            </div>
            <div class="rc-body">
              <span>{{ d.case_name }}</span>
              <span class="rc-meta">{{ formatSize(d.file_size) }} · {{ formatDate(d.uploaded_at) }}</span>
            </div>
            <div v-if="d.snippet" class="rc-snippet">{{ d.snippet }}…</div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped>
.header { margin-bottom: 24px; }
.header h1 { font-size: 26px; font-weight: 700; letter-spacing: -0.03em; }
.header p { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.search-box { margin-bottom: 24px; max-width: 680px; }
.search-input :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--border) inset; border-radius: var(--radius);
}
.search-input :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px var(--accent) inset; }
.search-input :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 2px var(--accent-soft), 0 0 0 1px var(--accent) inset; }

.empty-hint { text-align: center; padding: 80px 0; color: var(--text-tertiary); }
.empty-icon { font-size: 48px; display: block; margin-bottom: 16px; }
.empty-hint p { font-size: 16px; font-weight: 500; }
.empty-hint .sub { font-size: 13px; margin-top: 6px; }

.results-area { max-width: 860px; }
.no-results { text-align: center; padding: 40px 0; color: var(--text-tertiary); font-size: 14px; }

.result-card {
  padding: 16px 20px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  margin-bottom: 10px; cursor: pointer; transition: all 0.15s; background: var(--surface);
}
.result-card:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
html.dark .result-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.25); }
.rc-hd { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.rc-name { font-size: 14px; font-weight: 600; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc-body { display: flex; align-items: center; gap: 16px; font-size: 12px; color: var(--text-secondary); }
.rc-num { font-family: "SF Mono","Consolas",monospace; color: var(--text-tertiary); }
.rc-cause { color: var(--accent); }
.rc-meta { color: var(--text-tertiary); }
.rc-snippet {
  margin-top: 10px; padding: 10px 12px; background: var(--bg); border-radius: var(--radius-sm);
  font-size: 12px; color: var(--text-secondary); line-height: 1.6; max-height: 60px; overflow: hidden;
}
</style>
