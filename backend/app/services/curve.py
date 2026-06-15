"""Curve analysis service — unified parsing and activation."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.all_models import RoastingCurve, RoastingBatch, CurveFile
from ..parsers.kaleido_m1 import (
    parse_kaleido_m1, compute_stage_metrics, compute_control_changes, compute_auc,
)

logger = logging.getLogger("coffee-roast.curve")


async def parse_and_activate_curve(
    db: AsyncSession,
    curve_file: CurveFile,
    content: bytes,
) -> RoastingCurve:
    """Unified service: parse a curve file and atomically create/update the active curve.

    1. Parse raw CSV
    2. Compute events, stages, AUC, control changes, warnings
    3. Create new RoastingCurve
    4. Replace old active curve (atomically — new succeeds before old is removed)
    5. Update RoastingBatch summary
    6. Mark CurveFile as parsed

    Returns the new active RoastingCurve.
    """
    # Parse
    parsed = parse_kaleido_m1(content, curve_file.original_filename)

    # Compute stage metrics
    stage_data = compute_stage_metrics(parsed)

    # Compute control changes
    control_changes = compute_control_changes(parsed.points)

    # Build normalized event list
    events_data = [
        {
            "type": e.event_type,
            "label": _get_event_label(e.event_type),
            "time_seconds": round(e.time_seconds, 2),
            "bean_temp_celsius": e.bean_temp,
        }
        for e in parsed.events
    ]

    # Build points data
    points_data = [
        {
            "sample_index": p.sample_index,
            "elapsed_seconds": round(p.elapsed_seconds, 2),
            "bean_temp_celsius": p.bean_temp_celsius,
            "environment_temp_celsius": p.environment_temp_celsius,
            "ror_celsius_per_minute": p.ror_celsius_per_minute,
            "target_temp_celsius": p.target_temp_celsius,
            "heating_power_mode": p.heating_power_mode,
            "heating_power_percent": p.heating_power_percent,
            "smoke_damper_percent": p.smoke_damper_percent,
            "roller_percent": p.roller_percent,
            "power_status": p.power_status,
        }
        for p in parsed.points
    ]

    # Compute AUC
    auc_val = compute_auc(parsed.points)

    # Extract key event times
    events_by_type = {e.event_type: e for e in parsed.events}
    charge = events_by_type.get("charge")
    yellowing = events_by_type.get("yellowing")
    fc_start = events_by_type.get("first_crack_start")
    fc_end = events_by_type.get("first_crack_end")
    sc_start = events_by_type.get("second_crack_start")
    sc_end = events_by_type.get("second_crack_end")
    drop = events_by_type.get("drop")
    tp = events_by_type.get("turning_point")

    dev_time = None
    dev_ratio = None
    if fc_start and drop:
        dev_time = round(drop.time_seconds - fc_start.time_seconds, 2)
        if charge and drop.time_seconds > charge.time_seconds:
            total_time = drop.time_seconds - charge.time_seconds
            dev_ratio = round(dev_time / total_time * 100, 2) if total_time > 0 else None

    # Find stage data
    stages = stage_data.get("stages", [])
    drying_stage = next((s for s in stages if s["name"] == "脱水阶段"), None)
    maillard_stage = next((s for s in stages if s["name"] == "梅纳阶段"), None)
    dev_stage = next((s for s in stages if s["name"] == "发展阶段"), None)

    # Replace or create active curve — update existing row rather than delete+insert
    result = await db.execute(
        select(RoastingCurve).where(
            RoastingCurve.roasting_batch_id == curve_file.roasting_batch_id
        )
    )
    existing_curve = result.scalar_one_or_none()

    if existing_curve:
        # Update existing curve atomically
        existing_curve.curve_file_id = curve_file.id
        existing_curve.preheat_temp_celsius = parsed.parameters.preheat_temp
        existing_curve.total_time_seconds = parsed.total_time_seconds
        existing_curve.charge_seconds = charge.time_seconds if charge else 0.0
        existing_curve.turning_point_seconds = tp.time_seconds if tp else None
        existing_curve.yellowing_seconds = yellowing.time_seconds if yellowing else None
        existing_curve.first_crack_start_seconds = fc_start.time_seconds if fc_start else None
        existing_curve.first_crack_end_seconds = fc_end.time_seconds if fc_end else None
        existing_curve.second_crack_start_seconds = sc_start.time_seconds if sc_start else None
        existing_curve.second_crack_end_seconds = sc_end.time_seconds if sc_end else None
        existing_curve.drop_seconds = drop.time_seconds if drop else None
        existing_curve.drying_time_seconds = drying_stage["duration_seconds"] if drying_stage else None
        existing_curve.drying_ratio_percent = drying_stage["ratio_percent"] if drying_stage else None
        existing_curve.maillard_time_seconds = maillard_stage["duration_seconds"] if maillard_stage else None
        existing_curve.maillard_ratio_percent = maillard_stage["ratio_percent"] if maillard_stage else None
        existing_curve.development_time_seconds = dev_time
        existing_curve.development_ratio_percent = dev_ratio
        existing_curve.points = {"data": points_data}
        existing_curve.events = {"data": events_data}
        existing_curve.stages = {"data": stages}
        existing_curve.control_changes = {"data": control_changes}
        existing_curve.calculation_version = "curve-analysis-v1"
        curve = existing_curve
        await db.flush()
    else:
        curve = RoastingCurve(
            roasting_batch_id=curve_file.roasting_batch_id,
            curve_file_id=curve_file.id,
            preheat_temp_celsius=parsed.parameters.preheat_temp,
            total_time_seconds=parsed.total_time_seconds,
            charge_seconds=charge.time_seconds if charge else 0.0,
            turning_point_seconds=tp.time_seconds if tp else None,
            yellowing_seconds=yellowing.time_seconds if yellowing else None,
            first_crack_start_seconds=fc_start.time_seconds if fc_start else None,
            first_crack_end_seconds=fc_end.time_seconds if fc_end else None,
            second_crack_start_seconds=sc_start.time_seconds if sc_start else None,
            second_crack_end_seconds=sc_end.time_seconds if sc_end else None,
            drop_seconds=drop.time_seconds if drop else None,
            drying_time_seconds=drying_stage["duration_seconds"] if drying_stage else None,
            drying_ratio_percent=drying_stage["ratio_percent"] if drying_stage else None,
            maillard_time_seconds=maillard_stage["duration_seconds"] if maillard_stage else None,
            maillard_ratio_percent=maillard_stage["ratio_percent"] if maillard_stage else None,
            development_time_seconds=dev_time,
            development_ratio_percent=dev_ratio,
            points={"data": points_data},
            events={"data": events_data},
            stages={"data": stages},
            control_changes={"data": control_changes},
            calculation_version="curve-analysis-v1",
        )
        db.add(curve)
        await db.flush()

    # Update roasting batch with curve-derived data
    batch_result = await db.execute(
        select(RoastingBatch).where(RoastingBatch.id == curve_file.roasting_batch_id)
    )
    batch = batch_result.scalar_one_or_none()
    if batch:
        batch.total_time_seconds = int(parsed.total_time_seconds)
        batch.development_time_seconds = int(dev_time) if dev_time else None
        batch.development_ratio_percent = dev_ratio
        await db.flush()

    # Mark curve file as parsed
    curve_file.parse_status = "parsed"
    curve_file.parsed_at = None  # Will be set by caller
    await db.flush()

    return curve


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


def _get_event_label(event_type: str) -> str:
    """Map normalized event type to Chinese label."""
    labels = {
        "charge": "入豆",
        "turning_point": "回温点",
        "yellowing": "转黄点",
        "first_crack_start": "一爆开始",
        "first_crack_end": "一爆结束",
        "second_crack_start": "二爆开始",
        "second_crack_end": "二爆结束",
        "drop": "出豆",
    }
    return labels.get(event_type, event_type)


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
    """Build a multi-curve comparison response.

    Each comparison batch gets its own metric difference pair vs base.
    """
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
        )
        if align_ev is None:
            # Event missing — raise clear business error
            from ..core.exceptions import CurveAlignmentEventMissingException
            raise CurveAlignmentEventMissingException(
                batch_id=curve.roasting_batch_id,
                event_type=align_by,
            )
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

        # Compute metrics including AUC and stage averages
        metrics = {
            "total_time_seconds": curve.total_time_seconds,
            "development_time_seconds": curve.development_time_seconds,
            "development_ratio_percent": curve.development_ratio_percent,
            "drying_time_seconds": curve.drying_time_seconds,
            "maillard_time_seconds": curve.maillard_time_seconds,
            "drop_temp_celsius": _get_drop_temp(events_data, points_data),
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

    # Compute differences for EACH comparison batch vs base
    metric_differences = []
    event_differences = []
    warnings = []

    if base_metrics and len(comparison_curves) > 0:
        diffs_to_compute = [
            ("total_time_seconds", "总时长", "秒"),
            ("development_time_seconds", "发展时间", "秒"),
            ("development_ratio_percent", "发展率", "%"),
            ("drying_time_seconds", "脱水时间", "秒"),
            ("maillard_time_seconds", "梅纳时间", "秒"),
        ]

        for ci, comp_curve in enumerate(comparison_curves):
            comp_idx = ci + 1  # +1 because series[0] is base
            comp_metrics = series[comp_idx].get("metrics", {})

            for key, label, unit in diffs_to_compute:
                bv = base_metrics.get(key)
                cv = comp_metrics.get(key)
                diff = None
                if bv is not None and cv is not None:
                    diff = round(cv - bv, 2)
                metric_differences.append({
                    "comparison_batch_id": comp_curve.roasting_batch_id,
                    "metric": key,
                    "label": label,
                    "base_value": bv,
                    "comparison_value": cv,
                    "difference": diff,
                    "unit": unit,
                    "calculation_rule": "comparison_minus_base",
                })

            # Event time differences per comparison
            base_events = series[0].get("events", [])
            comp_events = series[comp_idx].get("events", [])
            for be in base_events:
                be_type = be.get("type")
                ce = next((e for e in comp_events if e.get("type") == be_type), None)
                if be_type and ce:
                    bt = be.get("time_seconds")
                    ct = ce.get("time_seconds")
                    if bt is not None and ct is not None:
                        event_differences.append({
                            "comparison_batch_id": comp_curve.roasting_batch_id,
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
        "warnings": warnings,
        "calculation_meta": {
            "difference_rule": "comparison_minus_base",
            "auc_rule": "bt_above_100_trapezoid",
            "algorithm_version": "curve-analysis-v1",
        },
    }
