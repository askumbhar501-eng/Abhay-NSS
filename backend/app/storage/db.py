import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from backend.app.models.schemas import (
    PipelineSection,
    SensorReading,
    AnomalyEvent,
    MultiSensorAssessment,
    Alert,
    InspectionTask,
)

class StorageDatabase:
    def __init__(self, db_path: str = "aquasentinel.db"):
        self.db_path = db_path
        self._init_sqlite()
        self.sections: Dict[str, PipelineSection] = {}
        self.sensor_readings: List[Dict[str, Any]] = []
        self.anomalies: List[AnomalyEvent] = []
        self.assessments: List[MultiSensorAssessment] = []
        self.alerts: Dict[str, Alert] = {}
        self.tasks: Dict[str, InspectionTask] = {}
        self._seed_default_network()

    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT,
                section_id TEXT,
                sensor_type TEXT,
                value REAL,
                unit TEXT,
                timestamp TEXT,
                battery_pct REAL,
                status TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                timestamp TEXT,
                section_id TEXT,
                section_name TEXT,
                risk_level TEXT,
                risk_score REAL,
                status TEXT,
                title TEXT,
                classification TEXT,
                pressure_drop_pct REAL,
                flow_increase_pct REAL,
                estimated_loss_rate_m3_h REAL,
                ai_explanation TEXT,
                multilingual_json TEXT,
                assigned_to TEXT,
                task_id TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inspection_tasks (
                task_id TEXT PRIMARY KEY,
                alert_id TEXT,
                section_id TEXT,
                technician_name TEXT,
                priority TEXT,
                status TEXT,
                created_at TEXT,
                completed_at TEXT,
                findings TEXT,
                repair_type TEXT,
                pre_repair_pressure REAL,
                post_repair_pressure REAL,
                verified_normal INTEGER,
                notes TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _seed_default_network(self):
        default_sections = [
            PipelineSection(
                section_id="SEC-A",
                name="Section A: Primary Transmission Main",
                zone="Zone 1 - Intake & Main Pump",
                upstream_node="PUMP-01 (Raw Water Station)",
                downstream_node="JUNC-01 (Central Junction)",
                length_meters=1400.0,
                pipe_diameter_mm=600.0,
                material="Ductile Iron",
                nominal_pressure_bar=6.5,
                nominal_flow_m3_h=450.0,
                current_status="NORMAL",
                coordinates=[[18.5204, 73.8567], [18.5240, 73.8610]],
            ),
            PipelineSection(
                section_id="SEC-B",
                name="Section B: Pipeline 3 (Industrial Feeder)",
                zone="Zone 2 - Industrial Corridor",
                upstream_node="JUNC-01 (Central Junction)",
                downstream_node="JUNC-02 (Industrial Terminal)",
                length_meters=950.0,
                pipe_diameter_mm=450.0,
                material="Mild Steel Mortar-Lined",
                nominal_pressure_bar=5.2,
                nominal_flow_m3_h=280.0,
                current_status="NORMAL",
                coordinates=[[18.5240, 73.8610], [18.5310, 73.8680]],
            ),
            PipelineSection(
                section_id="SEC-C",
                name="Section C: Sector 4-5 Residential Line",
                zone="Zone 3 - North Residential",
                upstream_node="JUNC-01 (Central Junction)",
                downstream_node="RESERV-01 (Elevated Tank 1)",
                length_meters=1200.0,
                pipe_diameter_mm=350.0,
                material="High-Density Polyethylene (HDPE)",
                nominal_pressure_bar=4.8,
                nominal_flow_m3_h=210.0,
                current_status="NORMAL",
                coordinates=[[18.5240, 73.8610], [18.5290, 73.8520]],
            ),
            PipelineSection(
                section_id="SEC-D",
                name="Section D: Commercial Central Loop",
                zone="Zone 4 - CBD & Commercial",
                upstream_node="JUNC-02 (Industrial Terminal)",
                downstream_node="JUNC-03 (Commercial Plaza)",
                length_meters=850.0,
                pipe_diameter_mm=300.0,
                material="Ductile Iron",
                nominal_pressure_bar=4.5,
                nominal_flow_m3_h=180.0,
                current_status="NORMAL",
                coordinates=[[18.5310, 73.8680], [18.5360, 73.8630]],
            ),
            PipelineSection(
                section_id="SEC-E",
                name="Section E: Elevated Reservoir Gravity Line",
                zone="Zone 5 - Hillside Residential",
                upstream_node="RESERV-01 (Elevated Tank 1)",
                downstream_node="JUNC-04 (Hill View)",
                length_meters=1600.0,
                pipe_diameter_mm=400.0,
                material="Cast Iron",
                nominal_pressure_bar=4.0,
                nominal_flow_m3_h=240.0,
                current_status="NORMAL",
                coordinates=[[18.5290, 73.8520], [18.5340, 73.8460]],
            ),
            PipelineSection(
                section_id="SEC-F",
                name="Section F: Suburb South Distribution",
                zone="Zone 6 - South Suburbs",
                upstream_node="JUNC-03 (Commercial Plaza)",
                downstream_node="TERMINAL-05 (South Gate)",
                length_meters=1100.0,
                pipe_diameter_mm=250.0,
                material="HDPE",
                nominal_pressure_bar=3.8,
                nominal_flow_m3_h=150.0,
                current_status="NORMAL",
                coordinates=[[18.5360, 73.8630], [18.5420, 73.8690]],
            ),
        ]
        for sec in default_sections:
            self.sections[sec.section_id] = sec

    def get_all_sections(self) -> List[PipelineSection]:
        return list(self.sections.values())

    def get_section(self, section_id: str) -> Optional[PipelineSection]:
        return self.sections.get(section_id)

    def update_section_status(self, section_id: str, status: str):
        if section_id in self.sections:
            self.sections[section_id].current_status = status

    def save_sensor_readings(self, readings: List[SensorReading]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for r in readings:
            r_dict = r.model_dump()
            r_dict["timestamp"] = r.timestamp.isoformat()
            self.sensor_readings.append(r_dict)
            cursor.execute("""
                INSERT INTO sensor_telemetry 
                (sensor_id, section_id, sensor_type, value, unit, timestamp, battery_pct, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.sensor_id,
                r.section_id,
                r.sensor_type,
                r.value,
                r.unit,
                r_dict["timestamp"],
                r.battery_pct,
                r.status,
            ))
        # Keep ring buffer at 5000 items in memory
        if len(self.sensor_readings) > 5000:
            self.sensor_readings = self.sensor_readings[-5000:]
        conn.commit()
        conn.close()

    def get_latest_readings(self, section_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        if section_id:
            filtered = [r for r in self.sensor_readings if r["section_id"] == section_id]
            return filtered[-limit:]
        return self.sensor_readings[-limit:]

    def add_alert(self, alert: Alert):
        self.alerts[alert.alert_id] = alert
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO alerts 
            (alert_id, timestamp, section_id, section_name, risk_level, risk_score, status, 
             title, classification, pressure_drop_pct, flow_increase_pct, estimated_loss_rate_m3_h, 
             ai_explanation, multilingual_json, assigned_to, task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.alert_id,
            alert.timestamp.isoformat(),
            alert.section_id,
            alert.section_name,
            alert.risk_level,
            alert.risk_score,
            alert.status,
            alert.title,
            alert.classification,
            alert.pressure_drop_pct,
            alert.flow_increase_pct,
            alert.estimated_loss_rate_m3_h,
            alert.ai_explanation,
            json.dumps(alert.multilingual_explanations),
            alert.assigned_to,
            alert.task_id,
        ))
        conn.commit()
        conn.close()

    def get_alerts(self, status: Optional[str] = None) -> List[Alert]:
        alerts_list = list(self.alerts.values())
        if status:
            return [a for a in alerts_list if a.status == status]
        return sorted(alerts_list, key=lambda a: a.timestamp, reverse=True)

    def update_alert_status(self, alert_id: str, new_status: str, task_id: Optional[str] = None, assigned_to: Optional[str] = None) -> Optional[Alert]:
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.status = new_status
            if task_id:
                alert.task_id = task_id
            if assigned_to:
                alert.assigned_to = assigned_to
            self.add_alert(alert)
            return alert
        return None

    def add_inspection_task(self, task: InspectionTask):
        self.tasks[task.task_id] = task
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO inspection_tasks
            (task_id, alert_id, section_id, technician_name, priority, status, 
             created_at, completed_at, findings, repair_type, pre_repair_pressure, 
             post_repair_pressure, verified_normal, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id,
            task.alert_id,
            task.section_id,
            task.technician_name,
            task.priority,
            task.status,
            task.created_at.isoformat(),
            task.completed_at.isoformat() if task.completed_at else None,
            task.findings,
            task.repair_type,
            task.pre_repair_pressure,
            task.post_repair_pressure,
            1 if task.verified_normal else 0,
            task.notes,
        ))
        conn.commit()
        conn.close()

    def get_tasks(self) -> List[InspectionTask]:
        return sorted(list(self.tasks.values()), key=lambda t: t.created_at, reverse=True)

    def get_task(self, task_id: str) -> Optional[InspectionTask]:
        return self.tasks.get(task_id)


# Global Database Singleton
db = StorageDatabase()
