<script setup>
import { computed } from 'vue'
import { STAGE_LABEL_MAP, STAGE_COLOR_MAP, STATUS_STYLE } from '@/utils/constants'

const props = defineProps({
  item: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  highlighted: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle', 'advance', 'assign', 'detail', 'delete'])

const rowCls = computed(() => {
  if (props.item.overdue_status === 'overdue') return 'rd'
  if (props.item.overdue_status === 'due_soon') return 'og'
  return ''
})

const statusTag = computed(() => {
  const s = props.item.overdue_status
  if (s === 'overdue') return { text: `超期 ${props.item.overdue_days} 天`, cls: 'rd' }
  if (s === 'due_soon') return { text: `剩 ${props.item.overdue_days} 天`, cls: 'og' }
  if (props.item.stage === 'closed') return { text: '已结', cls: 'gr' }
  if (props.item.stage === 'court_appearance' && props.item.court_date) {
    const d = new Date(props.item.court_date)
    const now = new Date()
    const diffDay = Math.ceil((d - now) / 86400000)
    if (diffDay <= 1) return { text: diffDay <= 0 ? '今天开庭' : '明天开庭', cls: 'bl' }
  }
  return { text: '进行中', cls: 'gr' }
})

const deadlineLabel = computed(() => {
  if (!props.item.deadline) return ''
  const d = props.item.overdue_status
  return d === 'overdue' ? `超期 ${props.item.overdue_days} 天` : d === 'due_soon' ? `剩 ${props.item.overdue_days} 天` : ''
})

const stageDot = computed(() => STAGE_COLOR_MAP[props.item.stage] || '#6366F1')
</script>

<template>
  <div :class="['row', rowCls, { sel: selected, hl: highlighted }]" :data-case-id="item.id" @click="emit('detail', item.id)">
    <div :class="['cb', { chk: selected }]" @click.stop="emit('toggle', item.id)"></div>
    <div class="rbd">
      <div class="r1">
        <span class="rn">{{ item.case_name }}</span>
        <span v-if="item.case_number" class="rr">{{ item.case_number }}</span>
        <span :class="['rs', statusTag.cls]">{{ statusTag.text }}</span>
      </div>
      <div class="r2">
        <span class="rp">{{ item.plaintiff }} → {{ item.defendant }} · {{ item.cause_of_action }}</span>
        <span v-if="item.deadline" :class="['rdl', rowCls]">截止 {{ item.deadline }} {{ deadlineLabel }}</span>
        <span class="rh">{{ STAGE_LABEL_MAP[item.stage] }} · 停留 {{ item.days_in_stage }} 天</span>
      </div>
    </div>
    <div class="rrt">
      <span class="rsi"><span class="sdot" :style="{ background: stageDot }"></span>{{ STAGE_LABEL_MAP[item.stage] }}</span>
      <div v-if="item.lawyer_name" class="rlr">
        <span class="rav">{{ item.lawyer_initials }}</span>
        <span class="rln">{{ item.lawyer_name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: flex; align-items: center; padding: 12px 20px; gap: 14px;
  border-top: 1px solid var(--border); transition: background 0.1s; cursor: pointer; position: relative;
}
.row:first-of-type { border-top: none; }
.row:hover { background: var(--bg); }
.row.sel { background: var(--accent-soft); }
.row.hl {
  border-top-color: var(--accent);
  box-shadow: inset 0 0 0 2px var(--accent), 0 0 16px rgba(99,102,241,0.25);
  animation: hl-pulse 0.8s ease-in-out 3;
  position: relative;
  z-index: 1;
  border-radius: var(--radius-sm);
}
.row.hl:first-of-type { border-top: 2px solid var(--accent); }
@keyframes hl-pulse {
  0%, 100% { box-shadow: inset 0 0 0 2px var(--accent), 0 0 8px rgba(99,102,241,0.15); }
  50% { box-shadow: inset 0 0 0 3px var(--accent), 0 0 24px rgba(99,102,241,0.4); }
}
html.dark .row.hl {
  box-shadow: inset 0 0 0 2px var(--accent), 0 0 20px rgba(124,124,240,0.3);
  animation: hl-pulse-dark 0.8s ease-in-out 3;
}
@keyframes hl-pulse-dark {
  0%, 100% { box-shadow: inset 0 0 0 2px var(--accent), 0 0 12px rgba(124,124,240,0.2); }
  50% { box-shadow: inset 0 0 0 3px var(--accent), 0 0 28px rgba(124,124,240,0.5); }
}
.row::before { content: ''; position: absolute; left: 0; top: 8px; bottom: 8px; width: 3px; border-radius: 2px; }
.row.rd::before { background: var(--red); }
.row.og::before { background: var(--orange); }
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
.rbd { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.r1 { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.rn { font-size: 15px; font-weight: 600; color: var(--text); }
.rr { font-size: 12px; color: var(--text-tertiary); font-family: "SF Mono","Consolas",monospace; }
.rs { font-size: 11px; font-weight: 500; padding: 1px 8px; border-radius: 5px; }
.rs.rd { color: var(--red); background: var(--red-soft); }
.rs.og { color: var(--orange); background: var(--orange-soft); }
.rs.gr { color: var(--green); background: var(--green-soft); }
.rs.bl { color: var(--blue); background: var(--blue-soft); }
.r2 { display: flex; align-items: center; gap: 16px; font-size: 12px; color: var(--text-secondary); }
.rp { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 220px; }
.rdl { white-space: nowrap; }
.rdl.rd { color: var(--red); }
.rdl.og { color: var(--orange); }
.rh { color: var(--text-tertiary); font-size: 11px; }
.rrt { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.rsi {
  font-size: 11px; color: var(--text-tertiary); padding: 4px 10px; border-radius: 6px;
  background: var(--bg); display: flex; align-items: center; gap: 5px;
}
.sdot { width: 6px; height: 6px; border-radius: 50%; }
.rlr { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.rav {
  width: 26px; height: 26px; border-radius: 50%; background: var(--accent-soft);
  color: var(--accent); display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600;
}
.rln { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
</style>
