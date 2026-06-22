<template>
  <div class="eval-detail">
    <div class="page-header">
      <button class="btn btn-text" @click="$router.back()">← 返回</button>
      <h2 class="page-heading">评价详情</h2>
      <span class="text-sm text-secondary">
        {{ getBeanNameForDetail }} · {{ getBatchDate }}
      </span>
    </div>

    <LoadingState v-if="loading" text="加载评价数据…" />
    <ErrorState v-else-if="error" :retry="true" @retry="fetchData" />

    <template v-else-if="questionnaire">
      <!-- 问卷状态与操作 -->
      <section class="info-bar">
        <div class="info-group">
          <span class="info-label">状态</span>
          <span class="status-dot" :class="questionnaire.status === 'open' ? 'info' : 'neutral'"></span>
          {{ questionnaire.status === 'open' ? '进行中' : '已关闭' }}
        </div>
        <div class="info-group">
          <span class="info-label">提交人数</span>
          <span class="num font-medium">{{ questionnaire.submissionCount }}</span>
        </div>
        <div class="info-group">
          <span class="info-label">分享链接</span>
          <code class="share-url">{{ shareUrl }}</code>
          <button class="btn-icon" @click="copyUrl" title="复制链接">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
        </div>
        <div class="info-group" v-if="questionnaire.status === 'open'">
          <button class="btn btn-danger btn-sm" @click="closeQ">关闭问卷</button>
        </div>
      </section>

      <!-- 各维度平均分 -->
      <section class="scores-panel">
        <h3 class="section-title">各维度平均分</h3>
        <div class="scores-grid">
          <div v-for="dim in computedDimensions" :key="dim.key" class="score-item">
            <div class="score-bar-label">
              <span>
                {{ dim.label }}
                <span v-if="dim.label === '酸感' || dim.label === '苦感'" class="text-xs text-tertiary">（强度）</span>
              </span>
              <span class="num font-medium">
                {{ dim.average > 0 ? dim.average.toFixed(1) : '-' }}
                <span class="text-xs text-tertiary">/5</span>
                <span class="text-xs text-tertiary ml-xs">({{ dim.validCount }} 人)</span>
              </span>
            </div>
            <div class="score-bar-track">
              <div
                class="score-bar-fill"
                :style="{ width: (dim.average / 5 * 100) + '%', background: dim.color }"
              ></div>
            </div>
          </div>
        </div>
      </section>

      <!-- 高频风味 -->
      <section class="flavor-panel">
        <h3 class="section-title">高频风味描述</h3>
        <div class="flavor-tags">
          <span v-for="f in topFlavors" :key="f.name" class="flavor-tag" :style="{ opacity: f.opacity }">
            {{ f.name }} ({{ f.count }})
          </span>
          <span v-if="!topFlavors.length" class="text-sm text-tertiary">暂无风味数据</span>
        </div>
      </section>

      <!-- 评价明细列表 -->
      <section>
        <h3 class="section-title">评价明细</h3>
        <div class="detail-table-wrapper" v-if="evaluations.length">
          <table class="detail-table">
            <thead>
              <tr>
                <th>评价者</th>
                <th>冲煮方式</th>
                <th>干香</th>
                <th>湿香</th>
                <th>酸感<span class="text-xs text-tertiary">(强度)</span></th>
                <th>甜感</th>
                <th>苦感<span class="text-xs text-tertiary">(强度)</span></th>
                <th>回味</th>
                <th>综合</th>
                <th>养豆</th>
                <th>风味</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in evaluations" :key="e.id">
                <td>{{ e.evaluatorName }}</td>
                <td>
                  <span class="text-xs">{{ e.brewMethod }}</span>
                  <span class="text-xs text-tertiary"> · {{ e.drinkTemperature }} · {{ e.drinkForm }}</span>
                </td>
                <td class="num">{{ e.dryFragrance > 0 ? e.dryFragrance : '-' }}</td>
                <td class="num">{{ e.wetAroma > 0 ? e.wetAroma : '-' }}</td>
                <td class="num">{{ e.acidity > 0 ? e.acidity : '-' }}</td>
                <td class="num">{{ e.sweetness > 0 ? e.sweetness : '-' }}</td>
                <td class="num">{{ e.bitterness > 0 ? e.bitterness : '-' }}</td>
                <td class="num">{{ e.aftertaste > 0 ? e.aftertaste : '-' }}</td>
                <td class="num font-semibold">{{ e.overallPreference }}</td>
                <td class="num">{{ e.beanAgeDays || '-' }}天</td>
                <td class="col-flavor">{{ e.flavorNotes.join('、') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else icon="📝" title="暂无评价记录" />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  fetchQuestionnaire,
  closeQuestionnaire,
} from '../services/questionnaireService'
import { fetchEvaluations } from '../services/evaluationService'
import type { Questionnaire, CuppingEvaluation } from '../types'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'

const route = useRoute()
const questionnaireId = route.params.questionnaireId as string

const loading = ref(false)
const error = ref(false)
const questionnaire = ref<Questionnaire | null>(null)
const evaluations = ref<CuppingEvaluation[]>([])

const dimensionLabels: Record<string, string> = {
  dryFragrance: '干香',
  wetAroma: '湿香',
  acidity: '酸感',
  sweetness: '甜感',
  bitterness: '苦感',
  aftertaste: '回味',
  overallPreference: '综合喜好',
}

const dimensionColors: Record<string, string> = {
  dryFragrance: '#e5a029',
  wetAroma: '#20a184',
  acidity: '#3478d4',
  sweetness: '#df5b45',
  bitterness: '#8b5cc7',
  aftertaste: '#1f9d68',
  overallPreference: '#2f6bff',
}

const dimKeys = ['dryFragrance', 'wetAroma', 'acidity', 'sweetness', 'bitterness', 'aftertaste', 'overallPreference']

const computedDimensions = computed(() => {
  return dimKeys.map(key => {
    const vals = evaluations.value
      .map((e: any) => e[key] as number)
      .filter(v => v > 0) // exclude "not evaluated" (0)
    const avg = vals.length > 0 ? vals.reduce((s, v) => s + v, 0) / vals.length : 0
    return {
      key,
      label: dimensionLabels[key] || key,
      color: dimensionColors[key] || '#718096',
      average: avg,
      validCount: vals.length,
    }
  })
})

const shareUrl = computed(() => {
  const base = window.location.origin + (window.location.pathname || '')
  return `${base}#/eval/${questionnaire.value?.shareCode || ''}`
})

const getBeanNameForDetail = computed(() => {
  if (!questionnaire.value) return '-'
  return questionnaire.value.roastingBatchId.replace('rb_', 'RB-')
})

const getBatchDate = computed(() => {
  if (!questionnaire.value) return '-'
  return questionnaire.value.createdAt || '-'
})

const topFlavors = computed(() => {
  const map = new Map<string, number>()
  evaluations.value.forEach(e => {
    e.flavorNotes.forEach(f => {
      map.set(f, (map.get(f) || 0) + 1)
    })
  })
  const sorted = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8)
  const max = sorted[0]?.[1] || 1
  return sorted.map(([name, count]) => ({ name, count, opacity: 0.5 + (count / max) * 0.5 }))
})

function copyUrl() {
  navigator.clipboard.writeText(shareUrl.value)
  alert('已复制链接')
}

async function closeQ() {
  if (questionnaire.value) {
    await closeQuestionnaire(questionnaire.value.id)
    await fetchData()
  }
}

async function fetchData() {
  loading.value = true
  error.value = false
  try {
    const [q, evals] = await Promise.all([
      fetchQuestionnaire(questionnaireId),
      fetchEvaluations(questionnaireId),
    ])
    questionnaire.value = q
    evaluations.value = evals
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.eval-detail { max-width: 1200px; }

.page-header {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-bottom: var(--sp-6);
}

.page-heading { font-size: var(--fs-xl); font-weight: 600; }

/* Info bar */
.info-bar {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-4);
  display: flex;
  align-items: center;
  gap: var(--sp-6);
  margin-bottom: var(--sp-4);
  flex-wrap: wrap;
}

.info-group {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.info-label { font-size: var(--fs-xs); color: var(--text-tertiary); }

.share-url {
  font-size: var(--fs-xs);
  background: var(--app-bg);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}

/* Scores panel */
.scores-panel {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-6);
  margin-bottom: var(--sp-4);
}

.section-title {
  font-size: var(--fs-md);
  font-weight: 600;
  margin-bottom: var(--sp-3);
}

.scores-grid {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.score-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.score-bar-label {
  display: flex;
  justify-content: space-between;
  font-size: var(--fs-sm);
}

.score-bar-track {
  height: 8px;
  background: var(--app-bg);
  border-radius: 4px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.ml-xs { margin-left: var(--sp-1); }

/* Flavor tags */
.flavor-panel {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-6);
  margin-bottom: var(--sp-4);
}

.flavor-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.flavor-tag {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: var(--fs-sm);
  background: var(--primary-subtle);
  color: var(--primary);
}

/* Detail table */
.detail-table-wrapper {
  overflow-x: auto;
}

.detail-table {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  border-collapse: collapse;
  font-size: var(--fs-sm);
  min-width: 900px;
}

.detail-table th {
  background: var(--surface-subtle);
  padding: var(--sp-2) var(--sp-2);
  text-align: left;
  font-weight: 500;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  border-bottom: 1px solid var(--border-default);
}

.detail-table td {
  padding: var(--sp-2);
  border-bottom: 1px solid var(--border-default);
  height: var(--table-row-height);
}

.col-flavor { min-width: 120px; }

/* Buttons */
.btn {
  height: var(--btn-height);
  padding: 0 var(--sp-4);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  font-family: var(--font-sans);
}

.btn-sm { height: 28px; padding: 0 var(--sp-3); }

.btn-danger {
  background: var(--danger);
  color: #fff;
  border-color: var(--danger);
}
.btn-danger:hover { opacity: 0.9; }

.btn-text { background: transparent; color: var(--text-secondary); border-color: transparent; }
.btn-text:hover { color: var(--text-primary); }

.btn-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text-secondary);
  cursor: pointer;
}

.btn-icon:hover { background: var(--app-bg); }
</style>
