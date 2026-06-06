<script setup>
import { inject, computed } from 'vue'

const triggerFilePick = inject('triggerFilePick', () => {})
const dragActive = inject('dragActive', { value: false })
const currentCaseId = inject('currentCaseId', null)
const caseStageLabel = inject('caseStageLabel', '')

const hintHtml = computed(() => {
  if (currentCaseId?.value) {
    const stage = caseStageLabel?.value || ''
    return `拖拽文件直接归入当前案件${stage ? `<br><small>（${stage}）</small>` : ''}`
  }
  return '拖拽文件到任意位置<br><small>AI 自动识别归属，静默分类</small>'
})
</script>

<template>
  <div :class="['sb-ingest-hint', { active: dragActive.value }]" @click="triggerFilePick">
    <span class="hint-icon">&#8682;</span>
    <span class="hint-text" v-html="hintHtml"></span>
  </div>
</template>

<style scoped>
.sb-ingest-hint {
  margin: 4px 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1.5px dashed var(--border);
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}
.sb-ingest-hint:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.sb-ingest-hint.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.hint-icon {
  font-size: 20px;
  color: var(--accent);
  display: block;
  margin-bottom: 4px;
}
.hint-text {
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1.4;
}
</style>
