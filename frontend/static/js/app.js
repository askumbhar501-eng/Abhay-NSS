// AquaSentinel AI - Frontend Operator Dashboard Application
// Built for Sociothon'26 | PRISM | 1M1B

let currentSelectedSection = "SEC-B";
let sensorChartInstance = null;
let networkData = null;
let alertsData = [];
let tasksData = [];

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
  initChart();
  fetchTopology();
  refreshDashboard();
  setupEventListeners();

  // Periodic poll every 2.5 seconds
  setInterval(refreshDashboard, 2500);
});

// Setup Chart.js Dual-Axis Real-Time Chart
function initChart() {
  const ctx = document.getElementById("sensorChart").getContext("2d");
  sensorChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Inlet Pressure (bar)",
          data: [],
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.15)",
          borderWidth: 2.5,
          yAxisID: "yPressure",
          tension: 0.3,
          fill: false,
          pointRadius: 2,
        },
        {
          label: "Baseline Upper (bar)",
          data: [],
          borderColor: "rgba(16, 185, 129, 0.4)",
          borderWidth: 1,
          borderDash: [4, 4],
          yAxisID: "yPressure",
          pointRadius: 0,
          fill: false,
        },
        {
          label: "Baseline Lower (bar)",
          data: [],
          borderColor: "rgba(16, 185, 129, 0.4)",
          backgroundColor: "rgba(16, 185, 129, 0.05)",
          borderWidth: 1,
          borderDash: [4, 4],
          yAxisID: "yPressure",
          pointRadius: 0,
          fill: "-1",
        },
        {
          label: "Flow Rate (m³/h)",
          data: [],
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.15)",
          borderWidth: 2,
          yAxisID: "yFlow",
          tension: 0.3,
          fill: false,
          pointRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          labels: {
            color: "#94a3b8",
            font: { size: 11 },
          },
        },
        tooltip: {
          backgroundColor: "#1e293b",
          titleColor: "#38bdf8",
          bodyColor: "#f8fafc",
          borderColor: "#334155",
          borderWidth: 1,
        },
      },
      scales: {
        x: {
          ticks: { color: "#64748b", maxRotation: 0, font: { size: 10 } },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
        },
        yPressure: {
          type: "linear",
          display: true,
          position: "left",
          title: { display: true, text: "Pressure (bar)", color: "#38bdf8", font: { size: 11 } },
          ticks: { color: "#38bdf8" },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
        },
        yFlow: {
          type: "linear",
          display: true,
          position: "right",
          title: { display: true, text: "Flow (m³/h)", color: "#f59e0b", font: { size: 11 } },
          ticks: { color: "#f59e0b" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

// Fetch Network Topology and Draw SVG
async function fetchTopology() {
  try {
    const res = await fetch("/api/network/topology");
    networkData = await res.json();
    drawSvgMap(networkData);
  } catch (err) {
    console.error("Failed to fetch topology:", err);
  }
}

// Draw Interactive SVG Pipeline Network
function drawSvgMap(topology) {
  const svg = document.getElementById("pipelineSvg");
  svg.innerHTML = "";

  const nodesMap = {};
  topology.nodes.forEach((n) => {
    nodesMap[n.id] = n;
  });

  // Custom node positions mapping for clear presentation diagram
  const customNodeCoords = {
    "PUMP-01": { x: 100, y: 260 },
    "JUNC-01": { x: 280, y: 260 },
    "JUNC-02": { x: 480, y: 150 },
    "RESERV-01": { x: 480, y: 380 },
    "JUNC-03": { x: 680, y: 170 },
    "JUNC-04": { x: 680, y: 390 },
    "TERMINAL-05": { x: 860, y: 200 },
  };

  // Section to node pair mapping
  const sectionEndpoints = {
    "SEC-A": ["PUMP-01", "JUNC-01"],
    "SEC-B": ["JUNC-01", "JUNC-02"],
    "SEC-C": ["JUNC-01", "RESERV-01"],
    "SEC-D": ["JUNC-02", "JUNC-03"],
    "SEC-E": ["RESERV-01", "JUNC-04"],
    "SEC-F": ["JUNC-03", "TERMINAL-05"],
  };

  // Draw Pipe Lines
  topology.sections.forEach((sec) => {
    const pair = sectionEndpoints[sec.section_id] || ["JUNC-01", "JUNC-02"];
    const p1 = customNodeCoords[pair[0]] || { x: 100, y: 100 };
    const p2 = customNodeCoords[pair[1]] || { x: 300, y: 300 };

    let statusClass = "status-normal";
    if (sec.current_status === "LEAK_DETECTED") statusClass = "status-leak";
    else if (sec.current_status === "WARNING") statusClass = "status-warning";
    else if (sec.current_status === "MAINTENANCE") statusClass = "status-maint";

    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", p1.x);
    line.setAttribute("y1", p1.y);
    line.setAttribute("x2", p2.x);
    line.setAttribute("y2", p2.y);
    line.setAttribute("class", `pipe-line ${statusClass}`);
    line.setAttribute("id", `pipe-${sec.section_id}`);
    line.setAttribute("title", `${sec.name} (${sec.current_status})`);

    line.addEventListener("click", () => {
      selectSection(sec.section_id);
    });

    svg.appendChild(line);

    // Section label on pipe midpoint
    const mx = (p1.x + p2.x) / 2;
    const my = (p1.y + p2.y) / 2 - 10;
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", mx);
    label.setAttribute("y", my);
    label.setAttribute("class", "node-text");
    label.setAttribute("style", "fill: #94a3b8; font-size: 10px; cursor: pointer;");
    label.textContent = sec.section_id;
    label.addEventListener("click", () => selectSection(sec.section_id));
    svg.appendChild(label);
  });

  // Draw Nodes
  Object.keys(customNodeCoords).forEach((nodeId) => {
    const coords = customNodeCoords[nodeId];
    const nodeObj = nodesMap[nodeId] || { name: nodeId, type: "NODE" };

    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", coords.x);
    circle.setAttribute("cy", coords.y);
    circle.setAttribute("r", 16);
    circle.setAttribute("class", "node-circle");
    if (nodeObj.type === "PUMP") circle.setAttribute("style", "stroke: #10b981; fill: #064e3b;");
    if (nodeObj.type === "RESERVOIR") circle.setAttribute("style", "stroke: #38bdf8; fill: #0c4a6e;");

    const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
    txt.setAttribute("x", coords.x);
    txt.setAttribute("y", coords.y + 28);
    txt.setAttribute("class", "node-text");
    txt.textContent = nodeId;

    g.appendChild(circle);
    g.appendChild(txt);
    svg.appendChild(g);
  });
}

// Select a section and update focused charts and view
function selectSection(secId) {
  currentSelectedSection = secId;
  const secName = {
    "SEC-A": "Section A: Transmission Main",
    "SEC-B": "Section B: Pipeline 3 (Industrial Feeder)",
    "SEC-C": "Section C: Sector 4-5 Residential Line",
    "SEC-D": "Section D: Commercial Central Loop",
    "SEC-E": "Section E: Elevated Reservoir Gravity Line",
    "SEC-F": "Section F: Suburb South Distribution",
  }[secId] || secId;

  document.getElementById("selectedSectionTitle").textContent = secName;
  updateChartData(secId);
}

// Refresh Dashboard Data from API
async function refreshDashboard() {
  try {
    const [summaryRes, alertsRes, tasksRes] = await Promise.all([
      fetch("/api/sensors/summary"),
      fetch("/api/alerts"),
      fetch("/api/repairs/tasks"),
    ]);

    const summary = await summaryRes.json();
    alertsData = await alertsRes.json();
    tasksData = await tasksRes.json();

    renderTelemetryTable(summary);
    renderAlerts(alertsData);
    renderTasks(tasksData);
    updateKPICards(summary, alertsData);
    updateChartData(currentSelectedSection);

    // Re-draw map statuses
    if (networkData) {
      summary.forEach((item) => {
        const pipeEl = document.getElementById(`pipe-${item.section_id}`);
        if (pipeEl) {
          pipeEl.className.baseVal = `pipe-line status-${item.status.toLowerCase().includes("leak") ? "leak" : item.status.toLowerCase()}`;
        }
      });
    }
  } catch (err) {
    console.warn("Polling update error:", err);
  }
}

// Update KPI Header Cards
function updateKPICards(summary, alerts) {
  const activeAlerts = alerts.filter((a) => a.status === "NEW" || a.status === "INSPECTION_ASSIGNED");
  const leakAlerts = activeAlerts.filter((a) => a.classification === "LOCALISED_LEAK");

  let totalLossRate = 0.0;
  activeAlerts.forEach((a) => {
    totalLossRate += a.estimated_loss_rate_m3_h || 0.0;
  });

  const kpiAlertsEl = document.getElementById("kpiAlerts");
  const kpiAlertsSubEl = document.getElementById("kpiAlertsSub");
  const kpiLossRateEl = document.getElementById("kpiLossRate");
  const kpiHealthEl = document.getElementById("kpiHealth");

  kpiAlertsEl.textContent = activeAlerts.length;
  kpiLossRateEl.textContent = `${totalLossRate.toFixed(1)} m³/h`;

  if (leakAlerts.length > 0) {
    kpiAlertsSubEl.textContent = `${leakAlerts[0].section_name}: Pipe Burst`;
    kpiHealthEl.textContent = `${Math.max(65.0, 98.0 - activeAlerts.length * 14.5).toFixed(1)}%`;
  } else if (activeAlerts.length > 0) {
    kpiAlertsSubEl.textContent = `Supply Anomaly`;
    kpiHealthEl.textContent = "86.2%";
  } else {
    kpiAlertsSubEl.textContent = "All sections within baseline";
    kpiHealthEl.textContent = "98.8%";
  }

  const activeBadge = document.getElementById("activeAlertBadge");
  if (leakAlerts.length > 0) {
    activeBadge.textContent = `${leakAlerts.length} Critical`;
    activeBadge.className = "status-pill CRITICAL";
  } else {
    activeBadge.textContent = "0 Active Leaks";
    activeBadge.className = "status-pill NORMAL";
  }
}

// Render Telemetry Table
function renderTelemetryTable(sectionsSummary) {
  const tbody = document.getElementById("telemetryTableBody");
  tbody.innerHTML = "";

  sectionsSummary.forEach((sec) => {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    if (sec.section_id === currentSelectedSection) {
      tr.style.background = "rgba(56, 189, 248, 0.12)";
    }

    const pDevColor = sec.pressure_deviation_pct < -15 ? "#ef4444" : sec.pressure_deviation_pct < -8 ? "#f59e0b" : "#10b981";

    tr.innerHTML = `
      <td><strong>${sec.section_name}</strong></td>
      <td>${sec.inlet_pressure.toFixed(2)}</td>
      <td>${sec.outlet_pressure.toFixed(2)}</td>
      <td>${sec.flow_rate.toFixed(1)}</td>
      <td>${sec.expected_pressure.toFixed(2)}</td>
      <td style="color: ${pDevColor}; font-weight: 700;">${sec.pressure_deviation_pct > 0 ? "+" : ""}${sec.pressure_deviation_pct.toFixed(1)}%</td>
      <td><span class="status-pill ${sec.status}">${sec.status}</span></td>
    `;

    tr.addEventListener("click", () => selectSection(sec.section_id));
    tbody.appendChild(tr);
  });
}

// Update Chart Data for Selected Section
async function updateChartData(sectionId) {
  try {
    const res = await fetch(`/api/sensors/latest?section_id=${sectionId}`);
    const readings = await res.json();
    if (!readings || readings.length === 0) return;

    // Separate pressure and flow readings sorted by timestamp
    const pReadings = readings.filter((r) => r.sensor_id.includes("-IN")).slice(-25);
    const qReadings = readings.filter((r) => r.sensor_type === "flow").slice(-25);

    const labels = pReadings.map((r) => {
      const d = new Date(r.timestamp);
      return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
    });

    const pData = pReadings.map((r) => r.value);
    const qData = qReadings.map((r) => r.value);

    // Compute expected baseline bounds for this section
    const baseP = sectionId === "SEC-A" ? 6.5 : sectionId === "SEC-B" ? 5.2 : 4.8;
    const baseUpper = pData.map(() => baseP + 0.35);
    const baseLower = pData.map(() => baseP - 0.35);

    sensorChartInstance.data.labels = labels;
    sensorChartInstance.data.datasets[0].data = pData;
    sensorChartInstance.data.datasets[1].data = baseUpper;
    sensorChartInstance.data.datasets[2].data = baseLower;
    sensorChartInstance.data.datasets[3].data = qData;
    sensorChartInstance.update("none");
  } catch (err) {
    console.error("Failed to update chart data:", err);
  }
}

// Render Explainable Alerts List
function renderAlerts(alerts) {
  const container = document.getElementById("alertsListContainer");
  if (!alerts || alerts.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 30px;">
        <span style="font-size: 24px;">✅</span><br>
        All pipeline sections operating within normal baseline bounds.
      </div>
    `;
    return;
  }

  container.innerHTML = "";
  alerts.forEach((alert) => {
    const card = document.createElement("div");
    card.className = `alert-card ${alert.risk_level}`;

    const lossBadge = alert.estimated_loss_rate_m3_h > 0 ? `| Est. Loss: <strong>${alert.estimated_loss_rate_m3_h} m³/h</strong>` : "";

    card.innerHTML = `
      <div class="alert-top">
        <div>
          <span class="status-pill ${alert.risk_level}">${alert.risk_level} (${alert.risk_score}%)</span>
          <span style="font-size: 11px; color: var(--text-muted); margin-left: 6px;">
            ${new Date(alert.timestamp).toLocaleTimeString()}
          </span>
          <div class="alert-title" style="margin-top: 4px;">${alert.title}</div>
        </div>
        <span class="status-pill ${alert.status}">${alert.status.replace("_", " ")}</span>
      </div>

      <div class="alert-metrics">
        <span>Pressure: <strong style="color: #ef4444;">${alert.pressure_drop_pct}%</strong></span>
        <span>Flow: <strong style="color: #f59e0b;">+${alert.flow_increase_pct}%</strong></span>
        ${lossBadge}
      </div>

      <div class="lang-tabs">
        <button class="tab-btn active" onclick="switchAlertLang(this, '${alert.alert_id}', 'en')">English</button>
        <button class="tab-btn" onclick="switchAlertLang(this, '${alert.alert_id}', 'hi')">हिन्दी</button>
        <button class="tab-btn" onclick="switchAlertLang(this, '${alert.alert_id}', 'mr')">मराठी</button>
      </div>

      <div class="alert-explanation" id="exp-${alert.alert_id}">
        ${alert.multilingual_explanations?.en || alert.ai_explanation}
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px;">
        ${
          alert.status === "NEW"
            ? `<button class="btn btn-primary" onclick="openAssignModal('${alert.alert_id}', '${alert.section_name}')">
                <span aria-hidden="true">👷</span> Dispatch Field Crew
               </button>`
            : `<span style="font-size: 12px; color: var(--accent-cyan); font-weight: 600;">
                Assigned: ${alert.assigned_to || "Field Team"}
               </span>`
        }
      </div>
    `;

    container.appendChild(card);
  });
}

// Switch Alert Multilingual Explanation
window.switchAlertLang = function (btn, alertId, lang) {
  const alert = alertsData.find((a) => a.alert_id === alertId);
  if (!alert) return;

  const parentTabs = btn.parentElement;
  parentTabs.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");

  const expEl = document.getElementById(`exp-${alertId}`);
  if (expEl && alert.multilingual_explanations) {
    expEl.textContent = alert.multilingual_explanations[lang] || alert.ai_explanation;
  }
};

// Render Inspection Tasks Queue (Step 6)
function renderTasks(tasks) {
  const tbody = document.getElementById("tasksTableBody");
  if (!tasks || tasks.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 16px;">No active work orders.</td></tr>`;
    return;
  }

  tbody.innerHTML = "";
  tasks.forEach((task) => {
    const tr = document.createElement("tr");
    const isCompleted = task.status === "COMPLETED";

    tr.innerHTML = `
      <td><strong>${task.task_id}</strong></td>
      <td>${task.section_id}</td>
      <td>${task.technician_name}</td>
      <td><span class="status-pill ${task.priority}">${task.priority}</span></td>
      <td><span class="status-pill ${isCompleted ? "NORMAL" : "MAINTENANCE"}">${task.status}</span></td>
      <td>${task.repair_type || "Inspection Underway"}</td>
      <td>
        ${
          !isCompleted
            ? `<button class="btn btn-success" style="padding: 4px 8px; font-size: 11px;" onclick="openCompleteModal('${task.task_id}')">
                <span aria-hidden="true">✔️</span> Verify & Complete
               </button>`
            : `<span style="color: #10b981; font-weight: 600; font-size: 11px;">Verified Normal</span>`
        }
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Modal Handlers
window.openAssignModal = function (alertId, sectionName) {
  document.getElementById("assignAlertId").value = alertId;
  document.getElementById("assignSectionName").value = sectionName;
  document.getElementById("assignModal").classList.add("active");
};

window.openCompleteModal = function (taskId) {
  document.getElementById("completeTaskId").value = taskId;
  document.getElementById("completeModal").classList.add("active");
};

// Event Listeners for UI Actions
function setupEventListeners() {
  // Modal closes
  document.getElementById("btnCloseAssignModal").onclick = () => document.getElementById("assignModal").classList.remove("active");
  document.getElementById("btnCancelAssign").onclick = () => document.getElementById("assignModal").classList.remove("active");

  document.getElementById("btnCloseCompleteModal").onclick = () => document.getElementById("completeModal").classList.remove("active");
  document.getElementById("btnCancelComplete").onclick = () => document.getElementById("completeModal").classList.remove("active");

  document.getElementById("btnOpenUploadModal").onclick = () => document.getElementById("uploadModal").classList.add("active");
  document.getElementById("btnCloseUploadModal").onclick = () => document.getElementById("uploadModal").classList.remove("active");
  document.getElementById("btnCancelUpload").onclick = () => document.getElementById("uploadModal").classList.remove("active");

  // Form Submissions
  document.getElementById("assignTaskForm").onsubmit = async (e) => {
    e.preventDefault();
    const alertId = document.getElementById("assignAlertId").value;
    const technician = document.getElementById("assignTechnician").value;
    const priority = document.getElementById("assignPriority").value;
    const notes = document.getElementById("assignNotes").value;

    try {
      await fetch("/api/repairs/assign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          alert_id: alertId,
          technician_name: technician,
          priority: priority,
          notes: notes,
        }),
      });
      document.getElementById("assignModal").classList.remove("active");
      refreshDashboard();
    } catch (err) {
      alert("Failed to assign technician: " + err);
    }
  };

  document.getElementById("completeTaskForm").onsubmit = async (e) => {
    e.preventDefault();
    const taskId = document.getElementById("completeTaskId").value;
    const repairType = document.getElementById("repairType").value;
    const findings = document.getElementById("repairFindings").value;
    const postP = parseFloat(document.getElementById("postRepairPressure").value);

    try {
      await fetch(`/api/repairs/tasks/${taskId}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          findings: findings,
          repair_type: repairType,
          post_repair_pressure: postP,
        }),
      });
      document.getElementById("completeModal").classList.remove("active");
      refreshDashboard();
    } catch (err) {
      alert("Failed to complete repair: " + err);
    }
  };

  // CSV Upload Submission
  document.getElementById("csvUploadForm").onsubmit = async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("csvFileInput");
    if (!fileInput.files.length) return;

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
      const res = await fetch("/api/upload/csv", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      alert(`Success! Processed ${data.rows_processed} rows and ingested ${data.readings_ingested} readings.`);
      document.getElementById("uploadModal").classList.remove("active");
      refreshDashboard();
    } catch (err) {
      alert("Upload failed: " + err);
    }
  };

  // Simulation Triggers
  document.getElementById("btnInjectLeak").onclick = async () => {
    selectSection("SEC-B");
    await fetch("/api/simulate/inject?section_id=SEC-B&fault_type=leak&severity=0.45", { method: "POST" });
    refreshDashboard();
  };

  document.getElementById("btnInjectMicroLeak").onclick = async () => {
    selectSection("SEC-C");
    await fetch("/api/simulate/inject?section_id=SEC-C&fault_type=leak&severity=0.20", { method: "POST" });
    refreshDashboard();
  };

  document.getElementById("btnInjectSupplyDrop").onclick = async () => {
    selectSection("SEC-A");
    await fetch("/api/simulate/inject?section_id=SEC-A&fault_type=supply_drop", { method: "POST" });
    refreshDashboard();
  };

  document.getElementById("btnResetSim").onclick = async () => {
    await fetch("/api/simulate/reset", { method: "POST" });
    refreshDashboard();
  };

  document.getElementById("btnManualDetect").onclick = async () => {
    await fetch("/api/detection/run", { method: "POST" });
    refreshDashboard();
  };
}
