"""
Kaleido M1 KLDO V101 CSV parser.
Parses Kaleido M1 CSV files with format:

  KLDO data file V101

  [{PARAMETERS}]
  [{TotalTime}]
  06:25

  [{PreTemp}]
  206

  [{EVENT}]
  [{StartBeansIn}]
  206@00:00

  [{TemperBack}]
  111@00:59

  [{DATA}]
  Index,Time,BT,ET,RoR,SV,HPM,HP,SM,RL,PS

Reference files: 260530_9.csv, 260530_10.csv
"""
import csv
import hashlib
import io
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("coffee-roast.parser")


def _decode_kldo_text(content: bytes) -> str:
    """Decode Kaleido exports produced on different desktop platforms.

    Kaleido files are commonly UTF-8 with BOM, but Windows exports can also
    be UTF-16 or GB18030. Normalize decoding failures into ``ValueError`` so
    every upload endpoint returns a useful 422 instead of an internal error.
    """
    if not content:
        raise ValueError("Empty file")

    encodings = ["utf-8-sig"]
    if content.startswith((b"\xff\xfe", b"\xfe\xff")) or content[:256].count(b"\x00") > 8:
        encodings.extend(["utf-16", "utf-16-le", "utf-16-be"])
    encodings.append("gb18030")

    for encoding in encodings:
        try:
            text = content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        if "\x00" not in text:
            return text

    raise ValueError("无法识别文件编码；请导出 UTF-8、UTF-16 或 GB18030 编码的 Kaleido CSV")

# ---------------------------------------------------------------------------
# Event name mapping: Kaleido M1 → internal event type
# ---------------------------------------------------------------------------
EVENT_TYPE_MAP = {
    "StartBeansIn": "charge",
    "TemperBack": "turning_point",
    "TurntoYellow": "yellowing",
    "1stBoomStart": "first_crack_start",
    "1stBoomEnd": "first_crack_end",
    "2ndBoomStart": "second_crack_start",
    "2ndBoomEnd": "second_crack_end",
    "BeansColdDown": "drop",
}

# ---------------------------------------------------------------------------
# Parameter name mapping
# ---------------------------------------------------------------------------
PARAM_NAME_MAP = {
    "TotalTime": "total_time",
    "PreTemp": "preheat_temp",
    "CookDate": "cooked_at",
    "Comment": "comment",
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class KaleidoParameters:
    total_time: str | None = None       # Raw time string e.g. "06:25"
    preheat_temp: float | None = None
    cooked_at: str | None = None
    comment: str | None = None


@dataclass
class KaleidoEvent:
    event_type: str  # charge, turning_point, yellowing, first_crack_start, ...
    time_seconds: float
    bean_temp: float | None = None

    def to_normalized_type(self) -> str:
        """Already normalized — kept for backward compatibility."""
        return self.event_type


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


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------

def split_kldo_sections(lines: list[str]) -> dict[str, list[str]]:
    """Split KLDO file contents into sections:
       - params: lines under [{PARAMETERS}]
       - events: lines under [{EVENT}]
       - data: lines under [{DATA}]
    """
    sections: dict[str, list[str]] = {"params": [], "events": [], "data": []}
    section: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped == "[{PARAMETERS}]":
            section = "params"
            continue
        elif stripped == "[{EVENT}]":
            section = "events"
            continue
        elif stripped == "[{DATA}]":
            section = "data"
            continue

        if section:
            sections[section].append(stripped)

    return sections


# ---------------------------------------------------------------------------
# Parameter parsing (marker-value pairs)
# ---------------------------------------------------------------------------

def parse_marker_value_section(lines: list[str]) -> KaleidoParameters:
    """Parse Kaleido M1 parameter section.

    Format: each parameter is a marker line like `[{TotalTime}]`
            immediately followed by its value on the next line.
    """
    params = KaleidoParameters()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match marker: [{SomeName}]
        m = re.match(r"\[\{(\w+)\}\]", line)
        if m:
            param_name = m.group(1)
            # Value is on the next line (if exists)
            if i + 1 < len(lines):
                value = lines[i + 1]
                # Make sure the value line is not itself a marker
                if not re.match(r"\[\{\w+\}\]", value):
                    mapped = PARAM_NAME_MAP.get(param_name, param_name.lower())
                    if mapped == "preheat_temp":
                        try:
                            params.preheat_temp = float(value)
                        except ValueError:
                            pass
                    elif mapped == "total_time":
                        params.total_time = value
                    elif mapped == "cooked_at":
                        params.cooked_at = value
                    elif mapped == "comment":
                        params.comment = value
                    i += 2
                    continue
        i += 1

    return params


# ---------------------------------------------------------------------------
# Event parsing (marker-value pairs with value@time format)
# ---------------------------------------------------------------------------

def parse_event_section(lines: list[str]) -> list[KaleidoEvent]:
    """Parse Kaleido M1 event section.

    Format: each event is a marker line like `[{StartBeansIn}]`
            immediately followed by a value like `206@00:00`
            where format is `<temperature>@<mm:ss>`
    """
    events: list[KaleidoEvent] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"\[\{(\w+)\}\]", line)
        if m:
            raw_event_name = m.group(1)
            event_type = EVENT_TYPE_MAP.get(raw_event_name)
            if event_type is None:
                # Unknown event — skip
                i += 1
                continue

            # Value is on the next line (if exists)
            if i + 1 < len(lines):
                value_line = lines[i + 1]
                if not re.match(r"\[\{\w+\}\]", value_line):
                    bean_temp, time_seconds = parse_event_value(value_line)
                    events.append(KaleidoEvent(
                        event_type=event_type,
                        time_seconds=time_seconds,
                        bean_temp=bean_temp,
                    ))
                    i += 2
                    continue
        i += 1

    return events


def parse_event_value(value: str) -> tuple[float | None, float]:
    """Parse event value in format `<temperature>@<mm:ss>` or `<temperature>@<seconds>`.

    Returns (bean_temp, time_seconds).
    """
    if "@" not in value:
        # Fallback: treat whole value as seconds
        try:
            return None, float(value)
        except ValueError:
            return None, 0.0

    temp_str, time_str = value.split("@", 1)
    temp_str = temp_str.strip()
    time_str = time_str.strip()

    bean_temp = None
    if temp_str:
        try:
            bean_temp = float(temp_str)
        except ValueError:
            pass

    time_seconds = _parse_time_to_seconds(time_str)

    return bean_temp, time_seconds


def _parse_time_to_seconds(time_str: str) -> float:
    """Parse time string in format mm:ss or raw seconds."""
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 2:
            try:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60.0 + seconds
            except ValueError:
                return 0.0
    try:
        return float(time_str)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# DATA rows parsing
# ---------------------------------------------------------------------------

def parse_data_rows(lines: list[str]) -> list[KaleidoDataPoint]:
    """Parse the [{DATA}] CSV section."""
    if not lines:
        return []

    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    points: list[KaleidoDataPoint] = []

    for row in reader:
        # Normalize column names (strip whitespace)
        row = {
            k.strip(): (v or "").strip()
            for k, v in row.items()
            if k is not None
        }

        # Index (capital I)
        try:
            sample_idx = int(row.get("Index", 0))

            # Time is in milliseconds — convert to seconds
            time_ms_raw = row.get("Time", "0")
            time_sec = float(time_ms_raw) / 1000.0
        except (TypeError, ValueError):
            logger.warning("Skipping malformed KLDO data row: %s", row)
            continue

        point = KaleidoDataPoint(
            sample_index=sample_idx,
            elapsed_seconds=time_sec,
        )

        # BT — raw value, do NOT divide by 10
        bt_raw = row.get("BT", "")
        if bt_raw and bt_raw != "0":
            try:
                val = float(bt_raw)
                if val != 0:
                    point.bean_temp_celsius = val
            except ValueError:
                pass

        # ET — raw value, do NOT divide by 10
        et_raw = row.get("ET", "")
        if et_raw and et_raw != "0":
            try:
                val = float(et_raw)
                if val != 0:
                    point.environment_temp_celsius = val
            except ValueError:
                pass

        # RoR — raw value, do NOT divide by 10
        ror_raw = row.get("RoR", "")
        if ror_raw and ror_raw != "0":
            try:
                val = float(ror_raw)
                if val != 0:
                    point.ror_celsius_per_minute = val
            except ValueError:
                pass

        # SV (target temp) — raw value, do NOT divide by 10
        sv_raw = row.get("SV", "")
        if sv_raw and sv_raw != "0":
            try:
                val = float(sv_raw)
                if val != 0:
                    point.target_temp_celsius = val
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

        points.append(point)

    return points


# ---------------------------------------------------------------------------
# Main parse entry point
# ---------------------------------------------------------------------------

def parse_kaleido_m1(content: bytes, filename: str) -> KaleidoParsedData:
    """Parse a Kaleido M1 KLDO V101 CSV file."""
    # Compute hash
    file_hash = hashlib.sha256(content).hexdigest()

    text = _decode_kldo_text(content)
    lines = text.splitlines()

    # Some desktop exporters prepend blank lines before the format marker.
    while lines and not lines[0].strip():
        lines.pop(0)

    # Identify format
    if not lines:
        raise ValueError("Empty file")

    first_line = lines[0].strip()
    version_match = re.fullmatch(r"KLDO data file V(\d+)", first_line)
    if not version_match:
        raise ValueError(
            f"不支持的曲线格式，首行是 '{first_line}'；当前仅支持 Kaleido M1 KLDO V101 CSV"
        )
    if version_match.group(1) != "101":
        raise ValueError(
            f"不支持 KLDO V{version_match.group(1)}；当前解析器仅支持 KLDO V101"
        )

    # Split into sections
    sections = split_kldo_sections(lines[1:])

    # Parse parameters (marker-value pairs)
    parameters = parse_marker_value_section(sections["params"])

    # Parse events (marker-value pairs with value@time)
    events = parse_event_section(sections["events"])

    # Parse DATA rows
    points = parse_data_rows(sections["data"])
    if not sections["data"]:
        raise ValueError("文件缺少 [{DATA}] 曲线数据段")
    if not points:
        raise ValueError("[{DATA}] 中没有可解析的数据行，请确认包含 Index、Time、BT 等列")

    data = KaleidoParsedData(
        file_hash=file_hash,
        parameters=parameters,
        events=events,
        points=points,
    )

    # Add data quality warnings
    _check_data_quality(data)

    return data


# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------

def _check_data_quality(data: KaleidoParsedData) -> None:
    """Generate data quality warnings without modifying raw data."""
    if not data.points:
        return

    # Check charge event temperature vs first BT sample
    charge_ev = next((e for e in data.events if e.event_type == "charge"), None)
    if charge_ev and data.points:
        first_bt = data.points[0].bean_temp_celsius
        if charge_ev.bean_temp and first_bt and abs(charge_ev.bean_temp - first_bt) > 5:
            data.warnings.append({
                "code": "CHARGE_TEMP_DIFFERS",
                "severity": "warning",
                "message": (
                    f"入豆事件温度({charge_ev.bean_temp}°C)与首个BT采样值"
                    f"({first_bt}°C)存在差异，请核对事件标记或探针记录。"
                ),
                "related_event": "charge",
            })

    # Check for missing key events
    event_types = {e.event_type for e in data.events}
    key_events = ["charge", "drop"]
    for ke in key_events:
        if ke not in event_types:
            data.warnings.append({
                "code": f"MISSING_{ke.upper()}",
                "severity": "warning",
                "message": f"缺少关键事件: {ke}",
                "related_event": ke,
            })


# ---------------------------------------------------------------------------
# Derived metric computation (unchanged logic, but now works with correct data)
# ---------------------------------------------------------------------------

def compute_stage_metrics(data: KaleidoParsedData) -> dict:
    """Compute stage durations, ratios, and average RoR from parsed data."""
    events_by_type = {e.event_type: e for e in data.events}

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
    """Compute average RoR over a time range, excluding None and zero values."""
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
        delta_min = (t1 - t0) / 60.0
        auc += (bt0 + bt1) / 2.0 * delta_min

    return round(auc, 1)
