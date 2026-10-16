from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone

# --- Sensor & Telemetry Models ---
class SensorReading(BaseModel):
    sensor_id: str
    section_id: str
    sensor_type: Literal["pressure", "flow"]
    value: float
    unit: str  # "bar", "psi", "m3/h", "L/min"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    battery_pct: Optional[float] = 98.5
    status: Literal["ONLINE", "OFFLINE", "DEGRADED"] = "ONLINE"

class TelemetryBatch(BaseModel):
    readings: List[SensorReading]
    source: str = "iot_gateway"

class SectionTelemetry(BaseModel):
    section_id: str
    section_name: str
    timestamp: datetime
    inlet_pressure: float
    outlet_pressure: float
    pressure_drop: float
    flow_rate: float
    expected_pressure: float
    expected_flow: float
    pressure_deviation_pct: float
    flow_deviation_pct: float
    status: Literal["NORMAL", "WARNING", "ANOMALY", "CRITICAL"] = "NORMAL"

# --- Pipeline Network Topology Models ---
class PipelineSection(BaseModel):
    section_id: str
    name: str
    zone: str
    upstream_node: str
    downstream_node: str
    length_meters: float
    pipe_diameter_mm: float
    material: str
    nominal_pressure_bar: float
    nominal_flow_m3_h: float
    current_status: Literal["NORMAL", "WARNING", "LEAK_DETECTED", "MAINTENANCE"] = "NORMAL"
    coordinates: List[List[float]] = []  # [[x1, y1], [x2, y2]]

class NetworkTopology(BaseModel):
    sections: List[PipelineSection]
    nodes: List[Dict[str, Any]]
    total_sections: int
    total_length_km: float

# --- Anomaly & Multi-Sensor Assessment Models ---
class AnomalyEvent(BaseModel):
    anomaly_id: str
    section_id: str
    timestamp: datetime
    anomaly_type: Literal["pressure_drop", "sustained_low_pressure", "flow_imbalance", "unusual_fluctuations"]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    confidence: float
    z_score: float
    raw_value: float
    expected_value: float
    deviation_pct: float
    model_used: str = "Granite-TSPulse-IsolationForest"

class MultiSensorAssessment(BaseModel):
    assessment_id: str
    section_id: str
    timestamp: datetime
    classification: Literal["LOCALISED_LEAK", "BROADER_SUPPLY_ISSUE", "NORMAL_DEMAND_FLUCTUATION", "SENSOR_FAULT"]
    probability: float
    risk_score: float  # 0 to 100
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    pressure_drop_pct: float
    flow_increase_pct: float
    upstream_vs_downstream_corr: float
    estimated_loss_rate_m3_h: float
    explanation_en: str
    explanation_hi: str
    explanation_mr: str
    recommended_action: str

# --- Alerts & Notifications ---
class Alert(BaseModel):
    alert_id: str
    timestamp: datetime
    section_id: str
    section_name: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_score: float
    status: Literal["NEW", "ACKNOWLEDGED", "INSPECTION_ASSIGNED", "RESOLVED", "FALSE_POSITIVE"] = "NEW"
    title: str
    classification: str
    pressure_drop_pct: float
    flow_increase_pct: float
    estimated_loss_rate_m3_h: float
    ai_explanation: str
    multilingual_explanations: Dict[str, str] = {}
    assigned_to: Optional[str] = None
    task_id: Optional[str] = None

class AlertStatusUpdate(BaseModel):
    status: Literal["NEW", "ACKNOWLEDGED", "INSPECTION_ASSIGNED", "RESOLVED", "FALSE_POSITIVE"]
    notes: Optional[str] = None

# --- Inspection & Repair Tracking ---
class InspectionTask(BaseModel):
    task_id: str
    alert_id: str
    section_id: str
    technician_name: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED", "VERIFIED"] = "PENDING"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    findings: Optional[str] = None
    repair_type: Optional[Literal["PIPE_CLAMP", "VALVE_REPLACEMENT", "JOINT_SEALING", "SECTION_REPLACEMENT", "NO_ISSUE_FOUND"]] = None
    pre_repair_pressure: Optional[float] = None
    post_repair_pressure: Optional[float] = None
    verified_normal: bool = False
    notes: Optional[str] = None

class InspectionAssignmentRequest(BaseModel):
    alert_id: str
    technician_name: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    notes: Optional[str] = None

class InspectionCompletionRequest(BaseModel):
    findings: str
    repair_type: Literal["PIPE_CLAMP", "VALVE_REPLACEMENT", "JOINT_SEALING", "SECTION_REPLACEMENT", "NO_ISSUE_FOUND"]
    post_repair_pressure: float
    notes: Optional[str] = None

# --- Simulation Controls ---
class SimulationConfig(BaseModel):
    running: bool = True
    interval_seconds: float = 2.0
    inject_leak: bool = False
    leak_section: str = "SEC-B"
    leak_severity: float = 0.45  # 0.1 to 1.0 (45% burst)
    supply_throttling: bool = False
    noise_level: float = 0.03
