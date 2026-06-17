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
    const res = await getMock().apiGetRoastingBatches()
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
export async function completeRoastingBatch(batchId: string): Promise<RoastingBatch> {
  if (isDemoMode) {
    const batch = await getMock().apiCompleteBatch(batchId)
    return batch as unknown as RoastingBatch
  }
  // Real API: complete with default roasted_at = now
  const dto: BatchCompleteRequestDto = {
    roasted_at: new Date().toISOString(),
    // actual_input_weight_grams must be set by the caller — but mock doesn't pass it.
    // For real API, caller should provide the weight. The store's markComplete
    // currently doesn't pass weight. We throw a clear error.
    actual_input_weight_grams: 0, // invalid — will be caught
  }
  throw new Error(
    '真实 API 下完成烘焙批次需要提供实际投豆量。请使用页面上的「完成」按钮。',
  )
}

// ---- Create (demo → mock; real → backend) ----
export async function createRoastingBatch(form: {
  purchaseBatchId: string
  plannedDate: string
  beanWeightIn: number
  targetDescription?: string
}): Promise<RoastingBatchResponseDto> {
  if (isDemoMode) {
    return getMock().apiCreateRoastingBatch(form)
  }
  const { toRoastingBatchCreateDto } = await import('../adapters/roastingBatch')
  return realApi.createRoastingBatch(toRoastingBatchCreateDto(form))
}
