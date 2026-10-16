from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.app.models.schemas import PipelineSection, NetworkTopology
from backend.app.storage.db import db

router = APIRouter(prefix="/api/network", tags=["Network Topology"])

@router.get("/topology", response_model=NetworkTopology)
def get_network_topology():
    sections = db.get_all_sections()
    total_length = sum(s.length_meters for s in sections) / 1000.0

    nodes = [
        {"id": "PUMP-01", "name": "Raw Water Intake Pump Station", "type": "PUMP", "status": "ONLINE", "x": 100, "y": 300},
        {"id": "JUNC-01", "name": "Central Treatment & Distribution Junction", "type": "JUNCTION", "status": "ONLINE", "x": 300, "y": 300},
        {"id": "JUNC-02", "name": "Industrial Terminal Node", "type": "JUNCTION", "status": "ONLINE", "x": 500, "y": 180},
        {"id": "RESERV-01", "name": "Sector 4 Elevated Reservoir", "type": "RESERVOIR", "status": "ONLINE", "x": 480, "y": 440},
        {"id": "JUNC-03", "name": "Commercial Plaza Hub", "type": "JUNCTION", "status": "ONLINE", "x": 700, "y": 200},
        {"id": "JUNC-04", "name": "Hill View Zone Junction", "type": "JUNCTION", "status": "ONLINE", "x": 680, "y": 460},
        {"id": "TERMINAL-05", "name": "South Gateway Distribution Terminal", "type": "TERMINAL", "status": "ONLINE", "x": 860, "y": 220},
    ]

    return NetworkTopology(
        sections=sections,
        nodes=nodes,
        total_sections=len(sections),
        total_length_km=round(total_length, 2),
    )

@router.get("/sections", response_model=List[PipelineSection])
def get_sections():
    return db.get_all_sections()

@router.get("/sections/{section_id}", response_model=PipelineSection)
def get_section(section_id: str):
    sec = db.get_section(section_id)
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
    return sec
