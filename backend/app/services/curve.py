"""Curve analysis service."""
import logging

from ..models.all_models import RoastingCurve, RoastingBatch
from ..parsers.kaleido_m1 import (
    compute_stage_metrics, compute_control_changes, compute_auc,
)

logger = logging.getLogger("coffee-roast.curve")


def build_curve_response(curve: RoastingCurve) -> dict:
    """Build a full curve response from the stored curve data."""
    points = curve.points.get("data", []) if curve.points else []
    events_raw = curve.events.get("data", []) if curve.events else []
    stages = curve.stages.get("data", []) if curve.stages else []
    control_changes = curve.control_changes.get("data", []) if curve.control_changes else []

    return {
        "curve_file": {
            "id": curve.curve_file.id if hasattr(curve, 'curve_file') and curve.curve_file else None,
            "original_filename": curve.curve_file.original_filename if hasattr(curve, 'curve_file') and curve.curve_file else None,
            "parse_status": curve.curve_file.parse_status if hasattr(curve, 'curve_file') and curve.curve_file else None,
        },
        "summary": {
            "preheat_temp_celsius": curve.preheat_temp_celsius,
            "total_time_seconds": curve.total_time_seconds,
            "development_time_seconds": curve.development_time_seconds,
            "development_ratio_percent": curve.development_ratio_percent,
            "drying_time_seconds": curve.drying_time_seconds,
            "maillard_time_seconds": curve.maillard_time_seconds,
            "drop_temp_celsius": _get_drop_temp(events_raw, points),
        },
        "events": events_raw,
        "points": points,
        "stages": stages,
        "control_changes": control_changes,
    }


def _get_drop_temp(events: list[dict], points: list[dict]) -> float | None:
    """Get drop event temperature."""
    drop_ev = next((e for e in events if e.get("type") == "drop"), None)
    if drop_ev:
        return drop_ev.get("bean_temp_celsius")
    # Fallback: last point's BT
    if points:
        return points[-1].get("bean_temp_celsius") if isinstance(points[-1], dict) else None
    return None


def get_aligned_seconds(elapsed_seconds: float, align_event_time: float | None) -> float:
    """Compute aligned time relative to an event."""
    if align_event_time is None:
        return elapsed_seconds
    return elapsed_seconds - align_event_time


def compute_curve_comparison(
    base_curve: RoastingCurve,
    comparison_curves: list[RoastingCurve],
    align_by: str = "charge",
) -> dict:
    """Build a multi-curve comparison response."""
    all_curves = [base_curve] + comparison_curves
    series = []
    base_metrics = None

    for i, curve in enumerate(all_curves):
        points_data = curve.points.get("data", []) if curve.points else []
        events_data = curve.events.get("data", []) if curve.events else []

        # Find alignment event time
        align_ev = next(
            (e for e in events_data if e.get("type") == align_by),
            None
        ) if isinstance(events_data, list) and len(events_data) > 0 else None
        align_time = align_ev.get("time_seconds") if align_ev else 0.0

        # Add aligned_seconds to each point
        aligned_points = []
        for p in points_data:
            if isinstance(p, dict):
                aligned_points.append({
                    **p,
                    "aligned_seconds": round(get_aligned_seconds(
                        p.get("elapsed_seconds", 0), align_time
                    ), 2),
                })

        # Compute metrics
        stages_data = curve.stages.get("data", []) if curve.stages else []
        metrics = {
            "total_time_seconds": curve.total_time_seconds,
            "development_time_seconds": curve.development_time_seconds,
            "development_ratio_percent": curve.development_ratio_percent,
            "drying_time_seconds": curve.drying_time_seconds,
            "maillard_time_seconds": curve.maillard_time_seconds,
        }
        if i == 0:
            base_metrics = metrics

        series.append({
            "batch": {
                "id": curve.roasting_batch_id,
            },
            "events": events_data,
            "metrics": metrics,
            "control_changes": curve.control_changes.get("data", []) if curve.control_changes else [],
            "points": aligned_points,
        })

    # Compute differences (comparison - base)
    metric_differences = []
    event_differences = []
    if base_metrics and len(comparison_curves) > 0:
        comp_metrics = series[1].get("metrics", {})

        diffs_to_compute = [
            ("total_time_seconds", "总时长", "秒"),
            ("development_time_seconds", "发展时间", "秒"),
            ("development_ratio_percent", "发展率", "%"),
            ("drying_time_seconds", "脱水时间", "秒"),
            ("maillard_time_seconds", "梅纳时间", "秒"),
        ]
        for key, label, unit in diffs_to_compute:
            bv = base_metrics.get(key)
            cv = comp_metrics.get(key)
            diff = None
            if bv is not None and cv is not None:
                diff = round(cv - bv, 2)
            metric_differences.append({
                "metric": key,
                "label": label,
                "base_value": bv,
                "comparison_value": cv,
                "difference": diff,
                "unit": unit,
                "calculation_rule": "comparison_minus_base",
            })

        # Event time differences
        base_events = series[0].get("events", [])
        comp_events = series[1].get("events", [])
        for be in base_events:
            be_type = be.get("type")
            ce = next((e for e in comp_events if e.get("type") == be_type), None)
            if be_type and ce:
                bt = be.get("time_seconds")
                ct = ce.get("time_seconds")
                if bt is not None and ct is not None:
                    event_differences.append({
                        "event_type": be_type,
                        "label": be.get("label", be_type),
                        "base_time_seconds": bt,
                        "comparison_time_seconds": ct,
                        "difference_seconds": round(ct - bt, 1),
                    })

    return {
        "base_batch_id": base_curve.roasting_batch_id,
        "align_by": align_by,
        "series": series,
        "metric_differences": metric_differences,
        "event_time_differences": event_differences,
        "warnings": [],
        "calculation_meta": {
            "difference_rule": "comparison_minus_base",
            "auc_rule": "bt_above_100_trapezoid",
            "algorithm_version": "curve-analysis-v1",
        },
    }
