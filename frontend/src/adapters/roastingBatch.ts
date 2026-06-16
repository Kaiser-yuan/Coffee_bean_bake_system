import type { RoastingBatchCreateRequestDto } from '../api/types'

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
