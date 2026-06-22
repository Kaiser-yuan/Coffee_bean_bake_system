import type {
  RoastingBatchCreateRequestDto,
  RoastingBatchResponseDto,
} from '../api/types'
import type { RoastingBatch, BatchStatus, CurveStatus, EvaluationStatus, ReviewStatus } from '../types'

/** Frontend roast plan form -> Backend CreateRoastingBatch DTO */
export function toRoastingBatchCreateDto(form: {
  purchaseBatchId: string
  plannedDate: string
  beanWeightIn: number
  targetDescription?: string
}): RoastingBatchCreateRequestDto {
  return {
    purchase_batch_id: form.purchaseBatchId,
    planned_at: new Date(form.plannedDate).toISOString(),
    planned_input_weight_grams: form.beanWeightIn,
    target_description: form.targetDescription || undefined,
  }
}

/** RoastingBatchResponseDto -> RoastingBatch (domain type) */
export function toRoastingBatch(dto: RoastingBatchResponseDto): RoastingBatch {
  return {
    id: dto.id,
    purchaseBatchId: dto.purchase_batch_id,
    plannedDate: dto.planned_at || undefined,
    actualDate: dto.roasted_at || undefined,
    beanWeightIn: dto.actual_input_weight_grams ?? dto.planned_input_weight_grams,
    beanWeightOut: dto.output_weight_grams ?? undefined,
    weightLossRate: dto.weight_loss_percent ?? undefined,
    totalTime: dto.total_time_seconds ?? undefined,
    developmentTime: dto.development_time_seconds ?? undefined,
    developmentRatio: dto.development_ratio_percent ?? undefined,
    targetDescription: dto.target_description || undefined,
    status: dto.status as BatchStatus,
    curveStatus: (dto.completeness && !dto.completeness.missing_curve ? 'parsed' : 'none') as CurveStatus,
    evaluationStatus: (dto.completeness && !dto.completeness.missing_evaluation ? 'closed' : 'none') as EvaluationStatus,
    reviewStatus: (dto.completeness && !dto.completeness.missing_review ? 'done' : 'none') as ReviewStatus,
    colorTag: dto.color_tag || undefined,
    entryMode: dto.entry_mode || undefined,
    inventoryEffective: dto.inventory_effective ?? undefined,
    sourceNote: dto.source_note || undefined,
  }
}
