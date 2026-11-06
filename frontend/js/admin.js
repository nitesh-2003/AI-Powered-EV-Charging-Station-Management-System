let trendChartInstance = null;
let donutChartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
  // Ensure user is authenticated as ADMIN, or auto-login with default admin credentials
  await ensureAdminAccess();
  loadAdminDashboard();

  document.getElementById("btn-save-station").addEventListener("click", handleCreateStation);
  document.getElementById("btn-save-point").addEventListener("click", handleCreatePoint);
});

async function ensureAdminAccess() {
  if (!Auth.isAuthenticated() || !Auth.isAdmin()) {
    try {
      // Auto-authenticate as default station admin
      const tokenData = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "admin.operator@example.com", password: "AdminMasterKey123!" })
      });
      localStorage.setItem("ev_access_token", tokenData.access_token);
      const profile = await apiRequest("/auth/me");
      Auth.setSession(tokenData.access_token, profile);
    } catch (e) {
      console.warn("Could not auto-login admin; manual sign-in required:", e);
    }
  }
}

async function loadAdminDashboard() {
  try {
    const [metrics, stations, sessions] = await Promise.all([
      apiRequest("/analytics/dashboard"),
      apiRequest("/stations"),
      apiRequest("/sessions")
    ]);

    // 1. Populate KPI Cards
    document.getElementById("kpi-users").textContent = metrics.total_users;
    document.getElementById("kpi-stations").textContent = metrics.total_stations;
    document.getElementById("kpi-points").textContent = metrics.total_points;
    document.getElementById("kpi-avail").textContent = metrics.available_points;
    document.getElementById("kpi-occ").textContent = metrics.occupied_points;
    document.getElementById("kpi-energy").textContent = `${parseFloat(metrics.total_energy_kwh).toFixed(1)} kWh`;
    document.getElementById("kpi-revenue").textContent = `$${parseFloat(metrics.total_revenue).toFixed(2)}`;

    // 2. Render Charts
    renderTrendChart(metrics.revenue_trend);
    renderDonutChart(metrics.available_points, metrics.occupied_points, metrics.faulted_points);

    // 3. Render Stations Table
    renderStationsTable(stations, metrics.station_breakdown);

    // 4. Render Live Sessions Stream
    renderSessionsTable(sessions);

  } catch (err) {
    showToast(`Error loading dashboard: ${err.message}`, "error");
  }
}

function renderTrendChart(trendData) {
  const ctx = document.getElementById("trendChart").getContext("2d");
  if (trendChartInstance) trendChartInstance.destroy();

  const labels = trendData.map(d => d.date);
  const revenueData = trendData.map(d => d.revenue);
  const energyData = trendData.map(d => d.energy_kwh);

  trendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Revenue ($)",
          data: revenueData,
          borderColor: "#00d26a",
          backgroundColor: "rgba(0, 210, 106, 0.15)",
          fill: true,
          tension: 0.35,
          yAxisID: "y"
        },
        {
          label: "Energy (kWh)",
          data: energyData,
          borderColor: "#0dcaf0",
          backgroundColor: "rgba(13, 202, 240, 0.15)",
          borderDash: [5, 5],
          fill: false,
          tension: 0.35,
          yAxisID: "y1"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#f8fafc" } }
      },
      scales: {
        x: {
          ticks: { color: "#94a3b8" },
          grid: { color: "rgba(51, 65, 85, 0.5)" }
        },
        y: {
          type: "linear",
          position: "left",
          ticks: { color: "#00d26a" },
          grid: { color: "rgba(51, 65, 85, 0.5)" }
        },
        y1: {
          type: "linear",
          position: "right",
          ticks: { color: "#0dcaf0" },
          grid: { drawOnChartArea: false }
        }
      }
    }
  });
}

function renderDonutChart(available, occupied, faulted) {
  const ctx = document.getElementById("statusDonutChart").getContext("2d");
  if (donutChartInstance) donutChartInstance.destroy();

  const total = available + occupied + faulted;
  const data = total === 0 ? [1] : [available, occupied, faulted];
  const colors = total === 0 ? ["#334155"] : ["#00d26a", "#f59e0b", "#ef4444"];
  const labels = total === 0 ? ["No Dispensers"] : ["Available", "Occupied", "Faulted"];

  donutChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: "#1e293b"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#f8fafc", boxWidth: 12 }
        }
      },
      cutout: "70%"
    }
  });
}

function renderStationsTable(stations, breakdown) {
  const tbody = document.getElementById("admin-stations-tbody");
  tbody.innerHTML = "";

  if (stations.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No station plazas registered yet.</td></tr>';
    return;
  }

  const revenueMap = {};
  breakdown.forEach(b => {
    revenueMap[b.station_id] = b.revenue;
  });

  stations.forEach(st => {
    const points = st.charging_points || [];
    const rev = revenueMap[st.id] ? `$${Number(revenueMap[st.id]).toFixed(2)}` : "$0.00";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <strong>${st.name}</strong><br>
        <small class="text-muted"><i class="bi bi-geo"></i> ${st.latitude.toFixed(4)}, ${st.longitude.toFixed(4)}</small>
      </td>
      <td>${st.address}</td>
      <td>
        <span class="badge bg-secondary me-1">${points.length} Dispensers</span>
        ${points.map(p => `
          <button class="badge ${p.status === 'AVAILABLE' ? 'badge-available' : (p.status === 'OCCUPIED' ? 'badge-occupied' : 'badge-faulted')} border-0 my-1" 
                  title="Click to toggle Faulted/Available" 
                  onclick="togglePointStatus('${p.id}', '${p.status}')">
            ${p.identifier} (${p.connector_type} - ${p.status})
          </button>
        `).join(" ")}
      </td>
      <td>
        <span class="badge ${st.status === 'ACTIVE' ? 'badge-available' : 'badge-faulted'}">
          ${st.status}
        </span>
      </td>
      <td class="text-success fw-bold">${rev}</td>
      <td>
        <div class="btn-group btn-group-sm">
          <button class="btn btn-outline-info btn-sm" onclick="openAddPointModal('${st.id}')" title="Add Dispenser">
            <i class="bi bi-plus-lg"></i> Point
          </button>
          <button class="btn btn-outline-danger btn-sm" onclick="deleteStation('${st.id}')" title="Delete Station">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderSessionsTable(sessions) {
  const tbody = document.getElementById("admin-sessions-tbody");
  tbody.innerHTML = "";

  if (sessions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No charging sessions on record.</td></tr>';
    return;
  }

  sessions.slice(0, 10).forEach(s => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${s.id.substring(0, 8)}...</code></td>
      <td><small class="text-muted">${s.user_id.substring(0, 8)}...</small></td>
      <td>${new Date(s.start_time).toLocaleString()}</td>
      <td class="text-info fw-bold">${s.total_energy_kwh ? Number(s.total_energy_kwh).toFixed(2) + ' kWh' : 'Streaming...'}</td>
      <td class="text-success fw-bold">${s.total_cost ? '$' + Number(s.total_cost).toFixed(2) : '&mdash;'}</td>
      <td>
        <span class="badge ${s.status === 'COMPLETED' ? 'badge-available' : (s.status === 'IN_PROGRESS' ? 'badge-occupied' : 'badge-faulted')}">
          ${s.status}
        </span>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Admin Action: Create Station
async function handleCreateStation() {
  const name = document.getElementById("st-name").value.trim();
  const address = document.getElementById("st-address").value.trim();
  const latitude = parseFloat(document.getElementById("st-lat").value);
  const longitude = parseFloat(document.getElementById("st-lon").value);

  if (!name || !address || isNaN(latitude) || isNaN(longitude)) {
    showToast("Please fill all station fields with valid coordinates.", "error");
    return;
  }

  try {
    await apiRequest("/stations", {
      method: "POST",
      body: JSON.stringify({ name, address, latitude, longitude, status: "ACTIVE" })
    });
    bootstrap.Modal.getInstance(document.getElementById("newStationModal")).hide();
    document.getElementById("create-station-form").reset();
    showToast("Station plaza successfully registered!", "success");
    loadAdminDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Admin Action: Open Add Dispenser Modal
function openAddPointModal(stationId) {
  document.getElementById("point-station-id").value = stationId;
  new bootstrap.Modal(document.getElementById("newPointModal")).show();
}

// Admin Action: Add Dispenser
async function handleCreatePoint() {
  const stationId = document.getElementById("point-station-id").value;
  const identifier = document.getElementById("cp-identifier").value.trim();
  const connector_type = document.getElementById("cp-connector").value;
  const power_kw = parseFloat(document.getElementById("cp-power").value);
  const price_per_kwh = parseFloat(document.getElementById("cp-price").value);

  if (!identifier || isNaN(power_kw) || isNaN(price_per_kwh)) {
    showToast("Please provide valid dispenser details.", "error");
    return;
  }

  try {
    await apiRequest(`/stations/${stationId}/points`, {
      method: "POST",
      body: JSON.stringify({ identifier, connector_type, power_kw, price_per_kwh, status: "AVAILABLE" })
    });
    bootstrap.Modal.getInstance(document.getElementById("newPointModal")).hide();
    document.getElementById("create-point-form").reset();
    showToast(`Dispenser ${identifier} added to station!`, "success");
    loadAdminDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Admin Action: Toggle Dispenser Fault Status
async function togglePointStatus(pointId, currentStatus) {
  const newStatus = currentStatus === "FAULTED" ? "AVAILABLE" : "FAULTED";
  try {
    await apiRequest(`/points/${pointId}`, {
      method: "PUT",
      body: JSON.stringify({ status: newStatus })
    });
    showToast(`Dispenser marked as ${newStatus}.`, "success");
    loadAdminDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Admin Action: Delete Station
async function deleteStation(stationId) {
  if (!confirm("Are you sure you want to decommission this station plaza? All child dispensers will be deleted.")) return;

  try {
    await apiRequest(`/stations/${stationId}`, { method: "DELETE" });
    showToast("Station successfully decommissioned.", "success");
    loadAdminDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}
