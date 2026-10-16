import os
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.routes import (
    sensors_router,
    network_router,
    detection_router,
    alerts_router,
    repairs_router,
    simulate_router,
    upload_router,
    run_detection_cycle,
)
from backend.app.storage.db import db
from simulator.network_sim import simulator

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed initial telemetry so charts and dashboard are populated
    now = datetime.now(timezone.utc)
    for i in range(40, 0, -1):
        past_ts = now - timedelta(seconds=i * 5)
        readings = simulator.generate_single_step(ts=past_ts)
        db.save_sensor_readings(readings)

    # Run initial detection cycle
    run_detection_cycle()

    # Pre-seed sample active alert matching PPT Slide 13 ("Section B (Pipeline 3)")
    sec_b = db.get_section("SEC-B")
    if sec_b:
        from backend.app.models.schemas import Alert
        seed_alert = Alert(
            alert_id=f"ALT-SEC-B-BENCHMARK",
            timestamp=now - timedelta(minutes=12),
            section_id="SEC-B",
            section_name=sec_b.name,
            risk_level="HIGH",
            risk_score=78.5,
            status="NEW",
            title="High Risk: Section B (Pipeline 3) - Suspected Pipe Leak",
            classification="LOCALISED_LEAK",
            pressure_drop_pct=-42.5,
            flow_increase_pct=+31.8,
            estimated_loss_rate_m3_h=48.5,
            ai_explanation=(
                "AI Anomaly Analysis for Section B (Pipeline 3) in Zone 2:\n"
                "• Measured Pressure: 3.12 bar (Baseline: 5.20 bar -> Deviation: -42.5%)\n"
                "• Measured Flow: 369.0 m³/h (Baseline: 280.0 m³/h -> Deviation: +31.8%)\n"
                "• Multi-Sensor Agreement: 94% confidence across upstream (PT-SEC-B-IN) and downstream (PT-SEC-B-OUT) gradient.\n"
                "• Root Cause Analysis: Sharp localized pressure drop combined with elevated inlet flow indicates sudden pipe wall rupture / joint blowout.\n"
                "• Recommended Protocol: Dispatch rapid response crew to close upstream isolation valve and survey pipeline with acoustic ground microphones."
            ),
            multilingual_explanations={
                "en": "Section B (Pipeline 3) has an acute 42.5% pressure collapse and 31.8% flow surge, indicating an active pipe rupture.",
                "hi": "सेक्शन बी (पाइपलाइन 3) में 42.5% दबाव की गिरावट और 31.8% प्रवाह वृद्धि दर्ज हुई है, जो सक्रिय पाइप फटने का संकेत है।",
                "mr": "सेक्शन बी (पाइपलाइन 3) मध्ये पाण्याचा दाब 42.5% कमी झाला असून प्रवाह 31.8% वाढला आहे, जे पाइपलाइन फुटल्याचे लक्षण आहे."
            }
        )
        db.add_alert(seed_alert)
        db.update_section_status("SEC-B", "LEAK_DETECTED")

    # Start live telemetry simulation loop
    simulator.start_background_loop()
    
    yield

    # Shutdown
    simulator.stop_background_loop()

app = FastAPI(
    title="AquaSentinel AI",
    description="AI-Powered Pipeline Leak Detection & Water Loss Monitoring (Sociothon'26)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(sensors_router)
app.include_router(network_router)
app.include_router(detection_router)
app.include_router(alerts_router)
app.include_router(repairs_router)
app.include_router(simulate_router)
app.include_router(upload_router)

# Mount Frontend static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_dashboard():
    index_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "templates", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AquaSentinel AI Backend is running. Please access frontend templates."}

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AquaSentinel AI Core Engine",
        "version": "1.0.0",
        "theme": "Smart Cities & Water Management (SDG 6, 11, 12)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
