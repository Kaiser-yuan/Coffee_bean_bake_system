import { apiRequest } from './http'
import type { RoastingBatchCreateRequestDto } from './types'

export function createRoastingBatch(body: RoastingBatchCreateRequestDto) {
  return apiRequest('/roasting-batches', {
    method: 'POST',
    body,
    auth: true,
  })
}
