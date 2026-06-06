<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadDocument } from '@/api/documents'

const props = defineProps({
  caseId: { type: Number, required: true },
})

const emit = defineEmits(['uploaded'])

const uploading = ref(false)
const fileList = ref([])

async function handleChange(file) {
  uploading.value = true
  try {
    const res = await uploadDocument(props.caseId, file.raw)
    ElMessage.success('上传成功，AI 正在分析…')
    emit('uploaded', res.data)
    fileList.value = []
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

function beforeUpload(file) {
  const valid = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
  if (!valid.includes(file.type)) {
    ElMessage.error('仅支持 PDF、DOCX、TXT 格式')
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 20MB')
    return false
  }
  return true
}
</script>

<template>
  <div class="uploader">
    <h3>上传文档 · AI 分析</h3>
    <p class="desc">上传起诉状、判决书等法律文档，AI 将自动识别案件阶段和关键信息</p>
    <el-upload
      v-model:file-list="fileList"
      class="upload-area"
      drag
      :auto-upload="false"
      :on-change="handleChange"
      :before-upload="beforeUpload"
      :show-file-list="true"
      :limit="1"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">
        拖拽文件到此处或 <em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">支持 PDF / DOCX / TXT，每个不超过 20MB</div>
      </template>
    </el-upload>
    <div v-if="uploading" style="text-align:center;margin-top:12px">
      <el-icon class="is-loading"><Loading /></el-icon> AI 正在分析文档…
    </div>
  </div>
</template>

<style scoped>
.uploader { padding: 20px; }
.uploader h3 { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.desc { font-size: 13px; color: var(--text-tertiary); margin-bottom: 16px; }
.upload-area { width: 100%; }
</style>
