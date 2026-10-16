import pytest
from simulator.network_sim import simulator
from backend.app.storage.db import db

def test_simulator_generates_readings():
    readings = simulator.generate_single_step()
    assert len(readings) == 18  # 6 sections * 3 sensors each
    sensor_types = {r.sensor_type for r in readings}
    assert "pressure" in sensor_types
    assert "flow" in sensor_types

def test_simulator_leak_injection():
    simulator.config.inject_leak = True
    simulator.config.leak_section = "SEC-B"
    simulator.config.leak_severity = 0.50

    readings = simulator.generate_single_step()
    sec_b_p_in = [r.value for r in readings if r.sensor_id == "PT-SEC-B-IN"][0]
    sec_b_q = [r.value for r in readings if r.sensor_id == "FT-SEC-B"][0]

    # Nominal is ~5.2 bar pressure and ~280 m3/h flow
    # With 50% leak: pressure drops, flow increases
    assert sec_b_p_in < 4.0
    assert sec_b_q > 320.0

    # Reset
    simulator.config.inject_leak = False
