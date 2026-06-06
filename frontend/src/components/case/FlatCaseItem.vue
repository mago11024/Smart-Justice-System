<script setup>
import { computed } from 'vue'
import { STAGE_LABEL_MAP, STAGE_COLOR_MAP, STATUS_STYLE } from '@/utils/constants'

const props = defineProps({
  item: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  highlighted: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle', 'detail'])

const tagColor = computed(() => STAGE_COLOR_MAP[props.item.stage] || '#6366F1')
const bgColor = computed(() => {
  const s = props.item.overdue_status
  if (s === 'overdue') return 'var(--red-soft)'
  if (s === 'due_soon') return 'var(--orange-soft)'
  return 'var(--bg)'
})

const stageText = computed(() => {
  const s = props.item.overdue_status
  if (s === 'overdue') return '超期 · ' + STAGE_LABEL_MAP[props.item.stage]
  if (s === 'due_soon') return '即将到期 · ' + STAGE_LABEL_MAP[props.item.stage]
  return STAGE_LABEL_MAP[props.item.stage]
})

const statusTag = computed(() => {
  const s = props.item.overdue_status
  if (s === 'overdue') return { text: `超期 ${props.item.overdue_days} 天`, cls: 'rd' }
  if (s === 'due_soon') return { text: `剩 ${props.item.overdue_days} 天`, cls: 'og' }
  return { text: '进行中', cls: 'gr' }
})
</script>

<template>
  <div :class="['flat-it', { sel: selected, hl: highlighted }]" :data-case-id="item.id" @click="emit('detail', item.id)">
    <div :class="['cb', { chk: selected }]" @click.stop="emit('toggle', item.id)"></div>
    <span class="ft" :style="{ color: tagColor, background: bgColor }">{{ stageText }}</span>
    <div class="rbd">
      <div class="r1">
        <span class="rn">{{ item.case_name }}</span>
        <span v-if="item.case_number" class="rr">{{ item.case_number }}</span>
        <span :class="['rs', statusTag.cls]">{{ statusTag.text }}</span>
      </div>
    </div>
    <div v-if="item.lawyer_name" class="rlr">
      <span class="rav">{{ item.lawyer_initials }}</span>
      <span class="rln">{{ item.lawyer_name }}</span>
    </div>
  </div>
</template>

<style scoped>
.flat-it {
  display: flex; align-items: center; padding: 10px 16px; gap: 12px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); cursor: pointer; transition: all 0.12s;
}
.flat-it:hover { border-color: var(--text-tertiary); box-shadow: 0 1px 2px rgba(0,0,0,0.06); }
html.dark .flat-it:hover { box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
.flat-it.sel { background: var(--accent-soft); border-color: var(--accent-soft); }
.flat-it.hl {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent), 0 0 16px rgba(99,102,241,0.25);
  animation: hl-pulse 0.8s ease-in-out 3;
  position: relative;
  z-index: 1;
}
@keyframes hl-pulse {
  0%, 100% { box-shadow: 0 0 0 2px var(--accent), 0 0 8px rgba(99,102,241,0.15); }
  50% { box-shadow: 0 0 0 3px var(--accent), 0 0 24px rgba(99,102,241,0.4); }
}
html.dark .flat-it.hl {
  box-shadow: 0 0 0 2px var(--accent), 0 0 20px rgba(124,124,240,0.3);
}
html.dark .flat-it.hl {
  animation: hl-pulse-dark 0.8s ease-in-out 3;
}
@keyframes hl-pulse-dark {
  0%, 100% { box-shadow: 0 0 0 2px var(--accent), 0 0 12px rgba(124,124,240,0.2); }
  50% { box-shadow: 0 0 0 3px var(--accent), 0 0 28px rgba(124,124,240,0.5); }
}
.cb {
  width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid var(--text-tertiary);
  cursor: pointer; flex-shrink: 0; transition: all 0.12s; background: transparent;
}
.cb:hover { border-color: var(--accent); }
.cb.chk { background: var(--accent); border-color: var(--accent); position: relative; }
.cb.chk::after {
  content: ''; width: 5px; height: 8px; border: solid #fff; border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg); position: absolute; top: 3px; left: 5px;
}
.ft { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 4px; white-space: nowrap; flex-shrink: 0; }
.rbd { flex: 1; min-width: 0; }
.r1 { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.rn { font-size: 14px; font-weight: 600; color: var(--text); }
.rr { font-size: 12px; color: var(--text-tertiary); font-family: "SF Mono","Consolas",monospace; }
.rs { font-size: 11px; font-weight: 500; padding: 1px 8px; border-radius: 5px; }
.rs.rd { color: var(--red); background: var(--red-soft); }
.rs.og { color: var(--orange); background: var(--orange-soft); }
.rs.gr { color: var(--green); background: var(--green-soft); }
.rs.bl { color: var(--blue); background: var(--blue-soft); }
.rlr { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.rav {
  width: 26px; height: 26px; border-radius: 50%; background: var(--accent-soft);
  color: var(--accent); display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600;
}
.rln { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
</style>
