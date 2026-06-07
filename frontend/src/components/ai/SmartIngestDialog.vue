<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { confirmIngest, reanalyzeDocument } from '@/api/documents'
import { getCases } from '@/api/cases'
import { STAGE_LABEL_MAP } from '@/utils/constants'

const props = defineProps({
  result: { type: Object, required: true },
  mode: { type: String, default: 'auto' }, // 'auto' | 'match' | 'create'
})

const emit = defineEmits(['confirm', 'close'])

const confirming = ref(false)
const manualMode = ref(false)
const manualCaseId = ref(null)
const allCases = ref([])

const extracted = computed(() => props.result.extracted || {})
const matched = computed(() => props.result.matched_case)
const candidates = computed(() => props.result.candidates || [])
const status = computed(() => props.result.status)
const failureMessage = computed(() => {
  if (status.value !== 'failed') return ''
  const ex = extracted.value || {}
  return props.result.error || ex.error || ex.raw || '文档内容无法识别，请手动处理'
})

const hasMatch = computed(() => status.value === 'completed' && matched.value && (matched.value.confidence || 0) > 0.3)

// mode='match' 时的高亮匹配展示
const highlightedMatch = computed(() => props.mode === 'match' && hasMatch.value)

// mode='create' 时强制进入审核创建模式
watch(() => props.mode, (m) => {
  if (m === 'create' && !reviewMode.value) {
    buildReviewForm()
    reviewMode.value = true
  }
}, { immediate: true })

const urgencyTag = computed(() => {
  const u = extracted.value.urgency
  if (u === 'high') return 'danger'
  if (u === 'medium') return 'warning'
  return 'info'
})

const urgencyLabel = computed(() => {
  const u = extracted.value.urgency
  if (u === 'high') return '高 — 需尽快处理'
  if (u === 'medium') return '中 — 近期处理'
  return '低'
})

function formatAmount(amount) {
  if (!amount) return null
  if (amount >= 10000) return `${(amount / 10000).toFixed(1)}万元`
  return `${amount}元`
}

const SUBMITTER_ROLES = [
  { value: '原告', label: '原告 / 申请人 / 公诉机关' },
  { value: '被告', label: '被告 / 被申请人' },
  { value: '第三人', label: '第三人' },
  { value: '上诉人', label: '上诉人' },
  { value: '被上诉人', label: '被上诉人' },
  { value: '申请执行人', label: '申请执行人' },
  { value: '其他', label: '其他' },
]

// 审核编辑表单
const reviewForm = ref({
  submitter_role: '',
  case_name: '',
  case_number: '',
  plaintiff: '',
  defendant: '',
  cause_of_action: '',
  stage: 'consultation',
  deadline: null,
  court_date: null,
})

function buildReviewForm() {
  const ex = extracted.value
  const raw = ex.raw ? (() => { try { return JSON.parse(ex.raw) } catch { return {} } })() : {}
  reviewForm.value = {
    submitter_role: '',
    case_name: ex.plaintiff && ex.defendant
      ? `${ex.plaintiff}诉${ex.defendant}${ex.cause_of_action || '纠纷'}`
      : (ex.case_number ? `案件 ${ex.case_number}` : ''),
    case_number: ex.case_number || raw.case_number || '',
    plaintiff: ex.plaintiff || raw.plaintiff || '',
    defendant: ex.defendant || raw.defendant || '',
    cause_of_action: ex.cause_of_action || raw.cause_of_action || '',
    stage: ex.stage || raw.stage || 'consultation',
    deadline: ex.deadline || raw.deadline || null,
    court_date: ex.court_date || raw.court_date || null,
  }
}

// 无匹配时自动进入审核创建模式
const noMatch = computed(() => status.value === 'completed' && !hasMatch.value)
if (noMatch.value) { buildReviewForm() }
const reviewMode = ref(noMatch.value)

function startReview() {
  buildReviewForm()
  reviewMode.value = true
}

function cancelReview() {
  reviewMode.value = false
}

async function loadAllCases() {
  try {
    const res = await getCases({ view: 'flat' })
    allCases.value = res.data || []
  } catch {}
}

async function doLink(caseId) {
  confirming.value = true
  try {
    await confirmIngest(props.result.document_id, 'link', caseId)
    ElMessage.success('已关联到案件')
    emit('confirm')
  } catch { ElMessage.error('操作失败') }
  finally { confirming.value = false }
}

async function retryAnalysis() {
  confirming.value = true
  try {
    await reanalyzeDocument(props.result.document_id)
    ElMessage.success('已重新提交分析')
    emit('close')
  } catch {
    ElMessage.error('重新分析失败')
  } finally {
    confirming.value = false
  }
}

async function doCreateConfirmed() {
  confirming.value = true
  const rf = reviewForm.value
  try {
    const newCase = {
      case_name: rf.case_name || `新案件 ${new Date().toLocaleDateString('zh-CN')}`,
      case_number: rf.case_number || '',
      plaintiff: rf.plaintiff || '',
      defendant: rf.defendant || '',
      cause_of_action: rf.cause_of_action || '',
      stage: rf.stage || 'consultation',
      deadline: rf.deadline || null,
      court_date: rf.court_date || null,
      notes: rf.submitter_role ? `提交人诉讼地位: ${rf.submitter_role}` : '',
    }
    await confirmIngest(props.result.document_id, 'new', null, newCase)
    ElMessage.success('已创建新案件')
    emit('confirm')
  } catch { ElMessage.error('创建失败') }
  finally { confirming.value = false }
}

async function toggleManual() {
  manualMode.value = true
  await loadAllCases()
}
</script>

<template>
  <el-dialog
    :model-value="true"
    :title="reviewMode ? '📝 编辑案件信息并创建' : (highlightedMatch ? '🎯 AI 识别到匹配案件' : 'AI 智能收件')"
    width="680px"
    @close="emit('close')"
    :close-on-click-modal="false"
  >
    <!-- 失败 -->
    <div v-if="status === 'failed'" class="si-section">
      <el-result icon="error" title="AI 分析失败" :sub-title="failureMessage">
        <template #extra>
          <el-button type="primary" :loading="confirming" @click="retryAnalysis">重新分析</el-button>
          <el-button @click="toggleManual">手动关联案件</el-button>
          <el-button @click="emit('close')">关闭</el-button>
        </template>
      </el-result>
      <div v-if="manualMode" class="si-section manual-fallback">
        <h4>手动选择案件</h4>
        <el-select v-model="manualCaseId" filterable placeholder="搜索案件…" style="width:100%">
          <el-option v-for="c in allCases" :key="c.id" :label="c.case_name" :value="c.id" />
        </el-select>
        <div class="match-actions" style="margin-top:12px">
          <el-button type="primary" :disabled="!manualCaseId" :loading="confirming" @click="doLink(manualCaseId)">
            确认归属
          </el-button>
        </div>
      </div>
    </div>

    <!-- 审核编辑模式 -->
    <template v-else-if="reviewMode">
      <div class="si-section">
        <el-alert type="warning" :closable="false" show-icon style="margin-bottom:12px;">
          <template #title>
            系统未找到匹配的已有案件，建议创建新案件。AI 已从文档中自动提取以下信息，请核对并补全。
          </template>
        </el-alert>

        <el-form :model="reviewForm" label-width="80px" size="small" label-position="top">

          <!-- 诉讼地位选择 — 醒目 -->
          <el-form-item label="提交人诉讼地位">
            <el-radio-group v-model="reviewForm.submitter_role" size="default">
              <el-radio-button v-for="r in SUBMITTER_ROLES" :key="r.value" :value="r.value">
                {{ r.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-row :gutter="12">
            <el-col :span="18">
              <el-form-item label="案件名称">
                <el-input v-model="reviewForm.case_name" placeholder="如：张三诉李四借款纠纷" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="阶段">
                <el-select v-model="reviewForm.stage" style="width:100%">
                  <el-option v-for="s in [
                    {k:'consultation',v:'接案/咨询'},{k:'document_prep',v:'文书准备'},{k:'court_appearance',v:'开庭审理'},{k:'awaiting_result',v:'等候判决'},{k:'closed',v:'结案/归档'}
                  ]" :key="s.k" :label="s.v" :value="s.k" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="原告">
                <el-input v-model="reviewForm.plaintiff" placeholder="原告/申请人" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="被告">
                <el-input v-model="reviewForm.defendant" placeholder="被告/被申请人" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="案由">
                <el-input v-model="reviewForm.cause_of_action" placeholder="如：民间借贷纠纷" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="案号">
                <el-input v-model="reviewForm.case_number" placeholder="如：(2025)沪0105民初1234号" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="截止日期">
                <el-date-picker v-model="reviewForm.deadline" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="开庭时间">
                <el-date-picker v-model="reviewForm.court_date" type="datetime" placeholder="选择时间" style="width:100%" value-format="YYYY-MM-DDTHH:mm" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <!-- 文档识别信息快照 -->
        <el-descriptions :column="2" size="small" border style="margin-top:16px;">
          <el-descriptions-item v-if="extracted.document_type" label="文书类型">{{ extracted.document_type }}</el-descriptions-item>
          <el-descriptions-item v-if="extracted.court" label="管辖法院">{{ extracted.court }}</el-descriptions-item>
          <el-descriptions-item v-if="extracted.judge" label="审判员">{{ extracted.judge }}</el-descriptions-item>
          <el-descriptions-item v-if="extracted.amount_in_dispute" label="标的金额">
            <strong>{{ formatAmount(extracted.amount_in_dispute) }}</strong>
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.key_facts" label="案情摘要" :span="2">
            <span style="font-size:12px;line-height:1.6;">{{ extracted.key_facts }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="match-actions">
        <el-button type="primary" :loading="confirming" @click="doCreateConfirmed">✅ 确认创建案件</el-button>
        <el-button @click="cancelReview">🔍 手动查找已有案件</el-button>
        <el-button @click="emit('close')">取消</el-button>
      </div>
    </template>

    <!-- 正常匹配模式 -->
    <template v-else>
      <!-- 文档概览 -->
      <div class="si-section">
        <div class="section-header">
          <h4>📄 文档识别</h4>
          <el-tag v-if="extracted.document_type" size="small" effect="plain">{{ extracted.document_type }}</el-tag>
          <el-tag v-if="extracted.urgency" :type="urgencyTag" size="small" effect="plain">{{ urgencyLabel }}</el-tag>
          <el-tag size="small" effect="plain" type="info">
            {{ ((extracted.confidence || 0) * 100).toFixed(0) }}% 置信
          </el-tag>
        </div>

        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="当事人">
            <span v-if="extracted.plaintiff || extracted.defendant">
              {{ extracted.plaintiff || '?' }} → {{ extracted.defendant || '?' }}
            </span>
            <span v-else class="na">未识别</span>
          </el-descriptions-item>
          <el-descriptions-item label="案由">
            {{ extracted.cause_of_action || '未识别' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.case_number" label="案号">
            <code class="mono">{{ extracted.case_number }}</code>
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.court" label="管辖法院">
            {{ extracted.court }}
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.judge" label="审判员">
            {{ extracted.judge }}
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.courtroom" label="法庭">
            {{ extracted.courtroom }}
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.amount_in_dispute" label="标的金额">
            <strong>{{ formatAmount(extracted.amount_in_dispute) }}</strong>
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.deadline" label="截止日期">
            <span class="deadline">{{ extracted.deadline }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.court_date" label="开庭时间">
            {{ extracted.court_date }}
          </el-descriptions-item>
          <el-descriptions-item label="识别阶段">
            <el-tag :type="extracted.stage === 'closed' ? 'success' : 'primary'" size="small">
              {{ STAGE_LABEL_MAP[extracted.stage] || extracted.stage || '?' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="extracted.plaintiff_agent || extracted.defendant_agent" label="代理律师">
            <template v-if="extracted.plaintiff_agent">原告方: {{ extracted.plaintiff_agent }}</template>
            <template v-if="extracted.plaintiff_agent && extracted.defendant_agent"><br /></template>
            <template v-if="extracted.defendant_agent">被告方: {{ extracted.defendant_agent }}</template>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="extracted.key_facts" class="facts-box">
          <div class="facts-label">📋 案情摘要</div>
          <p class="facts-text">{{ extracted.key_facts }}</p>
        </div>

        <div v-if="extracted.next_action" class="action-box">
          <span class="action-label">⚡ {{ extracted.next_action }}</span>
        </div>
      </div>

      <!-- 匹配结果 -->
      <div v-if="!manualMode" class="si-section">
        <div class="section-header">
          <h4>🔗 案件匹配</h4>
          <el-tag v-if="hasMatch" type="success" size="small">匹配 {{ ((matched.confidence || 0) * 100).toFixed(0) }}%</el-tag>
          <el-tag v-else type="info" size="small">未找到匹配</el-tag>
          <span v-if="matched && matched.reason" class="match-reason">{{ matched.reason }}</span>
        </div>

        <div v-if="hasMatch" :class="['match-card', 'matched', { highlight: highlightedMatch }]">
          <div class="match-info">
            <div class="match-name">{{ matched.case_name }}</div>
            <div v-if="highlightedMatch" class="match-confidence">
              🎯 AI 识别匹配 · 置信度 {{ ((matched.confidence || 0) * 100).toFixed(0) }}%
            </div>
            <div v-if="highlightedMatch && matched.reason" class="match-reason-banner">
              {{ matched.reason }}
            </div>
          </div>
          <el-button type="primary" size="small" :loading="confirming" @click="doLink(matched.id)">
            归属到此案件
          </el-button>
        </div>

        <div class="match-actions">
          <el-button type="success" @click="startReview">
            ➕ 创建为新案件
          </el-button>
          <el-button @click="toggleManual">手动选择案件…</el-button>
          <el-button @click="emit('close')">取消</el-button>
        </div>
      </div>

      <!-- 手动选择 -->
      <div v-else class="si-section">
        <h4>手动选择案件</h4>
        <el-select v-model="manualCaseId" filterable placeholder="搜索案件…" style="width:100%">
          <el-option v-for="c in allCases" :key="c.id" :label="c.case_name" :value="c.id" />
        </el-select>
        <div class="match-actions" style="margin-top:12px">
          <el-button type="primary" :disabled="!manualCaseId" :loading="confirming" @click="doLink(manualCaseId)">
            确认归属
          </el-button>
          <el-button @click="manualMode = false">返回</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.si-section { margin-bottom: 16px; }
.manual-fallback {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
}

.section-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap;
}
.section-header h4 { font-size: 14px; font-weight: 600; margin: 0; }

.na { color: var(--text-tertiary); }
.mono { font-family: "SF Mono","Consolas",monospace; font-size: 12px; background: var(--bg); padding: 1px 6px; border-radius: 3px; }
.deadline { color: var(--red); font-weight: 600; }

.facts-box {
  margin-top: 12px; padding: 12px 14px; border-radius: var(--radius-sm);
  border: 1px solid var(--border); background: var(--bg);
}
.facts-label { font-size: 12px; font-weight: 600; margin-bottom: 6px; }
.facts-text { font-size: 13px; line-height: 1.7; color: var(--text-secondary); }

.action-box {
  margin-top: 10px; padding: 8px 14px; border-radius: var(--radius-sm);
  border: 1px solid var(--accent); background: var(--accent-soft);
}
.action-label { font-size: 13px; font-weight: 500; color: var(--accent); }

.match-reason { font-size: 11px; color: var(--text-tertiary); }

.match-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  margin-bottom: 12px;
}
.match-card.matched { border-color: var(--green); background: var(--green-soft); }
.match-card.matched.highlight {
  border-color: var(--accent);
  background: var(--accent-soft);
  box-shadow: 0 0 12px rgba(99,102,241,0.2);
  animation: match-pulse 2s ease-in-out infinite;
  padding: 20px 24px;
  flex-wrap: wrap;
  gap: 12px;
}
.match-card.matched.highlight .match-name {
  font-size: 18px;
}
.match-info {
  display: flex; flex-direction: column; gap: 6px;
}
.match-name { font-size: 14px; font-weight: 600; }
.match-confidence {
  font-size: 14px; color: var(--accent); font-weight: 700;
}
.match-reason-banner {
  font-size: 12px; color: var(--text-secondary); line-height: 1.5;
  padding: 8px 12px; border-radius: var(--radius-sm);
  background: rgba(99,102,241,0.06); border: 1px dashed var(--accent);
}
@keyframes match-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(99,102,241,0.15); }
  50% { box-shadow: 0 0 20px rgba(99,102,241,0.35); }
}
.match-actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
