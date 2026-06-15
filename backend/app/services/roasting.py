"""Roasting batch business logic — state machine and completeness."""
import logging

from ..models.all_models import RoastingBatch

logger = logging.getLogger("coffee-roast.roasting")


def compute_batch_completeness(batch: RoastingBatch) -> dict:
    """Compute data completeness for a roasting batch.

    missing_evaluation is determined by whether the batch
    actually has evaluation submissions, not just a questionnaire.
    """
    has_curve = False
    if hasattr(batch, "active_curve") and batch.active_curve:
        has_curve = True
    elif hasattr(batch, "curve_files") and batch.curve_files:
        has_curve = any(
            f.parse_status == "parsed" for f in batch.curve_files
            if hasattr(f, "parse_status")
        )

    has_evaluation = False
    if hasattr(batch, "questionnaires") and batch.questionnaires:
        for q in batch.questionnaires:
            if q.submission_count > 0:
                has_evaluation = True
                break

    has_review = False
    if hasattr(batch, "review") and batch.review:
        r = batch.review
        has_review = r.comprehensive_review is not None

    missing_output_weight = batch.status == "completed" and batch.output_weight_grams is None
    missing_curve = not has_curve
    missing_evaluation = not has_evaluation
    missing_review = not has_review

    return {
        "missing_output_weight": missing_output_weight,
        "missing_curve": missing_curve,
        "missing_evaluation": missing_evaluation,
        "missing_review": missing_review,
        "is_complete": not any([
            missing_output_weight, missing_curve, missing_evaluation, missing_review,
        ]),
    }


def compute_allowed_actions(batch: RoastingBatch) -> list[str]:
    """Compute allowed UI actions based on batch status."""
    actions = []

    if batch.status == "planned":
        actions = ["complete", "edit", "void"]
    elif batch.status == "completed":
        actions = ["upload_curve", "create_questionnaire", "edit_output_weight", "reopen", "void", "view_curve"]
    elif batch.status == "voided":
        actions = ["view_history"]

    return actions
