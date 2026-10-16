from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime, timezone
from backend.app.models.schemas import (
    InspectionTask,
    InspectionAssignmentRequest,
    InspectionCompletionRequest,
)
from backend.app.storage.db import db

router = APIRouter(prefix="/api/repairs", tags=["Inspection & Repair Tracking"])

@router.get("/tasks", response_model=List[InspectionTask])
def get_all_tasks():
    return db.get_tasks()

@router.get("/tasks/{task_id}", response_model=InspectionTask)
def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/assign", response_model=InspectionTask)
def assign_inspection(req: InspectionAssignmentRequest):
    # Find alert
    alerts = db.get_alerts()
    target_alert = None
    for a in alerts:
        if a.alert_id == req.alert_id:
            target_alert = a
            break

    if not target_alert:
        raise HTTPException(status_code=404, detail="Associated alert not found")

    task_id = f"TASK-{int(datetime.now(timezone.utc).timestamp())}"
    task = InspectionTask(
        task_id=task_id,
        alert_id=req.alert_id,
        section_id=target_alert.section_id,
        technician_name=req.technician_name,
        priority=req.priority,
        status="IN_PROGRESS",
        created_at=datetime.now(timezone.utc),
        notes=req.notes,
    )

    db.add_inspection_task(task)
    db.update_alert_status(req.alert_id, "INSPECTION_ASSIGNED", task_id=task_id, assigned_to=req.technician_name)
    db.update_section_status(target_alert.section_id, "MAINTENANCE")

    return task

@router.post("/tasks/{task_id}/complete", response_model=InspectionTask)
def complete_repair(task_id: str, req: InspectionCompletionRequest):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)
    task.findings = req.findings
    task.repair_type = req.repair_type
    task.post_repair_pressure = req.post_repair_pressure
    task.verified_normal = True
    if req.notes:
        task.notes = (task.notes or "") + f" | Repair Note: {req.notes}"

    db.add_inspection_task(task)

    # Closed Feedback Loop: Mark alert resolved and restore section status to NORMAL
    db.update_alert_status(task.alert_id, "RESOLVED")
    db.update_section_status(task.section_id, "NORMAL")

    # If the simulator had injected leak in this section, turn off the injection
    from simulator.network_sim import simulator
    if simulator.config.inject_leak and simulator.config.leak_section == task.section_id:
        simulator.config.inject_leak = False

    return task
