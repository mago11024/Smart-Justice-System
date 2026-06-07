<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getIngestTasks, getIngestTaskText, getSmartIngestResult } from '@/api/documents'
import { STAGE_LABEL_MAP } from '@/utils/constants'
import SmartIngestDialog from '@/components/ai/SmartIngestDialog.vue'

const route = useRoute()
const router = useRouter()

const doc = ref(null)
const text = ref('')
const textLength = ref(0)
const result = ref(null)
const loading = ref(false)
const resultLoading = ref(false)
const showDialog = ref(false)

const taskId = computed(() => Number(route.params.id))
const extracted = computed(() => result.value?.extracted || {})
const matched = computed(() => result.value?.matched_case)

const STATUS_LABEL_MAP = {
  completed: '已完成',
  processing: '处理中',
  pending: '等待处理',
  failed: '识别失败',
}

const STATUS_TYPE_MAP = {
  completed: 'success',
  processing: 'warning',
  pending: 'info',
  failed: 'danger',
}

const statusLabel = computed(() => STATUS_LABEL_MAP[doc.value?.ai_analysis_status] || doc.value?.ai_analysis_status || '未知')
const statusType = computed(() => STATUS_TYPE_MAP[doc.value?.ai_analysis_status] || 'info')

function findTask(tasks = []) {
  return tasks.find(t => Number(t.id) === taskId.value) || null
}

function formatTime(value) {
  if (!value) return ''
  const normalized = typeof value === 'string' && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)
    ? `${value}Z`
    : value
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function loadPage() {
  if (!taskId.value) {
    ElMessage.error('任务编号无效')
    router.replace('/tasks')
    return
  }

  loading.value = true
  try {
    const [tasksRes, resultRes] = await Promise.all([
      getIngestTasks(null, { silent: true }),
      getSmartIngestResult(taskId.value),
    ])
    doc.value = findTask(tasksRes.data) || {
      id: taskId.value,
      ai_analysis_status: resultRes.data?.status || '',
    }
    result.value = resultRes.data
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '识别结果加载失败')
    loading.value = false
    return
  }

  try {
    const textRes = await getIngestTaskText(taskId.value, { silent: true })
    text.value = textRes.data?.text || ''
    textLength.value = textRes.data?.length || text.value.length
  } catch {
    text.value = ''
    textLength.value = 0
    ElMessage.warning('原文预览暂时无法加载，识别结果仍可查看')
  } finally {
    loading.value = false
  }
}

async function refreshResult() {
  resultLoading.value = true
  try {
    const [tasksRes, resultRes] = await Promise.all([
      getIngestTasks(null, { silent: true }),
      getSmartIngestResult(taskId.value),
    ])
    doc.value = findTask(tasksRes.data) || doc.value
    result.value = resultRes.data
  } catch {
    ElMessage.error('识别结果刷新失败')
  } finally {
    resultLoading.value = false
  }
}

function onConfirm() {
  showDialog.value = false
  refreshResult()
}

onMounted(loadPage)
watch(() => route.params.id, () => { loadPage() })
</script>

<template>
  <div v-loading="loading" class="text-page">
    <div class="page-head">
      <div>
        <div class="crumb" @click="router.push('/tasks')">任务中心 / 文本查看</div>
        <h1>{{ doc?.filename || '文档文本' }}</h1>
        <div class="meta-row">
          <el-tag :type="statusType" size="small" effect="plain">{{ statusLabel }}</el-tag>
          <span v-if="doc?.uploaded_at">{{ formatTime(doc.uploaded_at) }}</span>
          <span>{{ textLength }} 字</span>
        </div>
      </div>
      <div class="head-actions">
        <el-button @click="router.push('/tasks')">返回任务中心</el-button>
        <el-button
          type="primary"
          :loading="resultLoading"
          :disabled="!result || result.status === 'pending' || result.status === 'processing'"
          @click="showDialog = true"
        >
          查看识别结果
        </el-button>
      </div>
    </div>

    <div v-if="result" class="summary-band">
      <div class="summary-item">
        <span class="sk">案由</span>
        <strong>{{ extracted.cause_of_action || '未识别' }}</strong>
      </div>
      <div class="summary-item">
        <span class="sk">阶段</span>
        <strong>{{ STAGE_LABEL_MAP[extracted.stage] || extracted.stage || '未识别' }}</strong>
      </div>
      <div class="summary-item">
        <span class="sk">匹配案件</span>
        <strong>{{ matched?.case_name || '待确认' }}</strong>
      </div>
    </div>

    <section class="text-panel">
      <div class="panel-title">
        <span>提取文本</span>
        <el-button size="small" plain @click="loadPage">刷新</el-button>
      </div>
      <pre v-if="text">{{ text }}</pre>
      <div v-else class="empty-text">暂无可查看文本</div>
    </section>

    <SmartIngestDialog
      v-if="showDialog && result"
      :result="result"
      :mode="matched ? 'match' : 'create'"
      @confirm="onConfirm"
      @close="showDialog = false"
    />
  </div>
</template>

<style scoped>
.text-page { max-width: 1040px; margin: 0 auto; }
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.crumb {
  display: inline-flex;
  color: var(--accent);
  font-size: 12px;
  cursor: pointer;
  margin-bottom: 8px;
}
.page-head h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  word-break: break-word;
}
.meta-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
  color: var(--text-tertiary);
  font-size: 12px;
}
.head-actions { display: flex; gap: 8px; flex-shrink: 0; }
.summary-band {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
}
.summary-item { min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.sk { color: var(--text-tertiary); font-size: 12px; }
.summary-item strong {
  color: var(--text);
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.text-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  overflow: hidden;
}
.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
  font-weight: 600;
}
.text-panel pre {
  min-height: 420px;
  max-height: calc(100vh - 280px);
  overflow: auto;
  margin: 0;
  padding: 18px 20px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  font-size: 14px;
  color: var(--text-secondary);
  font-family: inherit;
  background: var(--bg);
}
.empty-text {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  background: var(--bg);
}
@media (max-width: 760px) {
  .page-head { flex-direction: column; }
  .head-actions { width: 100%; flex-wrap: wrap; }
  .summary-band { grid-template-columns: 1fr; }
}
</style>
