import { apiRequest } from './http'
import type { NextRoastPlanResponseDto, ReviewOverviewResponseDto } from './types'

export function getReview(batchId: string): Promise<ReviewOverviewResponseDto> {
  return apiRequest<ReviewOverviewResponseDto>(
    `/roasting-batches/${batchId}/review-overview`,
    { auth: true },
  )
}

export function updatePersonalReview(batchId: string, value: string) {
  return apiRequest(`/roasting-batches/${batchId}/review/personal`, {
    method: 'PATCH', body: { personal_review: value }, auth: true,
  })
}

export function updateComprehensiveReview(batchId: string, value: string) {
  return apiRequest(`/roasting-batches/${batchId}/review/comprehensive`, {
    method: 'PATCH', body: { comprehensive_review: value }, auth: true,
  })
}

export function updateSuggestion(batchId: string, value: string) {
  return apiRequest(`/roasting-batches/${batchId}/review/suggestion`, {
    method: 'PATCH', body: { next_batch_suggestion: value }, auth: true,
  })
}

export function replaceReminders(
  batchId: string,
  reminders: Array<{ priority: number; content: string }>,
) {
  return apiRequest(`/roasting-batches/${batchId}/review/reminders`, {
    method: 'PUT', body: { reminders }, auth: true,
  })
}

export function createNextRoastPlan(
  batchId: string,
  body: {
    planned_at: string
    purchase_batch_id: string
    planned_input_weight_grams: number
    target_description?: string | null
    review_reminder_ids: string[]
  },
): Promise<NextRoastPlanResponseDto> {
  return apiRequest<NextRoastPlanResponseDto>(
    `/roasting-batches/${batchId}/next-roast-plan`,
    { method: 'POST', body, auth: true },
  )
}
