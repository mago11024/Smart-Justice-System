<script setup>
import { computed } from 'vue'
import { STAGE_LABEL_MAP } from '@/utils/constants'

const props = defineProps({
  stats: { type: Object, default: () => ({ by_stage: {}, overdue_count: 0, due_3_days_count: 0, due_7_days_count: 0, due_14_days_count: 0, due_30_days_count: 0 }) },
  activeFilter: { type: String, default: 'all' },
})

const emit = defineEmits(['update:activeFilter'])

const filters = computed(() => {
  const list = [
    { key: 'all', label: '全部', count: props.stats.total_active || 0 },
    { key: 'overdue', label: '🔴 已超期', count: props.stats.overdue_count || 0, color: 'var(--red)' },
    { key: 'due_3', label: '3 天内', count: props.stats.due_3_days_count || 0, color: 'var(--red)' },
    { key: 'due_7', label: '7 天内', count: props.stats.due_7_days_count || 0, color: 'var(--orange)' },
    { key: 'due_14', label: '两周内', count: props.stats.due_14_days_count || 0 },
    { key: 'due_30', label: '一个月内', count: props.stats.due_30_days_count || 0 },
  ]
  for (const [k, v] of Object.entries(props.stats.by_stage || {})) {
    list.push({ key: k, label: STAGE_LABEL_MAP[k] || k, count: v })
  }
  return list
})
</script>

<template>
  <div class="flat-f">
    <button
      v-for="f in filters" :key="f.key"
      :class="['fli', { active: activeFilter === f.key }]"
      :style="activeFilter === f.key ? {} : { color: f.color }"
      @click="emit('update:activeFilter', f.key)"
    >
      {{ f.label }} <span class="n">{{ f.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.flat-f { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
.fli {
  padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 500;
  cursor: pointer; border: 1px solid var(--border); background: var(--surface);
  color: var(--text-secondary); font-family: inherit; transition: all 0.15s; white-space: nowrap;
}
.fli:hover { border-color: var(--accent); color: var(--accent); }
.fli.active { background: var(--accent); color: #fff !important; border-color: var(--accent); }
html.dark .fli.active { text-shadow: 0 1px 0 rgba(0,0,0,0.25); }
.fli.active .n { color: rgba(255,255,255,0.7); }
.n { opacity: 0.6; font-size: 10px; }
</style>
