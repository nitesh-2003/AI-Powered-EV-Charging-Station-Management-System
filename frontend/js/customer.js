let currentActiveSession = null;
let telemetryInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  renderAuthState();
  loadStations();
  checkActiveSession();

  document.getElementById("btn-apply-filters").addEventListener("click", loadStations);
  document.getElementById("filter-search").addEventListener("keyup", (e) => {
    if (e.key === "Enter") loadStations();
  });

  // AI Recommendation Controls
  const socSlider = document.getElementById("input-battery-soc");
  if (socSlider) {
    socSlider.addEventListener("input", (e) => {
      document.getElementById("label-soc-val").textContent = `${e.target.value}%`;
    });
  }
  const btnAiRec = document.getElementById("btn-run-ai-recommendation");
  if (btnAiRec) {
    btnAiRec.addEventListener("click", handleRunAIRecommendation);
  }

  document.getElementById("auth-form").addEventListener("submit", handleAuthSubmit);
  document.getElementById("btn-submit-booking").addEventListener("click", handleBookingSubmit);
  document.getElementById("btn-stop-charging").addEventListener("click", handleStopCharging);
  document.getElementById("btn-my-activity").addEventListener("click", loadActivityHistory);
});

// Render user status in navbar
function renderAuthState() {
  const container = document.getElementById("auth-section");
  const user = Auth.getUser();

  if (user) {
    container.innerHTML = `
      <div class="dropdown">
        <button class="btn btn-outline-ev btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
          <i class="bi bi-person-check-fill text-success"></i> ${user.full_name} (${user.role})
        </button>
        <ul class="dropdown-menu dropdown-menu-end dropdown-menu-dark">
          <li><span class="dropdown-item-text text-muted small">${user.email}</span></li>
          <li><hr class="dropdown-divider border-secondary"></li>
          ${user.role === "ADMIN" ? '<li><a class="dropdown-item text-info" href="/admin.html"><i class="bi bi-speedometer2"></i> Admin Panel</a></li>' : ''}
          <li><a class="dropdown-item text-danger" href="#" onclick="Auth.logout()"><i class="bi bi-box-arrow-right"></i> Sign Out</a></li>
        </ul>
      </div>
    `;
  } else {
    container.innerHTML = `
      <button class="btn btn-outline-ev btn-sm" data-bs-toggle="modal" data-bs-target="#authModal">
        <i class="bi bi-box-arrow-in-right"></i> Sign In
      </button>
    `;
  }
}

let authMode = "login";
function toggleAuthMode(mode) {
  authMode = mode;
  const isReg = mode === "register";
  document.getElementById("pill-login").classList.toggle("active", !isReg);
  document.getElementById("pill-register").classList.toggle("active", isReg);
  document.getElementById("auth-name-group").classList.toggle("d-none", !isReg);
  document.getElementById("auth-role-group").classList.toggle("d-none", !isReg);
  document.getElementById("auth-submit-btn").textContent = isReg ? "Create Account" : "Sign In";
  document.getElementById("authModalTitle").innerHTML = isReg
    ? '<i class="bi bi-person-plus text-primary me-2"></i> Register New Account'
    : '<i class="bi bi-person-circle text-primary me-2"></i> Account Sign In';
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("auth-email").value.trim();
  const password = document.getElementById("auth-password").value;

  try {
    if (authMode === "register") {
      const full_name = document.getElementById("auth-fullname").value.trim();
      const role = document.getElementById("auth-role").value;
      await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name, role })
      });
      showToast("Account registered! Signing you in...", "success");
    }

    // Login to get access token
    const tokenData = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });

    // Fetch user profile with token
    localStorage.setItem("ev_access_token", tokenData.access_token);
    const profile = await apiRequest("/auth/me");
    Auth.setSession(tokenData.access_token, profile);

    bootstrap.Modal.getInstance(document.getElementById("authModal")).hide();
    showToast(`Welcome back, ${profile.full_name}!`, "success");
    renderAuthState();
    checkActiveSession();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Load stations with filtering
async function loadStations() {
  const grid = document.getElementById("stations-grid");
  const countLabel = document.getElementById("stations-count");
  grid.innerHTML = '<div class="col-12 text-center text-muted py-5"><div class="spinner-border text-primary me-2"></div> Fetching live stations...</div>';

  const search = document.getElementById("filter-search").value.trim();
  const connector = document.getElementById("filter-connector").value;
  const power = document.getElementById("filter-power").value;

  let query = "/stations?";
  if (search) query += `search=${encodeURIComponent(search)}&`;

  try {
    const stations = await apiRequest(query);
    grid.innerHTML = "";

    if (!stations || stations.length === 0) {
      grid.innerHTML = '<div class="col-12 text-center py-5 text-muted"><i class="bi bi-geo-alt-slash h1 d-block mb-2"></i> No charging stations match your criteria.</div>';
      countLabel.textContent = "0 stations found";
      return;
    }

    countLabel.textContent = `${stations.length} station${stations.length > 1 ? "s" : ""} available`;

    stations.forEach(st => {
      // Apply client-side connector/power filtering on station points
      let points = st.charging_points || [];
      if (connector) {
        points = points.filter(p => p.connector_type.toUpperCase() === connector);
      }
      if (power) {
        points = points.filter(p => p.power_kw >= parseFloat(power));
      }

      const availCount = points.filter(p => p.status === "AVAILABLE").length;

      const card = document.createElement("div");
      card.className = "col-lg-6 col-12";
      card.innerHTML = `
        <div class="card card-hover h-100 p-3">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <div>
              <h5 class="fw-bold mb-1">${st.name}</h5>
              <small class="text-muted"><i class="bi bi-geo-alt-fill text-danger me-1"></i>${st.address}</small>
            </div>
            <span class="badge ${st.status === 'ACTIVE' ? 'badge-available' : 'badge-faulted'}">
              ${st.status}
            </span>
          </div>

          <div class="d-flex gap-3 my-2 text-muted small">
            <span><i class="bi bi-plug-fill text-info"></i> ${points.length} Dispensers</span>
            <span><i class="bi bi-check-circle-fill text-success"></i> ${availCount} Free Now</span>
            <span><i class="bi bi-compass"></i> ${st.latitude.toFixed(4)}, ${st.longitude.toFixed(4)}</span>
          </div>

          <hr class="border-secondary my-2">

          <div class="charging-points-list">
            <h6 class="small text-muted text-uppercase fw-bold mb-2">Dispensers at this Plaza:</h6>
            ${points.length === 0 ? '<div class="small text-muted py-2">No chargers match connector filter.</div>' : ''}
            <div class="row g-2">
              ${points.map(p => `
                <div class="col-md-6">
                  <div class="p-2 border border-secondary rounded bg-dark d-flex justify-content-between align-items-center">
                    <div>
                      <div class="fw-bold text-white">${p.identifier}</div>
                      <div class="small">
                        <span class="badge-connector">${p.connector_type}</span>
                        <span class="text-warning">${p.power_kw} kW</span>
                      </div>
                      <div class="small text-muted">₹${Number(p.price_per_kwh).toFixed(2)}/kWh</div>
                    </div>
                    <div>
                      <span class="badge ${p.status === 'AVAILABLE' ? 'badge-available' : (p.status === 'OCCUPIED' ? 'badge-occupied' : 'badge-faulted')} mb-1 d-block text-center">
                        ${p.status}
                      </span>
                      ${p.status === 'AVAILABLE' ? `
                        <div class="btn-group btn-group-sm">
                          <button class="btn btn-outline-success btn-sm" onclick="openBookingModal('${p.id}', '${st.name}', '${p.identifier}', '${p.connector_type}', ${p.power_kw}, ${p.price_per_kwh})">
                            Reserve
                          </button>
                          <button class="btn btn-primary-ev btn-sm" onclick="quickStartSession('${p.id}')">
                            Plug In
                          </button>
                        </div>
                      ` : ''}
                    </div>
                  </div>
                </div>
              `).join("")}
            </div>
          </div>
        </div>
      `;
      grid.appendChild(card);
    });

  } catch (err) {
    grid.innerHTML = `<div class="col-12 alert alert-danger">Error loading stations: ${err.message}</div>`;
  }
}

// Open booking reservation modal
function openBookingModal(pointId, stationName, identifier, connector, power, price) {
  if (!Auth.isAuthenticated()) {
    showToast("Please sign in to reserve a charging slot.", "error");
    new bootstrap.Modal(document.getElementById("authModal")).show();
    return;
  }

  document.getElementById("book-point-id").value = pointId;
  document.getElementById("book-point-summary").innerHTML = `
    <strong>${stationName}</strong> &bull; Dispenser: <strong>${identifier}</strong><br>
    <span class="badge-connector">${connector}</span> | ${power} kW | <strong>₹${price.toFixed(2)} / kWh</strong>
  `;

  // Set default date to today, start time to next round hour
  const now = new Date();
  document.getElementById("book-date").value = now.toISOString().split("T")[0];
  
  const startH = (now.getHours() + 1) % 24;
  const endH = (startH + 1) % 24;
  document.getElementById("book-start-time").value = `${String(startH).padStart(2, "0")}:00`;
  document.getElementById("book-end-time").value = `${String(endH).padStart(2, "0")}:00`;

  new bootstrap.Modal(document.getElementById("bookingModal")).show();
}

async function handleBookingSubmit() {
  const pointId = document.getElementById("book-point-id").value;
  const date = document.getElementById("book-date").value;
  const startTime = document.getElementById("book-start-time").value;
  const endTime = document.getElementById("book-end-time").value;

  if (!date || !startTime || !endTime) {
    showToast("Please specify date and time window.", "error");
    return;
  }

  const startIso = new Date(`${date}T${startTime}:00Z`).toISOString();
  const endIso = new Date(`${date}T${endTime}:00Z`).toISOString();

  try {
    const res = await apiRequest("/bookings", {
      method: "POST",
      body: JSON.stringify({
        charging_point_id: pointId,
        start_time: startIso,
        end_time: endIso
      })
    });

    bootstrap.Modal.getInstance(document.getElementById("bookingModal")).hide();
    showToast(`Reservation confirmed! Slot is guaranteed for ${startTime} - ${endTime}.`, "success");
    loadStations();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Start charging session directly
async function quickStartSession(pointId, bookingId = null) {
  if (!Auth.isAuthenticated()) {
    showToast("Please sign in to start a charging session.", "error");
    new bootstrap.Modal(document.getElementById("authModal")).show();
    return;
  }

  try {
    const session = await apiRequest("/sessions/start", {
      method: "POST",
      body: JSON.stringify({
        charging_point_id: pointId,
        booking_id: bookingId,
        initial_meter_kwh: 1250.00
      })
    });

    showToast("Charging session started! Power is streaming.", "success");
    currentActiveSession = session;
    startTelemetrySimulation(session);
    loadStations();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Check if user currently has an in-progress session
async function checkActiveSession() {
  if (!Auth.isAuthenticated()) return;

  try {
    const mySessions = await apiRequest("/sessions/my");
    const active = mySessions.find(s => s.status === "IN_PROGRESS");
    if (active) {
      currentActiveSession = active;
      startTelemetrySimulation(active);
    } else {
      stopTelemetrySimulation();
    }
  } catch (err) {
    console.error("Failed to check active sessions:", err);
  }
}

function startTelemetrySimulation(session) {
  const banner = document.getElementById("active-session-banner");
  banner.classList.remove("d-none");

  const kwhEl = document.getElementById("telemetry-kwh");
  const powerEl = document.getElementById("telemetry-power");
  const costEl = document.getElementById("telemetry-cost");

  powerEl.textContent = "120.0 kW";

  if (telemetryInterval) clearInterval(telemetryInterval);

  let delivered = session.total_energy_kwh ? parseFloat(session.total_energy_kwh) : 0.0;
  telemetryInterval = setInterval(() => {
    delivered += 0.25; // simulate energy delivery
    kwhEl.textContent = delivered.toFixed(2);
    costEl.textContent = `₹${(delivered * 24.0).toFixed(2)}`;
  }, 1000);
}

function stopTelemetrySimulation() {
  if (telemetryInterval) clearInterval(telemetryInterval);
  document.getElementById("active-session-banner").classList.add("d-none");
  currentActiveSession = null;
}

async function handleStopCharging() {
  if (!currentActiveSession) return;

  const currentDelivered = parseFloat(document.getElementById("telemetry-kwh").textContent) || 25.5;
  const initial = parseFloat(currentActiveSession.initial_meter_kwh) || 1000.0;
  const finalMeter = initial + currentDelivered;

  try {
    const res = await apiRequest(`/sessions/${currentActiveSession.id}/stop`, {
      method: "POST",
      body: JSON.stringify({ final_meter_kwh: finalMeter })
    });

    stopTelemetrySimulation();
    showToast(`Session Completed! Energy: ${res.total_energy_kwh} kWh | Total Billed: ₹${res.total_cost}`, "success");
    loadStations();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Load Activity History (Bookings & Sessions)
async function loadActivityHistory() {
  if (!Auth.isAuthenticated()) {
    showToast("Please sign in to view your activity history.", "error");
    new bootstrap.Modal(document.getElementById("authModal")).show();
    return;
  }

  const bList = document.getElementById("bookings-history-list");
  const sList = document.getElementById("sessions-history-list");
  bList.innerHTML = '<div class="spinner-border spinner-border-sm text-primary"></div> Loading...';
  sList.innerHTML = '<div class="spinner-border spinner-border-sm text-primary"></div> Loading...';

  try {
    const [bookings, sessions] = await Promise.all([
      apiRequest("/bookings/my"),
      apiRequest("/sessions/my")
    ]);

    // Render bookings
    if (bookings.length === 0) {
      bList.innerHTML = '<div class="text-muted small">No reservations found.</div>';
    } else {
      bList.innerHTML = `
        <div class="table-responsive">
          <table class="table table-dark-custom align-middle">
            <thead>
              <tr>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${bookings.map(b => `
                <tr>
                  <td>${new Date(b.start_time).toLocaleString()}</td>
                  <td>${new Date(b.end_time).toLocaleString()}</td>
                  <td>
                    <span class="badge ${b.status === 'CONFIRMED' ? 'badge-available' : (b.status === 'COMPLETED' ? 'badge-occupied' : 'badge-faulted')}">
                      ${b.status}
                    </span>
                  </td>
                  <td>
                    ${b.status === 'CONFIRMED' ? `
                      <button class="btn btn-outline-danger btn-sm" onclick="cancelBooking('${b.id}')">Cancel</button>
                    ` : '<span class="text-muted small">&mdash;</span>'}
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }

    // Render sessions
    if (sessions.length === 0) {
      sList.innerHTML = '<div class="text-muted small">No charging sessions found.</div>';
    } else {
      sList.innerHTML = `
        <div class="table-responsive">
          <table class="table table-dark-custom align-middle">
            <thead>
              <tr>
                <th>Date</th>
                <th>Energy (kWh)</th>
                <th>Total Cost</th>
                <th>Invoice Ref</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${sessions.map(s => `
                <tr>
                  <td>${new Date(s.start_time).toLocaleDateString()}</td>
                  <td class="fw-bold text-info">${s.total_energy_kwh || '0.00'} kWh</td>
                  <td class="fw-bold text-success">₹${s.total_cost || '0.00'}</td>
                  <td><code class="text-warning">${s.payment ? s.payment.transaction_ref : 'Pending'}</code></td>
                  <td>
                    <span class="badge ${s.status === 'COMPLETED' ? 'badge-available' : 'badge-occupied'}">
                      ${s.status}
                    </span>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }
  } catch (err) {
    bList.innerHTML = `<div class="text-danger small">Error: ${err.message}</div>`;
  }
}

async function cancelBooking(bookingId) {
  try {
    await apiRequest(`/bookings/${bookingId}/cancel`, { method: "POST" });
    showToast("Booking cancelled successfully.", "success");
    loadActivityHistory();
    loadStations();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==========================================
// AI FEATURE 2: INTELLIGENT STATION RECOMMENDATION
// ==========================================
async function handleRunAIRecommendation() {
  const soc = parseFloat(document.getElementById("input-battery-soc").value);
  const connector = document.getElementById("ai-filter-connector").value;
  const grid = document.getElementById("stations-grid");
  const countLabel = document.getElementById("stations-count");
  const alertBanner = document.getElementById("ai-soc-alert-banner");
  const alertText = document.getElementById("ai-soc-alert-text");

  grid.innerHTML = '<div class="col-12 text-center text-info py-5"><div class="spinner-border text-info me-2"></div> AI Engine evaluating multi-criteria ranking (proximity, bay availability, power, and tariff)...</div>';

  // Driver reference coordinates (defaulting to Bengaluru, India hub)
  let userLat = 12.9716;
  let userLon = 77.5946;

  // Try to acquire browser geolocation if available
  if (navigator.geolocation) {
    try {
      const pos = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 1500, enableHighAccuracy: false });
      });
      userLat = pos.coords.latitude;
      userLon = pos.coords.longitude;
    } catch (_) {
      // Graceful fallback to default Indian charging hub coordinates
    }
  }

  try {
    const response = await apiRequest("/ai/recommend-stations", {
      method: "POST",
      body: JSON.stringify({
        user_latitude: userLat,
        user_longitude: userLon,
        battery_percentage: soc,
        connector_type: connector || null,
        max_distance_km: 2500.0
      })
    });

    if (response.battery_soc_alert) {
      alertText.textContent = response.battery_soc_alert;
      alertBanner.classList.remove("d-none");
    } else {
      alertBanner.classList.add("d-none");
    }

    const recs = response.recommendations || [];
    countLabel.textContent = `${recs.length} AI-ranked recommendations`;

    if (recs.length === 0) {
      grid.innerHTML = '<div class="col-12 text-center py-5 text-muted">No charging stations match your criteria. Try changing the connector filter.</div>';
      return;
    }

    grid.innerHTML = "";
    recs.forEach(rec => {
      const isTopPick = rec.rank === 1;
      const card = document.createElement("div");
      card.className = "col-lg-6 col-12";

      let rankBadge = `<span class="badge bg-secondary">Rank #${rec.rank} • Score: ${rec.recommendation_score}/100</span>`;
      let borderStyle = "";
      if (isTopPick) {
        rankBadge = `<span class="badge bg-warning text-dark fw-bold"><i class="bi bi-trophy-fill me-1"></i> TOP AI MATCH (#1) • Score: ${rec.recommendation_score}/100</span>`;
        borderStyle = "border: 1.5px solid #f59e0b;";
      }

      card.innerHTML = `
        <div class="card card-hover h-100 p-3" style="${borderStyle}">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <div>
              <div class="mb-1">${rankBadge}</div>
              <h5 class="fw-bold mb-1 text-white">${rec.station_name}</h5>
              <div class="text-muted small"><i class="bi bi-geo-alt text-danger me-1"></i> ${rec.address} &bull; <strong class="text-info">${rec.distance_km} km away</strong></div>
            </div>
            <span class="badge ${rec.available_points > 0 ? 'badge-available' : 'badge-occupied'}">
              ${rec.available_points} of ${rec.total_points} Open
            </span>
          </div>

          <div class="p-2 rounded bg-dark border border-secondary mb-3 small">
            <i class="bi bi-stars text-info me-1"></i>
            <span class="text-light fw-medium">${rec.recommendation_reason}</span>
            <div class="d-flex gap-2 text-muted mt-1" style="font-size: 0.75rem;">
              <span>Dist: <strong>${rec.score_breakdown.distance_score}</strong></span> &bull;
              <span>Avail: <strong>${rec.score_breakdown.availability_score}</strong></span> &bull;
              <span>Power: <strong>${rec.score_breakdown.power_score}</strong></span> &bull;
              <span>Tariff: <strong>${rec.score_breakdown.price_score}</strong></span>
            </div>
          </div>

          <div class="d-flex justify-content-between align-items-center mt-auto pt-2 border-top border-secondary">
            <div>
              <span class="text-muted small">Max Power:</span>
              <strong class="text-white">${rec.max_power_kw} kW</strong>
              <span class="text-muted small ms-2">From:</span>
              <strong class="text-success">₹${rec.min_price_per_kwh.toFixed(2)} / kWh</strong>
            </div>
            <button class="btn btn-outline-primary btn-sm" onclick="filterToStation('${rec.station_name}')">
              <i class="bi bi-plug-fill me-1"></i> View Bays
            </button>
          </div>
        </div>
      `;
      grid.appendChild(card);
    });

    showToast(`AI ranking computed based on ${soc}% battery state!`, "success");
  } catch (err) {
    showToast(err.message, "error");
    grid.innerHTML = `<div class="col-12 text-center text-danger py-4">Failed to compute AI recommendations: ${err.message}</div>`;
  }
}

function filterToStation(stationName) {
  document.getElementById("filter-search").value = stationName;
  loadStations();
}

// ==========================================
// AI FEATURE 4: HYBRID RAG CHAT ASSISTANT
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  const chatForm = document.getElementById("chat-form");
  if (chatForm) {
    chatForm.addEventListener("submit", handleChatSubmit);
  }

  document.querySelectorAll(".chat-suggestion").forEach(btn => {
    btn.addEventListener("click", () => {
      const prompt = btn.dataset.prompt;
      document.getElementById("chat-input-text").value = prompt;
      handleChatSubmit(new Event("submit"));
    });
  });
});

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input-text");
  const message = input.value.trim();
  if (!message) return;

  const container = document.getElementById("chat-messages-container");

  // 1. Append User Message Bubble
  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble-user";
  userBubble.textContent = message;
  container.appendChild(userBubble);
  input.value = "";
  container.scrollTop = container.scrollHeight;

  // 2. Append Loading Placeholder
  const loadingBubble = document.createElement("div");
  loadingBubble.className = "chat-bubble-ai text-info";
  loadingBubble.id = "chat-loading-placeholder";
  loadingBubble.innerHTML = '<div class="spinner-grow spinner-grow-sm me-2"></div> Querying ChromaDB Vector Store & Live Database...';
  container.appendChild(loadingBubble);
  container.scrollTop = container.scrollHeight;

  try {
    const response = await apiRequest("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message })
    });

    // Remove loading placeholder
    const loader = document.getElementById("chat-loading-placeholder");
    if (loader) loader.remove();

    // 3. Append Grounded AI Response
    const aiBubble = document.createElement("div");
    aiBubble.className = "chat-bubble-ai";

    let sourcesHtml = "";
    if (response.sources && response.sources.length > 0) {
      sourcesHtml = `
        <div class="mt-2 pt-2 border-top border-secondary">
          <small class="text-muted d-block mb-1"><i class="bi bi-shield-check text-success me-1"></i> Grounded Information Sources:</small>
          <div class="d-flex flex-wrap gap-1">
            ${response.sources.map(s => `
              <span class="chat-source-tag" title="${s.snippet.replace(/"/g, '&quot;')}">
                <i class="bi bi-${s.source_type === 'LIVE_DATABASE' ? 'database-fill text-info' : 'book-fill text-warning'} me-1"></i>
                ${s.title}
              </span>
            `).join("")}
          </div>
        </div>
      `;
    }

    // Convert markdown bolding and bullet newlines to HTML
    const formattedAnswer = response.answer
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');

    aiBubble.innerHTML = `
      <div>${formattedAnswer}</div>
      ${sourcesHtml}
    `;

    container.appendChild(aiBubble);
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    const loader = document.getElementById("chat-loading-placeholder");
    if (loader) loader.remove();

    const errBubble = document.createElement("div");
    errBubble.className = "chat-bubble-ai text-danger";
    errBubble.innerHTML = `<i class="bi bi-exclamation-octagon me-1"></i> Error: ${err.message}`;
    container.appendChild(errBubble);
    container.scrollTop = container.scrollHeight;
  }
}



