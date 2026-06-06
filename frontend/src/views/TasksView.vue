<script setup>
import { ref, computed, onMounted, onBeforeUnmount, onActivated, onDeactivated, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { getIngestTasks, getSmartIngestResult, getIngestTaskText } from '@/api/documents'
import { useDeferredLoading } from '@/composables/useDeferredLoading'
import { useEventStream } from '@/composables/useEventStream'
import { STAGE_LABEL_MAP } from '@/utils/constants'
import SmartIngestDialog from '@/components/ai/SmartIngestDialog.vue'

const tasks = ref([])
const activeFilter = ref('all')
const { showLoading, run } = useDeferredLoading()
const showDialog = ref(false)
const dialogResult = ref(null)
const activeCount = ref(0)

const { taskVersion } = useEventStream()

function countActive(list) {
  return list.filter(t => t.ai_analysis_status === 'pending' || t.ai_analysis_status === 'processing').length
}

async function loadFull() {
  try {
    await run(async () => {
      const res = await getIngestTasks(null, { silent: true })
      if (res) tasks.value = res.data
    })
  } catch {
    // run() 的 finally 已清理 loading 状态，此处静默吞下错误
    // 网络异常时保留已有数据，不清空 tasks
  }
}

async function refreshTasks() {
  try {
    const res = await getIngestTasks(null, { silent: true })
    if (res) {
      tasks.value = res.data
      activeCount.value = countActive(res.data)
    }
  } catch {
    // 网络异常时保留已有数据，下次 SSE 事件会重试
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
function statusLabel(s) { return { completed: '已完成', processing: '处理中…', failed: '失败', pending: '等待中' }[s] || s }

// 展开查看提取文本
const expandedText = ref(new Map())
const loadingText = ref(new Set())

async function toggleText(task) {
  const id = task.id
  if (expandedText.value.has(id)) {
    expandedText.value.delete(id)
    expandedText.value = new Map(expandedText.value)
    return
  }
  loadingText.value.add(id)
  try {
    const res = await getIngestTaskText(id)
    expandedText.value.set(id, res.data.text || '(empty)')
    expandedText.value = new Map(expandedText.value)
  } catch {
    expandedText.value.set(id, '(failed to load)')
    expandedText.value = new Map(expandedText.value)
  } finally {
    loadingText.value.delete(id)
  }
}

async function handleClick(task) {
  if (task.ai_analysis_status === 'completed') {
    try {
      const res = await getSmartIngestResult(task.id)
      dialogResult.value = res.data
      showDialog.value = true
    } catch { ElMessage.error('获取分析结果失败') }
  } else if (task.ai_analysis_status === 'failed') {
    ElMessage.error(`分析失败：${(task.ai_raw_response || '未知错误').slice(0, 80)}`)
  }
}

function onConfirm() { showDialog.value = false; dialogResult.value = null; loadFull() }
function onDialogClose() { showDialog.value = false; dialogResult.value = null }
function parseDeadline(task) { return task.ai_extracted_deadline || '' }
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

    <div v-if="filtered.length === 0" class="empty">
      <p>暂无任务</p>
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
            <span v-if="task.ai_analysis_status === 'failed' && task.ai_raw_response" class="task-err">| {{ task.ai_raw_response.slice(0, 60) }}</span>
            <span class="task-time">{{ new Date(task.uploaded_at).toLocaleString('zh-CN') }}</span>
          </div>
          <div v-if="task.ai_analysis_status === 'processing' || task.ai_analysis_status === 'pending'" class="task-progress-box">
            <div class="progress-bar"><div class="progress-fill"></div></div>
            <span class="progress-text">{{ task.ai_progress || '正在处理…' }}</span>
            <button class="view-text-btn" @click.stop="toggleText(task)">
              {{ expandedText.has(task.id) ? '收起文本' : loadingText.has(task.id) ? '加载中…' : '查看文本' }}
            </button>
          </div>
          <div v-if="expandedText.has(task.id)" class="extracted-text" @click.stop>
            <pre>{{ expandedText.get(task.id) }}</pre>
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

.task-card { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border: 1px solid var(--border); border-radius: var(--radius-sm); margin-bottom: 8px; cursor: pointer; transition: all 0.15s; background: var(--surface); }
.task-card:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.task-left { display: flex; align-items: flex-start; gap: 12px; flex: 1; min-width: 0; }
.task-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 6px; }
.task-dot.completed { background: var(--green); }
.task-dot.processing { background: var(--orange); animation: pulse 1.2s ease-in-out infinite; }
.task-dot.pending { background: var(--text-tertiary); }
.task-dot.failed { background: var(--red); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

.task-body { flex: 1; min-width: 0; }
.task-title { font-size: 14px; font-weight: 600; }
.task-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; font-size: 12px; color: var(--text-tertiary); }
.task-cause { color: var(--accent); }
.task-err { color: var(--red); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-time { margin-left: auto; }
.task-progress-box { margin-top: 8px; display: flex; align-items: center; gap: 10px; }
.progress-bar { width: 120px; height: 4px; border-radius: 2px; background: var(--border); overflow: hidden; flex-shrink: 0; }
.progress-fill { height: 100%; width: 60%; border-radius: 2px; background: linear-gradient(90deg, var(--accent), #8B5CF6); animation: progress-slide 1.5s ease-in-out infinite; }
@keyframes progress-slide { 0%{width:20%} 50%{width:75%} 100%{width:20%} }
.progress-text { font-size: 12px; color: var(--text-tertiary); animation: pulse-text 2s ease-in-out infinite; flex: 1; }
.view-text-btn { font-size: 11px; color: var(--accent); background: none; border: none; cursor: pointer; padding: 0 4px; font-family: inherit; white-space: nowrap; }
.view-text-btn:hover { text-decoration: underline; }
@keyframes pulse-text { 0%,100%{opacity:0.6} 50%{opacity:1} }
.extracted-text {
  margin-top: 10px; padding: 12px; background: var(--bg); border: 1px solid var(--border);
  border-radius: var(--radius-sm); max-height: 300px; overflow-y: auto;
}
.extracted-text pre { white-space: pre-wrap; font-size: 12px; line-height: 1.7; color: var(--text-secondary); font-family: inherit; margin: 0; }
.task-preview { font-size: 11px; color: var(--text-tertiary); margin-top: 4px; display: flex; gap: 6px; }
.task-match-hint { color: var(--green); }
.task-arrow { font-size: 14px; color: var(--text-tertiary); flex-shrink: 0; }
</style>
