import pytest
from backend.app.routes.network import get_network_topology, get_sections
from backend.app.routes.sensors import get_sections_summary
from backend.app.routes.detection import run_detection_cycle, get_anomalies
from backend.app.routes.alerts import get_alerts
from backend.app.routes.repairs import assign_inspection, complete_repair, get_all_tasks
from backend.app.models.schemas import InspectionAssignmentRequest, InspectionCompletionRequest
from backend.app.storage.db import db
from simulator.network_sim import simulator

def test_get_network_topology():
    topo = get_network_topology()
    assert len(topo.sections) >= 6
    assert len(topo.nodes) >= 6
    assert topo.total_length_km > 0

def test_get_sensors_summary():
    # Generate a step first
    readings = simulator.generate_single_step()
    db.save_sensor_readings(readings)

    summary = get_sections_summary()
    assert len(summary) >= 6
    assert summary[0].inlet_pressure > 0.0
    assert summary[0].flow_rate > 0.0

def test_trigger_detection_cycle():
    result = run_detection_cycle()
    assert result["status"] == "completed"
    assert result["total_sections_evaluated"] >= 6

def test_get_alerts():
    alerts = get_alerts()
    assert isinstance(alerts, list)

def test_inspection_repair_feedback_loop():
    # 1. Trigger leak injection on Section B
    simulator.config.inject_leak = True
    simulator.config.leak_section = "SEC-B"
    simulator.config.leak_severity = 0.45

    readings = simulator.generate_single_step()
    db.save_sensor_readings(readings)
    run_detection_cycle()

    alerts = db.get_alerts(status="NEW")
    assert len(alerts) > 0
    target_alert = alerts[0]

    # 2. Assign technician
    task = assign_inspection(InspectionAssignmentRequest(
        alert_id=target_alert.alert_id,
        technician_name="Abhay Kumbhar",
        priority="HIGH",
        notes="Acoustic detection test"
    ))
    assert task.status == "IN_PROGRESS"
    assert task.technician_name == "Abhay Kumbhar"

    # 3. Complete repair
    completed_task = complete_repair(
        task_id=task.task_id,
        req=InspectionCompletionRequest(
            findings="Replaced fractured ductile iron coupling",
            repair_type="PIPE_CLAMP",
            post_repair_pressure=5.20,
            notes="Verified normal"
        )
    )
    assert completed_task.status == "COMPLETED"
    assert completed_task.verified_normal is True

    # 4. Verify section returned to NORMAL
    sec = db.get_section(target_alert.section_id)
    assert sec.current_status == "NORMAL"
