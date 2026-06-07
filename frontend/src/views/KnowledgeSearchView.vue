<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { getCases, searchKnowledgeCases } from '@/api/cases'

const router = useRouter()
const query = ref('')
const loading = ref(false)
const caseResults = ref([])

let debounceTimer = null

function fallbackQueries(value) {
  const normalized = value.normalize('NFKC')
  const compact = normalized.replace(/[\s()[\]{}<>,.，。:：;；、/\\\-_|\uFF08\uFF09]/g, '')
  const numberParts = [...normalized.matchAll(/\d{4,}/g)].map((match) => match[0]).reverse()
  return [...new Set([value, normalized, compact, ...numberParts].filter(Boolean))]
}

async function fallbackSearchCases(value) {
  const queries = fallbackQueries(value)
  for (const item of queries) {
    const res = await getCases({ search: item, view: 'flat' })
    const data = res.data || []
    if (data.length > 0) return data
  }
  return []
}

function doSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(async () => {
    const q = query.value.trim()
    if (!q) {
      caseResults.value = []
      return
    }
    loading.value = true
    try {
      const res = await searchKnowledgeCases(q)
      caseResults.value = res.data || []
    } catch {
      const fallback = await fallbackSearchCases(q)
      caseResults.value = fallback.map((item) => ({
        ...item,
        matched_fields: ['案件信息'],
        document_matches: [],
        snippet: '',
      }))
    }
    finally { loading.value = false }
  }, 300)
}

watch(query, doSearch)

function goCase(id) {
  router.push(`/case/${id}`)
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
      <p>检索现有案件的当事人、案号、案由和文书内容</p>
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
      <div class="result-meta">找到 {{ caseResults.length }} 件现有案件</div>
      <div v-if="caseResults.length === 0" class="no-results">无匹配案件</div>
      <div v-for="c in caseResults" :key="c.id" class="result-card case" @click="goCase(c.id)">
        <div class="rc-hd">
          <span class="rc-name">{{ c.case_name }}</span>
          <div class="rc-tags">
            <el-tag
              v-for="field in c.matched_fields"
              :key="field"
              size="small"
              type="success"
            >
              {{ field }}
            </el-tag>
            <el-tag size="small">{{ STAGE_MAP[c.stage] || c.stage }}</el-tag>
          </div>
        </div>
        <div class="rc-body">
          <span v-if="c.case_number" class="rc-num">{{ c.case_number }}</span>
          <span v-if="c.plaintiff || c.defendant">{{ c.plaintiff || '?' }} → {{ c.defendant || '?' }}</span>
          <span v-if="c.cause_of_action" class="rc-cause">{{ c.cause_of_action }}</span>
        </div>
        <div v-if="c.snippet" class="rc-snippet">{{ c.snippet }}</div>
        <div v-if="c.document_matches?.length" class="doc-matches">
          <div v-for="d in c.document_matches" :key="d.id" class="doc-line">
            <span class="doc-name">{{ d.filename }}</span>
            <span class="doc-meta">{{ d.file_type?.toUpperCase() }} · {{ formatDate(d.uploaded_at) }}</span>
            <span v-if="d.snippet" class="doc-snippet">{{ d.snippet }}</span>
          </div>
        </div>
      </div>
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

.results-area { max-width: 920px; }
.result-meta { color: var(--text-secondary); font-size: 13px; margin-bottom: 12px; }
.no-results { text-align: center; padding: 40px 0; color: var(--text-tertiary); font-size: 14px; }

.result-card {
  padding: 16px 20px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  margin-bottom: 10px; cursor: pointer; transition: all 0.15s; background: var(--surface);
}
.result-card:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
html.dark .result-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.25); }
.rc-hd { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px; }
.rc-name { font-size: 14px; font-weight: 600; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc-tags { flex-shrink: 0; display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 6px; max-width: 360px; }
.rc-body { display: flex; align-items: center; flex-wrap: wrap; gap: 10px 16px; font-size: 12px; color: var(--text-secondary); }
.rc-num { font-family: "SF Mono","Consolas",monospace; color: var(--text-tertiary); }
.rc-cause { color: var(--accent); }
.rc-snippet {
  margin-top: 10px; padding: 10px 12px; background: var(--bg); border-radius: var(--radius-sm);
  font-size: 12px; color: var(--text-secondary); line-height: 1.6; max-height: 72px; overflow: hidden;
}
.doc-matches {
  margin-top: 12px; border-top: 1px solid var(--border); padding-top: 10px;
  display: flex; flex-direction: column; gap: 8px;
}
.doc-line {
  display: grid; grid-template-columns: minmax(140px, 220px) minmax(90px, 140px) 1fr;
  gap: 10px; align-items: baseline; font-size: 12px;
}
.doc-name { color: var(--text); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-meta { color: var(--text-tertiary); }
.doc-snippet { color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@media (max-width: 720px) {
  .rc-hd { flex-direction: column; }
  .rc-tags { justify-content: flex-start; max-width: 100%; }
  .doc-line { grid-template-columns: 1fr; gap: 4px; }
  .doc-snippet { white-space: normal; }
}
</style>
