<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { searchSimilarCases, getAIEngines } from '@/api/ai'
import { STAGE_LABEL_MAP, STAGE_COLOR_MAP } from '@/utils/constants'

const activeDemo = ref('similar')

const demoTitle = {
  similar: '🔍 类案推送',
  evidence: '🩺 证据链体检',
  style: '✍️ 文书风格克隆',
}

// ── 类案推送 ──
const simQuery = ref('')
const simLoading = ref(false)
const simResults = ref([])
const simSearched = ref(false)

async function doSimilarSearch() {
  const q = simQuery.value.trim()
  if (!q) return
  simLoading.value = true
  simSearched.value = true
  try {
    const res = await searchSimilarCases(q, 5)
    simResults.value = res.data.results || []
    if (simResults.value.length === 0) {
      ElMessage.info('未找到相似案件，尝试更换关键词')
    }
  } catch {
    simResults.value = []
    ElMessage.error('搜索失败，请确认 AI 引擎已启动')
  } finally {
    simLoading.value = false
  }
}

// ── 引擎状态 ──
const engineInfo = ref({ engines: [], current: '', model: '', healthy: false })

async function checkEngine() {
  try {
    const res = await getAIEngines()
    engineInfo.value = res.data
  } catch {
    engineInfo.value = { engines: [], current: 'unknown', model: 'unknown', healthy: false }
  }
}

const overdueClass = (status) => {
  if (status === 'overdue') return 'rd'
  if (status === 'due_soon') return 'og'
  return 'gr'
}

// ── 证据链体检 ──
const evidenceItems = [
  { name: '借款合同/借条', required: true, have: true },
  { name: '转账凭证/银行流水', required: true, have: true },
  { name: '聊天记录/通话录音', required: true, have: false },
  { name: '身份证/主体信息', required: true, have: true },
  { name: '起诉状', required: true, have: true },
  { name: '送达地址确认书', required: false, have: false },
  { name: '财产保全申请书', required: false, have: false },
  { name: '授权委托书', required: true, have: true },
]
const completeness = Math.round(evidenceItems.filter(e => e.have).length / evidenceItems.length * 100)

// ── 文书风格克隆 ──
const styleSamples = [
  { lawyer: '王浩', content: '尊敬的审判长、审判员：\n\n受原告委托，现就本案发表如下代理意见：\n\n一、本案基本事实清楚，证据确凿\n……', type: '代理词' },
  { lawyer: '赵敏', content: '尊敬的审判长、审判员：\n\n本代理人认为，原告诉请具有充分的事实和法律依据：\n\n一、关于合同效力\n……', type: '代理词' },
]
const showStyleDialog = ref(false)
const selectedStyle = ref(null)
const generatedText = ref('')

function generateStyle(lawyer) {
  selectedStyle.value = lawyer
  generatedText.value = lawyer.content
  showStyleDialog.value = true
}

onMounted(checkEngine)
</script>

<template>
  <div>
    <div class="header">
      <h1>AI 智能能力</h1>
      <p>三个核心 AI 功能 · 智能收件已融入「拖拽上传」和「新建案件」</p>
    </div>

    <!-- 引擎状态条 -->
    <div :class="['engine-bar', engineInfo.healthy ? 'ok' : 'err']">
      <span :class="['status-dot', engineInfo.healthy ? 'ok' : 'err']"></span>
      <span class="engine-label">AI 引擎：{{ engineInfo.current }} / {{ engineInfo.model }}</span>
      <span class="engine-state">{{ engineInfo.healthy ? '● 在线' : '○ 离线' }}</span>
    </div>

    <!-- 三个能力卡片 -->
    <div class="cards">
      <div class="card" :class="{ active: activeDemo === 'similar' }" @click="activeDemo = 'similar'">
        <div class="card-icon">🔍</div>
        <h3>类案推送</h3>
        <p>检索所内历史案件和公开裁判文书的相似案例，辅助办案决策</p>
      </div>
      <div class="card" :class="{ active: activeDemo === 'evidence' }" @click="activeDemo = 'evidence'">
        <div class="card-icon">🩺</div>
        <h3>证据链体检</h3>
        <p>自动扫描案件所需证据，在立案前提醒补全关键材料</p>
      </div>
      <div class="card" :class="{ active: activeDemo === 'style' }" @click="activeDemo = 'style'">
        <div class="card-icon">✍️</div>
        <h3>文书风格克隆</h3>
        <p>学习律师写作风格和行文习惯，生成个性化代理词/答辩状草稿</p>
      </div>
    </div>

    <!-- Demo 区域 -->
    <div class="demo-panel">
      <div class="demo-title">{{ demoTitle[activeDemo] }}</div>

      <!-- 类案推送 -->
      <div v-if="activeDemo === 'similar'" class="demo-body">
        <div class="sim-search">
          <el-input
            v-model="simQuery"
            placeholder="输入案由或案情描述，如「民间借贷」「交通事故赔偿」…"
            :prefix-icon="Search"
            clearable
            size="large"
            @keyup.enter="doSimilarSearch"
          >
            <template #append>
              <el-button :loading="simLoading" @click="doSimilarSearch" type="primary">搜索类案</el-button>
            </template>
          </el-input>
        </div>

        <!-- 加载中 -->
        <div v-if="simLoading" class="sim-loading">
          <el-icon class="is-loading" :size="20"><Loading /></el-icon>
          <span>AI 正在检索相似案件…</span>
        </div>

        <!-- 结果列表 (后端真实数据) -->
        <div v-else-if="simSearched && simResults.length > 0" class="sim-results">
          <div v-for="sc in simResults" :key="sc.id" class="sim-item">
            <span class="score-badge" :style="{ opacity: 0.4 + (sc.score || 0) * 0.6 }">
              {{ sc.score_pct }}%
            </span>
            <div class="sim-info">
              <div class="sim-name">
                {{ sc.case_name }}
                <el-tag size="small" effect="plain" style="margin-left:6px">{{ sc.match_type === 'semantic' ? '语义' : '关键词' }}</el-tag>
              </div>
              <div class="sim-meta">
                <span v-if="sc.case_number" class="sim-num">{{ sc.case_number }}</span>
                <span>{{ sc.plaintiff }} → {{ sc.defendant }}</span>
                <span class="sim-cause">{{ sc.cause_of_action }}</span>
              </div>
              <div class="sim-extra">
                <el-tag size="small" effect="plain">{{ STAGE_LABEL_MAP[sc.stage] || sc.stage }}</el-tag>
                <span v-if="sc.lawyer_name">{{ sc.lawyer_name }}律师承办</span>
              </div>
            </div>
            <router-link :to="`/case/${sc.id}`" class="sim-link">查看</router-link>
          </div>
        </div>

        <!-- 空结果 -->
        <div v-else-if="simSearched" class="sim-empty">
          <p>未找到相似案件</p>
          <p class="sub">尝试更通用的关键词，如「合同纠纷」「侵权」</p>
        </div>

        <!-- 初始提示 -->
        <div v-else class="sim-hint">
          <p>在上方输入案由或案情关键词，AI 将从全所历史案件中检索最相似的案例</p>
          <div class="hint-tags">
            <el-tag v-for="kw in ['民间借贷','合同纠纷','交通事故','劳动争议','股权转让']" :key="kw" @click="simQuery = kw; doSimilarSearch()" style="cursor:pointer;margin:4px">
              {{ kw }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 证据链体检 Demo -->
      <div v-if="activeDemo === 'evidence'" class="demo-body">
        <div class="completeness-bar">
          <span class="comp-label">证据完整度</span>
          <div class="comp-track">
            <div class="comp-fill" :style="{ width: completeness + '%' }"></div>
          </div>
          <span class="comp-val">{{ completeness }}%</span>
        </div>
        <div class="comp-detail">
          <span>必需证据 {{ Math.round(evidenceItems.filter(e => e.required && e.have).length / evidenceItems.filter(e => e.required).length * 100) }}% 已齐备</span>
        </div>
        <el-divider />
        <div v-for="item in evidenceItems" :key="item.name" class="evidence-item">
          <span :class="['ei-dot', item.have ? 'ok' : 'miss']"></span>
          <span class="ei-name">{{ item.name }}</span>
          <el-tag v-if="item.required" size="small" type="danger" effect="plain">必需</el-tag>
          <el-tag v-else size="small" type="info" effect="plain">可选</el-tag>
          <span v-if="item.have" class="ei-status ok">✓ 已有</span>
          <span v-else class="ei-status miss">✗ 缺失</span>
        </div>
        <el-alert
          v-if="evidenceItems.filter(e => e.required && !e.have).length > 0"
          type="warning" :closable="false" style="margin-top:12px" show-icon
        >
          <template #title>
            立案前建议补全：
            <strong>{{ evidenceItems.filter(e => e.required && !e.have).map(e => e.name).join('、') }}</strong>
          </template>
        </el-alert>
      </div>

      <!-- 文书风格克隆 Demo -->
      <div v-if="activeDemo === 'style'" class="demo-body">
        <p class="demo-desc">选择律师写作风格，AI 将模仿其行文习惯生成文书初稿：</p>
        <div v-for="s in styleSamples" :key="s.lawyer" class="style-card" @click="generateStyle(s)">
          <span class="style-av">{{ s.lawyer[0] }}</span>
          <div class="style-info">
            <div class="style-name">{{ s.lawyer }}律师</div>
            <div class="style-type">{{ s.type }}风格模型 · 已学习 47 份文书</div>
          </div>
          <el-button size="small" type="primary">生成草稿</el-button>
        </div>
        <div class="note">以上为 AI 生成草稿，律师需逐条审核修改后方可使用</div>
      </div>
    </div>

    <!-- 文书生成弹窗 -->
    <el-dialog v-model="showStyleDialog" title="AI 生成文书草稿" width="640px">
      <div v-if="selectedStyle" class="generated">
        <div class="gen-label">{{ selectedStyle.lawyer }}律师 · {{ selectedStyle.type }}风格</div>
        <pre class="gen-text">{{ generatedText }}</pre>
      </div>
      <template #footer>
        <el-button @click="showStyleDialog = false">关闭</el-button>
        <el-button type="primary" @click="ElMessage.success('已复制到剪贴板（模拟）'); showStyleDialog = false">
          复制并审核
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.header { margin-bottom: 20px; }
.header h1 { font-size: 26px; font-weight: 700; letter-spacing: -0.03em; }
.header p { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

/* Engines Status Bar */
.engine-bar {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 16px; border-radius: var(--radius-sm); margin-bottom: 20px;
  font-size: 12px; border: 1px solid var(--border); background: var(--surface);
}
.engine-bar.ok { border-color: var(--green); }
.engine-bar.err { border-color: var(--red); }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.ok { background: var(--green); }
.status-dot.err { background: var(--red); }
.engine-label { color: var(--text-secondary); }
.engine-state { margin-left: auto; font-weight: 500; }
.engine-bar.ok .engine-state { color: var(--green); }
.engine-bar.err .engine-state { color: var(--red); }

.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 24px; }
.card {
  padding: 24px; border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); cursor: pointer; transition: all 0.2s;
}
.card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); transform: translateY(-2px); }
html.dark .card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.35); }
.card.active { border-color: var(--accent); background: var(--accent-soft); }
.card-icon { font-size: 28px; margin-bottom: 8px; }
.card h3 { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.card p { font-size: 12px; color: var(--text-secondary); line-height: 1.6; }

.demo-panel { border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); overflow: hidden; }
.demo-title { padding: 14px 20px; font-size: 14px; font-weight: 600; border-bottom: 1px solid var(--border); background: var(--bg); }
.demo-body { padding: 20px; }

/* Similar Case Search */
.sim-search { margin-bottom: 20px; }
.sim-loading { text-align: center; padding: 40px 0; color: var(--text-tertiary); display: flex; align-items: center; justify-content: center; gap: 8px; }
.sim-hint { text-align: center; padding: 30px 0; color: var(--text-secondary); }
.sim-hint p { font-size: 14px; margin-bottom: 16px; }
.sim-empty { text-align: center; padding: 40px 0; color: var(--text-tertiary); }
.sim-empty .sub { font-size: 12px; margin-top: 4px; }

.sim-results { display: flex; flex-direction: column; gap: 10px; }
.sim-item {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 16px 18px; border: 1px solid var(--border);
  border-radius: var(--radius-sm); transition: all 0.15s;
}
.sim-item:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
html.dark .sim-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.25); }
.score-badge {
  background: var(--accent); color: #fff; border-radius: 6px;
  padding: 4px 10px; font-size: 12px; font-weight: 700; flex-shrink: 0;
  min-width: 52px; text-align: center;
}
.sim-info { flex: 1; min-width: 0; }
.sim-name { font-size: 14px; font-weight: 600; }
.sim-meta { font-size: 12px; color: var(--text-secondary); margin-top: 4px; display: flex; gap: 12px; flex-wrap: wrap; }
.sim-num { font-family: "SF Mono","Consolas",monospace; color: var(--text-tertiary); }
.sim-cause { color: var(--accent); }
.sim-extra { font-size: 12px; color: var(--text-tertiary); margin-top: 6px; display: flex; align-items: center; gap: 8px; }
.sim-link { font-size: 12px; color: var(--accent); text-decoration: none; flex-shrink: 0; align-self: center; }
.sim-link:hover { text-decoration: underline; }

/* Evidence */
.completeness-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.comp-label { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }
.comp-track { flex: 1; height: 8px; border-radius: 4px; background: var(--border); overflow: hidden; }
.comp-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, var(--red), var(--orange) 40%, var(--green) 80%); transition: width 0.6s; }
.comp-val { font-size: 22px; font-weight: 700; }
.comp-detail { font-size: 11px; color: var(--text-tertiary); }
.evidence-item { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.evidence-item:last-child { border-bottom: none; }
.ei-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ei-dot.ok { background: var(--green); }
.ei-dot.miss { background: var(--red); }
.ei-name { flex: 1; }
.ei-status { font-size: 11px; font-weight: 500; }
.ei-status.ok { color: var(--green); }
.ei-status.miss { color: var(--red); }

/* Style Clone */
.demo-desc { font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; }
.style-card {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px; border: 1px solid var(--border);
  border-radius: var(--radius-sm); margin-bottom: 8px;
  cursor: pointer; transition: all 0.15s;
}
.style-card:hover { border-color: var(--accent); background: var(--accent-soft); }
.style-av { width: 36px; height: 36px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; flex-shrink: 0; }
.style-info { flex: 1; }
.style-name { font-size: 14px; font-weight: 600; }
.style-type { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.note { margin-top: 16px; padding: 10px 14px; background: var(--orange-soft); border-radius: var(--radius-sm); font-size: 12px; color: var(--orange); }

.generated { padding: 8px 0; }
.gen-label { font-size: 12px; color: var(--text-tertiary); margin-bottom: 10px; padding: 6px 10px; background: var(--bg); border-radius: var(--radius-sm); display: inline-block; }
.gen-text { white-space: pre-wrap; font-family: "PingFang SC","Microsoft YaHei",sans-serif; font-size: 13px; line-height: 2; color: var(--text); padding: 16px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); max-height: 400px; overflow-y: auto; }
</style>
