import { apiRequest } from './http'

// ---- Backend DTOs (snake_case) ----
export type RoastEntryMode =
  | 'manual_plan'
  | 'manual_completed'
  | 'csv_bulk_import'
  | 'historical_backfill'

export type RoastedAtSource =
  | 'csv_content'
  | 'filename'
  | 'file_last_modified'
  | 'manual'
  | 'upload_order'

export type TimeInferenceStrategy =
  | 'auto'
  | 'csv_content'
  | 'filename'
  | 'file_last_modified'
  | 'manual'
  | 'upload_order'

export interface BulkImportPreviewItemSummaryDto {
  total_time_seconds: number | null
  turning_point_seconds: number | null
  yellowing_seconds: number | null
  first_crack_start_seconds: number | null
  development_ratio_percent: number | null
  auc_bt_above_100: number | null
}

export interface BulkImportPreviewItemDto {
  item_id: string
  filename: string
  file_hash: string
  file_size_bytes: number
  inferred_roasted_at: string | null
  roasted_at_source: RoastedAtSource | null
  roasted_date_source: string | null
  roasted_time_source: string | null
  pot_order: number | null
  input_weight_grams: number | null
  output_weight_grams: number | null
  inventory_effective: boolean
  parse_status: 'parsed' | 'failed'
  parse_error_message: string | null
  summary: Partial<BulkImportPreviewItemSummaryDto>
  warnings: string[]
  is_duplicate: boolean
}

export interface BulkImportPreviewResponseDto {
  job_id: string
  purchase_batch_id: string | null
  mode: 'csv_bulk_import' | 'historical_backfill'
  inventory_effective_default: boolean
  available_stock_grams: number
  total_planned_input_grams: number
  items: BulkImportPreviewItemDto[]
  blocking_errors: string[]
}

export interface BulkImportCommitItemDto {
  item_id: string
  roasted_at?: string | null
  actual_input_weight_grams?: number | null
  output_weight_grams?: number | null
  inventory_effective?: boolean | null
  source_note?: string | null
}

export interface BulkImportCommitRequestDto {
  job_id: string
  items: BulkImportCommitItemDto[]
}

export interface BulkImportCommitResultItemDto {
  item_id: string
  filename: string | null
  success: boolean
  roasting_batch_id: string | null
  error_message: string | null
}

export interface BulkImportCommitResponseDto {
  job_id: string
  status: string
  success_count: number
  failed_count: number
  total_consumed_grams: number
  items: BulkImportCommitResultItemDto[]
}

// ---- API ----

export interface PreviewParams {
  default_input_weight_grams?: number
  inventory_effective_default?: boolean
  default_roast_date?: string
  first_roast_time?: string
  time_inference_strategy?: TimeInferenceStrategy
}

export function cancelBulkImportJob(jobId: string): Promise<{ job_id: string; status: string }> {
  return apiRequest<{ job_id: string; status: string }>(
    `/bulk-import-jobs/${jobId}/cancel`,
    { method: 'POST', auth: true },
  )
}

export function buildPreviewForm(files: File[], params: PreviewParams): FormData {
  const form = new FormData()
  for (const f of files) {
    form.append('files', f, f.name)
    form.append('client_last_modified', String(f.lastModified))
  }
  if (params.default_input_weight_grams != null)
    form.append('default_input_weight_grams', String(params.default_input_weight_grams))
  form.append('inventory_effective_default', String(params.inventory_effective_default ?? true))
  if (params.default_roast_date) form.append('default_roast_date', params.default_roast_date)
  if (params.first_roast_time) form.append('first_roast_time', params.first_roast_time)
  if (params.time_inference_strategy) form.append('time_inference_strategy', params.time_inference_strategy)
  return form
}

export function previewPurchaseBatchCsvImport(
  purchaseBatchId: string,
  files: File[],
  params: PreviewParams,
): Promise<BulkImportPreviewResponseDto> {
  return apiRequest<BulkImportPreviewResponseDto>(
    `/purchase-batches/${purchaseBatchId}/roasting-batches/bulk-preview`,
    { method: 'POST', body: buildPreviewForm(files, params), auth: true, timeoutMs: 60000 },
  )
}

export function commitPurchaseBatchCsvImport(
  purchaseBatchId: string,
  body: BulkImportCommitRequestDto,
  files: File[],
): Promise<BulkImportCommitResponseDto> {
  const form = new FormData()
  form.append('job_id', body.job_id)
  form.append('payload', JSON.stringify({ items: body.items }))
  for (const f of files) form.append('files', f, f.name)
  return apiRequest<BulkImportCommitResponseDto>(
    `/purchase-batches/${purchaseBatchId}/roasting-batches/bulk-commit`,
    { method: 'POST', body: form, auth: true, timeoutMs: 120000 },
  )
}
