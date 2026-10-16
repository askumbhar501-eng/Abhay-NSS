import pytest
from datetime import datetime
from backend.app.services.baseline import baseline_engine
from backend.app.services.detector import anomaly_detector
from backend.app.services.assessment import multi_sensor_engine
from backend.app.storage.db import db

def test_baseline_engine_diurnal_bounds():
    now = datetime(2026, 10, 16, 14, 0, 0)
    expected = baseline_engine.get_expected_values("SEC-B", now)
    
    assert "expected_pressure" in expected
    assert "expected_flow" in expected
    assert expected["pressure_lower_bound"] < expected["expected_pressure"] < expected["pressure_upper_bound"]
    assert expected["flow_lower_bound"] < expected["expected_flow"] < expected["flow_upper_bound"]

def test_anomaly_detector_normal_readings():
    now = datetime(2026, 10, 16, 14, 0, 0)
    expected = baseline_engine.get_expected_values("SEC-B", now)
    
    # Send normal reading
    event = anomaly_detector.analyze_readings(
        section_id="SEC-B",
        current_pressure=expected["expected_pressure"],
        current_flow=expected["expected_flow"],
        timestamp=now,
    )
    assert event is None

def test_anomaly_detector_detects_severe_pressure_drop():
    now = datetime(2026, 10, 16, 14, 0, 0)
    # Severe 45% drop in pressure
    event = anomaly_detector.analyze_readings(
        section_id="SEC-B",
        current_pressure=2.8,  # Nominal is ~5.2
        current_flow=360.0,    # Surge in flow
        timestamp=now,
    )
    assert event is not None
    assert event.anomaly_type == "pressure_drop"
    assert event.severity in ["HIGH", "CRITICAL"]

def test_multi_sensor_leak_classification():
    sec = db.get_section("SEC-B")
    now = datetime(2026, 10, 16, 14, 0, 0)
    
    # Pipe burst conditions: Inlet pressure drops, outlet drops, flow surges
    assessment = multi_sensor_engine.evaluate_section(
        section=sec,
        inlet_pressure=3.10,
        outlet_pressure=2.50,
        flow_rate=370.0,
        timestamp=now,
    )
    assert assessment.classification == "LOCALISED_LEAK"
    assert assessment.risk_level in ["HIGH", "CRITICAL"]
    assert assessment.risk_score >= 60.0
    assert assessment.estimated_loss_rate_m3_h > 0.0

def test_multi_sensor_supply_interruption_classification():
    sec = db.get_section("SEC-A")
    now = datetime(2026, 10, 16, 14, 0, 0)
    
    # Upstream pump failure: Both pressure and flow drop together
    assessment = multi_sensor_engine.evaluate_section(
        section=sec,
        inlet_pressure=3.2,
        outlet_pressure=2.8,
        flow_rate=180.0,  # Nominal is 450
        timestamp=now,
    )
    assert assessment.classification == "BROADER_SUPPLY_ISSUE"
