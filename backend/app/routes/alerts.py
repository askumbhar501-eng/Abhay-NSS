from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from backend.app.models.schemas import Alert, AlertStatusUpdate
from backend.app.storage.db import db

router = APIRouter(prefix="/api/alerts", tags=["Alerts & Notifications"])

@router.get("", response_model=List[Alert])
def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status: NEW, ACKNOWLEDGED, RESOLVED, etc."),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: LOW, MEDIUM, HIGH, CRITICAL"),
):
    alerts = db.get_alerts(status=status)
    if risk_level:
        alerts = [a for a in alerts if a.risk_level == risk_level]
    return alerts

@router.get("/{alert_id}", response_model=Alert)
def get_alert_detail(alert_id: str):
    alerts = db.get_alerts()
    for a in alerts:
        if a.alert_id == alert_id:
            return a
    raise HTTPException(status_code=404, detail="Alert not found")

@router.patch("/{alert_id}", response_model=Alert)
def update_alert(alert_id: str, update: AlertStatusUpdate):
    updated = db.update_alert_status(alert_id, update.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found")
    return updated

@router.get("/{alert_id}/explain")
def get_alert_explainability(alert_id: str):
    alerts = db.get_alerts()
    for a in alerts:
        if a.alert_id == alert_id:
            return {
                "alert_id": a.alert_id,
                "title": a.title,
                "section": a.section_name,
                "risk_score": a.risk_score,
                "risk_level": a.risk_level,
                "evidence": {
                    "pressure_drop_pct": a.pressure_drop_pct,
                    "flow_increase_pct": a.flow_increase_pct,
                    "estimated_loss_rate_m3_h": a.estimated_loss_rate_m3_h,
                },
                "root_cause_explanation": a.ai_explanation,
                "multilingual": a.multilingual_explanations,
            }
    raise HTTPException(status_code=404, detail="Alert not found")
