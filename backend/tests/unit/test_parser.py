"""Parser tests for Kaleido M1 CSV files."""
import pytest
from app.parsers.kaleido_m1 import (
    parse_kaleido_m1, parse_event_value, _parse_time_to_seconds,
    split_kldo_sections, compute_stage_metrics, compute_control_changes, compute_auc,
    KaleidoDataPoint, KaleidoEvent, KaleidoParsedData, KaleidoParameters,
)


SAMPLE_CSV = """KLDO data file V101

[{PARAMETERS}]
[{TotalTime}]
10:30
[{PreTemp}]
200

[{EVENT}]
[{StartBeansIn}]
200@00:00
[{TemperBack}]
105@01:15
[{TurntoYellow}]
150@05:00
[{1stBoomStart}]
190@08:00
[{1stBoomEnd}]
195@09:00
[{BeansColdDown}]
205@10:30

[{DATA}]
Index,Time,BT,ET,RoR,SV,HPM,HP,SM,RL,PS
0,0,200,200,0,200,2,100,50,30,1
1,1000,180,220,5,200,2,100,50,30,1
2,2000,140,240,10,200,2,90,50,30,1
3,3000,130,240,8,200,2,90,50,30,1
4,4000,135,245,7,200,2,80,50,30,1
5,5000,150,250,5,200,2,80,50,30,1
6,6000,160,255,4,200,2,70,50,30,1
7,7000,170,260,3,200,2,70,60,30,1
8,8000,190,270,2,200,2,60,60,30,1
9,9000,200,280,1,200,2,50,60,30,1
10,10000,205,290,0,200,2,50,60,30,1
""".encode("utf-8")


class TestParseEventValue:
    def test_with_temp_and_mmss(self):
        temp, sec = parse_event_value("200@01:15")
        assert temp == 200.0
        assert sec == 75.0

    def test_without_temp(self):
        temp, sec = parse_event_value("@00:00")
        assert temp is None
        assert sec == 0.0

    def test_raw_seconds(self):
        temp, sec = parse_event_value("105@75")
        assert temp == 105.0
        assert sec == 75.0


class TestParseTime:
    def test_mmss_format(self):
        assert _parse_time_to_seconds("01:15") == 75.0
        assert _parse_time_to_seconds("10:30") == 630.0

    def test_raw_seconds(self):
        assert _parse_time_to_seconds("75") == 75.0


class TestSectionSplitting:
    def test_splits_correctly(self):
        lines = [
            "[{PARAMETERS}]", "[{TotalTime}]", "10:30",
            "[{EVENT}]", "[{StartBeansIn}]", "200@00:00",
            "[{DATA}]", "Index,Time,BT",
        ]
        sections = split_kldo_sections(lines)
        assert "[{TotalTime}]" in sections["params"]
        assert "10:30" in sections["params"]
        assert "[{StartBeansIn}]" in sections["events"]
        assert "200@00:00" in sections["events"]
        assert "Index,Time,BT" in sections["data"]


class TestFullParsing:
    def test_parse_valid_csv(self):
        parsed = parse_kaleido_m1(SAMPLE_CSV, "test.csv")
        assert parsed.file_hash
        assert len(parsed.file_hash) == 64  # SHA-256

    def test_parse_parameters(self):
        parsed = parse_kaleido_m1(SAMPLE_CSV, "test.csv")
        assert parsed.parameters.preheat_temp == 200.0
        assert parsed.parameters.total_time == "10:30"

    def test_parse_events(self):
        parsed = parse_kaleido_m1(SAMPLE_CSV, "test.csv")
        event_types = {e.event_type for e in parsed.events}
        assert "charge" in event_types
        assert "turning_point" in event_types
        assert "yellowing" in event_types
        assert "first_crack_start" in event_types
        assert "first_crack_end" in event_types
        assert "drop" in event_types

    def test_parse_data_points(self):
        parsed = parse_kaleido_m1(SAMPLE_CSV, "test.csv")
        assert parsed.point_count == 11
        assert parsed.points[0].bean_temp_celsius == 200.0
        # Time should be in seconds (ms/1000)
        assert parsed.points[1].elapsed_seconds == 1.0

    def test_total_time_seconds(self):
        parsed = parse_kaleido_m1(SAMPLE_CSV, "test.csv")
        assert parsed.total_time_seconds == 10.0  # 10000ms / 1000

    def test_wrong_format_raises(self):
        with pytest.raises(ValueError, match="不支持的曲线格式"):
            parse_kaleido_m1(b"Not a valid file", "test.csv")

    def test_utf16_export_is_supported(self):
        content = SAMPLE_CSV.decode("utf-8").encode("utf-16")
        parsed = parse_kaleido_m1(content, "utf16.csv")
        assert parsed.point_count == 11

    def test_gb18030_export_is_supported(self):
        text = SAMPLE_CSV.decode("utf-8").replace(
            "10:30", "10:30\n[{Comment}]\n测试曲线", 1
        )
        parsed = parse_kaleido_m1(text.encode("gb18030"), "gb18030.csv")
        assert parsed.point_count == 11

    def test_leading_blank_lines_are_supported(self):
        parsed = parse_kaleido_m1(b"\r\n\r\n" + SAMPLE_CSV, "blank-prefix.csv")
        assert parsed.point_count == 11

    def test_unsupported_kldo_version_has_clear_error(self):
        content = SAMPLE_CSV.replace(b"V101", b"V102", 1)
        with pytest.raises(ValueError, match="仅支持 KLDO V101"):
            parse_kaleido_m1(content, "v102.csv")

    def test_missing_data_section_is_rejected(self):
        content = b"KLDO data file V101\n[{PARAMETERS}]\n[{TotalTime}]\n10:30\n"
        with pytest.raises(ValueError, match=r"\[\{DATA\}\]"):
            parse_kaleido_m1(content, "missing-data.csv")


class TestStageMetrics:
    def test_computes_stages(self):
        parsed = parse_kaleido_m1(SAMPLE_CSV, "test.csv")
        result = compute_stage_metrics(parsed)
        assert "stages" in result
        stages = result["stages"]
        assert len(stages) >= 2  # At least drying and development


class TestControlChanges:
    def test_detects_changes(self):
        points = [
            KaleidoDataPoint(0, 0.0, heating_power_percent=100, smoke_damper_percent=50),
            KaleidoDataPoint(1, 1.0, heating_power_percent=90, smoke_damper_percent=50),
            KaleidoDataPoint(2, 2.0, heating_power_percent=90, smoke_damper_percent=60),
        ]
        changes = compute_control_changes(points)
        assert len(changes) == 2

    def test_no_changes(self):
        points = [
            KaleidoDataPoint(0, 0.0, heating_power_percent=100),
            KaleidoDataPoint(1, 1.0, heating_power_percent=100),
        ]
        changes = compute_control_changes(points)
        assert len(changes) == 0


class TestAUC:
    def test_compute_auc(self):
        points = [
            KaleidoDataPoint(0, 0.0, bean_temp_celsius=90.0),
            KaleidoDataPoint(1, 60.0, bean_temp_celsius=120.0),
            KaleidoDataPoint(2, 120.0, bean_temp_celsius=150.0),
            KaleidoDataPoint(3, 180.0, bean_temp_celsius=180.0),
        ]
        auc = compute_auc(points)
        assert auc is not None
        assert auc > 0

    def test_all_below_threshold(self):
        points = [
            KaleidoDataPoint(0, 0.0, bean_temp_celsius=50.0),
            KaleidoDataPoint(1, 60.0, bean_temp_celsius=80.0),
        ]
        auc = compute_auc(points)
        assert auc is None
