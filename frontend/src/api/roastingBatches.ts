import { apiRequest } from './http'
import type {
  RoastingBatchCreateRequestDto,
  RoastingBatchListResponseDto,
  RoastingBatchResponseDto,
  BatchCompleteRequestDto,
} from './types'

export function createRoastingBatch(body: RoastingBatchCreateRequestDto): Promise<RoastingBatchResponseDto> {
  return apiRequest<RoastingBatchResponseDto>('/roasting-batches', {
    method: 'POST',
    body,
    auth: true,
  })
}

export interface ListRoastingBatchesParams {
  status?: string
  purchase_batch_id?: string
  search?: string
  has_curve?: boolean
  page?: number
  page_size?: number
}

export function listRoastingBatches(
  params: ListRoastingBatchesParams = {},
): Promise<RoastingBatchListResponseDto> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.purchase_batch_id) qs.set('purchase_batch_id', params.purchase_batch_id)
  if (params.search) qs.set('search', params.search)
  if (params.has_curve !== undefined) qs.set('has_curve', String(params.has_curve))
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  const query = qs.toString()
  return apiRequest<RoastingBatchListResponseDto>(
    `/roasting-batches${query ? `?${query}` : ''}`,
    { auth: true },
  )
}

export function completeRoastingBatch(
  batchId: string,
  body: BatchCompleteRequestDto,
): Promise<RoastingBatchResponseDto> {
  return apiRequest<RoastingBatchResponseDto>(
    `/roasting-batches/${batchId}/complete`,
    { method: 'POST', body, auth: true },
  )
}

export function reopenRoastingBatch(
  batchId: string,
): Promise<RoastingBatchResponseDto> {
  return apiRequest<RoastingBatchResponseDto>(
    `/roasting-batches/${batchId}/reopen`,
    { method: 'POST', auth: true },
  )
}

export function voidRoastingBatch(
  batchId: string,
): Promise<RoastingBatchResponseDto> {
  return apiRequest<RoastingBatchResponseDto>(
    `/roasting-batches/${batchId}/void`,
    { method: 'POST', auth: true },
  )
}

export function updateOutputWeight(
  batchId: string,
  outputWeightGrams: number,
): Promise<RoastingBatchResponseDto> {
  return apiRequest<RoastingBatchResponseDto>(
    `/roasting-batches/${batchId}/output-weight`,
    { method: 'PATCH', body: { output_weight_grams: outputWeightGrams }, auth: true },
  )
}
