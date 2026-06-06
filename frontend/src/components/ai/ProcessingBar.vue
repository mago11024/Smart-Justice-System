<script setup>
import { watch } from 'vue'
import { Close, Loading } from '@element-plus/icons-vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  message: { type: String, default: 'AI 正在分析文档…' },
  status: { type: String, default: 'processing' }, // 'processing' | 'success' | 'error'
})

const emit = defineEmits(['dismiss'])

// success/error 态 2s 后自动消失
let autoDismissTimer = null
watch(() => props.status, (val) => {
  if (autoDismissTimer) clearTimeout(autoDismissTimer)
  if (val === 'success' || val === 'error') {
    autoDismissTimer = setTimeout(() => {
      emit('dismiss')
    }, 2500)
  }
})
</script>

<template>
  <Transition name="processing-bar">
    <div v-if="visible" :class="['processing-bar', status]">
      <div class="pb-left">
        <!-- processing: 旋转 spinner -->
        <el-icon v-if="status === 'processing'" class="is-loading" :size="16"><Loading /></el-icon>
        <!-- success: 对勾 -->
        <span v-else-if="status === 'success'" class="pb-icon success-icon">&#10003;</span>
        <!-- error: 叉号 -->
        <span v-else-if="status === 'error'" class="pb-icon error-icon">&#10007;</span>

        <span class="pb-message">{{ message }}</span>

        <!-- 不确定进度条（仅 processing 状态） -->
        <div v-if="status === 'processing'" class="pb-progress">
          <div class="pb-progress-fill"></div>
        </div>
      </div>

      <el-button text :icon="Close" size="small" class="pb-close" @click="emit('dismiss')" />
    </div>
  </Transition>
</template>

<style scoped>
.processing-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding: 0 16px 0 20px;
  background: var(--accent-soft);
  border-bottom: 1px solid var(--accent);
  font-size: 13px;
  font-weight: 500;
  color: var(--accent);
  flex-shrink: 0;
  overflow: hidden;
}
.processing-bar.success {
  background: var(--green-soft, rgba(16,185,129,0.08));
  border-bottom-color: var(--green, #10B981);
  color: var(--green, #10B981);
}
.processing-bar.error {
  background: var(--red-soft, rgba(239,68,68,0.08));
  border-bottom-color: var(--red, #EF4444);
  color: var(--red, #EF4444);
}

.pb-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.pb-message {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pb-icon {
  font-size: 16px;
  font-weight: 700;
  line-height: 1;
  flex-shrink: 0;
}
.success-icon {
  color: var(--green, #10B981);
}
.error-icon {
  color: var(--red, #EF4444);
}

.pb-progress {
  width: 120px;
  height: 3px;
  border-radius: 2px;
  background: rgba(99,102,241,0.15);
  overflow: hidden;
  flex-shrink: 0;
}
.processing-bar.success .pb-progress,
.processing-bar.error .pb-progress {
  display: none;
}

.pb-progress-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--accent), #8B5CF6);
  animation: progress-slide 1.5s ease-in-out infinite;
}
@keyframes progress-slide {
  0% { width: 20%; }
  50% { width: 75%; }
  100% { width: 20%; }
}

.pb-close {
  flex-shrink: 0;
  color: inherit;
}

/* Transition */
.processing-bar-enter-active { transition: all 0.25s ease; }
.processing-bar-leave-active { transition: all 0.2s ease; }
.processing-bar-enter-from { max-height: 0; opacity: 0; }
.processing-bar-enter-to { max-height: 40px; opacity: 1; }
.processing-bar-leave-from { max-height: 40px; opacity: 1; }
.processing-bar-leave-to { max-height: 0; opacity: 0; }
</style>
