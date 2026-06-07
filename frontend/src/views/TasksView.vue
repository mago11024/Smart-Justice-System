<script setup>
import { ref, computed, onMounted, onBeforeUnmount, onActivated, onDeactivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { confirmIngest, getIngestTasks, getSmartIngestResult, reanalyzeDocument } from '@/api/documents'
import { getCases } from '@/api/cases'
import { useDeferredLoading } from '@/composables/useDeferredLoading'
import { useEventStream } from '@/composables/useEventStream'
import { STAGE_LABEL_MAP } from '@/utils/constants'
import SmartIngestDialog from '@/components/ai/SmartIngestDialog.vue'

const INGEST_STEPS = [
  { key: 'uploaded', label: '上传成功', percent: 8 },
  { key: 'extracting', label: '文本提取中', percent: 30 },
  { key: 'analyzing', label: 'AI 分析中', percent: 60 },
  { key: 'matching', label: '匹配案件中', percent: 85 },
  { key: 'confirming', label: '待确认', percent: 100 },
]

const INGEST_STEP_KEYS = new Set(INGEST_STEPS.map(s => s.key))

const router = useRouter()
const tasks = ref([])
const activeFilter = ref('all')
const { showLoading, run } = useDeferredLoading()
const showDialog = ref(false)
const dialogResult = ref(null)
const activeCount = ref(0)
const loadError = ref('')
const retryingIds = ref(new Set())
const manualDialogVisible = ref(false)
const manualTask = ref(null)
const manualCaseId = ref(null)
const allCases = ref([])
const manualLoading = ref(false)

const { taskVersion } = useEventStream()

function countActive(list) {
  return list.filter(t => t.ai_analysis_status === 'pending' || t.ai_analysis_status === 'processing').length
}

async function loadFull() {
  try {
    loadError.value = ''
    await run(async () => {
      const res = await getIngestTasks(null, { silent: true })
      if (res) tasks.value = res.data
    })
  } catch {
    loadError.value = '任务中心暂时无法加载，请检查后端服务或稍后重试'
  }
}

async function refreshTasks() {
  try {
    loadError.value = ''
    const res = await getIngestTasks(null, { silent: true })
    if (res) {
      tasks.value = res.data
      activeCount.value = countActive(res.data)
    }
  } catch {
    if (!tasks.value.length) loadError.value = '任务中心暂时无法加载，请检查后端服务或稍后重试'
  }
}

function onTaskCreated() {
  loadFull().then(() => {
    activeCount.value = countActive(tasks.value)
  })
}

onMounted(() => {
  loadFull().then(() => {
    activeCount.value = countActive(tasks.value)
  })
  window.addEventListener('ingest-task-created', onTaskCreated)
})
onBeforeUnmount(() => { window.removeEventListener('ingest-task-created', onTaskCreated) })
onDeactivated(() => {})  // SSE watch 保持活跃，无需停止
onActivated(() => {
  loadFull().then(() => { activeCount.value = countActive(tasks.value) })
})

// SSE 驱动刷新，仅在服务端真实状态变更时触发
watch(taskVersion, () => { refreshTasks() })

const filters = computed(() => [
  { key: 'all', label: '全部', count: tasks.value.length },
  { key: 'pending', label: '等待中', count: tasks.value.filter(t => t.ai_analysis_status === 'pending').length },
  { key: 'processing', label: '处理中', count: tasks.value.filter(t => t.ai_analysis_status === 'processing').length },
  { key: 'completed', label: '已完成', count: tasks.value.filter(t => t.ai_analysis_status === 'completed').length },
  { key: 'failed', label: '失败', count: tasks.value.filter(t => t.ai_analysis_status === 'failed').length },
])

const filtered = computed(() => {
  if (activeFilter.value === 'all') return tasks.value
  return tasks.value.filter(t => t.ai_analysis_status === activeFilter.value)
})

function statusType(s) { return { completed: 'success', processing: 'warning', failed: 'danger', pending: 'info' }[s] || 'info' }
function statusLabel(s) { return { completed: '待确认', processing: '处理中', failed: '失败', pending: '已上传' }[s] || s }

function inferStepFromProgress(progress = '') {
  if (progress.includes('匹配')) return 'matching'
  if (progress.includes('AI') || progress.includes('分析')) return 'analyzing'
  if (progress.includes('文本') || progress.includes('提取')) return 'extracting'
  return 'uploaded'
}

function currentStepKey(task) {
  if (task.ai_analysis_status === 'completed') return 'confirming'
  if (task.ai_analysis_status === 'pending') return 'uploaded'
  if (task.ai_analysis_status === 'failed') return inferStepFromProgress(task.ai_progress || '')
  if (INGEST_STEP_KEYS.has(task.ai_progress_stage)) return task.ai_progress_stage
  return inferStepFromProgress(task.ai_progress || '')
}

function stepClass(task, step) {
  const currentIndex = INGEST_STEPS.findIndex(s => s.key === currentStepKey(task))
  const stepIndex = INGEST_STEPS.findIndex(s => s.key === step.key)
  return {
    [step.key]: true,
    done: task.ai_analysis_status === 'completed' || stepIndex < currentIndex,
    current: stepIndex === currentIndex && task.ai_analysis_status !== 'completed',
    failed: task.ai_analysis_status === 'failed' && stepIndex === currentIndex,
  }
}

function progressPercent(task) {
  if (task.ai_analysis_status !== 'failed' && typeof task.ai_progress_percent === 'number') {
    return Math.min(100, Math.max(8, task.ai_progress_percent))
  }
  const step = INGEST_STEPS.find(s => s.key === currentStepKey(task))
  return step?.percent || 8
}

function progressLabel(task) {
  const step = INGEST_STEPS.find(s => s.key === currentStepKey(task))
  if (task.ai_analysis_status === 'failed') return `${step?.label || '处理'}失败`
  return task.ai_progress_label || step?.label || task.ai_progress || '上传成功'
}

function failureText(task) {
  return task.failure_reason || task.ai_raw_response || '处理失败，请重新分析或手动关联案件'
}

function formatTaskTime(value) {
  if (!value) return ''
  const normalized = typeof value === 'string' && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)
    ? `${value}Z`
    : value
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', { hour12: false })
}

function openTextPage(task) {
  router.push(`/tasks/${task.id}/text`)
}

async function handleClick(task) {
  if (task.ai_analysis_status === 'completed') {
    try {
      const res = await getSmartIngestResult(task.id)
      dialogResult.value = res.data
      showDialog.value = true
    } catch { ElMessage.error('获取分析结果失败') }
  } else if (task.ai_analysis_status === 'failed') {
    ElMessage.error(`分析失败：${failureText(task).slice(0, 80)}`)
  }
}

function onConfirm() { showDialog.value = false; dialogResult.value = null; loadFull() }
function onDialogClose() { showDialog.value = false; dialogResult.value = null }
function parseDeadline(task) { return task.ai_extracted_deadline || '' }

async function retryTask(task) {
  retryingIds.value.add(task.id)
  retryingIds.value = new Set(retryingIds.value)
  try {
    await reanalyzeDocument(task.id)
    ElMessage.success('已重新提交分析')
    task.ai_analysis_status = 'pending'
    task.ai_progress = '上传成功'
    task.failure_reason = ''
    task.ai_progress_stage = 'uploaded'
    await refreshTasks()
  } catch {
    ElMessage.error('重新分析失败，请稍后重试')
  } finally {
    retryingIds.value.delete(task.id)
    retryingIds.value = new Set(retryingIds.value)
  }
}

async function openManualLink(task) {
  manualTask.value = task
  manualCaseId.value = null
  manualDialogVisible.value = true
  manualLoading.value = true
  try {
    const res = await getCases({ view: 'flat' })
    allCases.value = res.data || []
  } catch {
    allCases.value = []
    ElMessage.error('案件列表加载失败')
  } finally {
    manualLoading.value = false
  }
}

async function confirmManualLink() {
  if (!manualTask.value || !manualCaseId.value) return
  manualLoading.value = true
  try {
    await confirmIngest(manualTask.value.id, 'link', manualCaseId.value)
    ElMessage.success('已手动关联案件')
    manualDialogVisible.value = false
    manualTask.value = null
    manualCaseId.value = null
    window.dispatchEvent(new CustomEvent('smart-ingest-confirmed'))
    await loadFull()
  } catch {
    ElMessage.error('手动关联失败')
  } finally {
    manualLoading.value = false
  }
}
</script>

<template>
  <div v-loading="showLoading">
    <div class="header">
      <h1>任务中心</h1>
      <p>AI 文档分析进度 — 拖拽文件后在此查看处理结果</p>
    </div>

    <div class="stats-row">
      <div v-for="f in filters" :key="f.key" :class="['stat-chip', { active: activeFilter === f.key }]" @click="activeFilter = f.key">
        <span class="chip-label">{{ f.label }}</span>
        <span class="chip-n">{{ f.count }}</span>
      </div>
    </div>

    <div v-if="loadError" class="empty error-empty">
      <p>{{ loadError }}</p>
      <el-button size="small" type="primary" plain @click="loadFull">重新加载</el-button>
    </div>

    <div v-else-if="filtered.length === 0" class="empty">
      <p>{{ activeFilter === 'all' ? '暂无任务' : '当前筛选下暂无任务' }}</p>
      <p class="sub">拖拽 PDF/DOCX 文件到任意位置即可开始 AI 智能收件</p>
    </div>

    <div v-for="task in filtered" :key="task.id" class="task-card" @click="handleClick(task)">
      <div class="task-left">
        <div :class="['task-dot', task.ai_analysis_status]"></div>
        <div class="task-body">
          <div class="task-title">{{ task.filename }}</div>
          <div class="task-meta">
            <el-tag :type="statusType(task.ai_analysis_status)" size="small" effect="plain">{{ statusLabel(task.ai_analysis_status) }}</el-tag>
            <span v-if="task.ai_extracted_cause" class="task-cause">| {{ task.ai_extracted_cause }}</span>
            <span class="task-time">{{ formatTaskTime(task.uploaded_at) }}</span>
          </div>

          <div class="task-progress-box">
            <div class="progress-bar">
              <div
                :class="['progress-fill', task.ai_analysis_status, currentStepKey(task)]"
                :style="{ width: `${progressPercent(task)}%` }"
              ></div>
            </div>
            <span class="progress-text">{{ progressLabel(task) }}</span>
            <button v-if="task.ai_analysis_status !== 'pending'" class="view-text-btn" @click.stop="openTextPage(task)">
              查看文本
            </button>
          </div>

          <div class="step-row" @click.stop>
            <div v-for="step in INGEST_STEPS" :key="step.key" :class="['step-item', stepClass(task, step)]">
              <span class="step-dot"></span>
              <span class="step-label">{{ step.label }}</span>
            </div>
          </div>

          <div v-if="task.ai_analysis_status === 'failed'" class="failure-box" @click.stop>
            <div class="failure-title">失败原因</div>
            <div class="failure-text">{{ failureText(task) }}</div>
            <div class="failure-actions">
              <el-button size="small" type="primary" :loading="retryingIds.has(task.id)" @click="retryTask(task)">
                重新分析
              </el-button>
              <el-button size="small" @click="openManualLink(task)">手动关联案件</el-button>
            </div>
          </div>

          <div v-if="task.ai_analysis_status === 'completed' && task.ai_extracted_stage" class="task-preview">
            <span>{{ STAGE_LABEL_MAP[task.ai_extracted_stage] || task.ai_extracted_stage }}</span>
            <span v-if="task.ai_extracted_deadline">| 截止: {{ parseDeadline(task) }}</span>
            <span v-if="task.ai_match_result" class="task-match-hint">| {{ task.ai_match_result.has_match ? '已匹配 ✓' : '无匹配案件' }}</span>
          </div>
        </div>
      </div>
      <el-icon v-if="task.ai_analysis_status === 'completed'" class="task-arrow"><ArrowRight /></el-icon>
    </div>

    <SmartIngestDialog v-if="showDialog && dialogResult" :result="dialogResult" @confirm="onConfirm" @close="onDialogClose" />

    <el-dialog v-model="manualDialogVisible" title="手动关联案件" width="520px">
      <div v-loading="manualLoading">
        <p class="manual-hint">选择一个已有案件，当前收件文档会直接归入该案件。</p>
        <el-select v-model="manualCaseId" filterable placeholder="搜索案件" style="width:100%">
          <el-option v-for="c in allCases" :key="c.id" :label="c.case_name" :value="c.id" />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="manualDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!manualCaseId" :loading="manualLoading" @click="confirmManualLink">
          确认关联
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.header { margin-bottom: 20px; }
.header h1 { font-size: 26px; font-weight: 700; letter-spacing: -0.03em; }
.header p { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.stats-row { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-chip { display: flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 20px; border: 1px solid var(--border); background: var(--surface); cursor: pointer; transition: all 0.15s; font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.stat-chip:hover { border-color: var(--accent); color: var(--accent); }
.stat-chip.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.chip-n { background: rgba(0,0,0,0.06); border-radius: 10px; padding: 1px 8px; font-size: 11px; font-weight: 600; }
html.dark .chip-n { background: rgba(255,255,255,0.08); }
.stat-chip.active .chip-n { background: rgba(255,255,255,0.2); }

.empty { text-align: center; padding: 60px 0; color: var(--text-tertiary); }
.empty p { font-size: 15px; font-weight: 500; }
.empty .sub { font-size: 12px; margin-top: 4px; }
.error-empty { color: var(--red); display: flex; flex-direction: column; align-items: center; gap: 12px; }

.task-card { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border: 1px solid var(--border); border-radius: var(--radius-sm); margin-bottom: 8px; cursor: pointer; transition: all 0.15s; background: var(--surface); }
.task-card:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.task-left { display: flex; align-items: flex-start; gap: 12px; flex: 1; min-width: 0; }
.task-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 6px; }
.task-dot.completed { background: var(--green); }
.task-dot.processing { background: var(--orange); box-shadow: 0 0 0 4px var(--orange-soft); animation: pulse 1.2s ease-in-out infinite; }
.task-dot.pending { background: var(--blue); }
.task-dot.failed { background: var(--red); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

.task-body { flex: 1; min-width: 0; }
.task-title { font-size: 14px; font-weight: 600; }
.task-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; font-size: 12px; color: var(--text-tertiary); }
.task-cause { color: var(--accent); }
.task-err { color: var(--red); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-time { margin-left: auto; }
.task-progress-box { margin-top: 10px; display: flex; align-items: center; gap: 10px; }
.progress-bar { width: 220px; height: 8px; border-radius: 999px; background: var(--border); overflow: hidden; flex-shrink: 0; }
.progress-fill { height: 100%; border-radius: 999px; transition: width 0.25s ease; }
.progress-fill.uploaded { background: linear-gradient(90deg, #60a5fa, var(--blue)); }
.progress-fill.extracting { background: linear-gradient(90deg, #fbbf24, var(--orange)); }
.progress-fill.analyzing { background: linear-gradient(90deg, #8b5cf6, var(--accent)); }
.progress-fill.matching { background: linear-gradient(90deg, #22d3ee, #14b8a6); }
.progress-fill.confirming { background: linear-gradient(90deg, #34d399, var(--green)); }
.progress-fill.failed { background: var(--red); }
.progress-fill.completed { background: var(--green); }
.progress-text { font-size: 12px; color: var(--text-secondary); flex: 1; }
.view-text-btn { font-size: 11px; color: var(--accent); background: none; border: none; cursor: pointer; padding: 0 4px; font-family: inherit; white-space: nowrap; }
.view-text-btn:hover { text-decoration: underline; }

.step-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(72px, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.step-item {
  --step-color: var(--text-tertiary);
  --step-soft: var(--bg);
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  color: var(--text-tertiary);
  font-size: 11px;
}
.step-item.uploaded { --step-color: var(--blue); --step-soft: var(--blue-soft); }
.step-item.extracting { --step-color: var(--orange); --step-soft: var(--orange-soft); }
.step-item.analyzing { --step-color: var(--accent); --step-soft: var(--accent-soft); }
.step-item.matching { --step-color: #14b8a6; --step-soft: rgba(20, 184, 166, 0.08); }
.step-item.confirming { --step-color: var(--green); --step-soft: var(--green-soft); }
.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
  border: 2px solid transparent;
  flex-shrink: 0;
}
.step-item.done { color: var(--step-color); }
.step-item.done .step-dot { background: var(--step-color); }
.step-item.current { color: var(--step-color); font-weight: 600; }
.step-item.current .step-dot { background: var(--step-color); box-shadow: 0 0 0 4px var(--step-soft); animation: pulse 1.2s ease-in-out infinite; }
.step-item.failed { color: var(--red); font-weight: 600; }
.step-item.failed .step-dot { background: var(--red); animation: none; }
.step-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.failure-box {
  margin-top: 12px;
  padding: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(239, 68, 68, 0.24);
  background: rgba(239, 68, 68, 0.06);
}
.failure-title { font-size: 12px; font-weight: 700; color: var(--red); margin-bottom: 4px; }
.failure-text { font-size: 12px; color: var(--text-secondary); line-height: 1.6; word-break: break-word; }
.failure-actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.task-preview { font-size: 11px; color: var(--text-tertiary); margin-top: 4px; display: flex; gap: 6px; }
.task-match-hint { color: var(--green); }
.task-arrow { font-size: 14px; color: var(--text-tertiary); flex-shrink: 0; }
.manual-hint { margin: 0 0 12px; color: var(--text-secondary); font-size: 13px; }

@media (max-width: 760px) {
  .task-card { padding: 14px; }
  .task-meta { align-items: flex-start; flex-wrap: wrap; }
  .task-time { margin-left: 0; width: 100%; }
  .task-progress-box { align-items: flex-start; flex-direction: column; }
  .progress-bar { width: 100%; }
  .step-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
