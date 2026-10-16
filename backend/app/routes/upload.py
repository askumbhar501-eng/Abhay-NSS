import io
import pandas as pd
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any, List
from backend.app.models.schemas import SensorReading
from backend.app.storage.db import db
from backend.app.routes.detection import run_detection_cycle

router = APIRouter(prefix="/api/upload", tags=["CSV Ingestion & Benchmarking"])

@router.post("/csv")
async def upload_csv_telemetry(file: UploadFile = File(...)):
    """
    Step 1 Architecture Blueprint: CSV Upload for Prototype testing.
    Supports BattLeDIM and SCADA CSV formats with columns:
    [timestamp, section_id, pressure, flow] or [timestamp, sensor_id, value, type].
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    # Clean missing values and normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.dropna()

    ingested_readings: List[SensorReading] = []
    now = datetime.now(timezone.utc)

    # Case A: tabular columns [timestamp, section_id, pressure, flow]
    if "pressure" in df.columns and "flow" in df.columns:
        for idx, row in df.iterrows():
            sec_id = str(row.get("section_id", "SEC-B"))
            p_val = float(row["pressure"])
            q_val = float(row["flow"])

            ingested_readings.append(SensorReading(
                sensor_id=f"PT-{sec_id}-IN",
                section_id=sec_id,
                sensor_type="pressure",
                value=p_val,
                unit="bar",
                timestamp=now,
            ))
            ingested_readings.append(SensorReading(
                sensor_id=f"FT-{sec_id}",
                section_id=sec_id,
                sensor_type="flow",
                value=q_val,
                unit="m3/h",
                timestamp=now,
            ))

    # Case B: long format [sensor_id, value, timestamp, sensor_type]
    elif "sensor_id" in df.columns and "value" in df.columns:
        for idx, row in df.iterrows():
            s_id = str(row["sensor_id"])
            sec_id = str(row.get("section_id", "SEC-B"))
            s_type = "pressure" if "PT" in s_id or "p" in str(row.get("sensor_type", "")) else "flow"
            val = float(row["value"])

            ingested_readings.append(SensorReading(
                sensor_id=s_id,
                section_id=sec_id,
                sensor_type=s_type,
                value=val,
                unit="bar" if s_type == "pressure" else "m3/h",
                timestamp=now,
            ))

    else:
        raise HTTPException(
            status_code=400, 
            detail="CSV format unrecognized. Requires columns 'pressure' & 'flow', or 'sensor_id' & 'value'."
        )

    # Save to DB and trigger anomaly detection cycle
    db.save_sensor_readings(ingested_readings)
    detection_summary = run_detection_cycle()

    return {
        "status": "success",
        "filename": file.filename,
        "rows_processed": len(df),
        "readings_ingested": len(ingested_readings),
        "detection_result": detection_summary,
    }
