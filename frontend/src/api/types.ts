export type LoginRequestDto = {
  username: string
  password: string
}

export type LoginResponseDto = {
  access_token: string
  token_type: string
  expires_at: string
  user_id: string
  display_name: string | null
}

export type StandardTermDto = {
  id: string
  category: string
  value: string
  display_order: number
  is_active: boolean
  usage_count: number
}

export type TermUpdateRequestDto = {
  value?: string
  display_order?: number
  is_active?: boolean
}

// -- Green Bean DTOs --
export type GreenBeanDto = {
  id: string
  name: string
  variety: string | null
  process: string | null
  region: string | null
  country: string | null
  farm: string | null
  elevation: string | null
  brand: string | null
  harvest_season: string | null
  vendor_flavor_description: string | null
  first_created_at: string | null
}

export type RoastingBatchTreeDto = {
  id: string
  purchase_batch_id: string
  status: 'planned' | 'completed' | 'voided'
  planned_at: string | null
  roasted_at: string | null
  planned_input_weight_grams: number
  actual_input_weight_grams: number | null
  output_weight_grams: number | null
  weight_loss_percent: number | null
  total_time_seconds: number | null
  development_time_seconds: number | null
  development_ratio_percent: number | null
  target_description: string | null
  color_tag: string | null
}

export type PurchaseBatchTreeDto = {
  id: string
  green_bean_id: string
  purchase_date: string | null
  total_weight_grams: number
  moisture_content_percent: number | null
  unit_price_fen_per_kg: number | null
  total_price_fen: number | null
  supplier: string | null
  lot_number: string | null
  notes: string | null
  remaining_weight_grams: number | null
  roasting_batches: RoastingBatchTreeDto[]
}

export type GreenBeanTreeDto = GreenBeanDto & {
  purchase_batches: PurchaseBatchTreeDto[]
}

export type GreenBeanMatchDto = {
  id: string
  name: string
  brand: string | null
  harvest_season: string | null
  processing_method: string | null
  region: string | null
}

export type GreenBeanWithFirstPurchaseRequestDto = {
  name: string
  variety?: string | null
  process?: string | null
  region?: string | null
  country?: string | null
  farm?: string | null
  elevation?: string | null
  brand?: string | null
  harvest_season?: string | null
  vendor_flavor_description?: string | null
  purchase_date?: string | null
  total_weight_grams: number
  unit_price_fen_per_kg?: number | null
  moisture_content_percent?: number | null
  supplier?: string | null
  lot_number?: string | null
  notes?: string | null
}

export type PurchaseBatchCreateRequestDto = {
  purchase_date: string
  total_weight_grams: number
  unit_price_fen_per_kg?: number | null
  moisture_content_percent?: number | null
  supplier?: string | null
  lot_number?: string | null
  notes?: string | null
}

export type RoastingBatchCreateRequestDto = {
  purchase_batch_id: string
  planned_at: string
  planned_input_weight_grams: number
  target_description?: string | null
  roast_level?: string | null
}

export type RoastingBatchResponseDto = {
  id: string
  purchase_batch_id: string
  status: 'planned' | 'completed' | 'voided'
  planned_at: string | null
  roasted_at: string | null
  planned_input_weight_grams: number
  actual_input_weight_grams: number | null
  output_weight_grams: number | null
  weight_loss_percent: number | null
  total_time_seconds: number | null
  development_time_seconds: number | null
  development_ratio_percent: number | null
  roast_level: string | null
  target_description: string | null
  color_tag: string | null
  entry_mode: string | null
  inventory_effective: boolean | null
  source_note: string | null
  green_bean_name: string | null
  purchase_batch_label: string | null
}

export type RoastingBatchListResponseDto = {
  items: RoastingBatchResponseDto[]
  page: number
  page_size: number
  total: number
}

export type BatchCompleteRequestDto = {
  roasted_at: string
  actual_input_weight_grams: number
}
