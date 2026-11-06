/**
 * Unified API Client for AI-Powered EV CSMS
 */
const API_BASE = "/api/v1";

const Auth = {
  getToken() {
    return localStorage.getItem("ev_access_token");
  },
  getUser() {
    const u = localStorage.getItem("ev_user");
    return u ? JSON.parse(u) : null;
  },
  setSession(token, user) {
    localStorage.setItem("ev_access_token", token);
    localStorage.setItem("ev_user", JSON.stringify(user));
  },
  logout() {
    localStorage.removeItem("ev_access_token");
    localStorage.removeItem("ev_user");
    window.location.reload();
  },
  isAuthenticated() {
    return !!this.getToken();
  },
  isAdmin() {
    const user = this.getUser();
    return user && user.role === "ADMIN";
  }
};

async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  const token = Auth.getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers
    });

    if (response.status === 204) {
      return null;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const errorMsg = data?.detail || `HTTP Error ${response.status}`;
      // Do not trigger logout/reload on credentials validation failure during login
      if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/register")) {
        Auth.logout();
      }
      throw new Error(errorMsg);
    }

    return data;
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

function showToast(message, type = "success") {
  const alertContainer = document.getElementById("toast-container");
  if (!alertContainer) return;

  const alertDiv = document.createElement("div");
  alertDiv.className = `alert alert-${type === "error" ? "danger" : "success"} alert-dismissible fade show shadow`;
  alertDiv.role = "alert";
  alertDiv.innerHTML = `
    <strong>${type === "error" ? "Error:" : "Success:"}</strong> ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  alertContainer.appendChild(alertDiv);
  setTimeout(() => {
    alertDiv.classList.remove("show");
    setTimeout(() => alertDiv.remove(), 200);
  }, 4000);
}

