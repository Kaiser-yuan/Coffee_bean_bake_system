"""Schema validation tests."""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from app.schemas.all_schemas import (
    RoastingBatchCreateRequest,
    BatchCompleteRequest,
    OutputWeightUpdateRequest,
    EvaluationSubmitRequest,
    InventoryAdjustmentRequest,
    GreenBeanWithFirstPurchaseRequest,
    NextRoastPlanRequest,
    BulkImportCommitItem,
)


class TestRoastingBatchCreate:
    def test_valid_request(self):
        req = RoastingBatchCreateRequest(
            purchase_batch_id="pb-123",
            planned_at=datetime.now(timezone.utc),
            planned_input_weight_grams=500,
        )
        assert req.planned_input_weight_grams == 500
        assert isinstance(req.planned_at, datetime)

    def test_zero_weight_rejected(self):
        with pytest.raises(ValidationError):
            RoastingBatchCreateRequest(
                purchase_batch_id="pb-123",
                planned_at=datetime.now(timezone.utc),
                planned_input_weight_grams=0,
            )

    def test_negative_weight_rejected(self):
        with pytest.raises(ValidationError):
            RoastingBatchCreateRequest(
                purchase_batch_id="pb-123",
                planned_at=datetime.now(timezone.utc),
                planned_input_weight_grams=-100,
            )

    def test_planned_at_must_be_datetime(self):
        with pytest.raises(ValidationError):
            RoastingBatchCreateRequest(
                purchase_batch_id="pb-123",
                planned_at="not-a-date",
                planned_input_weight_grams=500,
            )


class TestBatchComplete:
    def test_valid_request(self):
        req = BatchCompleteRequest(
            roasted_at=datetime.now(timezone.utc),
            actual_input_weight_grams=500,
        )
        assert req.actual_input_weight_grams == 500

    def test_zero_actual_weight_rejected(self):
        with pytest.raises(ValidationError):
            BatchCompleteRequest(
                roasted_at=datetime.now(timezone.utc),
                actual_input_weight_grams=0,
            )


class TestOutputWeight:
    def test_valid_request(self):
        req = OutputWeightUpdateRequest(output_weight_grams=450)
        assert req.output_weight_grams == 450

    def test_zero_output_rejected(self):
        with pytest.raises(ValidationError):
            OutputWeightUpdateRequest(output_weight_grams=0)


class TestEvaluationScores:
    def test_valid_scores(self):
        req = EvaluationSubmitRequest(
            dry_fragrance_score=4,
            wet_aroma_score=3,
            overall_preference_score=5,
        )
        assert req.dry_fragrance_score == 4

    def test_score_below_1_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationSubmitRequest(
                dry_fragrance_score=0,
                overall_preference_score=5,
            )

    def test_score_above_5_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationSubmitRequest(
                overall_preference_score=6,
            )

    def test_missing_overall_preference_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationSubmitRequest(
                dry_fragrance_score=4,
            )


class TestInventoryAdjustment:
    def test_valid_adjustment(self):
        req = InventoryAdjustmentRequest(
            amount_grams=100,
            reason="补录",
        )
        assert req.amount_grams == 100

    def test_missing_reason_rejected(self):
        with pytest.raises(ValidationError):
            InventoryAdjustmentRequest(amount_grams=100)


class TestGreenBeanWithFirstPurchase:
    def test_valid_request(self):
        req = GreenBeanWithFirstPurchaseRequest(
            name="Test Bean",
            total_weight_grams=1000,
        )
        assert req.name == "Test Bean"

    def test_zero_total_weight_rejected(self):
        with pytest.raises(ValidationError):
            GreenBeanWithFirstPurchaseRequest(
                name="Test Bean",
                total_weight_grams=0,
            )


class TestNextRoastPlan:
    def test_valid_plan(self):
        req = NextRoastPlanRequest(
            planned_at=datetime.now(timezone.utc),
            purchase_batch_id="pb-123",
            planned_input_weight_grams=500,
        )
        assert req.planned_input_weight_grams == 500

    def test_zero_weight_rejected(self):
        with pytest.raises(ValidationError):
            NextRoastPlanRequest(
                planned_at=datetime.now(timezone.utc),
                purchase_batch_id="pb-123",
                planned_input_weight_grams=0,
            )


def test_bulk_commit_item_python_dump_keeps_datetime():
    roasted_at = datetime.now(timezone.utc)
    item = BulkImportCommitItem(item_id="item-1", roasted_at=roasted_at)
    assert item.model_dump(mode="python")["roasted_at"] == roasted_at
