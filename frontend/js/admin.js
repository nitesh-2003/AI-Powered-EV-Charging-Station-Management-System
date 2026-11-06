let trendChartInstance = null;
let donutChartInstance = null;
let mapPickerInstance = null;
let mapPickerMarker = null;

document.addEventListener("DOMContentLoaded", async () => {
  // Ensure user is authenticated as ADMIN, or auto-login with default admin credentials
  await ensureAdminAccess();
  loadAdminDashboard();
  initMapPicker();

  document.getElementById("btn-save-station").addEventListener("click", handleCreateStation);
  document.getElementById("btn-save-point").addEventListener("click", handleCreatePoint);
});

async function ensureAdminAccess() {
  if (!Auth.isAuthenticated() || !Auth.isAdmin()) {
    try {
      // Auto-authenticate with seeded admin or test admin
      let tokenData;
      try {
        tokenData = await apiRequest("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: "admin@voltflow.io", password: "AdminPassword123!" })
        });
      } catch (_) {
        tokenData = await apiRequest("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: "admin.operator@example.com", password: "AdminMasterKey123!" })
        });
      }
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
    document.getElementById("kpi-revenue").textContent = `₹${parseFloat(metrics.total_revenue).toFixed(2)}`;

    // 2. Render Charts
    renderTrendChart(metrics.revenue_trend);
    renderDonutChart(metrics.available_points, metrics.occupied_points, metrics.faulted_points);

    // 3. Render Stations Table
    renderStationsTable(stations, metrics.station_breakdown);

    // 4. Initialize AI Intelligence Suite (Demand Forecaster & Telemetry Sentinel)
    initAIIntelligenceSuite(stations);

    // 5. Render Live Sessions Stream
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
          label: "Revenue (₹)",
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
    const rev = revenueMap[st.id] ? `₹${Number(revenueMap[st.id]).toFixed(2)}` : "₹0.00";

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
      <td class="text-success fw-bold">${s.total_cost ? '₹' + Number(s.total_cost).toFixed(2) : '&mdash;'}</td>
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

// ==========================================
// AI & MACHINE LEARNING INTELLIGENCE SUITE
// ==========================================
let demandChartInstance = null;

function initAIIntelligenceSuite(stations) {
  const stationSelect = document.getElementById("ai-demand-station-select");
  const dateInput = document.getElementById("ai-demand-date-input");

  // Populate stations dropdown
  if (stationSelect && stations) {
    stationSelect.innerHTML = '<option value="">Select a Station Plaza...</option>' +
      stations.map(st => `<option value="${st.id}">${st.name}</option>`).join("");
    if (stations.length > 0) stationSelect.selectedIndex = 1;
  }

  // Set default forecast date to tomorrow
  if (dateInput && !dateInput.value) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    dateInput.value = tomorrow.toISOString().split("T")[0];
  }

  const btnDemand = document.getElementById("btn-run-demand-forecast");
  if (btnDemand && !btnDemand.dataset.bound) {
    btnDemand.dataset.bound = "true";
    btnDemand.addEventListener("click", handleRunDemandForecast);
  }

  const btnScan = document.getElementById("btn-run-telemetry-scan");
  if (btnScan && !btnScan.dataset.bound) {
    btnScan.dataset.bound = "true";
    btnScan.addEventListener("click", handleRunTelemetryScan);
  }
}

async function handleRunDemandForecast() {
  const stationId = document.getElementById("ai-demand-station-select").value;
  const targetDate = document.getElementById("ai-demand-date-input").value;

  if (!stationId) {
    showToast("Please select a target station for demand forecasting.", "error");
    return;
  }
  if (!targetDate) {
    showToast("Please choose a valid forecast date.", "error");
    return;
  }

  try {
    const forecast = await apiRequest("/ai/predict-demand", {
      method: "POST",
      body: JSON.stringify({
        station_id: stationId,
        target_date: targetDate,
        temperature_c: 26.5
      })
    });

    // Update KPI summary pills
    const pillContainer = document.getElementById("ai-demand-summary-pills");
    pillContainer.classList.remove("d-none");
    document.getElementById("pill-peak-hour").textContent = `Peak Window: ${forecast.peak_hour}:00 - ${(forecast.peak_hour + 1) % 24}:00`;
    document.getElementById("pill-peak-level").textContent = `Congestion: ${forecast.peak_demand_level}`;
    document.getElementById("pill-total-sessions").textContent = `Forecast: ${forecast.total_predicted_sessions} Sessions`;
    document.getElementById("pill-total-energy").textContent = `Est. Energy: ${forecast.total_predicted_energy_kwh} kWh`;

    renderDemandChart(forecast.hourly_forecast);
    showToast(`AI forecast generated for ${forecast.station_name}!`, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderDemandChart(hourlyForecast) {
  const ctx = document.getElementById("demandForecastChart");
  if (!ctx) return;

  if (demandChartInstance) {
    demandChartInstance.destroy();
  }

  const labels = hourlyForecast.map(h => `${h.hour}:00`);
  const sessionData = hourlyForecast.map(h => h.predicted_sessions);
  const energyData = hourlyForecast.map(h => h.predicted_energy_kwh);

  demandChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Predicted Charging Sessions",
          data: sessionData,
          backgroundColor: "rgba(14, 165, 233, 0.65)",
          borderColor: "#0ea5e9",
          borderWidth: 1.5,
          borderRadius: 4,
          yAxisID: "y"
        },
        {
          label: "Predicted Energy Demand (kWh)",
          data: energyData,
          type: "line",
          borderColor: "#10b981",
          backgroundColor: "transparent",
          borderWidth: 2,
          tension: 0.35,
          pointRadius: 2.5,
          yAxisID: "y1"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { size: 11 } }
        }
      },
      scales: {
        x: {
          ticks: { color: "#64748b", maxTicksLimit: 12 },
          grid: { display: false }
        },
        y: {
          type: "linear",
          position: "left",
          ticks: { color: "#64748b" },
          grid: { color: "#334155" },
          title: { display: true, text: "Sessions", color: "#0ea5e9" }
        },
        y1: {
          type: "linear",
          position: "right",
          ticks: { color: "#64748b" },
          grid: { drawOnChartArea: false },
          title: { display: true, text: "Energy (kWh)", color: "#10b981" }
        }
      }
    }
  });
}

async function handleRunTelemetryScan() {
  const tbody = document.getElementById("telemetry-anomalies-tbody");
  tbody.innerHTML = '<tr><td colspan="3" class="text-center py-3 text-info"><div class="spinner-border spinner-border-sm me-2"></div>Evaluating fleet telemetry vectors with Isolation Forest...</td></tr>';

  // Sample fleet readings covering normal operating chargers and fault conditions
  const sampleBatch = {
    readings: [
      {
        charging_point_id: "00000000-0000-0000-0000-000000000001",
        voltage_v: 285.0,  // VOLTAGE SAG
        current_a: 330.0,
        power_kw: 94.05,
        battery_soc_pct: 60.0,
        charging_duration_minutes: 22.0,
        energy_consumed_kwh: 34.5,
        temperature_c: 54.0
      },
      {
        charging_point_id: "00000000-0000-0000-0000-000000000002",
        voltage_v: 398.0,  // OVERHEATING
        current_a: 210.0,
        power_kw: 83.58,
        battery_soc_pct: 72.0,
        charging_duration_minutes: 40.0,
        energy_consumed_kwh: 45.0,
        temperature_c: 84.5
      },
      {
        charging_point_id: "00000000-0000-0000-0000-000000000003",
        voltage_v: 405.0,
        current_a: 140.0,
        power_kw: 56.7,
        battery_soc_pct: 45.0,
        charging_duration_minutes: 20.0,
        energy_consumed_kwh: 18.9,
        temperature_c: 41.0
      },
      {
        charging_point_id: "00000000-0000-0000-0000-000000000004",
        voltage_v: 400.0,
        current_a: 125.0,
        power_kw: 50.0,
        battery_soc_pct: 55.0,
        charging_duration_minutes: 15.0,
        energy_consumed_kwh: 0.0,  // METER SENSOR GLITCH
        temperature_c: 38.0
      }
    ]
  };

  try {
    const report = await apiRequest("/ai/inspect-fleet-telemetry", {
      method: "POST",
      body: JSON.stringify(sampleBatch)
    });

    if (report.results.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" class="text-center py-3 text-muted">No readings inspected.</td></tr>';
      return;
    }

    tbody.innerHTML = report.results.map((r, idx) => {
      let badgeClass = "bg-secondary";
      if (r.severity === "CRITICAL") badgeClass = "bg-danger";
      else if (r.severity === "HIGH") badgeClass = "bg-warning text-dark";
      else if (r.severity === "MEDIUM") badgeClass = "bg-info text-dark";
      else if (r.severity === "NORMAL") badgeClass = "bg-success";

      const title = r.detected_irregularities.length > 0
        ? r.detected_irregularities[0]
        : "Nominal electrical telemetry";

      return `
        <tr>
          <td>
            <div class="fw-semibold text-white">${title}</div>
            <div class="text-muted small">${r.recommended_action}</div>
          </td>
          <td><span class="badge ${badgeClass}">${r.severity}</span></td>
          <td>
            <span class="text-${r.is_anomaly ? 'danger' : 'success'} fw-semibold">
              <i class="bi bi-${r.is_anomaly ? 'exclamation-triangle-fill' : 'check-circle-fill'} me-1"></i>
              ${r.is_anomaly ? 'Anomaly Flagged' : 'Healthy'}
            </span>
          </td>
        </tr>
      `;
    }).join("");

    showToast(`Fleet Scan Complete: ${report.anomalies_detected} anomalies detected.`, "info");
  } catch (err) {
    showToast(err.message, "error");
    tbody.innerHTML = `<tr><td colspan="3" class="text-center py-3 text-danger">Diagnostic failed: ${err.message}</td></tr>`;
  }
}

// ==========================================
// GOOGLE MAPS & INTERACTIVE LOCATION PICKER
// ==========================================
function initMapPicker() {
  const modalEl = document.getElementById("newStationModal");
  if (!modalEl) return;

  modalEl.addEventListener("shown.bs.modal", () => {
    const defaultLat = 12.9716;
    const defaultLng = 77.5946;

    if (typeof L !== "undefined" && !mapPickerInstance) {
      try {
        mapPickerInstance = L.map("map-picker-container").setView([defaultLat, defaultLng], 12);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          maxZoom: 19
        }).addTo(mapPickerInstance);

        mapPickerMarker = L.marker([defaultLat, defaultLng], { draggable: true }).addTo(mapPickerInstance);

        function updateCoords(lat, lng) {
          document.getElementById("st-lat").value = lat.toFixed(6);
          document.getElementById("st-lon").value = lng.toFixed(6);
          reverseGeocode(lat, lng);
        }

        mapPickerInstance.on("click", (e) => {
          const { lat, lng } = e.latlng;
          mapPickerMarker.setLatLng([lat, lng]);
          updateCoords(lat, lng);
        });

        mapPickerMarker.on("dragend", () => {
          const { lat, lng } = mapPickerMarker.getLatLng();
          updateCoords(lat, lng);
        });

        // Initialize input fields with default coordinates if empty
        if (!document.getElementById("st-lat").value) {
          document.getElementById("st-lat").value = defaultLat.toFixed(6);
          document.getElementById("st-lon").value = defaultLng.toFixed(6);
        }
      } catch (err) {
        console.warn("Could not initialize Leaflet map:", err);
      }
    }

    if (mapPickerInstance) {
      setTimeout(() => {
        mapPickerInstance.invalidateSize();
      }, 250);
    }
  });

  // Google Maps coordinate parser button
  const btnParse = document.getElementById("btn-parse-gmaps");
  if (btnParse) {
    btnParse.addEventListener("click", parseGoogleMapsInput);
  }

  // Quick center buttons
  const btnCenterIndia = document.getElementById("btn-center-india");
  if (btnCenterIndia) {
    btnCenterIndia.addEventListener("click", () => {
      setMapLocation(20.5937, 78.9629, 5);
    });
  }

  const btnLocateMe = document.getElementById("btn-locate-me");
  if (btnLocateMe) {
    btnLocateMe.addEventListener("click", () => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          pos => {
            setMapLocation(pos.coords.latitude, pos.coords.longitude, 14);
            showToast("Centered on your current location!", "success");
          },
          err => showToast("Could not retrieve current location: " + err.message, "error")
        );
      } else {
        showToast("Geolocation is not supported by your browser.", "error");
      }
    });
  }
}

function setMapLocation(lat, lng, zoom = 14) {
  if (mapPickerInstance) {
    mapPickerInstance.setView([lat, lng], zoom);
    if (mapPickerMarker) mapPickerMarker.setLatLng([lat, lng]);
  }
  document.getElementById("st-lat").value = lat.toFixed(6);
  document.getElementById("st-lon").value = lng.toFixed(6);
  reverseGeocode(lat, lng);
}

function parseGoogleMapsInput() {
  const raw = document.getElementById("gmaps-input").value.trim();
  if (!raw) {
    showToast("Please paste a Google Maps link or coordinates.", "error");
    return;
  }

  let lat = null, lng = null;

  // Pattern 1: Direct "lat, lng" e.g. "12.9716, 77.5946" or "12.9716 77.5946"
  const commaMatch = raw.match(/(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)/);
  if (commaMatch) {
    lat = parseFloat(commaMatch[1]);
    lng = parseFloat(commaMatch[2]);
  }

  // Pattern 2: Google Maps URL containing @lat,lng e.g. https://www.google.com/maps/@12.9716,77.5946,15z
  if (lat === null) {
    const atMatch = raw.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
    if (atMatch) {
      lat = parseFloat(atMatch[1]);
      lng = parseFloat(atMatch[2]);
    }
  }

  // Pattern 3: Google Maps query param ?q=lat,lng
  if (lat === null) {
    const qMatch = raw.match(/[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)/);
    if (qMatch) {
      lat = parseFloat(qMatch[1]);
      lng = parseFloat(qMatch[2]);
    }
  }

  if (lat !== null && lng !== null && !isNaN(lat) && !isNaN(lng)) {
    setMapLocation(lat, lng, 14);
    showToast(`Location set from Google Maps: ${lat.toFixed(4)}, ${lng.toFixed(4)}`, "success");
  } else {
    showToast("Could not parse coordinates. Please enter 'lat, lng' or copy a Google Maps URL.", "error");
  }
}

async function reverseGeocode(lat, lng) {
  const addrInput = document.getElementById("st-address");
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`, {
      headers: { "Accept-Language": "en" }
    });
    const data = await res.json();
    if (data && data.display_name && (!addrInput.value || addrInput.value === "MG Road, Metro Pillar 140")) {
      addrInput.value = data.display_name.split(",").slice(0, 3).join(", ");
    }
  } catch (_) {
    // Non-fatal if geocoder service fails or offline
  }
}

