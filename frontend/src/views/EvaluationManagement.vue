<template>
  <div class="eval-page">
    <div class="page-header">
      <h2 class="page-heading">评价管理</h2>
    </div>

    <LoadingState v-if="loading" text="加载问卷数据…" />
    <ErrorState v-else-if="error" :retry="true" @retry="fetchData" />

    <template v-else>
      <!-- 统计摘要 -->
      <div class="stats-bar">
        <div class="stat-item">
          <span class="stat-label">进行中</span>
          <span class="stat-value num">{{ openCount }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-label">已结束</span>
          <span class="stat-value num">{{ closedCount }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-label">总评价数</span>
          <span class="stat-value num">{{ totalSubmissions }}</span>
        </div>
      </div>

      <table class="eval-table" v-if="questionnaires.length">
        <thead>
          <tr>
            <th>关联批次</th>
            <th>生豆</th>
            <th>烘焙时间</th>
            <th>状态</th>
            <th class="num">提交数</th>
            <th>创建时间</th>
            <th class="col-action">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="q in questionnaires" :key="q.id" class="clickable" @click="goToDetail(q.id)">
            <td>{{ getBatchIdLabel(q.roastingBatchId) }}</td>
            <td>{{ getBeanNameForQ(q.roastingBatchId) }}</td>
            <td class="num">{{ getBatchDate(q.roastingBatchId) }}</td>
            <td>
              <span class="status-dot" :class="q.status === 'open' ? 'info' : 'neutral'"></span>
              {{ q.status === 'open' ? '进行中' : q.status === 'closed' ? '已关闭' : '已过期' }}
            </td>
            <td class="num">{{ q.submissionCount }}</td>
            <td class="num">{{ q.createdAt }}</td>
            <td @click.stop>
              <div class="action-group">
                <button
                  class="btn-icon"
                  @click="copyLink(q)"
                  title="复制链接"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                  </svg>
                </button>
                <button
                  v-if="q.status === 'open'"
                  class="btn-icon btn-icon-danger"
                  @click="closeQ(q.id)"
                  title="关闭问卷"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-else icon="📋" title="暂无问卷" description="问卷只能从烘焙批次发起" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  mockQuestionnaires, mockRoastingBatches,
  getGreenBeanByBatch,
  apiCloseQuestionnaire,
} from '../mock'
import type { Questionnaire } from '../types'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'

const router = useRouter()
const loading = ref(false)
const error = ref(false)
const questionnaires = ref<Questionnaire[]>([])

const openCount = computed(() => questionnaires.value.filter(q => q.status === 'open').length)
const closedCount = computed(() => questionnaires.value.filter(q => q.status === 'closed').length)
const totalSubmissions = computed(() => questionnaires.value.reduce((s, q) => s + q.submissionCount, 0))

function getBeanNameForQ(batchId: string) {
  const b = mockRoastingBatches.find(b => b.id === batchId)
  if (!b) return '-'
  return getGreenBeanByBatch(b)?.name || '-'
}

function getBatchIdLabel(batchId: string) {
  return batchId.replace('rb_', 'RB-')
}

function getBatchDate(batchId: string) {
  const b = mockRoastingBatches.find(b => b.id === batchId)
  return b?.actualDate || b?.plannedDate || '-'
}

function goToDetail(qId: string) { router.push(`/evaluations/${qId}`) }

async function closeQ(id: string) {
  await apiCloseQuestionnaire(id)
  await fetchData()
}

function copyLink(q: Questionnaire) {
  const url = `${window.location.origin}/eval/${q.shareCode}`
  navigator.clipboard.writeText(url).then(() => {
    alert('已复制问卷链接')
  })
}

async function fetchData() {
  loading.value = true
  error.value = false
  try {
    questionnaires.value = [...mockQuestionnaires]
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.eval-page { max-width: 1200px; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-6);
}

.page-heading { font-size: var(--fs-xl); font-weight: 600; }

/* Stats bar */
.stats-bar {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-3) var(--sp-6);
  display: flex;
  align-items: center;
  margin-bottom: var(--sp-6);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label { font-size: var(--fs-xs); color: var(--text-tertiary); }
.stat-value { font-size: var(--fs-lg); font-weight: 600; font-family: var(--font-mono); color: var(--text-primary); }

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--border-default);
  margin: 0 var(--sp-6);
}

/* Table */
.eval-table {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  border-collapse: collapse;
  font-size: var(--fs-sm);
}

.eval-table th {
  background: var(--surface-subtle);
  padding: var(--sp-2) var(--sp-3);
  text-align: left;
  font-weight: 500;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-default);
}

.eval-table td {
  padding: var(--sp-2) var(--sp-3);
  border-bottom: 1px solid var(--border-default);
  height: var(--table-row-height);
}

.col-action { width: 80px; }

.clickable { cursor: pointer; }
.clickable:hover { background: var(--surface-selected); }

.action-group {
  display: flex;
  gap: 4px;
}

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
.btn-icon-danger:hover { color: var(--danger); border-color: var(--danger); }
</style>
