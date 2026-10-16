import math
from datetime import datetime
from typing import Dict, Tuple

class BaselineEngine:
    """
    Computes diurnal (24-hour cycle) expected baselines for pressure and flow
    per pipeline section, modeling peak morning and evening consumption cycles.
    """
    def __init__(self):
        # Section nominal configurations [base_pressure, base_flow, pressure_var, flow_var]
        self.section_configs = {
            "SEC-A": {"p_nom": 6.5, "q_nom": 450.0, "p_std": 0.15, "q_std": 15.0},
            "SEC-B": {"p_nom": 5.2, "q_nom": 280.0, "p_std": 0.18, "q_std": 14.0},
            "SEC-C": {"p_nom": 4.8, "q_nom": 210.0, "p_std": 0.16, "q_std": 12.0},
            "SEC-D": {"p_nom": 4.5, "q_nom": 180.0, "p_std": 0.15, "q_std": 10.0},
            "SEC-E": {"p_nom": 4.0, "q_nom": 240.0, "p_std": 0.14, "q_std": 12.0},
            "SEC-F": {"p_nom": 3.8, "q_nom": 150.0, "p_std": 0.12, "q_std": 9.0},
        }

    def get_diurnal_factor(self, timestamp: datetime) -> float:
        """
        Calculates diurnal consumption factor (0.6 at 3 AM to 1.35 at 8 AM and 7 PM).
        Matches standard municipal water demand curves (BattLeDIM benchmark).
        """
        hour = timestamp.hour + timestamp.minute / 60.0
        
        # Dual peak model: Morning peak (8:00) + Evening peak (19:30), night dip (3:30)
        morning_peak = 0.35 * math.exp(-((hour - 8.0) ** 2) / 4.0)
        evening_peak = 0.30 * math.exp(-((hour - 19.5) ** 2) / 5.0)
        night_dip = -0.30 * math.exp(-((hour - 3.5) ** 2) / 6.0)
        
        factor = 1.0 + morning_peak + evening_peak + night_dip
        return max(0.55, min(1.45, factor))

    def get_expected_values(self, section_id: str, timestamp: datetime) -> Dict[str, float]:
        """
        Returns expected pressure, flow, and tolerance bounds (±2.5 sigma).
        """
        cfg = self.section_configs.get(
            section_id, 
            {"p_nom": 5.0, "q_nom": 250.0, "p_std": 0.15, "q_std": 12.0}
        )
        factor = self.get_diurnal_factor(timestamp)

        # In water networks: higher flow causes frictional head loss (slightly lower pressure)
        expected_flow = cfg["q_nom"] * factor
        frictional_loss = 0.15 * (factor - 1.0)
        expected_pressure = max(1.5, cfg["p_nom"] - frictional_loss)

        p_std = cfg["p_std"]
        q_std = cfg["q_std"] * factor

        return {
            "expected_pressure": round(expected_pressure, 3),
            "pressure_lower_bound": round(expected_pressure - 2.5 * p_std, 3),
            "pressure_upper_bound": round(expected_pressure + 2.5 * p_std, 3),
            "expected_flow": round(expected_flow, 2),
            "flow_lower_bound": round(max(0, expected_flow - 2.5 * q_std), 2),
            "flow_upper_bound": round(expected_flow + 2.5 * q_std, 2),
            "p_std": p_std,
            "q_std": q_std,
        }

baseline_engine = BaselineEngine()
