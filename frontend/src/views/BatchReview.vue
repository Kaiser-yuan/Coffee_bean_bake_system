<template>
  <div class="review-page">
    <div class="page-header">
      <button class="btn btn-text" @click="$router.back()">← 返回</button>
      <h2 class="page-heading">批次复盘</h2>
      <span v-if="batch" class="text-sm text-secondary">
        {{ getBeanName }} · {{ batch.actualDate || batch.plannedDate }}
      </span>
    </div>

    <LoadingState v-if="loading" text="加载复盘数据…" />
    <ErrorState v-else-if="error" :retry="true" @retry="fetchReview" />

    <template v-else>
      <div class="review-grid">
        <!-- 左侧主内容区 -->
        <div class="review-main">
          <!-- 批次概览 -->
          <section class="review-section">
            <h3 class="section-title">批次概览</h3>
            <div class="overview-grid">
              <div class="ov-item">
                <span class="ov-label">投豆量</span>
                <span class="ov-val num">{{ batch?.beanWeightIn }}g</span>
              </div>
              <div class="ov-item">
                <span class="ov-label">出豆量</span>
                <span class="ov-val num">
                  {{ batch?.beanWeightOut ? batch.beanWeightOut + 'g' : '未录入' }}
                  <button v-if="!batch?.beanWeightOut && batch?.status === 'completed'" class="btn btn-xs btn-text" @click="showWeightOutInput = true">
                    补录
                  </button>
                </span>
              </div>
              <div class="ov-item">
                <span class="ov-label">失重率</span>
                <span class="ov-val num">{{ batch?.weightLossRate ? batch.weightLossRate.toFixed(1) + '%' : batch?.beanWeightOut ? '计算中...' : '需先录入出豆量' }}</span>
              </div>
              <div class="ov-item">
                <span class="ov-label">总时长</span>
                <span class="ov-val num">{{ formatTime(batch?.totalTime || 0) }}</span>
              </div>
              <div class="ov-item">
                <span class="ov-label">烘焙度</span>
                <span class="ov-val">{{ batch?.roastLevel || '-' }}</span>
              </div>
              <div class="ov-item">
                <span class="ov-label">评价数</span>
                <span class="ov-val num">{{ evaluationCount }}</span>
              </div>
            </div>
          </section>

          <!-- 个人初始复盘 -->
          <section class="review-section">
            <h3 class="section-title">个人初始复盘</h3>
            <p class="text-xs text-tertiary mb-sm">记录烘焙过程中的观察、调整和初步判断</p>
            <textarea
              v-model="review.personalReview"
              class="textarea"
              rows="5"
              placeholder="记录烘焙过程中的观察、调整和初步判断…"
            ></textarea>
            <div class="action-row">
              <button class="btn btn-primary" @click="savePersonal">
                {{ review.personalReviewAt ? '更新个人复盘' : '保存个人复盘' }}
              </button>
              <span v-if="review.personalReviewAt" class="text-xs text-tertiary">
                记录于 {{ review.personalReviewAt }}
              </span>
            </div>
          </section>

          <!-- 评价反馈摘要 -->
          <section class="review-section">
            <h3 class="section-title">评价反馈摘要</h3>
            <div v-if="evaluationSummary">
              <p class="summary-text">{{ evaluationSummary }}</p>
              <span class="text-xs text-tertiary">系统根据已有评价自动生成</span>
            </div>
            <EmptyState
              v-else
              icon="📝"
              title="暂无评价反馈"
              description="发起公开评价问卷后，系统将自动生成反馈摘要"
            />
            <div class="action-row" v-if="batch && batch.evaluationStatus === 'none'">
              <button class="btn btn-primary" @click="createQuestionnaire">
                发起公开评价问卷
              </button>
            </div>
            <div class="action-row" v-else-if="questionnaire">
              <span class="status-dot" :class="questionnaire.status === 'open' ? 'info' : 'neutral'"></span>
              {{ questionnaire.status === 'open' ? '问卷进行中' : '问卷已关闭' }}
              <span class="text-sm text-tertiary">{{ questionnaire.submissionCount }} 人提交</span>
              <button
                v-if="questionnaire.status === 'open'"
                class="btn btn-xs btn-secondary"
                @click="closeQuestionnaire"
              >
                关闭问卷
              </button>
            </div>
          </section>

          <!-- 综合复盘 -->
          <section class="review-section">
            <h3 class="section-title">综合复盘</h3>
            <p class="text-xs text-tertiary mb-sm">结合曲线数据和评价反馈，进行综合分析</p>
            <textarea
              v-model="review.comprehensiveReview"
              class="textarea"
              rows="5"
              placeholder="结合曲线数据和评价反馈，进行综合分析…"
            ></textarea>
            <div class="action-row">
              <button class="btn btn-primary" @click="saveComprehensive">
                {{ review.comprehensiveReviewAt ? '更新综合复盘' : '保存综合复盘' }}
              </button>
              <span v-if="review.comprehensiveReviewAt" class="text-xs text-tertiary">
                记录于 {{ review.comprehensiveReviewAt }}
              </span>
            </div>
          </section>
        </div>

        <!-- 右侧固定摘要栏 -->
        <aside class="review-sidebar">
          <div class="sidebar-inner">
            <!-- 下一锅调整建议 -->
            <section class="sidebar-section">
              <h3 class="sidebar-section-title">下一锅调整建议</h3>
              <textarea
                v-model="review.nextBatchSuggestions"
                class="textarea-sm"
                rows="3"
                placeholder="记录下一锅的操作调整建议…"
              ></textarea>
              <button class="btn btn-xs btn-secondary mt-sm" @click="saveNextSuggestions">保存建议</button>
            </section>

            <!-- 下一次烘焙提醒 -->
            <section class="sidebar-section">
              <h3 class="sidebar-section-title">下一次烘焙提醒</h3>
              <p class="text-xs text-tertiary mb-sm">最多三条，简短、明确、可执行</p>
              <div
                v-for="(rem, i) in review.reminders"
                :key="i"
                class="reminder-item"
              >
                <span class="reminder-priority">#{{ rem.priority }}</span>
                <input
                  v-model="rem.content"
                  type="text"
                  class="input flex-1"
                  :placeholder="`提醒 ${i + 1}`"
                />
              </div>
              <div class="sidebar-actions">
                <button class="btn btn-xs btn-secondary" @click="addReminder" v-if="review.reminders.length < 3">
                  + 添加提醒
                </button>
                <button class="btn btn-xs btn-primary" @click="saveReminders">保存提醒</button>
              </div>
            </section>

            <!-- 补录出豆量 -->
            <section class="sidebar-section" v-if="showWeightOutInput">
              <h3 class="sidebar-section-title">补录出豆量</h3>
              <div class="form-row-inline">
                <input v-model.number="weightOutValue" type="number" class="input" placeholder="出豆量 (g)" />
                <button class="btn btn-xs btn-primary" @click="saveWeightOut">确认</button>
              </div>
            </section>

            <!-- 创建下一次计划 -->
            <button
              v-if="batch"
              class="btn btn-primary btn-full"
              @click="createNextBatch"
            >
              创建下一次待烘计划
            </button>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  mockRoastingBatches, mockReviews, mockQuestionnaires,
  getGreenBeanByBatch,
  apiSaveReview, apiCreateQuestionnaire, apiCloseQuestionnaire,
  apiCreateRoastingBatch, apiUpdateWeightOut,
} from '../mock'
import type { BatchReview, RoastingBatch, Questionnaire } from '../types'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const batchId = route.params.batchId as string
const loading = ref(false)
const error = ref(false)
const batch = ref<RoastingBatch | null>(null)
const review = ref<BatchReview>({
  id: '',
  roastingBatchId: batchId,
  personalReview: '',
  nextBatchSuggestions: '',
  reminders: [],
})
const questionnaire = ref<Questionnaire | null>(null)
const evaluationCount = ref(0)
const evaluationSummary = ref('')
const showWeightOutInput = ref(false)
const weightOutValue = ref(0)

const getBeanName = ref('')

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

async function fetchReview() {
  loading.value = true
  error.value = false
  try {
    batch.value = mockRoastingBatches.find(b => b.id === batchId) || null

    if (batch.value) {
      getBeanName.value = getGreenBeanByBatch(batch.value)?.name || ''
    }

    // 问卷不依赖曲线或复盘存在
    const q = mockQuestionnaires.find(q => q.roastingBatchId === batchId)
    if (q) {
      questionnaire.value = q
      evaluationCount.value = q.submissionCount
      if (q.submissionCount > 0) {
        evaluationSummary.value = '综合 ' + q.submissionCount + ' 位评价者反馈：评价结果显示整体接受度较高，建议关注酸度控制和甜感发展。'
      }
    }

    const existing = mockReviews.find(r => r.roastingBatchId === batchId)
    if (existing) {
      review.value = { ...existing }
    }
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

async function savePersonal() {
  await apiSaveReview({
    roastingBatchId: batchId,
    personalReview: review.value.personalReview,
    personalReviewAt: new Date().toISOString().split('T')[0],
  })
  review.value.personalReviewAt = new Date().toISOString().split('T')[0]
}

async function saveComprehensive() {
  await apiSaveReview({
    roastingBatchId: batchId,
    comprehensiveReview: review.value.comprehensiveReview,
    comprehensiveReviewAt: new Date().toISOString().split('T')[0],
  })
  review.value.comprehensiveReviewAt = new Date().toISOString().split('T')[0]
}

async function saveNextSuggestions() {
  await apiSaveReview({
    roastingBatchId: batchId,
    nextBatchSuggestions: review.value.nextBatchSuggestions,
  })
}

async function saveReminders() {
  await apiSaveReview({
    roastingBatchId: batchId,
    reminders: review.value.reminders,
  })
}

async function saveWeightOut() {
  if (!batch.value || weightOutValue.value <= 0) return
  await apiUpdateWeightOut(batch.value.id, weightOutValue.value)
  batch.value.beanWeightOut = weightOutValue.value
  // Re-fetch to get computed weightLossRate
  const updated = mockRoastingBatches.find(b => b.id === batchId)
  if (updated) batch.value = updated
  showWeightOutInput.value = false
}

function addReminder() {
  if (review.value.reminders.length >= 3) return
  review.value.reminders.push({
    id: `rem_${Date.now()}`,
    batchReviewId: review.value.id,
    priority: (review.value.reminders.length + 1) as 1 | 2 | 3,
    content: '',
  })
}

async function createQuestionnaire() {
  if (!batch.value) return
  await apiCreateQuestionnaire(batch.value.id)
  await fetchReview()
}

async function closeQuestionnaire() {
  if (!questionnaire.value) return
  await apiCloseQuestionnaire(questionnaire.value.id)
  await fetchReview()
}

async function createNextBatch() {
  if (!batch.value) return
  await apiCreateRoastingBatch({
    purchaseBatchId: batch.value.purchaseBatchId,
    beanWeightIn: batch.value.beanWeightIn,
    targetDescription: review.value.nextBatchSuggestions,
  })
  router.push('/roasting')
}

onMounted(fetchReview)
</script>

<style scoped>
.review-page { max-width: 1200px; }

.page-header {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-bottom: var(--sp-6);
}

.page-heading { font-size: var(--fs-xl); font-weight: 600; }

/* 双列布局 */
.review-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--sp-6);
  align-items: start;
}

/* 左侧主内容 */
.review-main {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.review-section {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-6);
}

.section-title {
  font-size: var(--fs-md);
  font-weight: 600;
  margin-bottom: var(--sp-3);
  color: var(--text-primary);
}

/* 右侧固定摘要栏 */
.review-sidebar {
  position: sticky;
  top: var(--sp-6);
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.sidebar-section {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-4);
}

.sidebar-section-title {
  font-size: var(--fs-sm);
  font-weight: 600;
  margin-bottom: var(--sp-2);
}

/* Overview */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-3);
}

.ov-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ov-label { font-size: var(--fs-xs); color: var(--text-tertiary); }
.ov-val { font-size: var(--fs-base); font-weight: 600; font-family: var(--font-mono); }

/* Textarea */
.textarea {
  width: 100%;
  padding: var(--sp-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-family: var(--font-sans);
  color: var(--text-primary);
  background: var(--app-bg);
  resize: vertical;
  outline: none;
}

.textarea:focus { border-color: var(--primary); background: var(--surface); }

.textarea-sm {
  width: 100%;
  padding: var(--sp-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-family: var(--font-sans);
  color: var(--text-primary);
  background: var(--app-bg);
  resize: vertical;
  outline: none;
}

.textarea-sm:focus { border-color: var(--primary); }

.summary-text {
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
  color: var(--text-primary);
}

.action-row {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-top: var(--sp-3);
}

.sidebar-actions {
  display: flex;
  gap: var(--sp-2);
  margin-top: var(--sp-2);
}

/* Reminders */
.reminder-item {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
}

.reminder-priority {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--primary-subtle);
  color: var(--primary);
  font-weight: 600;
  font-size: var(--fs-xs);
  flex-shrink: 0;
}

.form-row-inline {
  display: flex;
  gap: var(--sp-1);
}

.mb-sm { margin-bottom: var(--sp-2); }
.mt-sm { margin-top: var(--sp-2); }

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

.btn-xs { height: 24px; padding: 0 var(--sp-2); font-size: var(--fs-xs); }

.btn-primary { background: var(--primary); color: #fff; border-color: var(--primary); }
.btn-primary:hover { background: var(--primary-hover); }
.btn-secondary { background: var(--surface); color: var(--text-primary); border-color: var(--border-default); }
.btn-secondary:hover { background: var(--app-bg); }
.btn-text { background: transparent; color: var(--text-secondary); border-color: transparent; }
.btn-text:hover { color: var(--text-primary); }

.btn-full {
  width: 100%;
  justify-content: center;
}

/* Input */
.input {
  height: var(--input-height);
  padding: 0 var(--sp-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-family: var(--font-sans);
  background: var(--surface);
  color: var(--text-primary);
  outline: none;
}

.input:focus { border-color: var(--primary); }

.flex-1 { flex: 1; }
</style>
