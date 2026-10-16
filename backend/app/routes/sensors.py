from fastapi import APIRouter, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from backend.app.models.schemas import SensorReading, TelemetryBatch, SectionTelemetry
from backend.app.storage.db import db
from backend.app.services.baseline import baseline_engine

router = APIRouter(prefix="/api/sensors", tags=["Sensors & Telemetry"])

@router.get("/latest")
def get_latest_readings(section_id: Optional[str] = None):
    return db.get_latest_readings(section_id=section_id, limit=60)

@router.get("/summary", response_model=List[SectionTelemetry])
def get_sections_summary():
    sections = db.get_all_sections()
    summary: List[SectionTelemetry] = []
    now = datetime.now(timezone.utc)

    for sec in sections:
        readings = db.get_latest_readings(section_id=sec.section_id, limit=20)
        p_in = sec.nominal_pressure_bar
        p_out = sec.nominal_pressure_bar - 0.4
        flow = sec.nominal_flow_m3_h

        # Extract latest sensor values if available
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

        expected = baseline_engine.get_expected_values(sec.section_id, now)
        exp_p = expected["expected_pressure"]
        exp_q = expected["expected_flow"]

        p_dev = round(((p_in - exp_p) / exp_p) * 100.0, 1)
        q_dev = round(((flow - exp_q) / exp_q) * 100.0, 1)

        status = "NORMAL"
        if sec.current_status == "LEAK_DETECTED" or p_dev < -25.0:
            status = "CRITICAL"
        elif p_dev < -15.0 or q_dev > 15.0:
            status = "WARNING"

        summary.append(SectionTelemetry(
            section_id=sec.section_id,
            section_name=sec.name,
            timestamp=now,
            inlet_pressure=p_in,
            outlet_pressure=p_out,
            pressure_drop=round(p_in - p_out, 2),
            flow_rate=flow,
            expected_pressure=exp_p,
            expected_flow=exp_q,
            pressure_deviation_pct=p_dev,
            flow_deviation_pct=q_dev,
            status=status,
        ))

    return summary

@router.post("/stream")
def ingest_telemetry_batch(batch: TelemetryBatch):
    db.save_sensor_readings(batch.readings)
    return {
        "status": "success",
        "ingested_count": len(batch.readings),
        "source": batch.source,
    }
