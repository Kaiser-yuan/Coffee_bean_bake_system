import { apiRequest } from './http'
import type {
  PublicQuestionnaireResponseDto,
  QuestionnaireCreateResponseDto,
  QuestionnaireResponseDto,
} from './types'

export function listQuestionnaires(): Promise<QuestionnaireResponseDto[]> {
  return apiRequest<QuestionnaireResponseDto[]>('/questionnaires', { auth: true })
}

export function getQuestionnaire(id: string): Promise<QuestionnaireResponseDto> {
  return apiRequest<QuestionnaireResponseDto>(`/questionnaires/${id}`, { auth: true })
}

export function getPublicQuestionnaire(code: string): Promise<PublicQuestionnaireResponseDto> {
  return apiRequest<PublicQuestionnaireResponseDto>(`/public/questionnaires/${code}`)
}

export function createQuestionnaire(batchId: string): Promise<QuestionnaireCreateResponseDto> {
  return apiRequest<QuestionnaireCreateResponseDto>(
    `/roasting-batches/${batchId}/questionnaires`,
    { method: 'POST', auth: true },
  )
}

export function closeQuestionnaire(id: string): Promise<QuestionnaireResponseDto> {
  return apiRequest<QuestionnaireResponseDto>(
    `/questionnaires/${id}/close`,
    { method: 'POST', auth: true },
  )
}
