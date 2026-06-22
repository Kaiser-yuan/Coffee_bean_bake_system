/**
 * Roasting batch service — single entry point. Switches on isDemoMode.
 */
import { isDemoMode } from '../api/http'
import * as realApi from '../api/roastingBatches'
import { toRoastingBatch } from '../adapters/roastingBatch'
import type { RoastingBatch } from '../types'
import type {
  RoastingBatchListResponseDto,
  RoastingBatchResponseDto,
  BatchCompleteRequestDto,
} from '../api/types'

let _mockMod: typeof import('../mock') | null = null
async function getMock() {
  if (!_mockMod) {
    _mockMod = await import('../mock')
  }
  return _mockMod
}

// ---- List ----
export async function fetchRoastingBatches(): Promise<{
  items: RoastingBatch[]
  total: number
}> {
  if (isDemoMode) {
    const m = await getMock()
    const res = await m.apiGetRoastingBatches()
    // items are already RoastingBatch (mock returns domain type directly)
    return { items: res.items as RoastingBatch[], total: res.total }
  }
  const res: RoastingBatchListResponseDto = await realApi.listRoastingBatches({
    has_curve: undefined,
  })
  return {
    items: res.items.map(toRoastingBatch),
    total: res.total,
  }
}

// ---- Complete ----
export async function completeRoastingBatch(
  batchId: string,
  actualInputWeightGrams: number,
  roastedAt?: string,
): Promise<RoastingBatch> {
  if (isDemoMode) {
    const m = await getMock()
    const batch = await m.apiCompleteBatch(batchId, actualInputWeightGrams, roastedAt)
    return batch as unknown as RoastingBatch
  }
  const dto: BatchCompleteRequestDto = {
    roasted_at: roastedAt
      ? new Date(roastedAt).toISOString()
      : new Date().toISOString(),
    actual_input_weight_grams: actualInputWeightGrams,
  }
  const res: RoastingBatchResponseDto = await realApi.completeRoastingBatch(batchId, dto)
  return toRoastingBatch(res)
}

// ---- Create (demo → mock; real → backend) ----
export async function createRoastingBatch(form: {
  purchaseBatchId: string
  plannedDate: string
  beanWeightIn: number
  targetDescription?: string
}): Promise<RoastingBatchResponseDto> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiCreateRoastingBatch(form) as unknown as RoastingBatchResponseDto
  }
  const { toRoastingBatchCreateDto } = await import('../adapters/roastingBatch')
  return realApi.createRoastingBatch(toRoastingBatchCreateDto(form))
}

// ---- Update output weight ----
export async function updateOutputWeight(
  batchId: string,
  outputWeightGrams: number,
): Promise<RoastingBatch> {
  if (isDemoMode) {
    const m = await getMock()
    const batch = await m.apiUpdateWeightOut(batchId, outputWeightGrams)
    return batch as unknown as RoastingBatch
  }
  const res: RoastingBatchResponseDto = await realApi.updateOutputWeight(batchId, outputWeightGrams)
  return toRoastingBatch(res)
}

// ---- Void ----
export async function voidRoastingBatch(batchId: string): Promise<RoastingBatch> {
  if (isDemoMode) {
    // Mock has no void fn — simulate by mutating mockRoastingBatches
    const m = await getMock()
    const b = m.mockRoastingBatches.find((x) => x.id === batchId)
    if (b) b.status = 'voided'
    return b as unknown as RoastingBatch
  }
  const res: RoastingBatchResponseDto = await realApi.voidRoastingBatch(batchId)
  return toRoastingBatch(res)
}

// ---- Reopen (cancel completion) ----
export async function reopenRoastingBatch(batchId: string): Promise<RoastingBatch> {
  if (isDemoMode) {
    // Mock has no reopen fn — simulate by resetting fields
    const m = await getMock()
    const b = m.mockRoastingBatches.find((x) => x.id === batchId)
    if (b) {
      b.status = 'planned'
      b.actualDate = undefined
      b.beanWeightOut = undefined
      b.weightLossRate = undefined
      b.totalTime = undefined
    }
    return b as unknown as RoastingBatch
  }
  const res: RoastingBatchResponseDto = await realApi.reopenRoastingBatch(batchId)
  return toRoastingBatch(res)
}
