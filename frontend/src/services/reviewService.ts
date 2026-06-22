/**
 * Batch review service.
 */
import { isDemoMode } from '../api/http'
import * as reviewApi from '../api/reviews'
import { toRoastingBatch } from '../adapters/roastingBatch'
import type { BatchReview } from '../types'

let _mockMod: typeof import('../mock') | null = null
async function getMock() {
  if (!_mockMod) _mockMod = await import('../mock')
  return _mockMod
}

export async function fetchReview(batchId: string): Promise<BatchReview | null> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiGetReview(batchId)
  }
  const dto = await reviewApi.getReview(batchId)
  if (!dto.review && !dto.reminders.length && !dto.evaluation_summary) return null
  return {
    id: dto.review?.id || '',
    roastingBatchId: batchId,
    personalReview: dto.review?.personal_review || '',
    personalReviewAt: dto.review?.personal_review_at || undefined,
    evaluationSummary: dto.evaluation_summary || undefined,
    comprehensiveReview: dto.review?.comprehensive_review || undefined,
    comprehensiveReviewAt: dto.review?.comprehensive_review_at || undefined,
    nextBatchSuggestions: dto.review?.next_batch_suggestion || '',
    reminders: dto.reminders.map((reminder) => ({
      id: reminder.id,
      batchReviewId: dto.review?.id || '',
      priority: reminder.priority as 1 | 2 | 3,
      content: reminder.content,
    })),
  }
}

export async function saveReview(data: Partial<BatchReview>): Promise<BatchReview> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiSaveReview(data)
  }
  const batchId = data.roastingBatchId
  if (!batchId) throw new Error('缺少烘焙批次 ID')
  if (data.personalReview !== undefined) {
    await reviewApi.updatePersonalReview(batchId, data.personalReview)
  }
  if (data.comprehensiveReview !== undefined) {
    await reviewApi.updateComprehensiveReview(batchId, data.comprehensiveReview)
  }
  if (data.nextBatchSuggestions !== undefined) {
    await reviewApi.updateSuggestion(batchId, data.nextBatchSuggestions)
  }
  if (data.reminders !== undefined) {
    await reviewApi.replaceReminders(
      batchId,
      data.reminders.map(({ priority, content }) => ({ priority, content })),
    )
  }
  return (await fetchReview(batchId)) || {
    id: '', roastingBatchId: batchId, personalReview: '', nextBatchSuggestions: '', reminders: [],
  }
}

export async function createNextRoastPlan(
  sourceBatchId: string,
  form: {
    purchaseBatchId: string
    plannedDate: string
    beanWeightIn: number
    targetDescription?: string
    reminderIds: string[]
  },
) {
  if (isDemoMode) {
    const mock = await getMock()
    return mock.apiCreateRoastingBatch({
      purchaseBatchId: form.purchaseBatchId,
      plannedDate: form.plannedDate,
      beanWeightIn: form.beanWeightIn,
      targetDescription: form.targetDescription,
    })
  }
  const dto = await reviewApi.createNextRoastPlan(sourceBatchId, {
    planned_at: new Date(form.plannedDate).toISOString(),
    purchase_batch_id: form.purchaseBatchId,
    planned_input_weight_grams: form.beanWeightIn,
    target_description: form.targetDescription || undefined,
    review_reminder_ids: form.reminderIds,
  })
  return toRoastingBatch(dto.roasting_batch)
}
