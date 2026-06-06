<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSettings, updateSettings, resetSettings } from '@/api/settings'
import { getAIEngines } from '@/api/ai'

const config = ref({
  ai: {
    engine: 'ollama', embed_engine: 'ollama', timeout: 120,
    ollama: { base_url: 'http://localhost:11434', model: 'qwen2.5:7b', embed_model: 'nomic-embed-text' },
    openai: { base_url: 'https://api.openai.com/v1', api_key: '', model: 'gpt-4o-mini', embed_model: 'text-embedding-3-small' },
    deepseek: { base_url: 'https://api.deepseek.com/v1', api_key: '', model: 'deepseek-chat' },
    llamacpp: { base_url: 'http://localhost:8080/v1', model: 'qwen2.5-7b' },
  },
  display: { theme: 'auto', sidebar_default: 'expanded', language: 'zh-CN' },
  notification: { enabled: true, overdue_alert: true, due_soon_alert: true, court_reminder: true, auto_refresh_minutes: 30 },
  paddleocr: { token: '', model: 'PP-OCRv5' },
})

const saving = ref(false)
const testingEngine = ref(false)
const engineStatus = ref({ current: '', model: '', healthy: false, engines: [] })

// ── 引擎选项 ──
const chatEngineOptions = [
  { value: 'ollama', label: 'Ollama (本地)', desc: '免费本地运行，支持对话+向量', icon: '🏠', hasEmbed: true },
  { value: 'llamacpp', label: 'llama.cpp Server', desc: '本地 llama-server，OpenAI 兼容协议', icon: '🦙', hasEmbed: false },
  { value: 'openai', label: 'OpenAI 兼容', desc: 'OpenAI / 硅基流动 / 通义千问等云端 API', icon: '☁️', hasEmbed: true },
  { value: 'deepseek', label: 'DeepSeek', desc: '国产高性价比，仅对话不含向量', icon: '🐋', hasEmbed: false },
]

const embedEngineOptions = [
  { value: 'ollama', label: 'Ollama 本地向量', desc: '免费，需 nomic-embed-text 模型 (274MB)', icon: '🏠' },
  { value: 'openai', label: 'OpenAI Embedding', desc: '云端，需 API Key', icon: '☁️' },
]

const themeOptions = [
  { value: 'auto', label: '跟随系统' },
  { value: 'light', label: '浅色模式' },
  { value: 'dark', label: '深色模式' },
]

// ── 当前对话引擎信息 ──
const currentChatEngine = computed(() =>
  chatEngineOptions.find(e => e.value === config.value.ai.engine)
)

// ── 加载（后台静默，不显示 loading 遮罩） ──
async function load() {
  try {
    const [cfgRes, engRes] = await Promise.all([
      getSettings(),
      getAIEngines().catch(() => ({ data: {} })),
    ])
    config.value = cfgRes.data
    engineStatus.value = engRes.data
  } catch {}
}

onMounted(load)

// ── 保存 ──
async function doSave() {
  saving.value = true
  try {
    const payload = JSON.parse(JSON.stringify(config.value))
    await updateSettings(payload)
    ElMessage.success('设置已保存，引擎切换即时生效')

    try {
      const r = await getAIEngines()
      engineStatus.value = r.data
    } catch {}
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// ── 测试连接 ──
async function doTestEngine() {
  testingEngine.value = true
  try {
    const res = await getAIEngines()
    engineStatus.value = res.data
    ElMessage[res.data.healthy ? 'success' : 'warning'](
      res.data.healthy
        ? `${res.data.current} / ${res.data.model} 连接正常`
        : `${res.data.current} 无法连接，请检查配置和服务状态`
    )
  } catch {
    ElMessage.error('后端 API 不可达')
  } finally {
    testingEngine.value = false
  }
}

async function doReset() {
  try {
    await ElMessageBox.confirm('确定恢复所有设置为默认值？', '确认重置', { type: 'warning' })
    const res = await resetSettings()
    config.value = res.data.config
    ElMessage.success('已恢复默认设置')
  } catch {}
}
</script>

<template>
  <div>
    <div class="header">
      <h1>设置</h1>
      <p>配置 AI 引擎、显示偏好、通知策略</p>
    </div>

    <div class="settings-grid">
      <!-- ═══════ AI 引擎 ═══════ -->
      <div class="section">
        <div class="sec-title">🧠 对话引擎</div>
        <div class="sec-desc">选择大模型后端，用于文档分析、案件匹配等任务</div>

        <div class="field">
          <label>引擎类型</label>
          <div class="engine-cards">
            <div
              v-for="opt in chatEngineOptions"
              :key="opt.value"
              :class="['eng-card', { active: config.ai.engine === opt.value }]"
              @click="config.ai.engine = opt.value"
            >
              <span class="eng-icon">{{ opt.icon }}</span>
              <div class="eng-info">
                <div class="eng-name">{{ opt.label }}</div>
                <div class="eng-desc">{{ opt.desc }}</div>
              </div>
              <span v-if="!opt.hasEmbed" class="eng-tag">仅对话</span>
              <span v-else class="eng-tag ok">对话+向量</span>
            </div>
          </div>
        </div>

        <!-- 引擎状态条 -->
        <div class="engine-status">
          <div class="es-row">
            <span :class="['es-dot', engineStatus.healthy ? 'ok' : 'err']"></span>
            <span v-if="engineStatus.current" class="es-text">
              {{ engineStatus.current }} / {{ engineStatus.model }}
              — {{ engineStatus.healthy ? '在线' : '离线' }}
            </span>
            <span v-else class="es-text">未检测</span>
            <el-button size="small" text :loading="testingEngine" @click="doTestEngine">测试连接</el-button>
          </div>
        </div>

        <!-- Ollama -->
        <template v-if="config.ai.engine === 'ollama'">
          <div class="field">
            <label>服务地址</label>
            <el-input v-model="config.ai.ollama.base_url" placeholder="http://localhost:11434" />
          </div>
          <div class="field">
            <label>对话模型</label>
            <el-input v-model="config.ai.ollama.model" placeholder="qwen2.5:7b" />
          </div>
          <div class="field">
            <label>向量模型</label>
            <el-input v-model="config.ai.ollama.embed_model" placeholder="nomic-embed-text" />
            <span class="hint">用于类案语义搜索，需先 <code>ollama pull nomic-embed-text</code></span>
          </div>
        </template>

        <!-- OpenAI -->
        <template v-if="config.ai.engine === 'openai'">
          <div class="field">
            <label>API 地址</label>
            <el-input v-model="config.ai.openai.base_url" placeholder="https://api.openai.com/v1" />
            <span class="hint">兼容所有 OpenAI-format 服务</span>
          </div>
          <div class="field">
            <label>API Key</label>
            <el-input v-model="config.ai.openai.api_key" type="password" show-password placeholder="sk-…" />
          </div>
          <div class="field">
            <label>对话模型</label>
            <el-input v-model="config.ai.openai.model" placeholder="gpt-4o-mini" />
          </div>
          <div class="field">
            <label>向量模型</label>
            <el-input v-model="config.ai.openai.embed_model" placeholder="text-embedding-3-small" />
          </div>
        </template>

        <!-- DeepSeek -->
        <template v-if="config.ai.engine === 'deepseek'">
          <div class="field">
            <label>API 地址</label>
            <el-input v-model="config.ai.deepseek.base_url" placeholder="https://api.deepseek.com/v1" />
          </div>
          <div class="field">
            <label>API Key</label>
            <el-input v-model="config.ai.deepseek.api_key" type="password" show-password placeholder="sk-…" />
            <span class="hint">在 <a href="https://platform.deepseek.com" target="_blank">platform.deepseek.com</a> 获取</span>
          </div>
          <div class="field">
            <label>模型</label>
            <el-input v-model="config.ai.deepseek.model" placeholder="deepseek-chat" />
            <span class="hint"><code>deepseek-chat</code> (V3) 或 <code>deepseek-reasoner</code> (R1 推理)</span>
          </div>
        </template>

        <!-- llama.cpp -->
        <template v-if="config.ai.engine === 'llamacpp'">
          <div class="field">
            <label>服务地址</label>
            <el-input v-model="config.ai.llamacpp.base_url" placeholder="http://localhost:8080/v1" />
            <span class="hint">llama-server 的 OpenAI 兼容端点，形如 <code>http://localhost:8080/v1</code></span>
          </div>
          <div class="field">
            <label>模型标识</label>
            <el-input v-model="config.ai.llamacpp.model" placeholder="qwen2.5-7b" />
            <span class="hint">任意名称即可，llama-server 会自动使用已加载的模型</span>
          </div>
          <el-alert type="info" :closable="false" show-icon style="margin-top:8px">
            <template #title>
              启动命令：<code>llama-server -hf lmstudio-community/Qwen2.5-7B-Instruct-GGUF:Q4_K_M --port 8080</code>
            </template>
          </el-alert>
        </template>

        <div class="field">
          <label>请求超时（秒）</label>
          <el-input-number v-model="config.ai.timeout" :min="30" :max="600" style="width:180px" />
        </div>
      </div>

      <!-- ═══════ 向量引擎 (独立) ═══════ -->
      <div class="section">
        <div class="sec-title">🔢 向量引擎（类案语义搜索）</div>
        <div class="sec-desc">
          独立于对话引擎。若对话引擎不支持向量化，需额外配置此引擎。
          <template v-if="currentChatEngine && !currentChatEngine.hasEmbed">
            <el-tag type="warning" size="small" effect="plain" style="margin-left:6px">
              {{ currentChatEngine.label }} 不含向量能力，必须单独配置
            </el-tag>
          </template>
          <template v-else>
            <el-tag type="success" size="small" effect="plain" style="margin-left:6px">
              当前对话引擎自带向量，无需额外配置
            </el-tag>
          </template>
        </div>

        <div class="field">
          <label>向量引擎</label>
          <el-select v-model="config.ai.embed_engine" style="width:100%">
            <el-option
              v-for="opt in embedEngineOptions"
              :key="opt.value"
              :value="opt.value"
              :label="`${opt.icon} ${opt.label}`"
            />
          </el-select>
          <span class="hint">推荐选 Ollama：免费本地运行，<code>ollama pull nomic-embed-text</code> 即可</span>
        </div>

        <div v-if="config.ai.embed_engine === 'ollama'" class="field">
          <label>Ollama 地址（向量专用）</label>
          <el-input v-model="config.ai.ollama.base_url" placeholder="http://localhost:11434" />
        </div>
        <div v-if="config.ai.embed_engine === 'ollama'" class="field">
          <label>向量模型名</label>
          <el-input v-model="config.ai.ollama.embed_model" placeholder="nomic-embed-text" />
        </div>
        <div v-if="config.ai.embed_engine === 'openai'" class="field">
          <label>OpenAI API Key（向量专用）</label>
          <el-input v-model="config.ai.openai.api_key" type="password" show-password placeholder="sk-…" />
        </div>
      </div>

      <!-- ═══════ PaddleOCR ═══════ -->
      <div class="section">
        <div class="sec-title">🔬 PaddleOCR 云端识别</div>
        <div class="sec-desc">扫描件 PDF / 图片的 OCR 文字提取。PDF 优先读文字层，空则自动回退 OCR</div>

        <div class="field">
          <label>API Token</label>
          <el-input v-model="config.paddleocr.token" type="password" show-password placeholder="PaddleOCR API Token…" />
          <span class="hint">在 PaddleOCR AI Studio 获取</span>
        </div>
        <div class="field">
          <label>模型</label>
          <el-input v-model="config.paddleocr.model" placeholder="PP-OCRv5" />
          <span class="hint"><code>PP-OCRv5</code> 中文精度最高，推荐</span>
        </div>
      </div>

      <!-- ═══════ 显示偏好 ═══════ -->
      <div class="section">
        <div class="sec-title">🎨 显示偏好</div>
        <div class="field">
          <label>主题模式</label>
          <el-radio-group v-model="config.display.theme">
            <el-radio-button v-for="opt in themeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</el-radio-button>
          </el-radio-group>
        </div>
        <div class="field">
          <label>侧边栏默认</label>
          <el-radio-group v-model="config.display.sidebar_default">
            <el-radio-button value="expanded">展开</el-radio-button>
            <el-radio-button value="collapsed">收起</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- ═══════ 通知设置 ═══════ -->
      <div class="section">
        <div class="sec-title">🔔 通知与提醒</div>
        <div class="sec-desc">控制预警生成和自动刷新策略</div>
        <div class="field">
          <div class="switch-row">
            <div><label style="margin-bottom:0">启用通知</label><span class="hint">关闭后不再生成新提醒</span></div>
            <el-switch v-model="config.notification.enabled" />
          </div>
        </div>
        <template v-if="config.notification.enabled">
          <div class="field">
            <div class="switch-row">
              <div><label style="margin-bottom:0">超期预警</label><span class="hint">案件超过截止日期时生成提醒</span></div>
              <el-switch v-model="config.notification.overdue_alert" />
            </div>
          </div>
          <div class="field">
            <div class="switch-row">
              <div><label style="margin-bottom:0">即将到期提醒</label><span class="hint">未来 7 天内截止的案件</span></div>
              <el-switch v-model="config.notification.due_soon_alert" />
            </div>
          </div>
          <div class="field">
            <div class="switch-row">
              <div><label style="margin-bottom:0">开庭提醒</label><span class="hint">明天或今天开庭的案件</span></div>
              <el-switch v-model="config.notification.court_reminder" />
            </div>
          </div>
        </template>
        <div class="field">
          <label>自动刷新间隔（分钟）</label>
          <el-input-number v-model="config.notification.auto_refresh_minutes" :min="5" :max="120" :step="5" style="width:180px" />
        </div>
      </div>
    </div>

    <div class="actions">
      <el-button type="primary" :loading="saving" @click="doSave" size="large">保存设置</el-button>
      <el-button @click="doReset" size="large">恢复默认</el-button>
      <span class="save-hint">修改即时生效，无需重启</span>
    </div>
  </div>
</template>

<style scoped>
.header { margin-bottom: 28px; }
.header h1 { font-size: 26px; font-weight: 700; letter-spacing: -0.03em; }
.header p { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.settings-grid { display: flex; flex-direction: column; gap: 24px; max-width: 760px; }

.section { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; }
.sec-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.sec-desc { font-size: 12px; color: var(--text-tertiary); margin-bottom: 20px; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }

.field { margin-bottom: 16px; }
.field:last-child { margin-bottom: 0; }
.field label { display: block; font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
.hint { display: block; font-size: 11px; color: var(--text-tertiary); margin-top: 4px; }
.hint code { font-family: var(--font); background: var(--bg); padding: 1px 5px; border-radius: 3px; font-size: 11px; }
.hint a { color: var(--accent); }

/* 引擎卡片 */
.engine-cards { display: flex; flex-direction: column; gap: 8px; }
.eng-card {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px; border: 1.5px solid var(--border); border-radius: var(--radius-sm);
  cursor: pointer; transition: all 0.15s;
}
.eng-card:hover { border-color: var(--accent); }
.eng-card.active { border-color: var(--accent); background: var(--accent-soft); }
.eng-icon { font-size: 22px; flex-shrink: 0; }
.eng-info { flex: 1; min-width: 0; }
.eng-name { font-size: 13px; font-weight: 600; }
.eng-desc { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.eng-tag {
  font-size: 10px; padding: 2px 8px; border-radius: 10px; font-weight: 500;
  background: var(--orange-soft); color: var(--orange); flex-shrink: 0;
}
.eng-tag.ok { background: var(--green-soft); color: var(--green); }

.switch-row { display: flex; align-items: center; justify-content: space-between; }

.engine-status { padding: 10px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg); margin-bottom: 16px; }
.es-row { display: flex; align-items: center; gap: 8px; }
.es-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.es-dot.ok { background: var(--green); }
.es-dot.err { background: var(--red); }
.es-text { font-size: 12px; color: var(--text-secondary); flex: 1; }

.actions { display: flex; align-items: center; gap: 12px; margin-top: 28px; padding-bottom: 40px; }
.save-hint { font-size: 12px; color: var(--text-tertiary); margin-left: 8px; }
</style>
