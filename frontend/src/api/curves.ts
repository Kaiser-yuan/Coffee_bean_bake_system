import { apiRequest } from './http'
import type { CurveComparisonResponseDto, CurveResponseDto } from './types'

export function getCurve(batchId: string): Promise<CurveResponseDto> {
  return apiRequest<CurveResponseDto>(`/roasting-batches/${batchId}/curve`, { auth: true })
}

export function compareCurves(batchIds: string[]): Promise<CurveComparisonResponseDto> {
  const params = new URLSearchParams({ batch_ids: batchIds.join(','), align_by: 'charge' })
  return apiRequest<CurveComparisonResponseDto>(`/curve-comparisons?${params}`, { auth: true })
}
