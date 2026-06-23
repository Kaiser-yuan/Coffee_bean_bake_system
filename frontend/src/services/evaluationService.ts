/**
 * Cupping evaluation service. The public submission endpoint is stateless
 * (no auth required), so it gets special real-mode treatment.
 */
import { isDemoMode } from '../api/http'
import * as evaluationApi from '../api/evaluations'
import type { CuppingEvaluation } from '../types'
import type { EvaluationResponseDto, EvaluationSubmitRequestDto } from '../api/types'

let _mockMod: typeof import('../mock') | null = null
async function getMock() {
  if (!_mockMod) _mockMod = await import('../mock')
  return _mockMod
}

function toEvaluation(dto: EvaluationResponseDto): CuppingEvaluation {
  return {
    id: dto.id,
    questionnaireId: dto.questionnaire_id,
    roastingBatchId: '',
    evaluatorName: dto.evaluator_name || '匿名',
    evaluatorType: (dto.evaluator_type || 'customer') as CuppingEvaluation['evaluatorType'],
    brewMethod: (dto.brew_method || '其他') as CuppingEvaluation['brewMethod'],
    drinkTemperature: (dto.drink_temperature || '热饮') as CuppingEvaluation['drinkTemperature'],
    drinkForm: (dto.drink_form || '其他') as CuppingEvaluation['drinkForm'],
    dryFragrance: dto.dry_fragrance_score ?? 0,
    wetAroma: dto.wet_aroma_score ?? 0,
    acidity: dto.acidity_intensity_score ?? 0,
    sweetness: dto.sweetness_score ?? 0,
    bitterness: dto.bitterness_intensity_score ?? 0,
    aftertaste: dto.aftertaste_score ?? 0,
    overallPreference: dto.overall_preference_score ?? 0,
    flavorNotes: dto.flavor_notes,
    freeFlavorDescription: dto.free_flavor_description || undefined,
    freeNotes: dto.free_notes || undefined,
    beanAgeDays: dto.bean_age_days ?? undefined,
    submittedAt: dto.submitted_at || '',
  }
}

export async function fetchEvaluations(questionnaireId: string): Promise<CuppingEvaluation[]> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiGetEvaluations(questionnaireId)
  }
  const dto = await evaluationApi.listEvaluations(questionnaireId)
  return dto.evaluations.map(toEvaluation)
}

export async function submitEvaluation(
  shareCode: string,
  data: Partial<CuppingEvaluation>,
): Promise<CuppingEvaluation> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiSubmitEvaluation(data)
  }
  const optionalScore = (value: number | undefined) => value && value > 0 ? value : undefined
  const body: EvaluationSubmitRequestDto = {
    evaluator_name: data.evaluatorName || undefined,
    evaluator_type: data.evaluatorType || undefined,
    brew_method: data.brewMethod || undefined,
    drink_temperature: data.drinkTemperature || undefined,
    drink_form: data.drinkForm || undefined,
    dry_fragrance_score: optionalScore(data.dryFragrance),
    wet_aroma_score: optionalScore(data.wetAroma),
    acidity_intensity_score: optionalScore(data.acidity),
    sweetness_score: optionalScore(data.sweetness),
    bitterness_intensity_score: optionalScore(data.bitterness),
    aftertaste_score: optionalScore(data.aftertaste),
    overall_preference_score: data.overallPreference || 1,
    flavor_notes: data.flavorNotes || [],
    free_flavor_description: data.freeFlavorDescription || undefined,
    free_notes: data.freeNotes || undefined,
  }
  const result = await evaluationApi.submitEvaluation(shareCode, body)
  return {
    id: result.id,
    questionnaireId: data.questionnaireId || '',
    roastingBatchId: data.roastingBatchId || '',
    evaluatorName: data.evaluatorName || '匿名',
    evaluatorType: data.evaluatorType || 'customer',
    brewMethod: data.brewMethod || '其他',
    drinkTemperature: data.drinkTemperature || '热饮',
    drinkForm: data.drinkForm || '其他',
    dryFragrance: data.dryFragrance || 0,
    wetAroma: data.wetAroma || 0,
    acidity: data.acidity || 0,
    sweetness: data.sweetness || 0,
    bitterness: data.bitterness || 0,
    aftertaste: data.aftertaste || 0,
    overallPreference: data.overallPreference || 1,
    flavorNotes: data.flavorNotes || [],
    freeNotes: data.freeNotes,
    beanAgeDays: result.bean_age_days ?? undefined,
    submittedAt: new Date().toISOString(),
  }
}
