import time
import random
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from backend.app.models.schemas import SensorReading, SimulationConfig
from backend.app.services.baseline import baseline_engine
from backend.app.storage.db import db

class NetworkSimulator:
    """
    Step 1: Pipeline Sensor Data Collection (Simulated SCADA / IoT Gateway)
    Generates realistic hydraulic telemetry (Pressure in bar, Flow in m³/h)
    modeling the BattLeDIM benchmark water distribution network.
    """
    def __init__(self):
        self.config = SimulationConfig()
        self.lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.step_count = 0

    def update_config(self, new_config: SimulationConfig):
        with self.lock:
            self.config = new_config

    def generate_single_step(self, ts: Optional[datetime] = None) -> List[SensorReading]:
        timestamp = ts or datetime.now(timezone.utc)
        readings: List[SensorReading] = []
        sections = db.get_all_sections()

        with self.lock:
            cfg = self.config

        for sec in sections:
            expected = baseline_engine.get_expected_values(sec.section_id, timestamp)
            base_p = expected["expected_pressure"]
            base_q = expected["expected_flow"]

            # Add small sensor measurement noise (±1.5%)
            noise_p = random.gauss(0, cfg.noise_level * base_p)
            noise_q = random.gauss(0, cfg.noise_level * base_q)

            p_in = base_p + noise_p
            q = base_q + noise_q

            # Normal frictional head loss over pipe distance
            friction_head_loss = 0.45 * (sec.length_meters / 1000.0)
            p_out = max(0.5, p_in - friction_head_loss + random.gauss(0, 0.02))

            # Simulate Leak Anomaly if active on this section
            if cfg.inject_leak and sec.section_id == cfg.leak_section:
                # Pressure collapse
                p_drop_factor = (1.0 - cfg.leak_severity)
                p_in = max(1.0, p_in * p_drop_factor)
                p_out = max(0.4, p_out * (p_drop_factor * 0.85))

                # Flow surge to feed the ruptured orifice (orifice flow equation)
                flow_surge_factor = 1.0 + (cfg.leak_severity * 0.75)
                q = q * flow_surge_factor

            # Simulate broader pump failure / supply throttling
            if cfg.supply_throttling:
                p_in = max(0.8, p_in * 0.6)
                p_out = max(0.4, p_out * 0.5)
                q = max(10.0, q * 0.55)

            # Create individual sensor telemetry readings
            # 1. Inlet Pressure Sensor
            readings.append(SensorReading(
                sensor_id=f"PT-{sec.section_id}-IN",
                section_id=sec.section_id,
                sensor_type="pressure",
                value=round(p_in, 2),
                unit="bar",
                timestamp=timestamp,
                battery_pct=round(random.uniform(94.0, 99.5), 1),
                status="ONLINE",
            ))

            # 2. Outlet Pressure Sensor
            readings.append(SensorReading(
                sensor_id=f"PT-{sec.section_id}-OUT",
                section_id=sec.section_id,
                sensor_type="pressure",
                value=round(p_out, 2),
                unit="bar",
                timestamp=timestamp,
                battery_pct=round(random.uniform(93.0, 99.0), 1),
                status="ONLINE",
            ))

            # 3. Flow Sensor
            readings.append(SensorReading(
                sensor_id=f"FT-{sec.section_id}",
                section_id=sec.section_id,
                sensor_type="flow",
                value=round(q, 1),
                unit="m3/h",
                timestamp=timestamp,
                battery_pct=round(random.uniform(95.0, 100.0), 1),
                status="ONLINE",
            ))

        return readings

    def start_background_loop(self):
        """Starts continuous real-time background sensor generator."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()

        def _worker():
            while not self._stop_event.is_set():
                if self.config.running:
                    readings = self.generate_single_step()
                    db.save_sensor_readings(readings)
                    # Periodically run assessment loop
                    from backend.app.routes.detection import run_detection_cycle
                    run_detection_cycle()
                    self.step_count += 1
                time.sleep(self.config.interval_seconds)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def stop_background_loop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

simulator = NetworkSimulator()
