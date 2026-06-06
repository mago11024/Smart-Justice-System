<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, required: true },
})

const emit = defineEmits(['filter'])

const cards = computed(() => [
  {
    key: 'overdue', label: '已超期', sub: '需立即处理',
    value: props.stats.overdue_count || 0,
    color: 'var(--red)', bg: 'var(--red-soft)',
  },
  {
    key: 'due_3', label: '3 天内到期', sub: '极度紧迫',
    value: props.stats.due_3_days_count || 0,
    color: 'var(--red)', bg: 'var(--red-soft)',
  },
  {
    key: 'due_7', label: '7 天内到期', sub: '本周内截止',
    value: props.stats.due_7_days_count || 0,
    color: 'var(--orange)', bg: 'var(--orange-soft)',
  },
  {
    key: 'due_14', label: '两周内到期', sub: '半个月内截止',
    value: props.stats.due_14_days_count || 0,
    color: 'var(--text-secondary)', bg: 'var(--bg)',
  },
  {
    key: 'due_30', label: '一个月内到期', sub: '30 天内截止',
    value: props.stats.due_30_days_count || 0,
    color: 'var(--text-secondary)', bg: 'var(--bg)',
  },
])
</script>

<template>
  <div class="stats">
    <div
      v-for="card in cards"
      :key="card.key"
      class="stat"
      :style="{ '--card-color': card.color, '--card-bg': card.bg }"
      @click="emit('filter', card.key)"
    >
      <div class="st-n" :style="{ color: card.color }">{{ card.value }}</div>
      <div class="st-l">{{ card.label }}</div>
      <div class="st-s">{{ card.sub }}</div>
    </div>
  </div>
</template>

<style scoped>
.stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 28px; }

.stat {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 18px 20px; transition: all 0.2s; cursor: pointer;
}
.stat:hover {
  border-color: var(--card-color); box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}
html.dark .stat:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.35); }
.st-n { font-size: 32px; font-weight: 700; letter-spacing: -0.04em; line-height: 1.1; }
.st-l { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
.st-s { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
</style>
