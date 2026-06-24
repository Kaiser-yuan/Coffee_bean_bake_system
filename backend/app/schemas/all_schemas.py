"""
Pydantic schemas for request/response validation.
Field naming: snake_case, matching DB and REST API.
"""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, Field, StringConstraints, model_validator
import re


# ============================================================
# Common
# ============================================================
class PaginatedResponse(BaseModel):
    items: list
    page: int
    page_size: int
    total: int


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None
    request_id: str | None = None


# ============================================================
# Auth
# ============================================================
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user_id: str
    display_name: str | None


# ============================================================
# Standard Terms
# ============================================================
class TermResponse(BaseModel):
    id: str
    category: str
    value: str
    display_order: int
    is_active: bool
    usage_count: int

    model_config = {"from_attributes": True}


class TermCreateRequest(BaseModel):
    category: str
    value: str
    display_order: int = 0


class TermUpdateRequest(BaseModel):
    value: str | None = None
    display_order: int | None = None
    is_active: bool | None = None


# ============================================================
# Green Beans
# ============================================================
class GreenBeanMatchResponse(BaseModel):
    id: str
    name: str
    brand: str | None = None
    harvest_season: str | None = None
    processing_method: str | None = None
    region: str | None = None

    model_config = {"from_attributes": True}


class GreenBeanResponse(BaseModel):
    id: str
    name: str
    variety: str | None = None
    process: str | None = None
    region: str | None = None
    country: str | None = None
    farm: str | None = None
    elevation: str | None = None
    brand: str | None = None
    harvest_season: str | None = None
    vendor_flavor_description: str | None = None
    first_created_at: str | None = None

    model_config = {"from_attributes": True}


class GreenBeanWithFirstPurchaseRequest(BaseModel):
    # Green bean fields
    name: str
    variety: str | None = None
    process: str | None = None
    region: str | None = None
    country: str | None = None
    farm: str | None = None
    elevation: str | None = None
    brand: str | None = None
    harvest_season: str | None = Field(
        default=None,
        description="四位年份，1900..当前+1，可为空",
        pattern=r"^(19\d{2}|20\d{2})$",
    )
    vendor_flavor_description: str | None = None

    # Purchase batch fields
    purchase_date: str | None = None
    total_weight_grams: int = Field(gt=0)
    unit_price_fen_per_kg: int | None = Field(default=None, ge=0)
    moisture_content_percent: float | None = Field(default=None, ge=0, le=100)
    supplier: str | None = None
    lot_number: str | None = None
    notes: str | None = None
    inventory_tracking_mode: Literal["normal", "historical_archive"] = "normal"
    opening_stock_grams: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate_opening_stock_le_total(self):
        if self.opening_stock_grams is not None and self.opening_stock_grams > self.total_weight_grams:
            raise ValueError("期初库存不能超过原采购总重量")
        return self


class GreenBeanUpdateRequest(BaseModel):
    """P1-2: Partial update of a green bean's metadata fields.
    All fields are optional but at least one must be provided.
    """
    name: str | None = None
    variety: str | None = None
    process: str | None = None
    region: str | None = None
    country: str | None = None
    farm: str | None = None
    elevation: str | None = None
    brand: str | None = None
    harvest_season: str | None = Field(
        default=None,
        description="四位年份，1900..当前+1，可为空",
        pattern=r"^(19\d{2}|20\d{2})$",
    )
    vendor_flavor_description: str | None = None

    @model_validator(mode="after")
    def _validate_at_least_one_field(self):
        fields = (
            "name", "variety", "process", "region", "country", "farm",
            "elevation", "brand", "harvest_season", "vendor_flavor_description",
        )
        if all(getattr(self, f, None) is None for f in fields):
            raise ValueError("至少需要提供一个字段进行更新")
        return self


class PurchaseBatchCreateRequest(BaseModel):
    purchase_date: str
    total_weight_grams: int = Field(gt=0)
    unit_price_fen_per_kg: int | None = Field(default=None, ge=0)
    moisture_content_percent: float | None = Field(default=None, ge=0, le=100)
    supplier: str | None = None
    lot_number: str | None = None
    notes: str | None = None
    inventory_tracking_mode: Literal["normal", "historical_archive"] = "normal"
    opening_stock_grams: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate_opening_stock_le_total(self):
        if self.opening_stock_grams is not None and self.opening_stock_grams > self.total_weight_grams:
            raise ValueError("期初库存不能超过原采购总重量")
        return self


# ============================================================
# Purchase Batches
# ============================================================
class PurchaseBatchResponse(BaseModel):
    id: str
    green_bean_id: str
    purchase_date: str | None = None
    total_weight_grams: int
    inventory_tracking_mode: str | None = None
    opening_stock_grams: int | None = None
    moisture_content_percent: float | None = None
    unit_price_fen_per_kg: int | None = None
    total_price_fen: int | None = None
    supplier: str | None = None
    lot_number: str | None = None
    notes: str | None = None
    remaining_weight_grams: int | None = None
    allowed_actions: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RoastingBatchTreeResponse(BaseModel):
    id: str
    purchase_batch_id: str
    status: str
    planned_at: str | None = None
    roasted_at: str | None = None
    planned_input_weight_grams: int
    actual_input_weight_grams: int | None = None
    output_weight_grams: int | None = None
    weight_loss_percent: float | None = None
    total_time_seconds: int | None = None
    development_time_seconds: int | None = None
    development_ratio_percent: float | None = None
    target_description: str | None = None
    color_tag: str | None = None
    entry_mode: str | None = None
    inventory_effective: bool | None = None
    source_note: str | None = None

    model_config = {"from_attributes": True}


class PurchaseBatchTreeResponse(PurchaseBatchResponse):
    roasting_batches: list[RoastingBatchTreeResponse] = Field(default_factory=list)


class GreenBeanTreeResponse(GreenBeanResponse):
    purchase_batches: list[PurchaseBatchTreeResponse] = Field(default_factory=list)


class InventoryLedgerResponse(BaseModel):
    id: str
    event_type: str
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    change_grams: int
    resulting_grams: int
    created_at: str


class InventoryAdjustmentRequest(BaseModel):
    amount_grams: int
    reason: str = Field(min_length=1)
    notes: str | None = None


# ============================================================
# Roasting Batches
# ============================================================
class RoastingBatchCreateRequest(BaseModel):
    purchase_batch_id: str
    planned_at: datetime
    planned_input_weight_grams: int = Field(gt=0)
    target_description: str | None = None
    roast_level: str | None = None


class BatchCompleteRequest(BaseModel):
    roasted_at: datetime
    actual_input_weight_grams: int = Field(gt=0)


class OutputWeightUpdateRequest(BaseModel):
    output_weight_grams: int = Field(gt=0)


class BatchCompleteness(BaseModel):
    missing_output_weight: bool
    missing_curve: bool
    missing_evaluation: bool
    missing_review: bool
    is_complete: bool


class CurveFileSummary(BaseModel):
    """P1-4: Lightweight curve file info embedded in roasting batch responses."""
    curve_file_id: str | None = None
    curve_filename: str | None = None
    curve_uploaded_at: str | None = None
    curve_parse_status: str | None = None
    curve_parser_version: str | None = None


class RoastingBatchResponse(BaseModel):
    id: str
    purchase_batch_id: str
    status: str
    planned_at: str | None = None
    roasted_at: str | None = None
    planned_input_weight_grams: int
    actual_input_weight_grams: int | None = None
    output_weight_grams: int | None = None
    weight_loss_percent: float | None = None
    total_time_seconds: int | None = None
    development_time_seconds: int | None = None
    development_ratio_percent: float | None = None
    roast_level: str | None = None
    target_description: str | None = None
    color_tag: str | None = None
    entry_mode: str | None = None
    inventory_effective: bool | None = None
    source_note: str | None = None
    completeness: BatchCompleteness | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    green_bean_name: str | None = None
    purchase_batch_label: str | None = None
    curve_file_summary: CurveFileSummary | None = None

    model_config = {"from_attributes": True}


# ============================================================
# Curves
# ============================================================
class CurvePoint(BaseModel):
    sample_index: int
    elapsed_seconds: float
    bean_temp_celsius: float | None = None
    environment_temp_celsius: float | None = None
    ror_celsius_per_minute: float | None = None
    target_temp_celsius: float | None = None
    heating_power_mode: str | None = None
    heating_power_percent: int | None = None
    smoke_damper_percent: int | None = None
    roller_percent: int | None = None
    power_status: str | None = None


class CurveEvent(BaseModel):
    type: str
    label: str
    time_seconds: float | None = None
    bean_temp_celsius: float | None = None


class CurveStage(BaseModel):
    name: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    ratio_percent: float
    avg_ror: float | None = None


class CurveControlChange(BaseModel):
    time_seconds: float
    parameter: str
    old_value: float | None = None
    new_value: float


class CurveComparisonPoint(BaseModel):
    sample_index: int
    elapsed_seconds: float
    aligned_seconds: float
    bean_temp_celsius: float | None = None
    environment_temp_celsius: float | None = None
    ror_celsius_per_minute: float | None = None
    heating_power_percent: int | None = None
    smoke_damper_percent: int | None = None
    roller_percent: int | None = None


class CurveFileResponse(BaseModel):
    id: str
    roasting_batch_id: str
    original_filename: str
    file_size_bytes: int
    source_type: str
    format_type: str
    parse_status: str
    parse_error_code: str | None = None
    parse_error_message: str | None = None
    uploaded_at: str | None = None
    parsed_at: str | None = None

    model_config = {"from_attributes": True}


class CurveResponse(BaseModel):
    curve_file: CurveFileResponse | None = None
    summary: dict | None = None
    stages: list[CurveStage] = Field(default_factory=list)
    events: list[CurveEvent] = Field(default_factory=list)
    points: list[CurvePoint] = Field(default_factory=list)
    control_changes: list[CurveControlChange] = Field(default_factory=list)


class MetricDifference(BaseModel):
    metric: str
    label: str
    base_value: float | None = None
    comparison_value: float | None = None
    difference: float | None = None
    unit: str | None = None
    calculation_rule: str | None = None


class CurveComparisonWarning(BaseModel):
    code: str
    severity: str
    batch_id: str
    message: str


class CurveComparisonResponse(BaseModel):
    base_batch_id: str
    align_by: str
    series: list[dict] = Field(default_factory=list)
    metric_differences: list[MetricDifference] = Field(default_factory=list)
    event_time_differences: list[dict] = Field(default_factory=list)
    warnings: list[CurveComparisonWarning] = Field(default_factory=list)
    missing_batch_ids: list[str] = Field(default_factory=list)
    calculation_meta: dict = Field(default_factory=dict)


# ============================================================
# Questionnaires
# ============================================================
class QuestionnaireResponse(BaseModel):
    id: str
    roasting_batch_id: str
    status: str
    share_code: str
    share_url: str | None = None
    created_at: str
    expires_at: str | None = None
    closed_at: str | None = None
    submission_count: int

    model_config = {"from_attributes": True}


class QuestionnaireCreateResponse(BaseModel):
    id: str
    status: str
    share_code: str
    share_url: str
    expires_at: str | None = None


class PublicQuestionnaireResponse(BaseModel):
    share_code: str
    roast_date: str | None = None
    green_bean_name: str | None = None
    status: str
    expires_at: str | None = None


# ============================================================
# Evaluations
# ============================================================
# Controlled vocabularies for the public evaluation form. drink_temperature /
# drink_form / evaluator_type are Literal enums (matching the values the
# frontend sends) — they are NOT free text and never create standard terms.
# brew_method and flavor_notes are *standard-term backed*: the public endpoint
# only accepts active terms and returns 422 for unknown values (it never
# creates terms). Free-text flavor descriptions go to free_flavor_description.
FlavorNoteStr = Annotated[str, StringConstraints(max_length=128, strip_whitespace=False)]


class EvaluationSubmitRequest(BaseModel):
    evaluator_name: str | None = Field(default=None, max_length=64)
    evaluator_type: Literal["roaster", "colleague", "customer"] | None = None
    brew_method: str | None = Field(default=None, max_length=128)
    # Preferred: submit term IDs directly. When provided, these take
    # precedence over the display-value fields below and are validated active.
    brew_method_term_id: str | None = None
    drink_temperature: Literal["热饮", "冷饮"] | None = None
    drink_form: Literal["黑咖啡", "加奶", "其他"] | None = None
    dry_fragrance_score: int | None = Field(default=None, ge=1, le=5)
    wet_aroma_score: int | None = Field(default=None, ge=1, le=5)
    acidity_intensity_score: int | None = Field(default=None, ge=1, le=5)
    sweetness_score: int | None = Field(default=None, ge=1, le=5)
    bitterness_intensity_score: int | None = Field(default=None, ge=1, le=5)
    aftertaste_score: int | None = Field(default=None, ge=1, le=5)
    overall_preference_score: int = Field(ge=1, le=5)
    flavor_notes: list[FlavorNoteStr] = Field(default_factory=list, max_length=50)
    flavor_term_ids: list[str] = Field(default_factory=list, max_length=50)
    free_flavor_description: str | None = Field(default=None, max_length=2000)
    free_notes: str | None = Field(default=None, max_length=2000)


class DimensionSummary(BaseModel):
    label: str
    average: float | None = None
    valid_count: int = 0


class FlavorFrequency(BaseModel):
    name: str
    count: int


class EvaluationResponse(BaseModel):
    id: str
    questionnaire_id: str
    evaluator_name: str | None = None
    evaluator_type: str | None = None
    brew_method: str | None = None
    drink_temperature: str | None = None
    drink_form: str | None = None
    dry_fragrance_score: int | None = None
    wet_aroma_score: int | None = None
    acidity_intensity_score: int | None = None
    sweetness_score: int | None = None
    bitterness_intensity_score: int | None = None
    aftertaste_score: int | None = None
    overall_preference_score: int | None = None
    flavor_notes: list[str] = Field(default_factory=list)
    free_flavor_description: str | None = None
    free_notes: str | None = None
    bean_age_days: int | None = None
    submitted_at: str | None = None

    model_config = {"from_attributes": True}


class EvaluationStatsResponse(BaseModel):
    dimensions: list[DimensionSummary]
    top_flavors: list[FlavorFrequency] = Field(default_factory=list)
    total_submissions: int = 0


# ============================================================
# Reviews
# ============================================================
class ReminderResponse(BaseModel):
    id: str
    priority: int
    content: str


class ReviewOverviewResponse(BaseModel):
    batch: dict | None = None
    review: dict | None = None
    reminders: list[ReminderResponse] = Field(default_factory=list)
    evaluation_summary: str | None = None
    evaluations: list[dict] = Field(default_factory=list)
    questionnaires: list[dict] = Field(default_factory=list)


class PersonalReviewUpdateRequest(BaseModel):
    personal_review: str


class ComprehensiveReviewUpdateRequest(BaseModel):
    comprehensive_review: str


class SuggestionUpdateRequest(BaseModel):
    next_batch_suggestion: str


class RemindersPutRequest(BaseModel):
    reminders: list[dict]


class NextRoastPlanRequest(BaseModel):
    planned_at: datetime
    purchase_batch_id: str
    planned_input_weight_grams: int = Field(gt=0)
    target_description: str | None = None
    review_reminder_ids: list[str] = Field(default_factory=list, max_length=3)


class NextRoastPlanResponse(BaseModel):
    roasting_batch: RoastingBatchResponse
    copied_reminders: int


# ============================================================
# Dashboard
# ============================================================
class PendingGroupResponse(BaseModel):
    bean_id: str
    bean_name: str
    variety: str | None = None
    process: str | None = None
    region: str | None = None
    batch_count: int
    batches: list[dict]


class DashboardResponse(BaseModel):
    year: int
    total_completed_roasts: int
    total_roasted_bean_profiles: int
    total_input_weight_grams: int
    average_weight_loss_percent: float | None = None
    monthly_roasts: list[dict]
    variety_distribution: list[dict]
    region_distribution: list[dict]
    pending_groups: list[PendingGroupResponse]
    recent_batches: list[dict]
    pending_actions: dict


# ============================================================
# Bulk Import (multi-CSV roast generation & historical backfill)
# ============================================================
class BulkImportPreviewItemSummary(BaseModel):
    total_time_seconds: float | None = None
    turning_point_seconds: float | None = None
    yellowing_seconds: float | None = None
    first_crack_start_seconds: float | None = None
    development_ratio_percent: float | None = None
    auc_bt_above_100: float | None = None


class BulkImportPreviewItem(BaseModel):
    item_id: str
    filename: str
    file_hash: str
    file_size_bytes: int
    inferred_roasted_at: str | None = None
    roasted_at_source: str | None = None
    roasted_date_source: str | None = None
    roasted_time_source: str | None = None
    pot_order: int | None = None
    input_weight_grams: int | None = None
    output_weight_grams: int | None = None
    inventory_effective: bool
    parse_status: str  # parsed | failed
    parse_error_message: str | None = None
    summary: dict
    warnings: list[str] = Field(default_factory=list)
    is_duplicate: bool = False


class BulkImportPreviewResponse(BaseModel):
    job_id: str
    purchase_batch_id: str | None = None
    mode: str
    inventory_effective_default: bool
    available_stock_grams: int
    total_planned_input_grams: int
    items: list[BulkImportPreviewItem]
    blocking_errors: list[str] = Field(default_factory=list)


class BulkImportCommitItem(BaseModel):
    item_id: str
    roasted_at: datetime | None = None
    actual_input_weight_grams: int | None = Field(default=None, gt=0)
    output_weight_grams: int | None = Field(default=None, gt=0)
    inventory_effective: bool | None = None
    source_note: str | None = None


class BulkImportCommitResultItem(BaseModel):
    item_id: str
    filename: str | None = None
    success: bool
    roasting_batch_id: str | None = None
    error_message: str | None = None


class BulkImportCommitResponse(BaseModel):
    job_id: str
    status: str
    success_count: int
    failed_count: int
    total_consumed_grams: int
    items: list[BulkImportCommitResultItem]
