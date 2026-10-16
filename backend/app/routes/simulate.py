from fastapi import APIRouter
from backend.app.models.schemas import SimulationConfig
from simulator.network_sim import simulator
from backend.app.storage.db import db
from backend.app.routes.detection import run_detection_cycle

router = APIRouter(prefix="/api/simulate", tags=["Simulator Controls"])

@router.get("/status")
def get_simulation_status():
    return {
        "running": simulator.config.running,
        "interval_seconds": simulator.config.interval_seconds,
        "inject_leak": simulator.config.inject_leak,
        "leak_section": simulator.config.leak_section,
        "leak_severity": simulator.config.leak_severity,
        "supply_throttling": simulator.config.supply_throttling,
        "step_count": simulator.step_count,
    }

@router.post("/config")
def update_config(config: SimulationConfig):
    simulator.update_config(config)
    return {"status": "updated", "config": config}

@router.post("/inject")
def inject_fault(
    section_id: str = "SEC-B",
    fault_type: str = "leak",  # "leak" or "supply_drop"
    severity: float = 0.45,
):
    if fault_type == "leak":
        simulator.config.inject_leak = True
        simulator.config.leak_section = section_id
        simulator.config.leak_severity = severity
        simulator.config.supply_throttling = False
    elif fault_type == "supply_drop":
        simulator.config.supply_throttling = True
        simulator.config.inject_leak = False

    # Immediately execute a step and run detection
    readings = simulator.generate_single_step()
    db.save_sensor_readings(readings)
    detection_result = run_detection_cycle()

    return {
        "status": "fault_injected",
        "fault_type": fault_type,
        "section_id": section_id,
        "severity": severity,
        "detection_result": detection_result,
    }

@router.post("/reset")
def reset_simulation():
    simulator.config.inject_leak = False
    simulator.config.supply_throttling = False
    
    # Restore all sections to NORMAL
    for sec in db.get_all_sections():
        db.update_section_status(sec.section_id, "NORMAL")

    # Generate clean step
    readings = simulator.generate_single_step()
    db.save_sensor_readings(readings)
    run_detection_cycle()

    return {"status": "simulation_reset_to_normal"}

@router.post("/step")
def trigger_step():
    readings = simulator.generate_single_step()
    db.save_sensor_readings(readings)
    res = run_detection_cycle()
    return {"status": "step_executed", "detection": res}
