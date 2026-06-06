<script setup>
import { reactive, ref, onMounted } from 'vue'
import { STAGE_OPTIONS } from '@/utils/constants'
import { getLawyers } from '@/api/lawyers'

const props = defineProps({
  initial: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['submit'])

const lawyers = ref([])
const form = reactive({
  case_name: '', case_number: '', plaintiff: '', defendant: '',
  cause_of_action: '', stage: 'consultation', deadline: null,
  court_date: null, lawyer_id: null, notes: '',
  ...props.initial,
})

const rules = {
  case_name: [{ required: true, message: '请输入案件名称', trigger: 'blur' }],
  case_number: [{ required: true, message: '请输入案号（咨询类可填"-"）', trigger: 'blur' }],
}

const formRef = ref(null)

async function doSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  const data = {
    ...form,
    lawyer_id: form.lawyer_id || null,
  }
  emit('submit', data)
}

onMounted(async () => {
  try {
    const res = await getLawyers()
    lawyers.value = res.data
  } catch {}
})
</script>

<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" @submit.prevent="doSubmit">
    <el-form-item label="案件名称" prop="case_name">
      <el-input v-model="form.case_name" placeholder="如：张三诉李四借款纠纷" />
    </el-form-item>
    <el-form-item label="案号" prop="case_number">
      <el-input v-model="form.case_number" placeholder="(2025)沪0105民初1234号" />
    </el-form-item>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item label="原告">
          <el-input v-model="form.plaintiff" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="被告">
          <el-input v-model="form.defendant" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-form-item label="案由">
      <el-input v-model="form.cause_of_action" placeholder="民间借贷 / 合同纠纷 / 劳动争议..." />
    </el-form-item>
    <el-form-item label="当前阶段">
      <el-select v-model="form.stage">
        <el-option v-for="s in STAGE_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
    </el-form-item>
    <el-form-item label="截止日期">
      <el-date-picker v-model="form.deadline" type="date" value-format="YYYY-MM-DD" style="width:100%" />
    </el-form-item>
    <el-form-item label="开庭时间">
      <el-date-picker v-model="form.court_date" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
    </el-form-item>
    <el-form-item label="承办律师">
      <el-select v-model="form.lawyer_id" clearable placeholder="选择律师">
        <el-option v-for="l in lawyers" :key="l.id" :label="`${l.name} · ${l.role}`" :value="l.id" />
      </el-select>
    </el-form-item>
    <el-form-item label="备注">
      <el-input v-model="form.notes" type="textarea" :rows="3" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="doSubmit">保存</el-button>
      <el-button @click="$router.back()">取消</el-button>
    </el-form-item>
  </el-form>
</template>
