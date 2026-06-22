import { apiRequest } from './http'
import type {
  BulkImportCommitRequestDto,
  BulkImportCommitResponseDto,
  BulkImportPreviewResponseDto,
  PreviewParams,
  TimeInferenceStrategy,
} from './bulkImports'

export interface BackfillPreviewParams extends PreviewParams {
  purchase_batch_id: string
  // backfill defaults inventory_effective_default to false
  inventory_effective_default?: boolean
}

export function previewHistoricalRoastCsvBackfill(
  params: BackfillPreviewParams,
  files: File[],
): Promise<BulkImportPreviewResponseDto> {
  const form = new FormData()
  form.append('purchase_batch_id', params.purchase_batch_id)
  for (const f of files) {
    form.append('files', f, f.name)
    form.append('client_last_modified', String(f.lastModified))
  }
  if (params.default_input_weight_grams != null)
    form.append('default_input_weight_grams', String(params.default_input_weight_grams))
  form.append('inventory_effective_default', String(params.inventory_effective_default ?? false))
  if (params.default_roast_date) form.append('default_roast_date', params.default_roast_date)
  if (params.first_roast_time) form.append('first_roast_time', params.first_roast_time)
  if (params.time_inference_strategy)
    form.append('time_inference_strategy', params.time_inference_strategy as TimeInferenceStrategy)
  return apiRequest<BulkImportPreviewResponseDto>(
    `/backfills/roasting-csv/preview`,
    { method: 'POST', body: form, auth: true, timeoutMs: 60000 },
  )
}

export function commitHistoricalRoastCsvBackfill(
  body: BulkImportCommitRequestDto,
  files: File[],
): Promise<BulkImportCommitResponseDto> {
  const form = new FormData()
  form.append('job_id', body.job_id)
  form.append('payload', JSON.stringify({ items: body.items }))
  for (const f of files) form.append('files', f, f.name)
  return apiRequest<BulkImportCommitResponseDto>(
    `/backfills/roasting-csv/commit`,
    { method: 'POST', body: form, auth: true, timeoutMs: 120000 },
  )
}
