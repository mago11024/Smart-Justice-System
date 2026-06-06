<script setup>
import { ref } from 'vue'
import CaseRow from './CaseRow.vue'

const props = defineProps({
  section: { type: Object, required: true },
  itemSelected: { type: Function, required: true },
  highlightedCaseId: { type: Number, default: null },
})

const emit = defineEmits(['toggle', 'advance', 'assign', 'detail', 'delete'])

const collapsed = ref(false)

const isOverdue = (s) => s.overdue_status === 'overdue'
const isDueSoon = (s) => s.overdue_status === 'due_soon'
</script>

<template>
  <div :class="['sec', { collapsed }]" :style="{ borderLeft: section.overdue_count > 0 ? '3px solid var(--red)' : 'none' }">
    <div class="sec-hd" @click="collapsed = !collapsed">
      <div class="hdl">
        <span class="hd-arr">&#x2304;</span>
        <span class="hd-l" :style="{ color: section.overdue_count > 0 ? 'var(--red)' : '' }">{{ section.stage_label }}</span>
        <span class="hd-c">{{ section.count }} 件</span>
        <span v-if="section.overdue_count > 0" class="hd-b rd">超期 {{ section.overdue_count }}</span>
        <span v-else-if="section.cases.some(isDueSoon)" class="hd-b og">有案件即将到期</span>
      </div>
    </div>
    <div v-show="!collapsed" class="sec-bd">
      <CaseRow
        v-for="item in section.cases"
        :key="item.id"
        :item="item"
        :selected="itemSelected(item.id)"
        :highlighted="highlightedCaseId === item.id"
        @toggle="emit('toggle', $event)"
        @advance="emit('advance', $event)"
        @assign="emit('assign', $event)"
        @detail="emit('detail', $event)"
        @delete="emit('delete', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.sec {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); overflow: hidden; margin-bottom: 6px;
}
.sec-hd {
  display: flex; align-items: center; padding: 14px 20px;
  cursor: pointer; user-select: none; gap: 8px;
}
.sec-hd:hover { background: var(--bg); }
.hdl { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.hd-arr { font-size: 9px; color: var(--text-tertiary); transition: transform 0.15s; flex-shrink: 0; }
.collapsed .hd-arr { transform: rotate(-90deg); }
.hd-l { font-size: 15px; font-weight: 600; }
.hd-c { font-size: 13px; color: var(--text-tertiary); font-weight: 400; }
.hd-b { font-size: 11px; padding: 2px 10px; border-radius: 4px; font-weight: 500; }
.hd-b.rd { color: var(--red); background: var(--red-soft); }
.hd-b.og { color: var(--orange); background: var(--orange-soft); }
</style>
