<script setup>
defineProps({
  view: { type: String, default: 'flow' },
})

const emit = defineEmits(['update:view'])
</script>

<template>
  <div class="view-toggle">
    <button :class="{ active: view === 'flow' }" @click="emit('update:view', 'flow')">按流程分组</button>
    <button :class="{ active: view === 'flat' }" @click="emit('update:view', 'flat')">全部案件</button>
  </div>
</template>

<style scoped>
.view-toggle { display: flex; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm); overflow: hidden; }
.view-toggle button {
  padding: 6px 14px; font-size: 12px; font-weight: 500; border: none;
  background: transparent; color: var(--text-secondary); cursor: pointer;
  font-family: inherit; transition: all 0.12s;
}
.view-toggle button:hover { color: var(--text); }
.view-toggle button.active { background: var(--text); color: var(--surface); }
html.dark .view-toggle button.active { background: var(--accent); color: #fff; }
</style>
