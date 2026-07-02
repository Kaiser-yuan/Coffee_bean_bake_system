import { apiRequest } from './http'
import type { CurveComparisonResponseDto, CurveResponseDto } from './types'

export type CurveUploadResponseDto = {
  id: string
  parse_status: 'parsed' | 'failed'
  parse_error_message?: string | null
  data_points?: number
  total_time_seconds?: number
  events_found?: number
  warnings?: unknown[]
}

export function getCurve(batchId: string): Promise<CurveResponseDto> {
  return apiRequest<CurveResponseDto>(`/roasting-batches/${batchId}/curve`, { auth: true })
}

export function compareCurves(
  batchIds: string[],
  alignBy: 'none' | 'charge' | 'yellowing' | 'first_crack_start' | 'drop' = 'charge',
): Promise<CurveComparisonResponseDto> {
  const params = new URLSearchParams({
    batch_ids: batchIds.join(','),
    align_by: alignBy,
    strict: 'false',
  })
  return apiRequest<CurveComparisonResponseDto>(`/curve-comparisons?${params}`, { auth: true })
}

export function uploadCurveFile(batchId: string, file: File): Promise<CurveUploadResponseDto> {
  const form = new FormData()
  form.append('file', file, file.name)
  return apiRequest<CurveUploadResponseDto>(
    `/roasting-batches/${batchId}/curve-files`,
    { method: 'POST', body: form, auth: true, timeoutMs: 60000 },
  )
}
