<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import CaseForm from '@/components/case/CaseForm.vue'
import { getCase, updateCase } from '@/api/cases'
import { useDeferredLoading } from '@/composables/useDeferredLoading'

const route = useRoute()
const router = useRouter()
const initial = ref({})
const loading = ref(true)
const { showLoading, run } = useDeferredLoading()

onMounted(() => run(async () => {
  const res = await getCase(route.params.id)
  initial.value = res.data
}).finally(() => { loading.value = false }))

async function handleSubmit(data) {
  await updateCase(route.params.id, data)
  ElMessage.success('已更新')
  router.push(`/case/${route.params.id}`)
}
</script>

<template>
  <div v-loading="showLoading">
    <div class="header">
      <h1>编辑案件</h1>
    </div>
    <div class="form-wrap">
      <CaseForm v-if="!loading" :initial="initial" @submit="handleSubmit" />
    </div>
  </div>
</template>

<style scoped>
.header { margin-bottom: 28px; }
.header h1 { font-size: 26px; font-weight: 700; color: var(--text); }
.form-wrap { max-width: 700px; background: var(--surface); padding: 32px; border-radius: var(--radius); border: 1px solid var(--border); }
</style>
