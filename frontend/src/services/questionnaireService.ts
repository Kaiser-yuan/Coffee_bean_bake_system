/**
 * Questionnaire service — single entry point for views.
 * Demo mode delegates to the in-memory mock; real mode either calls the
 * existing backend client or throws a clear "未接入" error when the real
 * API client is not yet wired (still leaves pages renderable in demo).
 */
import { isDemoMode } from '../api/http'
import * as questionnaireApi from '../api/questionnaires'
import type { Questionnaire } from '../types'
import type { QuestionnaireResponseDto } from '../api/types'

let _mockMod: typeof import('../mock') | null = null
async function getMock() {
  if (!_mockMod) _mockMod = await import('../mock')
  return _mockMod
}

export interface PublicQuestionnaireView {
  shareCode: string
  status: Questionnaire['status']
  expiresAt?: string
  roastDate?: string
  greenBeanName?: string
}

function toQuestionnaire(dto: QuestionnaireResponseDto): Questionnaire {
  return {
    id: dto.id,
    roastingBatchId: dto.roasting_batch_id,
    shareCode: dto.share_code,
    status: dto.status,
    createdAt: dto.created_at,
    expiresAt: dto.expires_at || undefined,
    closedAt: dto.closed_at || undefined,
    submissionCount: dto.submission_count,
  }
}

export async function fetchQuestionnaires(): Promise<Questionnaire[]> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiGetQuestionnaires()
  }
  return (await questionnaireApi.listQuestionnaires()).map(toQuestionnaire)
}

export async function fetchQuestionnaire(id: string): Promise<Questionnaire | null> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiGetQuestionnaire(id)
  }
  return toQuestionnaire(await questionnaireApi.getQuestionnaire(id))
}

export async function fetchQuestionnaireByCode(code: string): Promise<PublicQuestionnaireView | null> {
  if (isDemoMode) {
    const m = await getMock()
    const q = await m.apiGetQuestionnaireByCode(code)
    if (!q) return null
    const batch = m.mockRoastingBatches.find((item) => item.id === q.roastingBatchId)
    const bean = batch ? m.getGreenBeanByBatch(batch) : undefined
    return {
      shareCode: q.shareCode,
      status: q.status,
      expiresAt: q.expiresAt,
      roastDate: batch?.actualDate || batch?.plannedDate,
      greenBeanName: bean?.name,
    }
  }
  const dto = await questionnaireApi.getPublicQuestionnaire(code)
  return {
    shareCode: dto.share_code,
    status: dto.status,
    expiresAt: dto.expires_at || undefined,
    roastDate: dto.roast_date || undefined,
    greenBeanName: dto.green_bean_name || undefined,
  }
}

export async function createQuestionnaire(batchId: string): Promise<Questionnaire> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiCreateQuestionnaire(batchId)
  }
  const dto = await questionnaireApi.createQuestionnaire(batchId)
  return {
    id: dto.id,
    roastingBatchId: batchId,
    shareCode: dto.share_code,
    status: dto.status,
    createdAt: new Date().toISOString(),
    expiresAt: dto.expires_at || undefined,
    submissionCount: 0,
  }
}

export async function closeQuestionnaire(id: string): Promise<Questionnaire> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiCloseQuestionnaire(id)
  }
  return toQuestionnaire(await questionnaireApi.closeQuestionnaire(id))
}
