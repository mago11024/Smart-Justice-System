<script setup>
import { ref, provide, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { smartIngestAsync, uploadDocument, confirmIngest, getSmartIngestResult } from '@/api/documents'
import { getCase } from '@/api/cases'
import { STAGE_LABEL_MAP } from '@/utils/constants'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
import ProcessingBar from '@/components/ai/ProcessingBar.vue'
import SmartIngestDialog from '@/components/ai/SmartIngestDialog.vue'
import { useEventStream } from '@/composables/useEventStream'

const route = useRoute()
const router = useRouter()

// 置信度阈值
const AUTO_LINK_THRESHOLD = 0.85
const MATCH_SUGGEST_THRESHOLD = 0.3

const fileInput = ref(null)
const dragActive = ref(false)
const processing = ref(false)
const processingMessage = ref('AI 正在分析文档…')
const processingStatus = ref('processing') // 'processing' | 'success' | 'error'
const result = ref(null)
const showDialog = ref(false)
const dialogMode = ref('auto') // 'auto' | 'match' | 'create'
const trackedTaskId = ref(null)
const handlingTaskCompletion = ref(false)
let taskPollTimer = null

/* 当前是否在案件详情页 */
const currentCaseId = computed(() => {
  const id = route.params.id
  if (id && route.path.startsWith('/case/') && !route.path.endsWith('/edit') && !route.path.endsWith('/create')) {
    const num = parseInt(id)
    return isNaN(num) ? null : num
  }
  return null
})
const caseStage = ref(null)
const caseStageLabel = ref('')

/* 页面切换时清除缓存的案件阶段 */
watch(() => route.params.id, (newId) => {
  if (newId && route.path.startsWith('/case/') && !route.path.endsWith('/edit') && !route.path.endsWith('/create')) {
    loadCaseStage(parseInt(newId))
  } else {
    caseStage.value = null
    caseStageLabel.value = ''
  }
}, { immediate: true })

/* 导航离开时关闭 ProcessingBar */
watch(() => route.path, () => {
  if (processing.value) {
    processing.value = false
    ElMessage.info('AI 分析将在后台继续，可在「任务中心」查看结果')
  }
})

async function loadCaseStage(caseId) {
  try {
    const res = await getCase(caseId)
    caseStage.value = res.data?.stage || null
    caseStageLabel.value = STAGE_LABEL_MAP[caseStage.value] || caseStage.value || ''
  } catch {
    caseStage.value = null
    caseStageLabel.value = ''
  }
}

/* 侧边栏收放 */
const sidebarCollapsed = ref(false)
const AUTO_COLLAPSE_WIDTH = 1024
let resizeObserver = null

function applyWidth(width) {
  if (width < AUTO_COLLAPSE_WIDTH) {
    sidebarCollapsed.value = true
  } else {
    sidebarCollapsed.value = false
  }
}

onMounted(() => {
  applyWidth(window.innerWidth)
  resizeObserver = new ResizeObserver(([entry]) => {
    applyWidth(entry.contentRect.width)
  })
  resizeObserver.observe(document.body)

  // 全局阻止浏览器默认拖拽行为（打开文件）
  window.addEventListener('dragover', _onWindowDrag, false)
  window.addEventListener('drop', _onWindowDrop, false)

  // SSE 连接
  connect()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('dragover', _onWindowDrag, false)
  window.removeEventListener('drop', _onWindowDrop, false)
  stopTaskPolling()
  disconnect()
})

function _onWindowDrag(e) { e.preventDefault() }
function _onWindowDrop(e) { e.preventDefault() }

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

/* 暗色模式 */
const isDark = ref(false)

function initTheme() {
  const saved = localStorage.getItem('theme')
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }
}

function toggleTheme() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

initTheme()

/* SSE 实时推送 — 应用级单例生命周期 */
const { connect, disconnect, lastTaskEvent } = useEventStream()

watch(lastTaskEvent, (event) => {
  if (!event || !trackedTaskId.value || event.task_id !== trackedTaskId.value) return
  if (event.status === 'processing' || event.status === 'pending') {
    processing.value = true
    processingStatus.value = 'processing'
    processingMessage.value = event.progress || 'AI 正在识别文档…'
    return
  }
  if (event.status === 'completed' || event.status === 'failed') {
    finishTrackedTask(event.status)
  }
})

function stopTaskPolling() {
  if (taskPollTimer) {
    clearInterval(taskPollTimer)
    taskPollTimer = null
  }
}

function startTaskPolling(taskId) {
  stopTaskPolling()
  taskPollTimer = setInterval(async () => {
    try {
      const res = await getSmartIngestResult(taskId)
      const status = res.data?.status
      if (status === 'completed' || status === 'failed') {
        finishTrackedTask(status, res.data)
      }
    } catch {
      // SSE 仍会继续兜底；短暂网络错误不打断当前进度条。
    }
  }, 3000)
}

async function finishTrackedTask(status, knownResult = null) {
  if (!trackedTaskId.value || handlingTaskCompletion.value) return
  handlingTaskCompletion.value = true
  stopTaskPolling()

  const taskId = trackedTaskId.value
  trackedTaskId.value = null

  try {
    if (status === 'completed') {
      processingStatus.value = 'success'
      processingMessage.value = 'AI 识别完成'

      const data = knownResult || (await getSmartIngestResult(taskId)).data
      const matchedCase = data.matched_case
      const confidence = matchedCase?.confidence || 0

      if (matchedCase && confidence >= AUTO_LINK_THRESHOLD) {
        try {
          await confirmIngest(taskId, 'link', matchedCase.id)
          processingMessage.value = `已自动关联到案件「${matchedCase.case_name}」`
          window.dispatchEvent(new CustomEvent('smart-ingest-confirmed'))
          window.dispatchEvent(new CustomEvent('highlight-case', { detail: { caseId: matchedCase.id } }))
          await ElMessageBox.alert(
            `AI 识别已完成，并已自动关联到案件「${matchedCase.case_name}」。`,
            '任务完成',
            { type: 'success', confirmButtonText: '知道了' }
          ).catch(() => {})
        } catch {
          processingStatus.value = 'error'
          processingMessage.value = '自动关联失败，请在任务中心手动处理'
          await ElMessageBox.alert('AI 识别已完成，但自动关联失败，请在任务中心手动处理。', '任务完成', {
            type: 'warning',
            confirmButtonText: '知道了',
          }).catch(() => {})
        }
      } else {
        result.value = data
        dialogMode.value = matchedCase && confidence >= MATCH_SUGGEST_THRESHOLD ? 'match' : 'create'
        try {
          await ElMessageBox.alert('AI 已完成文件识别，请查看识别结果并确认案件归属。', '任务完成', {
            type: 'success',
            confirmButtonText: '查看结果',
          })
          processing.value = false
          router.push(`/tasks/${taskId}/text`)
        } catch {}
      }

      setTimeout(() => { processing.value = false }, 1200)
    } else {
      processingStatus.value = 'error'
      processingMessage.value = 'AI 识别失败'
      setTimeout(() => { processing.value = false }, 2500)
      ElMessageBox.alert('AI 识别失败，请在任务中心查看失败原因并重试。', '任务失败', {
        type: 'error',
        confirmButtonText: '知道了',
      }).catch(() => {})
    }
  } finally {
    handlingTaskCompletion.value = false
  }
}

function triggerFilePick() {
  fileInput.value?.click()
}

function onDragOver(e) {
  e.preventDefault()
  dragActive.value = true
}

function onDragLeave(e) {
  if (!e.currentTarget.contains(e.relatedTarget)) {
    dragActive.value = false
  }
}

async function onDrop(e) {
  e.preventDefault()
  dragActive.value = false
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  await processFile(file)
}

async function onFileInput(e) {
  const file = e.target.files?.[0]
  if (!file) return
  await processFile(file)
  e.target.value = ''
}

async function processFile(file) {
  const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'image/png', 'image/jpeg', 'image/webp']
  const validExts = ['.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff']
  const fileName = file.name.toLowerCase()
  const hasValidType = validTypes.includes(file.type)
  const hasValidExt = validExts.some(ext => fileName.endsWith(ext))
  if (!hasValidType && !hasValidExt) { ElMessage.error('仅支持 PDF、DOCX、TXT、图片'); return }
  if (file.size > 20 * 1024 * 1024) { ElMessage.error('文件不超过 20MB'); return }

  // 防重复提交
  if (processing.value || trackedTaskId.value) {
    ElMessage.warning('请等待当前文件处理完成')
    return
  }

  const caseId = currentCaseId.value
  if (caseId) {
    // === 案件详情页：直接归入当前案件 ===
    processing.value = true
    processingMessage.value = `正在上传至当前案件${caseStageLabel.value ? `（${caseStageLabel.value}）` : ''}…`
    processingStatus.value = 'processing'
    try {
      if (!caseStage.value) await loadCaseStage(caseId)
      const res = await uploadDocument(caseId, file)
      ElMessage.success(`文件已归入当前案件${caseStageLabel.value ? `（${caseStageLabel.value}）` : ''}，AI 正在分析…`)
      window.dispatchEvent(new CustomEvent('case-file-uploaded', { detail: { caseId, documentId: res.data?.document_id } }))
      processingStatus.value = 'success'
      processingMessage.value = '上传完成，AI 后台分析中'
    } catch {
      ElMessage.error('上传失败，请重试')
      processingStatus.value = 'error'
      processingMessage.value = '上传失败'
    } finally {
      setTimeout(() => { processing.value = false }, 2500)
    }
  } else {
    // === 非案件页（仪表盘等）：静默 AI 处理，自动归类 ===
    processing.value = true
    processingMessage.value = '正在上传文档并提取文本…'
    processingStatus.value = 'processing'
    try {
      const res = await smartIngestAsync(file)
      trackedTaskId.value = res.data?.document_id || null
      if (!trackedTaskId.value) throw new Error('missing task id')
      processingMessage.value = '文件已上传，AI 正在识别文档…'
      ElMessage.success('文件已上传，AI 正在识别文档…')
      window.dispatchEvent(new CustomEvent('ingest-task-created', { detail: { taskId: trackedTaskId.value } }))
      if (trackedTaskId.value) startTaskPolling(trackedTaskId.value)
    } catch (e) {
      processing.value = false
      trackedTaskId.value = null
      stopTaskPolling()
      if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout')) {
        ElMessage.warning('AI 分析超时，已转为后台处理，可在任务中心查看结果')
      } else {
        ElMessage.error('AI 分析失败，请在任务中心手动处理')
      }
    }
  }
}

function onConfirm() {
  const matchedId = result.value?.matched_case?.id
  showDialog.value = false
  result.value = null
  window.dispatchEvent(new CustomEvent('smart-ingest-confirmed'))
  // 如果是匹配模式确认关联，高亮对应案件
  if (matchedId && dialogMode.value === 'match') {
    window.dispatchEvent(new CustomEvent('highlight-case', { detail: { caseId: matchedId } }))
  }
  dialogMode.value = 'auto'
}

provide('triggerFilePick', triggerFilePick)
provide('dragActive', dragActive)
provide('processing', processing)
provide('currentCaseId', currentCaseId)
provide('caseStageLabel', caseStageLabel)
provide('sidebarCollapsed', sidebarCollapsed)
provide('toggleSidebar', toggleSidebar)
provide('isDark', isDark)
provide('toggleTheme', toggleTheme)
</script>

<template>
  <div
    :class="['layout', { 'drag-active': dragActive }]"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <input ref="fileInput" type="file" accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.webp,.bmp,.tiff" style="display:none" @change="onFileInput" />

    <AppSidebar :collapsed="sidebarCollapsed" />
    <div class="main">
      <AppTopbar :sidebar-collapsed="sidebarCollapsed" @toggle-sidebar="toggleSidebar" @toggle-theme="toggleTheme" :is-dark="isDark" />
      <ProcessingBar
        :visible="processing"
        :message="processingMessage"
        :status="processingStatus"
        @dismiss="processing = false"
      />
      <div class="content">
        <keep-alive>
          <router-view />
        </keep-alive>
      </div>
    </div>

    <!-- 全页面拖拽时的遮罩提示（仅拖拽悬停时显示，处理时不阻塞） -->
    <div v-if="dragActive" class="drag-overlay">
      <div class="drag-hint">
        <span class="drag-icon">&#8682;</span>
        <template v-if="currentCaseId">
          <span>释放文件，直接归入当前案件</span>
          <span v-if="caseStageLabel" class="drag-stage-tag">{{ caseStageLabel }}</span>
        </template>
        <span v-else>释放文件，AI 将自动识别归属案件</span>
      </div>
    </div>

    <SmartIngestDialog
      v-if="showDialog && result"
      :result="result"
      :mode="dialogMode"
      @confirm="onConfirm"
      @close="showDialog = false; result = null"
    />
  </div>
</template>

<style scoped>
.layout { display: flex; height: 100vh; position: relative; }
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.content { flex: 1; overflow-y: auto; padding: 28px 32px; max-width: 1280px; margin: 0 auto; width: 100%; }

.drag-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: var(--accent-soft);
  border: 3px dashed var(--accent);
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;
}
html.dark .drag-overlay { background: rgba(124,124,240,0.12); }
.drag-hint {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  background: var(--surface); padding: 40px 60px; border-radius: var(--radius);
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
html.dark .drag-hint { box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
.drag-icon { font-size: 48px; color: var(--accent); }
.drag-hint span { font-size: 18px; font-weight: 600; color: var(--accent); }
.drag-stage-tag {
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 4px 14px;
  border-radius: 20px;
  background: var(--accent);
  color: #fff !important;
  margin-top: 4px;
}
</style>
