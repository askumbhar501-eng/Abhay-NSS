import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone

from backend.app.storage.db import db
from backend.app.services.baseline import baseline_engine
from backend.app.services.detector import anomaly_detector
from backend.app.services.assessment import multi_sensor_engine
from backend.app.services.ibm_adapter import ibm_adapter
from simulator.network_sim import simulator

st.set_page_config(
    page_title="AquaSentinel AI - Operator Console",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💧 AquaSentinel AI - Pipeline Leak Detection & Water Loss Monitoring")
st.caption("Sociothon'26 | PRISM | 1 Million for 1 Billion (1M1B) | SDG 6 · SDG 11 · SDG 12")

# Sidebar Configuration
st.sidebar.header("🕹️ Simulation & Control Deck")
sec_options = ["SEC-A", "SEC-B", "SEC-C", "SEC-D", "SEC-E", "SEC-F"]
selected_sec = st.sidebar.selectbox("Inspect Pipeline Section", sec_options, index=1)

st.sidebar.subheader("Fault Injection (Demo)")
leak_severity = st.sidebar.slider("Burst Severity", 0.1, 0.8, 0.45, 0.05)

col_b1, col_b2 = st.sidebar.columns(2)
if col_b1.button("💥 Inject Leak", use_container_width=True):
    simulator.config.inject_leak = True
    simulator.config.leak_section = selected_sec
    simulator.config.leak_severity = leak_severity
    simulator.config.supply_throttling = False
    readings = simulator.generate_single_step()
    db.save_sensor_readings(readings)
    st.sidebar.success(f"Leak injected on {selected_sec}!")

if col_b2.button("🔄 Reset Normal", use_container_width=True):
    simulator.config.inject_leak = False
    simulator.config.supply_throttling = False
    for sec in db.get_all_sections():
        db.update_section_status(sec.section_id, "NORMAL")
    readings = simulator.generate_single_step()
    db.save_sensor_readings(readings)
    st.sidebar.info("Network reset to normal baseline.")

st.sidebar.markdown("---")
st.sidebar.subheader("IBM watsonx.ai Integration")
ibm_info = ibm_adapter.get_service_status()
st.sidebar.json(ibm_info["watsonx_ai_studio"])

# Top KPI Row
sections = db.get_all_sections()
alerts = db.get_alerts()
active_alerts = [a for a in alerts if a.status in ["NEW", "INSPECTION_ASSIGNED"]]
total_loss = sum(a.estimated_loss_rate_m3_h for a in active_alerts)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Network Health Index", "92.4%", "+1.2%")
k2.metric("Active Leak Alerts", f"{len(active_alerts)} Alerts", f"{len([a for a in active_alerts if a.risk_level=='HIGH'])} High Risk", delta_color="inverse")
k3.metric("Estimated Water Loss", f"{total_loss:.1f} m³/h", "-12.5 m³/h vs yesterday", delta_color="inverse")
k4.metric("IoT Monitoring Nodes", f"{len(sections) * 3} Active Sensors", "100% Online")

st.markdown("---")

# Main Content: Charts & Multi-Sensor Analytics
col_main, col_alerts = st.columns([1.6, 1.0])

with col_main:
    st.subheader(f"📈 Real-Time Sensor Telemetry: {selected_sec}")
    
    # Generate / Fetch Readings
    readings = db.get_latest_readings(section_id=selected_sec, limit=30)
    if not readings:
        readings = simulator.generate_single_step()
        db.save_sensor_readings(readings)

    p_in_vals = [r["value"] for r in readings if "-IN" in r["sensor_id"]][-20:]
    flow_vals = [r["value"] for r in readings if r["sensor_type"] == "flow"][-20:]
    timestamps = [r["timestamp"][-8:] for r in readings if "-IN" in r["sensor_id"]][-20:]

    expected = baseline_engine.get_expected_values(selected_sec, datetime.now(timezone.utc))
    exp_p = expected["expected_pressure"]
    exp_q = expected["expected_flow"]

    # Dual-Axis Plotly Figure
    fig = go.Figure()

    # Pressure Observed
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=p_in_vals,
        name="Inlet Pressure (bar)",
        line=dict(color="#38bdf8", width=3),
        mode="lines+markers",
    ))

    # Baseline Upper and Lower
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=[expected["pressure_upper_bound"]] * len(timestamps),
        name="Baseline Upper",
        line=dict(color="#10b981", width=1, dash="dash"),
        mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=[expected["pressure_lower_bound"]] * len(timestamps),
        name="Baseline Lower",
        line=dict(color="#10b981", width=1, dash="dash"),
        mode="lines",
        fill="tonexty",
        fillcolor="rgba(16, 185, 129, 0.08)",
    ))

    # Flow Observed on secondary axis
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=flow_vals,
        name="Flow Rate (m³/h)",
        line=dict(color="#f59e0b", width=2),
        mode="lines+markers",
        yaxis="y2",
    ))

    fig.update_layout(
        template="plotly_dark",
        height=380,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(title="Pressure (bar)", side="left"),
        yaxis2=dict(title="Flow (m³/h)", side="right", overlaying="y"),
        legend=dict(orientation="h", y=1.15),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Telemetry Table
    st.subheader("📋 Section Status Matrix")
    sec_data = []
    for s in sections:
        sec_data.append({
            "Section": s.name,
            "Zone": s.zone,
            "Nominal P (bar)": s.nominal_pressure_bar,
            "Nominal Flow (m³/h)": s.nominal_flow_m3_h,
            "Length (m)": s.length_meters,
            "Status": s.current_status,
        })
    st.dataframe(pd.DataFrame(sec_data), use_container_width=True)

with col_alerts:
    st.subheader("🚨 Explainable AI Risk Alerts")
    if not active_alerts:
        st.success("All sections normal. No active alerts.")
    else:
        for alert in active_alerts:
            with st.expander(f"{alert.risk_level}: {alert.title}", expanded=True):
                st.markdown(f"**Risk Score**: `{alert.risk_score}%` | **Status**: `{alert.status}`")
                st.markdown(f"**Pressure Drop**: `{alert.pressure_drop_pct}%` | **Flow Surge**: `+{alert.flow_increase_pct}%`")
                if alert.estimated_loss_rate_m3_h > 0:
                    st.error(f"Est. Water Loss Rate: **{alert.estimated_loss_rate_m3_h} m³/h**")

                tab_en, tab_hi, tab_mr = st.tabs(["English", "हिन्दी", "मराठी"])
                with tab_en:
                    st.write(alert.multilingual_explanations.get("en", alert.ai_explanation))
                with tab_hi:
                    st.write(alert.multilingual_explanations.get("hi", "उपलब्ध नहीं"))
                with tab_mr:
                    st.write(alert.multilingual_explanations.get("mr", "उपलब्ध नाही"))

st.markdown("---")
st.subheader("🔧 Inspection & Repair Feedback Loop (Step 6)")
tasks = db.get_tasks()
if tasks:
    task_rows = []
    for t in tasks:
        task_rows.append({
            "Task ID": t.task_id,
            "Section": t.section_id,
            "Technician": t.technician_name,
            "Priority": t.priority,
            "Status": t.status,
            "Repair Type": t.repair_type or "Pending Inspection",
            "Post-Repair P (bar)": t.post_repair_pressure or "N/A",
        })
    st.dataframe(pd.DataFrame(task_rows), use_container_width=True)
else:
    st.info("No work orders logged. Dispatch field crews from the Alerts panel.")
