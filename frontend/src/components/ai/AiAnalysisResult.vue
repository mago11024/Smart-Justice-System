<script setup>
import { computed } from 'vue'
import { STAGE_LABEL_MAP } from '@/utils/constants'

const props = defineProps({
  doc: { type: Object, required: true },
})

const emit = defineEmits(['apply', 'reanalyze'])

const statusText = computed(() => {
  const map = { pending: '等待分析', processing: '正在分析…', completed: '已完成', failed: '分析失败' }
  return map[props.doc.ai_analysis_status] || props.doc.ai_analysis_status
})

const statusType = computed(() => {
  const map = { completed: 'success', processing: 'warning', failed: 'danger', pending: 'info' }
  return map[props.doc.ai_analysis_status] || 'info'
})

const parties = computed(() => {
  if (!props.doc.ai_extracted_parties) return null
  try {
    return JSON.parse(props.doc.ai_extracted_parties)
  } catch {
    return null
  }
})
</script>

<template>
  <div class="ai-card">
    <div class="ai-head">
      <strong>{{ doc.filename }}</strong>
      <el-tag :type="statusType" size="small">{{ statusText }}</el-tag>
    </div>

    <div v-if="doc.ai_analysis_status === 'completed'" class="ai-body">
      <div class="ai-row">
        <span class="ai-label">识别阶段</span>
        <span class="ai-value">{{ STAGE_LABEL_MAP[doc.ai_extracted_stage] || doc.ai_extracted_stage || '-' }}</span>
      </div>
      <div v-if="parties" class="ai-row">
        <span class="ai-label">当事人</span>
        <span class="ai-value">{{ parties.plaintiff }} → {{ parties.defendant }}</span>
      </div>
      <div v-if="doc.ai_extracted_cause" class="ai-row">
        <span class="ai-label">案由</span>
        <span class="ai-value">{{ doc.ai_extracted_cause }}</span>
      </div>
      <div v-if="doc.ai_extracted_deadline" class="ai-row">
        <span class="ai-label">截止日期</span>
        <span class="ai-value">{{ doc.ai_extracted_deadline }}</span>
      </div>
      <div v-if="doc.ai_extracted_court_date" class="ai-row">
        <span class="ai-label">开庭时间</span>
        <span class="ai-value">{{ new Date(doc.ai_extracted_court_date).toLocaleString('zh-CN') }}</span>
      </div>
      <div class="ai-actions">
        <el-button size="small" type="primary" @click="emit('apply', doc)">应用此信息</el-button>
        <el-button size="small" @click="emit('reanalyze', doc.id)">重新分析</el-button>
      </div>
    </div>

    <div v-else-if="doc.ai_analysis_status === 'failed'" class="ai-body">
      <p class="ai-error">分析失败，请重试或检查文档格式</p>
      <el-button size="small" @click="emit('reanalyze', doc.id)">重新分析</el-button>
    </div>

    <div v-else class="ai-body">
      <p class="ai-waiting">文档正在等待 AI 分析…</p>
    </div>
  </div>
</template>

<style scoped>
.ai-card {
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  padding: 16px; margin-bottom: 12px;
}
.ai-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.ai-head strong { font-size: 14px; }
.ai-body { font-size: 13px; }
.ai-row { display: flex; gap: 12px; padding: 4px 0; }
.ai-label { color: var(--text-tertiary); min-width: 70px; }
.ai-value { color: var(--text); font-weight: 500; }
.ai-actions { margin-top: 12px; display: flex; gap: 8px; }
.ai-error { color: var(--red); margin-bottom: 8px; }
.ai-waiting { color: var(--text-tertiary); }
</style>
