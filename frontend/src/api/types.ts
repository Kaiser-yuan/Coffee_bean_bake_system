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
  is_archived: boolean
  archived_at: string | null
}

export type GreenBeanUpdateRequestDto = {
  name?: string
  variety?: string | null
  process?: string | null
  region?: string | null
  country?: string | null
  farm?: string | null
  elevation?: string | null
  brand?: string | null
  harvest_season?: string | null
  vendor_flavor_description?: string | null
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
  entry_mode: string | null
  inventory_effective: boolean | null
  source_note: string | null
}

export type PurchaseBatchTreeDto = {
  id: string
  green_bean_id: string
  purchase_date: string | null
  total_weight_grams: number
  inventory_tracking_mode: string | null
  opening_stock_grams: number | null
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
  inventory_tracking_mode?: 'normal' | 'historical_archive' | null
  opening_stock_grams?: number | null
}

export type PurchaseBatchCreateRequestDto = {
  purchase_date: string
  total_weight_grams: number
  unit_price_fen_per_kg?: number | null
  moisture_content_percent?: number | null
  supplier?: string | null
  lot_number?: string | null
  notes?: string | null
  inventory_tracking_mode?: 'normal' | 'historical_archive' | null
  opening_stock_grams?: number | null
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
  completeness?: {
    missing_output_weight: boolean
    missing_curve: boolean
    missing_evaluation: boolean
    missing_review: boolean
    is_complete: boolean
  } | null
  allowed_actions?: string[]
  green_bean_name: string | null
  green_bean_is_archived?: boolean
  purchase_batch_label: string | null
  curve_file_summary?: {
    curve_file_id: string | null
    curve_filename: string | null
    curve_uploaded_at: string | null
    curve_parse_status: string | null
    curve_parser_version: string | null
  } | null
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

export type DashboardResponseDto = {
  year: number
  total_completed_roasts: number
  total_roasted_bean_profiles: number
  total_input_weight_grams: number
  average_weight_loss_percent: number | null
  monthly_roasts: { month: number; count: number }[]
  variety_distribution: { name: string; count: number }[]
  region_distribution: { name: string; count: number }[]
  pending_groups: Array<{
    bean_id: string
    bean_name: string
    variety: string | null
    process: string | null
    region: string | null
    batch_count: number
    batches: Record<string, unknown>[]
  }>
  recent_batches: Record<string, unknown>[]
  pending_actions: Record<string, number>
}

export type CurvePointDto = {
  sample_index: number
  elapsed_seconds: number
  bean_temp_celsius: number | null
  environment_temp_celsius: number | null
  ror_celsius_per_minute: number | null
  target_temp_celsius: number | null
  heating_power_mode: string | null
  heating_power_percent: number | null
  smoke_damper_percent: number | null
  roller_percent: number | null
  power_status: string | null
  aligned_seconds?: number
}

export type CurveEventDto = {
  type: string
  label: string
  time_seconds: number | null
  bean_temp_celsius: number | null
}

export type CurveResponseDto = {
  curve_file: {
    id: string | null
    original_filename: string | null
    parse_status: string | null
  } | null
  summary: Record<string, unknown> | null
  events: CurveEventDto[]
  points: CurvePointDto[]
}

export type CurveComparisonResponseDto = {
  base_batch_id: string
  align_by: string
  series: Array<{
    batch: { id: string }
    events: CurveEventDto[]
    points: CurvePointDto[]
  }>
  warnings?: Array<{ code: string; severity: string; batch_id: string; message: string }>
  missing_batch_ids?: string[]
}

export type QuestionnaireResponseDto = {
  id: string
  roasting_batch_id: string
  status: 'open' | 'closed' | 'expired'
  share_code: string
  share_url: string | null
  created_at: string
  expires_at: string | null
  closed_at: string | null
  submission_count: number
}

export type QuestionnaireCreateResponseDto = {
  id: string
  status: 'open' | 'closed' | 'expired'
  share_code: string
  share_url: string
  expires_at: string | null
}

export type PublicQuestionnaireResponseDto = {
  share_code: string
  roast_date: string | null
  green_bean_name: string | null
  status: 'open' | 'closed' | 'expired'
  expires_at: string | null
}

export type EvaluationResponseDto = {
  id: string
  questionnaire_id: string
  evaluator_name: string | null
  evaluator_type: 'roaster' | 'colleague' | 'customer' | null
  brew_method: string | null
  drink_temperature: '热饮' | '冷饮' | null
  drink_form: '黑咖啡' | '加奶' | '其他' | null
  dry_fragrance_score: number | null
  wet_aroma_score: number | null
  acidity_intensity_score: number | null
  sweetness_score: number | null
  bitterness_intensity_score: number | null
  aftertaste_score: number | null
  overall_preference_score: number | null
  flavor_notes: string[]
  free_flavor_description: string | null
  free_notes: string | null
  bean_age_days: number | null
  submitted_at: string | null
}

export type EvaluationListResponseDto = {
  evaluations: EvaluationResponseDto[]
  stats: Record<string, unknown>
}

export type EvaluationSubmitRequestDto = {
  evaluator_name?: string | null
  evaluator_type?: 'roaster' | 'colleague' | 'customer' | null
  brew_method?: string | null
  /** Preferred: existing active standard term id. Takes precedence over brew_method. */
  brew_method_term_id?: string | null
  drink_temperature?: '热饮' | '冷饮' | null
  drink_form?: '黑咖啡' | '加奶' | '其他' | null
  dry_fragrance_score?: number | null
  wet_aroma_score?: number | null
  acidity_intensity_score?: number | null
  sweetness_score?: number | null
  bitterness_intensity_score?: number | null
  aftertaste_score?: number | null
  overall_preference_score: number
  flavor_notes: string[]
  /** Preferred: existing active standard term ids. Takes precedence over flavor_notes. */
  flavor_term_ids?: string[] | null
  /** Free-text flavor description — stored separately, never creates a standard term. */
  free_flavor_description?: string | null
  free_notes?: string | null
}

export type ReviewOverviewResponseDto = {
  batch: Record<string, unknown> | null
  review: {
    id: string
    personal_review: string | null
    personal_review_at: string | null
    comprehensive_review: string | null
    comprehensive_review_at: string | null
    next_batch_suggestion: string | null
  } | null
  reminders: Array<{ id: string; priority: number; content: string }>
  evaluation_summary: string | null
  evaluations: Record<string, unknown>[]
  questionnaires: Array<{ id: string; status: string; submission_count: number }>
}

export type NextRoastPlanResponseDto = {
  roasting_batch: RoastingBatchResponseDto
  copied_reminders: number
}
