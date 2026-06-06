<script setup>
defineProps({
  selectedCount: { type: Number, default: 0 },
})

const emit = defineEmits(['advance', 'assign', 'clear'])
</script>

<template>
  <div :class="['batch-bar', { show: selectedCount > 0 }]">
    <span>已选 <strong>{{ selectedCount }}</strong> 件</span>
    <el-button size="small" type="primary" @click="emit('advance')">推进</el-button>
    <el-button size="small" type="primary" @click="emit('assign')">指派</el-button>
    <el-button size="small" @click="emit('clear')">取消</el-button>
  </div>
</template>

<style scoped>
.batch-bar {
  display: none; align-items: center; gap: 8px; padding: 5px 12px;
  background: var(--accent-soft); border: 1px solid var(--accent-soft);
  border-radius: var(--radius-sm); font-size: 12px; color: var(--accent);
}
.batch-bar.show { display: flex; }
</style>
