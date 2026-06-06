<script setup>
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import CaseForm from '@/components/case/CaseForm.vue'
import { createCase } from '@/api/cases'

const router = useRouter()

async function handleSubmit(data) {
  await createCase(data)
  ElMessage.success('案件已创建')
  router.push('/')
}
</script>

<template>
  <div>
    <div class="header">
      <h1>新建案件</h1>
    </div>
    <div class="form-wrap">
      <CaseForm @submit="handleSubmit" />
    </div>
  </div>
</template>

<style scoped>
.header { margin-bottom: 28px; }
.header h1 { font-size: 26px; font-weight: 700; color: var(--text); }
.form-wrap { max-width: 700px; background: var(--surface); padding: 32px; border-radius: var(--radius); border: 1px solid var(--border); }
</style>
