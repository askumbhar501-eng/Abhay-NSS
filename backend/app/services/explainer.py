from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.app.models.schemas import Alert, MultiSensorAssessment, PipelineSection

class ExplainableAIEngine:
    """
    Step 5 of Architecture Blueprint: Explainable Alerts & Risk Prioritization
    Transforms mathematical anomaly metrics into clear, actionable,
    multilingual operational alerts for municipal engineers and field workers.
    """
    def generate_alert(
        self,
        section: PipelineSection,
        assessment: MultiSensorAssessment,
        raw_p: float,
        raw_q: float,
        exp_p: float,
        exp_q: float,
    ) -> Alert:
        ts = assessment.timestamp or datetime.now(timezone.utc)
        alert_id = f"ALT-{section.section_id}-{int(ts.timestamp())}"

        title = f"{assessment.risk_level} Risk: {section.name}"
        if assessment.classification == "LOCALISED_LEAK":
            title += " (Suspected Pipe Burst / Leak)"
        elif assessment.classification == "BROADER_SUPPLY_ISSUE":
            title += " (Upstream Supply Anomaly)"

        ai_explanation = (
            f"AI Anomaly Analysis for {section.name} in {section.zone}:\n"
            f"• Measured Pressure: {raw_p:.2f} bar (Baseline: {exp_p:.2f} bar -> Deviation: {assessment.pressure_drop_pct:+.1f}%)\n"
            f"• Measured Flow: {raw_q:.1f} m³/h (Baseline: {exp_q:.1f} m³/h -> Deviation: {assessment.flow_increase_pct:+.1f}%)\n"
            f"• Classification: {assessment.classification} (Confidence: {int(assessment.probability * 100)}%)\n"
            f"• Root Cause Analysis: {assessment.explanation_en}\n"
            f"• Recommended Protocol: {assessment.recommended_action}"
        )

        multilingual = {
            "en": assessment.explanation_en,
            "hi": assessment.explanation_hi,
            "mr": assessment.explanation_mr,
        }

        alert = Alert(
            alert_id=alert_id,
            timestamp=ts,
            section_id=section.section_id,
            section_name=section.name,
            risk_level=assessment.risk_level,
            risk_score=assessment.risk_score,
            status="NEW",
            title=title,
            classification=assessment.classification,
            pressure_drop_pct=assessment.pressure_drop_pct,
            flow_increase_pct=assessment.flow_increase_pct,
            estimated_loss_rate_m3_h=assessment.estimated_loss_rate_m3_h,
            ai_explanation=ai_explanation,
            multilingual_explanations=multilingual,
        )
        return alert

explainer_engine = ExplainableAIEngine()
