import { apiRequest } from './http'
import type {
  EvaluationListResponseDto,
  EvaluationSubmitRequestDto,
} from './types'

export function listEvaluations(questionnaireId: string): Promise<EvaluationListResponseDto> {
  return apiRequest<EvaluationListResponseDto>(
    `/evaluations/questionnaires/${questionnaireId}`,
    { auth: true },
  )
}

export function submitEvaluation(
  shareCode: string,
  body: EvaluationSubmitRequestDto,
): Promise<{ id: string; status: string; bean_age_days: number | null }> {
  return apiRequest(`/public/questionnaires/${shareCode}/evaluations`, {
    method: 'POST',
    body,
  })
}
