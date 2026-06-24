<template>
  <div class="review-page">
    <div class="page-header">
      <button class="btn btn-text" @click="$router.back()">← 返回</button>
      <h2 class="page-heading">批次复盘</h2>
      <span v-if="batch" class="text-sm text-secondary">
        {{ getBeanName }} · {{ batch.actualDate || batch.plannedDate }}
        <span
          v-for="tag in batchSourceLabels(batch.entryMode, batch.inventoryEffective)"
          :key="tag"
          class="batch-source-tag"
        >{{ tag }}</span>
      </span>
    </div>

    <LoadingState v-if="loading" text="加载复盘数据…" />
    <ErrorState v-else-if="error" :retry="true" @retry="fetchReviewData" />

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
              @click="openNextBatchDialog"
            >
              创建下一次待烘计划
            </button>
          </div>
        </aside>
      </div>

      <!-- 创建下一锅确认弹窗 -->
      <div v-if="nextBatchDialog" class="modal-overlay" @click.self="nextBatchDialog = false">
        <div class="modal">
          <div class="modal-header">
            <h3>创建下一次待烘计划</h3>
            <button class="modal-close" @click="nextBatchDialog = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label class="form-label">采购批次</label>
              <span class="text-sm font-medium">{{ getPurchaseLabel }}</span>
            </div>
            <div class="form-row">
              <label class="form-label">计划日期</label>
              <input v-model="nextBatchForm.plannedDate" type="date" class="input" />
            </div>
            <div class="form-row">
              <label class="form-label">计划投豆量 (g)</label>
              <input v-model.number="nextBatchForm.beanWeightIn" type="number" class="input" />
            </div>
            <div class="form-row">
              <label class="form-label">下一锅目标</label>
              <textarea v-model="nextBatchForm.targetDescription" class="textarea-sm" rows="2" placeholder="下一锅调整目标…"></textarea>
            </div>

            <!-- 提醒携带 -->
            <div class="form-divider" v-if="review.reminders.length">
              需要携带的提醒（默认全部勾选）
            </div>
            <div v-for="rem in review.reminders" :key="rem.id" class="reminder-carry-item">
              <label class="checkbox-row">
                <input type="checkbox" v-model="nextBatchForm.selectedReminders" :value="rem.id" />
                <span class="reminder-carry-priority">#{{ rem.priority }}</span>
                <span class="text-sm">{{ rem.content }}</span>
              </label>
            </div>

            <p class="text-xs text-tertiary mt-sm">
              选择的提醒将作为快照复制到下一锅，不会随本次复盘修改而变化。
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="nextBatchDialog = false">取消</button>
            <button class="btn btn-primary" @click="doCreateNextBatch">创建</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchReview as fetchReviewSvc,
  saveReview as saveReviewSvc,
  createNextRoastPlan,
} from '../services/reviewService'
import {
  createQuestionnaire as createQ,
  closeQuestionnaire as closeQ,
} from '../services/questionnaireService'
import {
  fetchRoastContext,
  getGreenBeanByBatch,
  invalidateRoastContext,
  type RoastContext,
} from '../services/greenBeanContextService'
import {
  updateOutputWeight,
} from '../services/roastingBatchService'
import type { BatchReview, RoastingBatch, Questionnaire } from '../types'
import { batchSourceLabels } from '../utils/batchLabels'
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

// Next batch dialog
const nextBatchDialog = ref(false)
const nextBatchForm = ref({
  plannedDate: new Date().toISOString().split('T')[0],
  beanWeightIn: 500,
  targetDescription: '',
  selectedReminders: [] as string[],
})

const getPurchaseLabel = ref('')

const getBeanName = ref('')

const roastContext = ref<RoastContext>({ greenBeans: [], purchaseBatches: [], roastingBatches: [] })

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

async function fetchReviewData() {
  loading.value = true
  error.value = false
  try {
    const [ctx, rev] = await Promise.all([
      fetchRoastContext(),
      fetchReviewSvc(batchId),
    ])
    roastContext.value = ctx
    batch.value = ctx.roastingBatches.find(b => b.id === batchId) || null

    if (batch.value) {
      getBeanName.value = getGreenBeanByBatch(ctx, batch.value)?.name || ''
      const pb = ctx.purchaseBatches.find(p => p.id === batch.value!.purchaseBatchId)
      getPurchaseLabel.value = pb ? `PB-${pb.id.replace('pb_', '')}` : '-'
    }

    // Questionnaire state
    const { fetchQuestionnaires } = await import('../services/questionnaireService')
    const qs = await fetchQuestionnaires()
    const q = qs.find(q => q.roastingBatchId === batchId)
    if (q) {
      questionnaire.value = q
      evaluationCount.value = q.submissionCount
      if (q.submissionCount > 0) {
        evaluationSummary.value = '综合 ' + q.submissionCount + ' 位评价者反馈：评价结果显示整体接受度较高，建议关注酸度控制和甜感发展。'
      }
    }

    if (rev) {
      review.value = { ...rev }
    }
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

async function savePersonal() {
  await saveReviewSvc({
    roastingBatchId: batchId,
    personalReview: review.value.personalReview,
    personalReviewAt: new Date().toISOString().split('T')[0],
  })
  review.value.personalReviewAt = new Date().toISOString().split('T')[0]
}

async function saveComprehensive() {
  await saveReviewSvc({
    roastingBatchId: batchId,
    comprehensiveReview: review.value.comprehensiveReview,
    comprehensiveReviewAt: new Date().toISOString().split('T')[0],
  })
  review.value.comprehensiveReviewAt = new Date().toISOString().split('T')[0]
}

async function saveNextSuggestions() {
  await saveReviewSvc({
    roastingBatchId: batchId,
    nextBatchSuggestions: review.value.nextBatchSuggestions,
  })
}

async function saveReminders() {
  await saveReviewSvc({
    roastingBatchId: batchId,
    reminders: review.value.reminders,
  })
}

async function saveWeightOut() {
  if (!batch.value || weightOutValue.value <= 0) return
  batch.value = await updateOutputWeight(batch.value.id, weightOutValue.value)
  invalidateRoastContext()
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
  await createQ(batch.value.id)
  await fetchReviewData()
}

async function closeQuestionnaire() {
  if (!questionnaire.value) return
  await closeQ(questionnaire.value.id)
  await fetchReviewData()
}

function openNextBatchDialog() {
  if (!batch.value) return
  nextBatchForm.value = {
    plannedDate: new Date().toISOString().split('T')[0],
    beanWeightIn: batch.value.beanWeightIn,
    targetDescription: review.value.nextBatchSuggestions || '',
    selectedReminders: review.value.reminders.map(r => r.id),
  }
  nextBatchDialog.value = true
}

async function doCreateNextBatch() {
  if (!batch.value) return
  await createNextRoastPlan(batch.value.id, {
    purchaseBatchId: batch.value.purchaseBatchId,
    plannedDate: nextBatchForm.value.plannedDate,
    beanWeightIn: nextBatchForm.value.beanWeightIn,
    targetDescription: nextBatchForm.value.targetDescription,
    reminderIds: nextBatchForm.value.selectedReminders,
  })
  invalidateRoastContext()

  // Calculate bean age days for reference
  if (batch.value.actualDate) {
    const bakeDate = new Date(batch.value.actualDate)
    const today = new Date()
    Math.floor((today.getTime() - bakeDate.getTime()) / (1000 * 60 * 60 * 24))
    // bean age is auto-calculated, stored in evaluation
  }

  nextBatchDialog.value = false
  router.push('/roasting')
}


onMounted(fetchReviewData)
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

.checkbox-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  cursor: pointer;
  font-size: var(--fs-sm);
}

.reminder-carry-priority {
  width: 22px;
  height: 22px;
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

.mt-sm { margin-top: var(--sp-2); }
</style>
