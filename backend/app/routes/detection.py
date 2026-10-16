from fastapi import APIRouter
from typing import List, Dict, Any
from datetime import datetime, timezone
from backend.app.models.schemas import AnomalyEvent, MultiSensorAssessment
from backend.app.storage.db import db
from backend.app.services.baseline import baseline_engine
from backend.app.services.detector import anomaly_detector
from backend.app.services.assessment import multi_sensor_engine
from backend.app.services.explainer import explainer_engine
from backend.app.services.ibm_adapter import ibm_adapter

router = APIRouter(prefix="/api/detection", tags=["AI Anomaly Detection"])

recent_anomalies: List[AnomalyEvent] = []
recent_assessments: Dict[str, MultiSensorAssessment] = {}

def run_detection_cycle() -> Dict[str, Any]:
    global recent_anomalies, recent_assessments
    sections = db.get_all_sections()
    now = datetime.now(timezone.utc)
    new_anomalies = []

    for sec in sections:
        readings = db.get_latest_readings(section_id=sec.section_id, limit=20)
        p_in = sec.nominal_pressure_bar
        p_out = sec.nominal_pressure_bar - 0.4
        flow = sec.nominal_flow_m3_h

        for r in reversed(readings):
            if r["sensor_id"] == f"PT-{sec.section_id}-IN":
                p_in = r["value"]
                break
        for r in reversed(readings):
            if r["sensor_id"] == f"PT-{sec.section_id}-OUT":
                p_out = r["value"]
                break
        for r in reversed(readings):
            if r["sensor_id"] == f"FT-{sec.section_id}":
                flow = r["value"]
                break

        # Step 3: Anomaly Detection
        anom = anomaly_detector.analyze_readings(
            section_id=sec.section_id,
            current_pressure=p_in,
            current_flow=flow,
            timestamp=now,
        )
        if anom:
            new_anomalies.append(anom)
            recent_anomalies.append(anom)
            if len(recent_anomalies) > 100:
                recent_anomalies.pop(0)

        # Step 4: Multi-Sensor Assessment
        assessment = multi_sensor_engine.evaluate_section(
            section=sec,
            inlet_pressure=p_in,
            outlet_pressure=p_out,
            flow_rate=flow,
            timestamp=now,
        )
        recent_assessments[sec.section_id] = assessment

        # Update Section Status in DB
        if assessment.classification == "LOCALISED_LEAK" and assessment.risk_score >= 60:
            db.update_section_status(sec.section_id, "LEAK_DETECTED")
        elif assessment.risk_level in ["MEDIUM", "HIGH"]:
            db.update_section_status(sec.section_id, "WARNING")
        else:
            # If no active inspection or alert is pending, keep normal
            current = db.get_section(sec.section_id)
            if current and current.current_status != "MAINTENANCE":
                db.update_section_status(sec.section_id, "NORMAL")

        # Step 5: Explainable Alert Generation
        if assessment.risk_score >= 55.0:
            exp_vals = baseline_engine.get_expected_values(sec.section_id, now)
            alert = explainer_engine.generate_alert(
                section=sec,
                assessment=assessment,
                raw_p=p_in,
                raw_q=flow,
                exp_p=exp_vals["expected_pressure"],
                exp_q=exp_vals["expected_flow"],
            )
            # Avoid duplicate spamming if an alert already exists within 5 mins for this section
            existing_alerts = [a for a in db.get_alerts() if a.section_id == sec.section_id and a.status == "NEW"]
            if not existing_alerts:
                db.add_alert(alert)

    return {
        "status": "completed",
        "timestamp": now.isoformat(),
        "anomalies_detected": len(new_anomalies),
        "total_sections_evaluated": len(sections),
    }

@router.post("/run")
def trigger_detection():
    return run_detection_cycle()

@router.get("/anomalies", response_model=List[AnomalyEvent])
def get_anomalies():
    return list(reversed(recent_anomalies[-30:]))

@router.get("/assessments", response_model=List[MultiSensorAssessment])
def get_assessments():
    return list(recent_assessments.values())

@router.get("/ibm-status")
def get_ibm_service_status():
    return ibm_adapter.get_service_status()
