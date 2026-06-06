<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCase, advanceCase, assignCase, deleteCase, updateCase, addCaseLog, generateCoreSummary } from '@/api/cases'
import { getLawyers } from '@/api/lawyers'
import { getDocument, reanalyzeDocument } from '@/api/documents'
import { STAGE_LABEL_MAP, STAGE_COLOR_MAP } from '@/utils/constants'
import { useDeferredLoading } from '@/composables/useDeferredLoading'
import DocumentUploader from '@/components/ai/DocumentUploader.vue'
import AiAnalysisResult from '@/components/ai/AiAnalysisResult.vue'

const route = useRoute()
const router = useRouter()
const item = ref(null)
const lawyers = ref([])
const docs = ref([])
const quickNote = ref('')
const postingNote = ref(false)
const generatingCatalog = ref(false)
const editingCatalog = ref(false)
const savingCatalog = ref(false)
const editForm = ref({ submitter_role: '', items: [] })
const { showLoading, run } = useDeferredLoading()

const EVIDENCE_TYPES = ['书证', '物证', '证人证言', '视听资料', '电子数据', '鉴定意见', '勘验笔录', '当事人陈述']

const SUBMITTER_ROLES = [
  { value: '原告', label: '原告 / 申请人 / 公诉机关' },
  { value: '被告', label: '被告 / 被申请人' },
  { value: '第三人', label: '第三人' },
  { value: '上诉人', label: '上诉人' },
  { value: '被上诉人', label: '被上诉人' },
  { value: '申请执行人', label: '申请执行人' },
  { value: '其他', label: '其他' },
]

const STAGES = [
  { key: 'consultation', label: '接案/咨询' },
  { key: 'document_prep', label: '文书准备' },
  { key: 'court_appearance', label: '开庭审理' },
  { key: 'awaiting_result', label: '等候判决' },
  { key: 'closed', label: '结案/归档' },
]

const currentStageIdx = computed(() => {
  if (!item.value) return -1
  return STAGES.findIndex(s => s.key === item.value.stage)
})

const overdueClass = computed(() => {
  if (!item.value) return ''
  if (item.value.overdue_status === 'overdue') return 'overdue'
  if (item.value.overdue_status === 'due_soon') return 'due-soon'
  return ''
})

const evidenceCatalog = computed(() => {
  if (!item.value?.core_summary) return null
  try {
    return JSON.parse(item.value.core_summary)
  } catch {
    return null
  }
})

const catalogCount = computed(() => {
  return evidenceCatalog.value?.evidence_list?.length || 0
})

async function loadCase() {
  const [caseRes, lawyerRes] = await Promise.all([
    getCase(route.params.id),
    getLawyers(),
  ])
  item.value = caseRes.data
  lawyers.value = lawyerRes.data
  docs.value = caseRes.data.documents || []
}

onMounted(() => {
  run(loadCase)
  window.addEventListener('case-file-uploaded', onGlobalFileUploaded)
})

onBeforeUnmount(() => {
  window.removeEventListener('case-file-uploaded', onGlobalFileUploaded)
})

// 全局拖拽上传后刷新文档列表
function onGlobalFileUploaded(e) {
  if (e.detail?.caseId === item.value?.id) {
    loadCase()
  }
}

// keep-alive 下切案件时重新加载
watch(() => route.params.id, () => { if (route.params.id) run(loadCase) })

async function doGenerateEvidenceCatalog() {
  generatingCatalog.value = true
  try {
    const res = await generateCoreSummary(item.value.id)
    if (res.data?.ok) {
      ElMessage.success(`证据目录已生成，共 ${res.data.core_summary ? JSON.parse(res.data.core_summary).evidence_list?.length || 0 : 0} 项证据`)
      await loadCase()
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || 'AI 生成失败，请确认已配置AI引擎且有已分析的文档')
  } finally {
    generatingCatalog.value = false
  }
}

function startEditCatalog() {
  const cat = evidenceCatalog.value
  editForm.value = {
    submitter_role: cat?.submitter_role || '',
    items: (cat?.evidence_list || []).map((e, i) => ({
      _key: i,
      name: e.name || '',
      proof_content: e.proof_content || '',
      type: e.type || '书证',
    })),
  }
  // 如果完全没有数据，初始给 3 行空位
  if (editForm.value.items.length === 0) {
    editForm.value.items = [
      { _key: 1, name: '', proof_content: '', type: '书证' },
      { _key: 2, name: '', proof_content: '', type: '书证' },
      { _key: 3, name: '', proof_content: '', type: '书证' },
    ]
  }
  editingCatalog.value = true
}

function cancelEditCatalog() {
  editingCatalog.value = false
}

function addEvidenceRow() {
  editForm.value.items.push({ _key: Date.now(), name: '', proof_content: '', type: '书证' })
}

function removeEvidenceRow(idx) {
  editForm.value.items.splice(idx, 1)
}

function moveEvidenceRow(idx, dir) {
  const arr = editForm.value.items
  const target = idx + dir
  if (target < 0 || target >= arr.length) return
  const tmp = arr[idx]
  arr[idx] = arr[target]
  arr[target] = tmp
}

async function saveCatalog() {
  savingCatalog.value = true
  try {
    const evidence_list = editForm.value.items
      .filter(e => e.name.trim() || e.proof_content.trim())
      .map((e, i) => ({
        index: i + 1,
        name: e.name.trim(),
        proof_content: e.proof_content.trim(),
        type: e.type || '书证',
      }))
    if (evidence_list.length === 0) {
      ElMessage.warning('请至少填写一条证据')
      savingCatalog.value = false
      return
    }
    const data = {
      submitter_role: editForm.value.submitter_role.trim(),
      evidence_list,
    }
    await updateCase(item.value.id, { core_summary: JSON.stringify(data) })
    ElMessage.success('证据目录已保存')
    editingCatalog.value = false
    await loadCase()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    savingCatalog.value = false
  }
}

async function doAdvance() {
  try {
    await ElMessageBox.confirm('确认推进到下一阶段？', '确认推进')
    await advanceCase(item.value.id)
    ElMessage.success('已推进')
    await loadCase()
  } catch {}
}

async function doAssign() {
  const list = lawyers.value.map((l, i) => `${i + 1}. ${l.name} (${l.role})`).join('\n')
  try {
    const { value } = await ElMessageBox.prompt(`选择律师:\n${list}\n输入序号:`, '指派律师', {
      inputPattern: /^[0-9]+$/,
      inputErrorMessage: '请输入有效序号',
    })
    const idx = parseInt(value) - 1
    if (lawyers.value[idx]) {
      await assignCase(item.value.id, lawyers.value[idx].id)
      ElMessage.success('已指派')
      await loadCase()
    }
  } catch {}
}

async function doDelete() {
  try {
    await ElMessageBox.confirm('确定删除此案件？', '确认', { type: 'warning' })
    await deleteCase(item.value.id)
    ElMessage.success('已删除')
    router.push('/')
  } catch {}
}

async function postNote() {
  const note = quickNote.value.trim()
  if (!note) return
  postingNote.value = true
  try {
    await addCaseLog(item.value.id, note)
    quickNote.value = ''
    ElMessage.success('已添加更新')
    await loadCase()
  } catch {}
  finally { postingNote.value = false }
}

async function onDocUploaded(result) {
  const pollDoc = async () => {
    const res = await getDocument(result.document_id)
    const doc = res.data
    if (doc.ai_analysis_status === 'completed' || doc.ai_analysis_status === 'failed') return doc
    await new Promise((r) => setTimeout(r, 2000))
    return pollDoc()
  }
  const doc = await pollDoc()
  await loadCase()
  ElMessage.success(doc.ai_analysis_status === 'completed' ? 'AI 分析完成' : 'AI 分析失败，请重试')
}

async function applyAiResult(doc) {
  const updates = {}
  if (doc.ai_extracted_stage) updates.stage = doc.ai_extracted_stage
  if (doc.ai_extracted_cause) updates.cause_of_action = doc.ai_extracted_cause
  if (doc.ai_extracted_deadline) updates.deadline = doc.ai_extracted_deadline
  if (doc.ai_extracted_court_date) updates.court_date = doc.ai_extracted_court_date
  try {
    const parties = JSON.parse(doc.ai_extracted_parties || '{}')
    if (parties.plaintiff) updates.plaintiff = parties.plaintiff
    if (parties.defendant) updates.defendant = parties.defendant
  } catch {}
  if (Object.keys(updates).length === 0) { ElMessage.warning('没有可应用的信息'); return }
  await updateCase(item.value.id, updates)
  ElMessage.success('AI 分析结果已应用')
  await loadCase()
}

async function doReanalyze(id) {
  await reanalyzeDocument(id)
  ElMessage.info('已重新提交分析')
  await onDocUploaded({ document_id: id })
}
</script>

<template>
  <div v-loading="showLoading">
    <div v-if="item" class="detail-layout">
      <!-- 左侧：案件信息 + 阶段流程 + 快速更新 -->
      <div class="detail-left">
        <div class="case-summary">
          <h2>{{ item.case_name }}</h2>
          <p v-if="item.case_number" class="case-num">{{ item.case_number }}</p>
          <p v-if="item.cause_of_action" class="case-cause">{{ item.cause_of_action }}</p>
        </div>

        <!-- 关键信息卡片 -->
        <div class="info-card">
          <div class="info-row">
            <span class="ik">承办人</span>
            <span class="iv accent">{{ item.lawyer_name ? `${item.lawyer_name}律师` : '未分配' }}</span>
          </div>
          <div class="info-row">
            <span class="ik">当前阶段</span>
            <span class="iv" :style="{ color: STAGE_COLOR_MAP[item.stage] }">{{ STAGE_LABEL_MAP[item.stage] }}</span>
          </div>
          <div class="info-row">
            <span class="ik">已停留</span>
            <span class="iv">{{ item.days_in_stage }} 天</span>
          </div>
          <div class="info-row">
            <span class="ik">截止日期</span>
            <span class="iv" :class="overdueClass">
              {{ item.deadline || '无' }}
              <template v-if="item.overdue_status === 'overdue'"> (超期 {{ item.overdue_days }} 天)</template>
              <template v-else-if="item.overdue_status === 'due_soon'"> (剩 {{ item.overdue_days }} 天)</template>
            </span>
          </div>
          <div v-if="item.court_date" class="info-row">
            <span class="ik">开庭时间</span>
            <span class="iv">{{ new Date(item.court_date).toLocaleString('zh-CN') }}</span>
          </div>
        </div>

        <!-- 阶段流程树 -->
        <div class="stage-tree">
          <div class="st-label">🌳 民事案件流程</div>
          <div class="st-steps">
            <template v-for="(s, i) in STAGES" :key="s.key">
              <div
                :class="['st-node', {
                  done: i < currentStageIdx,
                  cur: i === currentStageIdx,
                  future: i > currentStageIdx,
                }]"
              >
                {{ s.label }}
              </div>
              <div v-if="i < STAGES.length - 1" class="st-conn">
                <div :class="['st-line', { done: i < currentStageIdx, active: i === currentStageIdx }]"></div>
                <div :class="['st-dot', { done: i < currentStageIdx, active: i === currentStageIdx }]"></div>
              </div>
            </template>
          </div>
          <div v-if="item.stage !== 'closed'" class="st-hint">
            <span v-if="currentStageIdx < STAGES.length - 1">
              下一步：{{ STAGES[currentStageIdx + 1].label }}
            </span>
            <span v-else>当前已是最终阶段</span>
          </div>
        </div>

        <!-- 近期时间线 -->
        <div v-if="item.logs && item.logs.length > 0" class="timeline-card">
          <div class="tl-title">⏳ 近期时间线</div>
          <div class="tl-list">
            <div v-for="log in item.logs.slice(0, 5)" :key="log.id" class="tl-item">
              <div class="tl-dot"></div>
              <div class="tl-content">
                <div class="tl-note">{{ log.note || `${log.action}: ${log.old_value} → ${log.new_value}` }}</div>
                <div class="tl-time">{{ new Date(log.created_at).toLocaleString('zh-CN') }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 快速进展更新 -->
        <div class="quick-update">
          <el-input
            v-model="quickNote"
            type="textarea"
            :rows="3"
            placeholder="输入进展更新…"
            resize="none"
            @keydown.enter.ctrl="postNote"
          />
          <el-button
            type="primary"
            size="small"
            :loading="postingNote"
            @click="postNote"
            style="margin-top:8px;align-self:flex-end;"
          >
            发送更新
          </el-button>
        </div>
      </div>

      <!-- 右侧：案件详情 + 操作 + AI 文档 -->
      <div class="detail-right">
        <!-- 证据目录 -->
        <div v-if="evidenceCatalog" class="evidence-catalog-card">
          <div class="ec-header">
            <div class="ec-header-left">
              <span class="ec-icon">📋</span>
              <span class="ec-title">证据目录</span>
              <el-tag size="small" type="info" effect="plain">{{ evidenceCatalog.submitter_role }}</el-tag>
              <span class="ec-count">共 {{ catalogCount }} 项证据</span>
            </div>
            <div class="ec-header-actions">
              <template v-if="editingCatalog">
                <el-button size="small" type="primary" :loading="savingCatalog" @click="saveCatalog">💾 保存</el-button>
                <el-button size="small" @click="cancelEditCatalog">取消</el-button>
              </template>
              <template v-else>
                <el-button size="small" plain @click="startEditCatalog">✏️ 编辑</el-button>
                <el-button size="small" plain type="primary" :loading="generatingCatalog" @click="doGenerateEvidenceCatalog">🤖 AI 生成</el-button>
              </template>
            </div>
          </div>

          <!-- 编辑模式 -->
          <div v-if="editingCatalog" class="ec-edit-area">
            <div class="ec-field-row">
              <span class="ec-field-label">提交人：</span>
              <el-radio-group v-model="editForm.submitter_role" size="small">
                <el-radio-button v-for="r in SUBMITTER_ROLES" :key="r.value" :value="r.value">
                  {{ r.label }}
                </el-radio-button>
              </el-radio-group>
            </div>
            <div class="ec-table">
              <div class="ec-thead">
                <span class="ec-th ec-th-idx">序号</span>
                <span class="ec-th ec-th-name">证据名称</span>
                <span class="ec-th ec-th-proof">证明内容</span>
                <span class="ec-th ec-th-type">类型</span>
                <span class="ec-th ec-th-ops">操作</span>
              </div>
              <div
                v-for="(row, idx) in editForm.items"
                :key="row._key"
                class="ec-tr"
              >
                <span class="ec-td ec-td-idx">{{ idx + 1 }}</span>
                <el-input v-model="row.name" size="small" placeholder="证据名称（含编号、日期等）" class="ec-td ec-td-name" />
                <el-input v-model="row.proof_content" size="small" placeholder="该证据用于证明…" class="ec-td ec-td-proof" />
                <el-select v-model="row.type" size="small" class="ec-td ec-td-type">
                  <el-option v-for="t in EVIDENCE_TYPES" :key="t" :label="t" :value="t" />
                </el-select>
                <span class="ec-td ec-td-ops">
                  <el-button size="small" text type="primary" :disabled="idx === 0" @click="moveEvidenceRow(idx, -1)" class="ec-op-btn">↑</el-button>
                  <el-button size="small" text type="primary" :disabled="idx === editForm.items.length - 1" @click="moveEvidenceRow(idx, 1)" class="ec-op-btn">↓</el-button>
                  <el-button size="small" text type="danger" @click="removeEvidenceRow(idx)" class="ec-op-btn">✕</el-button>
                </span>
              </div>
            </div>
            <el-button size="small" dashed style="width:100%;margin-top:8px;" @click="addEvidenceRow">+ 添加一条证据</el-button>
          </div>

          <!-- 查看模式 -->
          <div v-else class="ec-view-table">
            <table>
              <thead>
                <tr>
                  <th class="ec-th-idx">序号</th>
                  <th class="ec-th-name">证据名称</th>
                  <th class="ec-th-proof">证明内容</th>
                  <th class="ec-th-type">类型</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="ev in evidenceCatalog.evidence_list" :key="ev.index">
                  <td class="ec-td-idx">{{ ev.index }}</td>
                  <td class="ec-td-name">{{ ev.name }}</td>
                  <td class="ec-td-proof">{{ ev.proof_content }}</td>
                  <td class="ec-td-type"><el-tag size="small" type="info">{{ ev.type }}</el-tag></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 尚未生成证据目录时显示入口 -->
        <div v-else class="evidence-catalog-empty">
          <div class="ece-content">
            <span class="ece-icon">📋</span>
            <div>
              <div class="ece-title">证据目录</div>
              <div class="ece-hint">AI 读取已上传的诉状、判决书、合同等材料，自动生成证据清单（证据名称 + 证明内容）。生成后可手动编辑调整，作为提交法院的证据目录草稿。</div>
            </div>
          </div>
          <div class="ece-actions">
            <el-button size="small" plain @click="startEditCatalog">✏️ 手动创建</el-button>
            <el-button size="small" type="primary" :loading="generatingCatalog" @click="doGenerateEvidenceCatalog">🤖 AI 生成证据目录</el-button>
          </div>
        </div>

        <div class="section-card">
          <div class="sc-title">案件信息</div>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="原告">{{ item.plaintiff || '-' }}</el-descriptions-item>
            <el-descriptions-item label="被告">{{ item.defendant || '-' }}</el-descriptions-item>
            <el-descriptions-item label="案由">{{ item.cause_of_action || '-' }}</el-descriptions-item>
            <el-descriptions-item label="案号">{{ item.case_number || '-' }}</el-descriptions-item>
            <el-descriptions-item v-if="item.stage === 'closed'" label="结果">{{ item.outcome_note || '-' }}</el-descriptions-item>
            <el-descriptions-item label="备注">{{ item.notes || '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="actions">
          <el-button type="primary" @click="doAdvance" :disabled="item.stage === 'closed'">推进到下一阶段 →</el-button>
          <el-button @click="doAssign">指派律师</el-button>
          <el-button @click="router.push(`/case/${item.id}/edit`)">编辑</el-button>
          <el-button type="danger" plain @click="doDelete">删除</el-button>
        </div>

        <!-- AI 文档分析 -->
        <div class="section-card">
          <div class="sc-title">📄 智能文档分析</div>
          <DocumentUploader :case-id="item.id" @uploaded="onDocUploaded" />
          <div v-if="docs.length > 0" class="docs-list">
            <AiAnalysisResult
              v-for="doc in docs"
              :key="doc.id"
              :doc="doc"
              @apply="applyAiResult"
              @reanalyze="doReanalyze"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-layout { display: flex; gap: 20px; align-items: flex-start; }

.detail-left {
  width: 320px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px;
}

.detail-right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 16px; }

.case-summary h2 { font-size: 17px; font-weight: 700; line-height: 1.3; }
.case-num { font-size: 12px; color: var(--text-tertiary); font-family: "SF Mono","Consolas",monospace; margin-top: 4px; }
.case-cause { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }

/* 信息卡片 */
.info-card {
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); overflow: hidden;
}
.info-row {
  display: flex; justify-content: space-between; padding: 8px 14px;
  font-size: 12px; border-bottom: 1px solid var(--border);
}
.info-row:last-child { border-bottom: none; }
.ik { color: var(--text-tertiary); }
.iv { font-weight: 500; }
.iv.accent { color: var(--accent); }
.iv.overdue { color: var(--red); font-weight: 600; }
.iv.due-soon { color: var(--orange); font-weight: 600; }

/* 阶段流程树 */
.stage-tree {
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); padding: 16px; overflow: hidden;
}
.st-label { font-size: 13px; font-weight: 600; margin-bottom: 14px; }
.st-steps { display: flex; flex-direction: column; align-items: center; gap: 0; }
.st-node {
  padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 500;
  border: 1.5px solid var(--border); text-align: center; width: 140px;
  transition: all 0.2s;
}
.st-node.done { border-color: var(--green); background: var(--green-soft); color: var(--green); }
.st-node.done::before { content: '✓ '; font-weight: 700; }
.st-node.cur { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.st-node.future { opacity: 0.5; }
.st-conn { display: flex; flex-direction: column; align-items: center; padding: 2px 0; }
.st-line { width: 2px; height: 10px; background: var(--border); }
.st-line.done { background: var(--green); }
.st-line.active { background: var(--accent); }
.st-hint { text-align: center; font-size: 11px; color: var(--text-tertiary); margin-top: 8px; }

/* 时间线 */
.timeline-card {
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); overflow: hidden;
}
.tl-title { padding: 10px 14px; font-size: 12px; font-weight: 600; border-bottom: 1px solid var(--border); background: var(--bg); }
.tl-list { padding: 8px 14px 12px; }
.tl-item { display: flex; gap: 10px; padding: 6px 0; }
.tl-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
  flex-shrink: 0; margin-top: 5px;
}
.tl-note { font-size: 12px; line-height: 1.5; }
.tl-time { font-size: 10px; color: var(--text-tertiary); margin-top: 2px; }

/* 快速更新 */
.quick-update { display: flex; flex-direction: column; }
.quick-update :deep(.el-textarea__inner) {
  font-size: 12px; border-radius: var(--radius-sm);
}

/* 证据目录卡片 */
.evidence-catalog-card {
  border: 1px solid var(--accent-border); border-radius: var(--radius);
  background: var(--surface); padding: 16px 20px; overflow: hidden;
}
.ec-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px; flex-wrap: wrap; gap: 8px;
}
.ec-header-left { display: flex; align-items: center; gap: 8px; }
.ec-header-actions { display: flex; align-items: center; gap: 6px; }
.ec-icon { font-size: 16px; }
.ec-title { font-size: 14px; font-weight: 700; }
.ec-count { font-size: 11px; color: var(--text-tertiary); }

.ec-field-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap;
}
.ec-field-label { font-size: 12px; color: var(--text-secondary); white-space: nowrap; }

/* 编辑表格 */
.ec-edit-area { margin-bottom: 4px; }
.ec-table { display: flex; flex-direction: column; gap: 4px; }
.ec-thead {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 0; border-bottom: 2px solid var(--border);
  font-size: 11px; font-weight: 600; color: var(--text-tertiary);
}
.ec-tr {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 0; border-bottom: 1px solid var(--border);
}
.ec-tr:last-child { border-bottom: none; }
.ec-th, .ec-td { flex-shrink: 0; }
.ec-th-idx, .ec-td-idx { width: 36px; text-align: center; font-size: 12px; color: var(--text-secondary); }
.ec-th-name, .ec-td-name { width: 200px; }
.ec-th-proof, .ec-td-proof { flex: 1; min-width: 0; }
.ec-th-type, .ec-td-type { width: 110px; }
.ec-th-ops, .ec-td-ops { width: 90px; text-align: center; }
.ec-td-ops { display: flex; gap: 0; justify-content: center; }
.ec-op-btn { padding: 2px 4px !important; font-size: 12px !important; min-height: auto !important; }

/* 查看表格 */
.ec-view-table table {
  width: 100%; border-collapse: collapse; font-size: 12px;
}
.ec-view-table th {
  background: var(--bg); font-weight: 600; color: var(--text-tertiary);
  text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--border);
  white-space: nowrap; font-size: 11px;
}
.ec-view-table td {
  padding: 8px 10px; border-bottom: 1px solid var(--border);
  vertical-align: top; line-height: 1.5;
}
.ec-view-table .ec-th-idx, .ec-view-table .ec-td-idx { width: 40px; text-align: center; }
.ec-view-table .ec-th-name { width: 200px; }
.ec-view-table .ec-th-proof {  }
.ec-view-table .ec-th-type { width: 80px; }

/* 证据目录空状态 */
.evidence-catalog-empty {
  border: 1px dashed var(--accent-border); border-radius: var(--radius);
  background: var(--surface); padding: 16px 20px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.ece-content { display: flex; align-items: flex-start; gap: 10px; }
.ece-icon { font-size: 20px; flex-shrink: 0; margin-top: 2px; }
.ece-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 2px; }
.ece-hint { font-size: 11px; color: var(--text-tertiary); line-height: 1.5; max-width: 420px; }
.ece-actions { display: flex; gap: 6px; flex-shrink: 0; }

/* 右侧 */
.section-card {
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); padding: 16px;
}
.sc-title { font-size: 13px; font-weight: 600; margin-bottom: 12px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.docs-list { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
</style>
