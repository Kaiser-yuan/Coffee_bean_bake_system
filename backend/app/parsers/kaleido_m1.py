"""
Kaleido M1 KLDO V101 CSV parser.
Parses Kaleido M1 CSV files with format:
  [{PARAMETERS}]
  [{EVENT}]
  [{DATA}]
  index, Time, BT, ET, RoR, SV, HP, HPM, SM, RL, PS

Reference files: 260530_9.csv, 260530_10.csv
"""
import csv
import hashlib
import io
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("coffee-roast.parser")


@dataclass
class KaleidoParameters:
    preheat_temp: float | None = None
    charge_temp: float | None = None

    @classmethod
    def from_lines(cls, lines: list[str]) -> "KaleidoParameters":
        params = cls()
        for line in lines:
            line = line.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key == "Pre Heat Temperature":
                    try:
                        params.preheat_temp = float(value)
                    except ValueError:
                        pass
                elif key == "Charge Temperature":
                    try:
                        params.charge_temp = float(value)
                    except ValueError:
                        pass
        return params


@dataclass
class KaleidoEvent:
    event_type: str  # charge, tp, yellowing, fc_start, fc_end, sc_start, sc_end, drop
    time_seconds: float
    bean_temp: float | None = None

    def to_normalized_type(self) -> str:
        """Map Kaleido event names to standard type names."""
        mapping = {
            "CHARGE": "charge",
            "TURNING POINT": "turning_point",
            "Y": "yellowing",
            "FCs": "first_crack_start",
            "FCe": "first_crack_end",
            "SCs": "second_crack_start",
            "SCe": "second_crack_end",
            "DROP": "drop",
        }
        return mapping.get(self.event_type, self.event_type.lower())


@dataclass
class KaleidoDataPoint:
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


@dataclass
class KaleidoParsedData:
    file_hash: str
    parameters: KaleidoParameters = field(default_factory=KaleidoParameters)
    events: list[KaleidoEvent] = field(default_factory=list)
    points: list[KaleidoDataPoint] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    @property
    def total_time_seconds(self) -> float:
        return self.points[-1].elapsed_seconds if self.points else 0.0

    @property
    def point_count(self) -> int:
        return len(self.points)


def parse_kaleido_m1(content: bytes, filename: str) -> KaleidoParsedData:
    """Parse a Kaleido M1 KLDO V101 CSV file."""

    # Compute hash
    file_hash = hashlib.sha256(content).hexdigest()

    text = content.decode("utf-8-sig")
    lines = text.splitlines()

    # Identify format
    if not lines:
        raise ValueError("Empty file")

    first_line = lines[0].strip()
    if first_line != "KLDO data file V101":
        raise ValueError(f"Unexpected format: '{first_line}'. Expected 'KLDO data file V101'.")

    data = KaleidoParsedData(file_hash=file_hash)

    # Parse sections
    section = None
    param_lines: list[str] = []
    event_lines: list[str] = []
    data_lines: list[str] = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        if line == "[{PARAMETERS}]":
            section = "params"
            continue
        elif line == "[{EVENT}]":
            section = "events"
            continue
        elif line == "[{DATA}]":
            section = "data"
            continue

        if section == "params":
            param_lines.append(line)
        elif section == "events":
            event_lines.append(line)
        elif section == "data":
            data_lines.append(line)

    # Parse parameters
    data.parameters = KaleidoParameters.from_lines(param_lines)

    # Parse events
    for line in event_lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3:
            event_label = parts[0]
            try:
                time_sec = float(parts[1]) / 1000.0
            except (ValueError, IndexError):
                continue
            bean_temp = None
            try:
                bt_str = parts[2].replace("°C", "").strip()
                if bt_str:
                    bean_temp = float(bt_str)
            except (ValueError, IndexError):
                pass
            data.events.append(KaleidoEvent(
                event_type=event_label,
                time_seconds=time_sec,
                bean_temp=bean_temp,
            ))

    # Parse CSV data section
    if data_lines:
        reader = csv.DictReader(io.StringIO("\n".join(data_lines)))

        for row in reader:
            # Normalize column names (strip whitespace)
            row = {k.strip(): v.strip() for k, v in row.items()}

            sample_idx = int(row.get("index", 0))
            time_ms_raw = row.get("Time", "0")
            time_sec = float(time_ms_raw) / 1000.0

            point = KaleidoDataPoint(
                sample_index=sample_idx,
                elapsed_seconds=time_sec,
            )

            # BT
            bt_raw = row.get("BT", "")
            if bt_raw and bt_raw != "0":
                try:
                    point.bean_temp_celsius = float(bt_raw) / 10.0
                except ValueError:
                    pass

            # ET
            et_raw = row.get("ET", "")
            if et_raw and et_raw != "0":
                try:
                    point.environment_temp_celsius = float(et_raw) / 10.0
                except ValueError:
                    pass

            # RoR
            ror_raw = row.get("RoR", "")
            if ror_raw and ror_raw != "0":
                try:
                    point.ror_celsius_per_minute = float(ror_raw) / 10.0
                except ValueError:
                    pass

            # SV
            sv_raw = row.get("SV", "")
            if sv_raw and sv_raw != "0":
                try:
                    point.target_temp_celsius = float(sv_raw) / 10.0
                except ValueError:
                    pass

            # HP — heating power
            hp_raw = row.get("HP", "")
            if hp_raw:
                try:
                    val = int(hp_raw)
                    if val > 0:
                        point.heating_power_percent = val
                except ValueError:
                    pass

            # HPM — heating power mode
            hpm_raw = row.get("HPM", "")
            if hpm_raw:
                point.heating_power_mode = hpm_raw

            # SM — smoke damper
            sm_raw = row.get("SM", "")
            if sm_raw:
                try:
                    val = int(sm_raw)
                    if val >= 0:
                        point.smoke_damper_percent = val
                except ValueError:
                    pass

            # RL — roller
            rl_raw = row.get("RL", "")
            if rl_raw:
                try:
                    val = int(rl_raw)
                    if val >= 0:
                        point.roller_percent = val
                except ValueError:
                    pass

            # PS — power status
            ps_raw = row.get("PS", "")
            if ps_raw:
                point.power_status = ps_raw

            data.points.append(point)

    # Add data quality warnings
    _check_data_quality(data)

    return data


def _check_data_quality(data: KaleidoParsedData) -> None:
    """Generate data quality warnings without modifying raw data."""
    if not data.points:
        return

    # Check charge event temperature vs first BT sample
    charge_ev = next((e for e in data.events if e.event_type == "CHARGE"), None)
    if charge_ev and data.points:
        first_bt = data.points[0].bean_temp_celsius
        if charge_ev.bean_temp and first_bt and abs(charge_ev.bean_temp - first_bt) > 5:
            data.warnings.append({
                "code": "CHARGE_TEMP_DIFFERS",
                "severity": "warning",
                "message": f"入豆事件温度({charge_ev.bean_temp}°C)与首个BT采样值({first_bt}°C)存在差异，请核对事件标记或探针记录。",
                "related_event": "charge",
            })

    # Check for missing key events
    event_types = {e.event_type for e in data.events}
    key_events = ["CHARGE", "DROP"]
    for ke in key_events:
        if ke not in event_types:
            data.warnings.append({
                "code": f"MISSING_{ke}",
                "severity": "warning",
                "message": f"缺少关键事件: {ke}",
                "related_event": ke.lower(),
            })


def compute_stage_metrics(data: KaleidoParsedData) -> dict:
    """Compute stage durations, ratios, and average RoR from parsed data."""
    events_by_type = {e.to_normalized_type(): e for e in data.events}

    charge = events_by_type.get("charge")
    yellowing = events_by_type.get("yellowing")
    first_crack_start = events_by_type.get("first_crack_start")
    drop = events_by_type.get("drop")

    if not charge or not drop:
        return {"stages": [], "total_time_seconds": data.total_time_seconds}

    total = drop.time_seconds - charge.time_seconds
    stages = []

    # Drying: charge -> yellowing
    if yellowing:
        drying_end = yellowing.time_seconds
    elif first_crack_start:
        drying_end = first_crack_start.time_seconds * 0.55  # fallback estimate
    else:
        drying_end = total * 0.53
    drying_duration = drying_end - charge.time_seconds
    avg_ror_drying = _compute_avg_ror(data.points, charge.time_seconds, drying_end)
    stages.append({
        "name": "脱水阶段",
        "start_seconds": charge.time_seconds,
        "end_seconds": drying_end,
        "duration_seconds": round(drying_duration, 1),
        "ratio_percent": round(drying_duration / total * 100, 1) if total > 0 else 0,
        "avg_ror": avg_ror_drying,
    })

    # Maillard: yellowing -> first_crack_start
    if yellowing and first_crack_start:
        maillard_start = yellowing.time_seconds
        maillard_end = first_crack_start.time_seconds
        maillard_duration = maillard_end - maillard_start
        avg_ror_maillard = _compute_avg_ror(data.points, maillard_start, maillard_end)
        stages.append({
            "name": "梅纳阶段",
            "start_seconds": round(maillard_start, 1),
            "end_seconds": round(maillard_end, 1),
            "duration_seconds": round(maillard_duration, 1),
            "ratio_percent": round(maillard_duration / total * 100, 1) if total > 0 else 0,
            "avg_ror": avg_ror_maillard,
        })

    # Development: first_crack_start -> drop
    if first_crack_start:
        dev_start = first_crack_start.time_seconds
        dev_end = drop.time_seconds
        dev_duration = dev_end - dev_start
        avg_ror_dev = _compute_avg_ror(data.points, dev_start, dev_end)
        stages.append({
            "name": "发展阶段",
            "start_seconds": round(dev_start, 1),
            "end_seconds": round(dev_end, 1),
            "duration_seconds": round(dev_duration, 1),
            "ratio_percent": round(dev_duration / total * 100, 1) if total > 0 else 0,
            "avg_ror": avg_ror_dev,
        })

    return {
        "stages": stages,
        "total_time_seconds": round(total, 1),
    }


def _compute_avg_ror(points: list[KaleidoDataPoint], start_sec: float, end_sec: float) -> float | None:
    """Compute average RoR over a time range, excluding None values."""
    vals = [
        p.ror_celsius_per_minute
        for p in points
        if start_sec <= p.elapsed_seconds <= end_sec
        and p.ror_celsius_per_minute is not None
        and p.ror_celsius_per_minute > 0
    ]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


def compute_control_changes(points: list[KaleidoDataPoint]) -> list[dict]:
    """Detect control parameter changes (HP, SM, RL)."""
    changes: list[dict] = []
    if len(points) < 2:
        return changes

    prev = points[0]
    for p in points[1:]:
        if (p.heating_power_percent is not None
                and prev.heating_power_percent is not None
                and p.heating_power_percent != prev.heating_power_percent):
            changes.append({
                "time_seconds": p.elapsed_seconds,
                "parameter": "heating_power",
                "old_value": prev.heating_power_percent,
                "new_value": p.heating_power_percent,
            })
        if (p.smoke_damper_percent is not None
                and prev.smoke_damper_percent is not None
                and p.smoke_damper_percent != prev.smoke_damper_percent):
            changes.append({
                "time_seconds": p.elapsed_seconds,
                "parameter": "smoke_damper",
                "old_value": prev.smoke_damper_percent,
                "new_value": p.smoke_damper_percent,
            })
        prev = p

    return changes


def compute_auc(points: list[KaleidoDataPoint], threshold_celsius: float = 100.0) -> float | None:
    """Compute area under BT curve using trapezoidal rule (only BT > threshold)."""
    filtered = [
        (p.elapsed_seconds, p.bean_temp_celsius)
        for p in points
        if p.bean_temp_celsius is not None and p.bean_temp_celsius > threshold_celsius
    ]
    if len(filtered) < 2:
        return None

    # Convert seconds to minutes for AUC unit: °C·min
    auc = 0.0
    for i in range(1, len(filtered)):
        t0, bt0 = filtered[i - 1]
        t1, bt1 = filtered[i]
        # Trapezoid: (bt0 + bt1)/2 * delta_t / 60
        delta_min = (t1 - t0) / 60.0
        auc += (bt0 + bt1) / 2.0 * delta_min

    return round(auc, 1)
