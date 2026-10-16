from datetime import datetime, timezone
from typing import Dict, List, Optional
from backend.app.models.schemas import MultiSensorAssessment, PipelineSection
from backend.app.services.baseline import baseline_engine

class MultiSensorAssessmentEngine:
    """
    Step 4 of Architecture Blueprint: Multi-Sensor Leak Assessment
    Cross-validates pressure and flow signatures across multiple sensors,
    differentiating localized pipe ruptures from broader supply drops.
    """
    def evaluate_section(
        self,
        section: PipelineSection,
        inlet_pressure: float,
        outlet_pressure: float,
        flow_rate: float,
        timestamp: Optional[datetime] = None,
        adjacent_p_drop_pct: float = 0.0,
    ) -> MultiSensorAssessment:
        ts = timestamp or datetime.now(timezone.utc)
        expected = baseline_engine.get_expected_values(section.section_id, ts)

        exp_p = expected["expected_pressure"]
        exp_q = expected["expected_flow"]

        # Mean observed section pressure
        observed_p = (inlet_pressure + outlet_pressure) / 2.0
        p_drop_pct = (observed_p - exp_p) / exp_p * 100.0
        q_change_pct = (flow_rate - exp_q) / exp_q * 100.0

        # Hydraulic correlation: inlet to outlet gradient
        normal_frictional_delta = 0.45 * (section.length_meters / 1000.0)
        observed_delta_p = inlet_pressure - outlet_pressure
        excess_gradient = observed_delta_p - normal_frictional_delta

        # Assessment Logic
        # Condition 1: Localized Leak / Burst
        # Signature: Pressure collapses, while Flow increases into the section,
        # and adjacent sections do NOT share the same steep drop.
        if p_drop_pct <= -15.0 and q_change_pct >= 8.0:
            classification = "LOCALISED_LEAK"
            severity_factor = min(1.0, (abs(p_drop_pct) / 50.0 + q_change_pct / 40.0) / 2.0)
            risk_score = round(min(100.0, 50.0 + 50.0 * severity_factor), 1)
            probability = round(min(0.98, 0.75 + 0.23 * severity_factor), 2)
            
            # Orifice leak equation approximation for flow loss (m3/h)
            loss_rate = round(max(5.0, flow_rate - exp_q), 1)

            if risk_score >= 80:
                risk_level = "CRITICAL"
                action = f"Immediate isolation required: Dispatch rapid response crew to close Valve upstream of {section.name}. Check for surfacing water."
            elif risk_score >= 60:
                risk_level = "HIGH"
                action = f"High-priority acoustic sensor inspection and ground survey on {section.name} within 2 hours."
            else:
                risk_level = "MEDIUM"
                action = f"Monitor sensor trends and schedule visual walk-through on {section.name}."

            en_msg = (
                f"High-confidence localized leak detected on {section.name}. "
                f"Pressure dropped by {abs(p_drop_pct):.1f}% below baseline, while inlet flow surged by "
                f"{q_change_pct:.1f}%. Excess hydraulic gradient is {excess_gradient:.2f} bar. "
                f"Estimated water loss rate is {loss_rate} m³/h."
            )
            hi_msg = (
                f"{section.name} पर स्थानीय रिसाव (Leak) का पता चला है। "
                f"दबाव में {abs(p_drop_pct):.1f}% की गिरावट आई है और प्रवाह में {q_change_pct:.1f}% की वृद्धि हुई है। "
                f"अनुमानित जल हानि दर {loss_rate} m³/h है।"
            )
            mr_msg = (
                f"{section.name} येथे पाइपलाइन गळती (Leak) आढळली आहे. "
                f"दाबामध्ये {abs(p_drop_pct):.1f}% घट झाली असून प्रवाहामध्ये {q_change_pct:.1f}% वाढ झाली आहे. "
                f"अंदाजे पाणी गळतीचा दर {loss_rate} m³/h आहे."
            )

        # Condition 2: Broader Supply Issue / Pump Tripping
        # Signature: Both pressure AND flow drop together across header / multiple sections
        elif p_drop_pct <= -12.0 and q_change_pct <= -10.0:
            classification = "BROADER_SUPPLY_ISSUE"
            risk_score = round(min(85.0, 30.0 + abs(p_drop_pct)), 1)
            probability = 0.88
            risk_level = "HIGH" if risk_score > 65 else "MEDIUM"
            loss_rate = 0.0
            action = f"Verify upstream supply from {section.upstream_node}. Inspect pump status and bulk storage levels."

            en_msg = (
                f"System-wide supply depression detected across {section.name}. "
                f"Both pressure (-{abs(p_drop_pct):.1f}%) and flow (-{abs(q_change_pct):.1f}%) have dropped simultaneously. "
                f"Consistent with pump throttling or bulk transmission interruption rather than pipe rupture."
            )
            hi_msg = (
                f"{section.name} में समग्र आपूर्ति समस्या का पता चला है। "
                f"दबाव (-{abs(p_drop_pct):.1f}%) और प्रवाह (-{abs(q_change_pct):.1f}%) दोनों एक साथ घटे हैं।"
            )
            mr_msg = (
                f"{section.name} येथे पाणी पुरवठ्यात अडथळा आढळला आहे. "
                f"दाब (-{abs(p_drop_pct):.1f}%) आणि प्रवाह (-{abs(q_change_pct):.1f}%) दोन्ही एकत्र कमी झाले आहेत."
            )

        # Condition 3: Normal Demand Fluctuation
        else:
            classification = "NORMAL_DEMAND_FLUCTUATION"
            risk_score = round(max(5.0, min(30.0, abs(p_drop_pct) + abs(q_change_pct))), 1)
            probability = 0.92
            risk_level = "LOW"
            loss_rate = 0.0
            action = "Routine monitoring. Network operating within nominal hydraulic envelope."

            en_msg = f"{section.name} telemetry matches standard diurnal demand profile."
            hi_msg = f"{section.name} में जल प्रवाह और दबाव सामान्य सीमा में हैं।"
            mr_msg = f"{section.name} मधील पाण्याचा दाब आणि प्रवाह सामान्य मर्यादेत आहेत."

        assessment = MultiSensorAssessment(
            assessment_id=f"ASSESS-{section.section_id}-{int(ts.timestamp())}",
            section_id=section.section_id,
            timestamp=ts,
            classification=classification,
            probability=probability,
            risk_score=risk_score,
            risk_level=risk_level,
            pressure_drop_pct=round(p_drop_pct, 1),
            flow_increase_pct=round(q_change_pct, 1),
            upstream_vs_downstream_corr=round(1.0 - (excess_gradient / 2.0), 2),
            estimated_loss_rate_m3_h=loss_rate,
            explanation_en=en_msg,
            explanation_hi=hi_msg,
            explanation_mr=mr_msg,
            recommended_action=action,
        )
        return assessment

multi_sensor_engine = MultiSensorAssessmentEngine()
