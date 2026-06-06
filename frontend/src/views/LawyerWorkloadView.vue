<script setup>
import { ref, onMounted } from 'vue'
import { getLawyers, getLawyerCases } from '@/api/lawyers'
import { STAGE_LABEL_MAP } from '@/utils/constants'
import { useDeferredLoading } from '@/composables/useDeferredLoading'

const lawyers = ref([])
const { showLoading, run } = useDeferredLoading()

onMounted(() => run(async () => {
  const res = await getLawyers()
  const withCases = await Promise.all(
    res.data.map(async (l) => {
      const cr = await getLawyerCases(l.id)
      return { ...l, cases: cr.data }
    })
  )
  lawyers.value = withCases
}))
</script>

<template>
  <div v-loading="showLoading">
    <div class="header">
      <h1>律师工作负载</h1>
    </div>
    <div class="grid">
      <div v-for="l in lawyers" :key="l.id" class="card">
        <div class="card-hd">
          <span class="av">{{ l.initials }}</span>
          <div>
            <div class="name">{{ l.name }}</div>
            <div class="role">{{ l.role }}</div>
          </div>
          <span class="count">{{ l.case_count }} 件进行中</span>
        </div>
        <div v-if="l.cases && l.cases.length > 0" class="card-bd">
          <div v-for="c in l.cases" :key="c.id" class="case-item">
            <span :class="['dot', c.overdue_status === 'overdue' ? 'rd' : c.overdue_status === 'due_soon' ? 'og' : '']"></span>
            <span class="cname">{{ c.case_name }}</span>
            <span class="cstage">{{ STAGE_LABEL_MAP[c.stage] }}</span>
          </div>
        </div>
        <div v-else class="card-empty">暂无进行中案件</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header { margin-bottom: 24px; }
.header h1 { font-size: 22px; font-weight: 700; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }
.card-hd { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.av {
  width: 36px; height: 36px; border-radius: 50%; background: var(--accent-soft);
  color: var(--accent); display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700;
}
.name { font-size: 15px; font-weight: 600; }
.role { font-size: 12px; color: var(--text-tertiary); }
.count { margin-left: auto; font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.card-bd { display: flex; flex-direction: column; gap: 6px; }
.case-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); flex-shrink: 0; }
.dot.rd { background: var(--red); }
.dot.og { background: var(--orange); }
.cname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cstage { color: var(--text-tertiary); font-size: 11px; white-space: nowrap; }
.card-empty { text-align: center; color: var(--text-tertiary); padding: 20px 0; font-size: 13px; }
</style>
