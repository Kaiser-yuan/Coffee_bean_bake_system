"""
SQLAlchemy ORM models — 15 tables covering the full coffee roast system.
Database: PostgreSQL 17
Naming: snake_case in DB, matching REST API conventions.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint, CheckConstraint, JSON, BigInteger, Enum as SQLEnum, true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ============================================================
# 1. users — 用户
# ============================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ============================================================
# 2. standard_terms — 标准词表
# ============================================================
class StandardTerm(Base):
    __tablename__ = "standard_terms"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="flavor|defect|roast_level|process|variety|region|brew_method|drink_temperature|drink_form|evaluator_type|supplier"
    )
    value: Mapped[str] = mapped_column(String(128), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("category", "value", name="uq_term_category_value"),
    )


# ============================================================
# 3. green_beans — 生豆档案
# ============================================================
class GreenBean(Base):
    __tablename__ = "green_beans"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    variety_term_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("standard_terms.id"))
    process_term_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("standard_terms.id"))
    region: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(128))
    farm: Mapped[str | None] = mapped_column(String(256))
    elevation: Mapped[str | None] = mapped_column(String(64))
    brand: Mapped[str | None] = mapped_column(String(128))
    harvest_season: Mapped[str | None] = mapped_column(String(64))
    vendor_flavor_description: Mapped[str | None] = mapped_column(Text)
    first_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # relationships
    variety = relationship("StandardTerm", foreign_keys=[variety_term_id])
    process = relationship("StandardTerm", foreign_keys=[process_term_id])
    purchase_batches = relationship("PurchaseBatch", back_populates="green_bean")


# ============================================================
# 4. purchase_batches — 采购批次
# ============================================================
class PurchaseBatch(Base):
    __tablename__ = "purchase_batches"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    green_bean_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("green_beans.id"), nullable=False, index=True)
    purchase_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    inventory_tracking_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="normal",
        comment="normal|historical_archive — normal tracks stock; historical_archive is archive-only"
    )
    opening_stock_grams: Mapped[int | None] = mapped_column(
        Integer,
        comment="Opening stock when this batch entered the system. NULL = total_weight_grams"
    )
    moisture_content_percent: Mapped[float | None] = mapped_column(Float)
    unit_price_fen_per_kg: Mapped[int | None] = mapped_column(BigInteger, comment="单价：分/公斤")
    total_price_fen: Mapped[int | None] = mapped_column(BigInteger, comment="总价：分")
    supplier_term_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("standard_terms.id"))
    lot_number: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("total_weight_grams > 0", name="ck_pb_weight_positive"),
    )

    # relationships
    green_bean = relationship("GreenBean", back_populates="purchase_batches")
    supplier = relationship("StandardTerm", foreign_keys=[supplier_term_id])
    adjustments = relationship("InventoryAdjustment", back_populates="purchase_batch")


# ============================================================
# 5. inventory_adjustments — 库存调整
# ============================================================
class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    purchase_batch_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("purchase_batches.id"), nullable=False, index=True)
    adjustment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount_grams: Mapped[int] = mapped_column(Integer, nullable=False, comment="正数为增加，负数为扣减")
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    purchase_batch = relationship("PurchaseBatch", back_populates="adjustments")


# ============================================================
# 6. roasting_batches — 烘焙批次
# ============================================================
class RoastingBatch(Base):
    __tablename__ = "roasting_batches"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    purchase_batch_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("purchase_batches.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="planned", index=True,
        comment="planned|completed|voided"
    )
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roasted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Weights
    planned_input_weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_input_weight_grams: Mapped[int | None] = mapped_column(Integer)
    output_weight_grams: Mapped[int | None] = mapped_column(Integer)

    # Derived
    weight_loss_percent: Mapped[float | None] = mapped_column(Float)
    total_time_seconds: Mapped[int | None] = mapped_column(Integer)
    development_time_seconds: Mapped[int | None] = mapped_column(Integer)
    development_ratio_percent: Mapped[float | None] = mapped_column(Float)

    # Roast level
    roast_level_term_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("standard_terms.id"))

    target_description: Mapped[str | None] = mapped_column(Text)
    color_tag: Mapped[str | None] = mapped_column(String(7))

    # Entry / backfill metadata (see bulk import & historical backfill design)
    entry_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual_plan", server_default="manual_plan",
        comment="manual_plan|manual_completed|csv_bulk_import|historical_backfill",
    )
    inventory_effective: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(),
        comment="true=影响当前库存；false=仅归档",
    )
    roasted_at_source: Mapped[str | None] = mapped_column(
        String(32),
        comment="csv_content|filename|file_last_modified|manual|upload_order",
    )
    bulk_import_group_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        comment="同一次批量上传的分组 ID（对应 bulk_import_jobs.id）",
    )
    source_note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Status constraints
    __table_args__ = (
        CheckConstraint("planned_input_weight_grams > 0", name="ck_rb_weight_positive"),
    )

    # relationships
    purchase_batch = relationship("PurchaseBatch")
    roast_level = relationship("StandardTerm", foreign_keys=[roast_level_term_id])
    curve_files = relationship("CurveFile", back_populates="roasting_batch")
    active_curve = relationship("RoastingCurve", back_populates="roasting_batch", uselist=False)
    questionnaires = relationship("Questionnaire", back_populates="roasting_batch")
    review = relationship("BatchReview", back_populates="roasting_batch", uselist=False)
    reminders = relationship("BatchReminder", back_populates="roasting_batch")


# ============================================================
# 7. curve_files — 曲线原始文件
# ============================================================
class CurveFile(Base):
    __tablename__ = "curve_files"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    roasting_batch_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("roasting_batches.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="SHA-256")
    source_type: Mapped[str] = mapped_column(String(32), default="kaleido_m1")
    format_type: Mapped[str] = mapped_column(String(32), default="kaleido_kldo_v101")
    parse_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending",
        comment="pending|parsing|parsed|failed"
    )
    parse_error_code: Mapped[str | None] = mapped_column(String(64))
    parse_error_message: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str | None] = mapped_column(String(16))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roasting_batch = relationship("RoastingBatch", back_populates="curve_files")


# ============================================================
# 8. roasting_curves — 当前生效曲线
# ============================================================
class RoastingCurve(Base):
    __tablename__ = "roasting_curves"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    roasting_batch_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("roasting_batches.id"), nullable=False, unique=True, index=True)
    curve_file_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("curve_files.id"), nullable=False)

    # Summary
    preheat_temp_celsius: Mapped[float | None] = mapped_column(Float)
    total_time_seconds: Mapped[float | None] = mapped_column(Float)

    # Event times (seconds from charge)
    charge_seconds: Mapped[float | None] = mapped_column(Float, default=0.0)
    turning_point_seconds: Mapped[float | None] = mapped_column(Float)
    yellowing_seconds: Mapped[float | None] = mapped_column(Float)
    first_crack_start_seconds: Mapped[float | None] = mapped_column(Float)
    first_crack_end_seconds: Mapped[float | None] = mapped_column(Float)
    second_crack_start_seconds: Mapped[float | None] = mapped_column(Float)
    second_crack_end_seconds: Mapped[float | None] = mapped_column(Float)
    drop_seconds: Mapped[float | None] = mapped_column(Float)

    # Stage durations
    drying_time_seconds: Mapped[float | None] = mapped_column(Float)
    drying_ratio_percent: Mapped[float | None] = mapped_column(Float)
    maillard_time_seconds: Mapped[float | None] = mapped_column(Float)
    maillard_ratio_percent: Mapped[float | None] = mapped_column(Float)
    development_time_seconds: Mapped[float | None] = mapped_column(Float)
    development_ratio_percent: Mapped[float | None] = mapped_column(Float)

    # JSON arrays
    points: Mapped[dict | None] = mapped_column(JSON, comment="Array of curve data points")
    events: Mapped[dict | None] = mapped_column(JSON)
    stages: Mapped[dict | None] = mapped_column(JSON)
    control_changes: Mapped[dict | None] = mapped_column(JSON)

    calculation_version: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    roasting_batch = relationship("RoastingBatch", back_populates="active_curve")
    curve_file = relationship("CurveFile")


# ============================================================
# 9. questionnaires — 评价问卷
# ============================================================
class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    roasting_batch_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("roasting_batches.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="open",
        comment="open|closed (expired 由 expires_at 动态计算)"
    )
    share_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    share_url: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission_count: Mapped[int] = mapped_column(Integer, default=0)

    roasting_batch = relationship("RoastingBatch", back_populates="questionnaires")
    evaluations = relationship("CuppingEvaluation", back_populates="questionnaire")


# ============================================================
# 10. cupping_evaluations — 杯测评价
# ============================================================
class CuppingEvaluation(Base):
    __tablename__ = "cupping_evaluations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    questionnaire_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("questionnaires.id"), nullable=False, index=True)
    roasting_batch_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("roasting_batches.id"), nullable=False, index=True)

    evaluator_name: Mapped[str | None] = mapped_column(String(64))
    evaluator_type: Mapped[str | None] = mapped_column(String(16), comment="roaster|colleague|customer")

    brew_method_term_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("standard_terms.id"))
    drink_temperature: Mapped[str | None] = mapped_column(String(8), comment="hot|cold")
    drink_form: Mapped[str | None] = mapped_column(String(16), comment="black|milk|other")

    # Scores 1-5, NULL = not evaluated
    dry_fragrance_score: Mapped[int | None] = mapped_column(Integer)
    wet_aroma_score: Mapped[int | None] = mapped_column(Integer)
    acidity_intensity_score: Mapped[int | None] = mapped_column(Integer)
    sweetness_score: Mapped[int | None] = mapped_column(Integer)
    bitterness_intensity_score: Mapped[int | None] = mapped_column(Integer)
    aftertaste_score: Mapped[int | None] = mapped_column(Integer)
    overall_preference_score: Mapped[int | None] = mapped_column(Integer, nullable=False)

    flavor_term_ids: Mapped[dict | None] = mapped_column(JSON, comment="Array of standard_term UUIDs")
    free_flavor_description: Mapped[str | None] = mapped_column(
        Text, comment="自由风味描述（不进入标准词表）"
    )
    free_notes: Mapped[str | None] = mapped_column(Text)

    bean_age_days: Mapped[int | None] = mapped_column(Integer)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    questionnaire = relationship("Questionnaire", back_populates="evaluations")
    brew_method = relationship("StandardTerm", foreign_keys=[brew_method_term_id])


# ============================================================
# 11. batch_reviews — 批次复盘
# ============================================================
class BatchReview(Base):
    __tablename__ = "batch_reviews"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    roasting_batch_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("roasting_batches.id"),
        nullable=False, unique=True, index=True
    )

    personal_review: Mapped[str | None] = mapped_column(Text)
    personal_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    evaluation_summary: Mapped[str | None] = mapped_column(Text)
    comprehensive_review: Mapped[str | None] = mapped_column(Text)
    comprehensive_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    next_batch_suggestion: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    roasting_batch = relationship("RoastingBatch", back_populates="review")
    source_reminders = relationship("ReviewReminder", back_populates="batch_review")


# ============================================================
# 12. review_reminders — 复盘来源提醒
# ============================================================
class ReviewReminder(Base):
    __tablename__ = "review_reminders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    batch_review_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("batch_reviews.id"), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, comment="1|2|3")
    content: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 3", name="ck_reminder_priority"),
    )

    batch_review = relationship("BatchReview", back_populates="source_reminders")


# ============================================================
# 13. batch_reminders — 烘焙批次提醒快照
# ============================================================
class BatchReminder(Base):
    """Immutable reminder snapshots copied to a roasting batch.

    source_review_reminder_id is stored as a plain UUID field (no FK constraint)
    so that deleting a review's reminders does not break existing batches.
    """
    __tablename__ = "batch_reminders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    roasting_batch_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("roasting_batches.id"), nullable=False, index=True)
    source_review_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    source_roasting_batch_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    source_review_reminder_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 3", name="ck_batch_rem_priority"),
    )

    roasting_batch = relationship("RoastingBatch", back_populates="reminders")


# ============================================================
# 14. inventory_ledger — 库存流水
# ============================================================
class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    purchase_batch_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("purchase_batches.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="purchase_in|roast_consumption|roast_return|adjustment"
    )
    related_entity_type: Mapped[str | None] = mapped_column(String(32), comment="roasting_batch|inventory_adjustment")
    related_entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    change_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    resulting_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ============================================================
# 15. bulk_import_jobs — 批量导入任务
# ============================================================
class BulkImportJob(Base):
    """一次批量 CSV 上传（多 CSV 生成烘焙批次 / 历史补录）的导入任务。

    一个 job 包含多个 BulkImportItem；预览阶段落库 job+items，
    提交阶段据此创建 roasting_batches / curve_files / curves。
    """
    __tablename__ = "bulk_import_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    purchase_batch_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("purchase_batches.id"), index=True,
    )
    mode: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="csv_bulk_import|historical_backfill",
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="previewed", server_default="previewed",
        comment="previewed|committed|failed|cancelled",
    )
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    default_input_weight_grams: Mapped[int | None] = mapped_column(Integer)
    inventory_effective_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(),
    )
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    items = relationship("BulkImportItem", back_populates="job", cascade="all, delete-orphan")


# ============================================================
# 16. bulk_import_items — 批量导入条目（每个 CSV 一行）
# ============================================================
class BulkImportItem(Base):
    """单个 CSV 在一次批量导入中的预览/提交记录。"""
    __tablename__ = "bulk_import_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bulk_import_jobs.id"), nullable=False, index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    client_last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inferred_roasted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roasted_at_source: Mapped[str | None] = mapped_column(
        String(32),
        comment="csv_content|filename|file_last_modified|manual|upload_order",
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    parse_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="parsed", server_default="parsed",
        comment="parsed|failed",
    )
    parse_error_message: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[dict | None] = mapped_column(JSON)
    preview_summary: Mapped[dict | None] = mapped_column(JSON)
    roasting_batch_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("roasting_batches.id"),
    )
    curve_file_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("curve_files.id"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job = relationship("BulkImportJob", back_populates="items")
