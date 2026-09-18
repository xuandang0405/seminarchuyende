// Centralized Same-Origin API Resolver for Tourist Client
function resolveClientApiBase() {
  if (typeof window !== "undefined" && window.TOURVOICE_API_BASE) {
    const custom = window.TOURVOICE_API_BASE.trim().replace(/\/+$/, "");
    if (custom.includes("localhost") && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
      console.warn("[Client API] Rejecting localhost in remote environment, falling back to same-origin /api/v1");
      return "/api/v1";
    }
    return custom;
  }
  return "/api/v1";
}
const API_BASE = resolveClientApiBase();

// State
let map;
let userMarker;
let userLocation = { lat: 10.7655, lng: 106.7035 }; // District 4 center
let currentLang = "vi";
let poiDataList = [];
let poiLayers = [];
let activeSessionId = null;
let currentPlaybackId = null;
let lastTriggeredPoiId = null;
let poiCooldowns = {}; // poi_id -> timestamp

// User & Entitlement State
let currentUser = null;
let currentGuestCredential = localStorage.getItem("guest_credential") || null;
let currentAuthToken = localStorage.getItem("auth_token") || null;
let userEntitledTours = [];
let activeTourId = "tour_quan_4_lich_su";
let trialRemaining = 1;
let pendingTrialPoiId = null;
let pendingCheckoutTourId = null;
let activeOrderId = null;
let selectedPaymentMethod = "vietqr";
let reconcileInterval = null;

// Routing & Search State
let routeLayerGroup = null;
let tourLayerGroup = null;
let activeRouteResult = null;
let activeRoutingMode = "walking";
let isPickingOriginOnMap = false;
let pickedOriginLocation = null;
let followUser = true;
let searchDebounceTimer = null;
let currentCategoryFilter = "all";
let mapConfig = null;

// Audio Elements
const audioElement = document.getElementById("global-audio");
const playerBar = document.getElementById("player-bar");
const btnPlayPause = document.getElementById("btn-play-pause");
const playerTitle = document.getElementById("player-poi-title");
const playerDesc = document.getElementById("player-poi-desc");
const triggerTypeLabel = document.getElementById("player-trigger-type");
const progressFill = document.getElementById("progress-fill");
const currentTimeLabel = document.getElementById("current-time");
const totalTimeLabel = document.getElementById("total-time");
const seekBar = document.getElementById("seek-bar");

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
  await initMap();
  await initSession();
  await fetchPOIs();
  setupEventListeners();
  setupSearchAndFilters();
  await loadTourRouteLine(activeTourId);
});

function getAuthHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (currentAuthToken) {
    headers["Authorization"] = `Bearer ${currentAuthToken}`;
  }
  if (currentGuestCredential) {
    headers["X-Guest-Credential"] = currentGuestCredential;
  }
  return headers;
}

// ==========================================================================
// SESSION & AUTHENTICATION (SECTION 2 & 4)
// ==========================================================================

async function initSession() {
  // 1. Verify User Token if present
  if (currentAuthToken) {
    try {
      const meRes = await fetch(`${API_BASE}/auth/me`, {
        headers: { "Authorization": `Bearer ${currentAuthToken}` }
      });
      if (meRes.ok) {
        currentUser = await meRes.json();
        console.log("Logged in as user:", currentUser.email);
        await refreshUserEntitlements();
      } else {
        // Token expired
        localStorage.removeItem("auth_token");
        currentAuthToken = null;
        currentUser = null;
      }
    } catch (e) {
      console.warn("Could not verify auth token:", e);
    }
  }

  // 2. If not logged in, check Guest session
  if (!currentUser) {
    if (currentGuestCredential) {
      // Check trial status on default tour
      await checkTourAccess(activeTourId);
    } else {
      // First visit: Show Welcome Modal
      openModal("welcome-modal");
    }
  }

  updateIdentityUI();
}

function updateIdentityUI() {
  const nameEl = document.getElementById("user-display-name");
  const badgeEl = document.getElementById("user-trial-badge");
  const btnAction = document.getElementById("btn-auth-action");

  if (!nameEl) return;

  if (currentUser) {
    nameEl.innerText = `👤 ${currentUser.full_name || currentUser.email}`;
    const ownedCount = userEntitledTours.length;
    badgeEl.innerText = `🌟 Đã sở hữu ${ownedCount} Tour (${currentUser.role || 'Du khách'})`;
    badgeEl.style.color = "#00b4d8";
    btnAction.innerText = "Đăng Xuất";
    btnAction.onclick = logoutUser;
    btnAction.style.background = "#475569";
  } else if (currentGuestCredential) {
    nameEl.innerText = "👤 Khách Ẩn Danh";
    if (trialRemaining > 0) {
      badgeEl.innerText = "🎙️ Còn 1 lượt nghe thử";
      badgeEl.style.color = "#10b981";
    } else {
      badgeEl.innerText = "🔒 Đã dùng lượt nghe thử";
      badgeEl.style.color = "#f59e0b";
    }
    btnAction.innerText = "Đăng Nhập";
    btnAction.onclick = () => openAuthModal("login");
    btnAction.style.background = "#ff6b35";
  } else {
    nameEl.innerText = "👤 Chưa kích hoạt";
    badgeEl.innerText = "Chọn tiếp tục để bắt đầu";
    badgeEl.style.color = "#94a3b8";
    btnAction.innerText = "Bắt Đầu";
    btnAction.onclick = () => openModal("welcome-modal");
  }
}

window.continueAsGuest = async function() {
  try {
    const res = await fetch(`${API_BASE}/guest-sessions`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      currentGuestCredential = data.guest_credential;
      localStorage.setItem("guest_credential", currentGuestCredential);
      closeModal("welcome-modal");
      trialRemaining = 1;
      updateIdentityUI();
      console.log("Guest session active:", data.guest_session_id);
    }
  } catch (err) {
    console.error("Error creating guest session:", err);
    closeModal("welcome-modal");
  }
};

window.openAuthModal = function(tab = "login") {
  closeModal("welcome-modal");
  document.getElementById("auth-modal").classList.add("active");
  switchAuthTab(tab);
};

window.switchAuthTab = function(tab) {
  const loginForm = document.getElementById("auth-login-form");
  const regForm = document.getElementById("auth-register-form");
  const btnLogin = document.getElementById("tab-btn-login");
  const btnReg = document.getElementById("tab-btn-register");
  const title = document.getElementById("auth-modal-title");

  if (tab === "login") {
    loginForm.style.display = "block";
    regForm.style.display = "none";
    btnLogin.style.background = "#ff6b35";
    btnLogin.style.color = "white";
    btnReg.style.background = "transparent";
    btnReg.style.color = "#94a3b8";
    title.innerText = "🔑 Đăng Nhập";
  } else {
    loginForm.style.display = "none";
    regForm.style.display = "block";
    btnReg.style.background = "#10b981";
    btnReg.style.color = "white";
    btnLogin.style.background = "transparent";
    btnLogin.style.color = "#94a3b8";
    title.innerText = "📝 Đăng Ký Tài Khoản Du Khách";
  }
};

window.submitLogin = async function() {
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  if (!email || !password) {
    alert("Vui lòng điền email và mật khẩu.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Đăng nhập không thành công.");
    }

    currentAuthToken = data.access_token;
    localStorage.setItem("auth_token", currentAuthToken);

    // If had guest session, claim it
    if (currentGuestCredential) {
      try {
        await fetch(`${API_BASE}/guest-sessions/claim`, {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({ guest_credential: currentGuestCredential })
        });
        localStorage.removeItem("guest_credential");
        currentGuestCredential = null;
      } catch (e) {
        console.warn("Guest claim notice:", e);
      }
    }

    closeModal("auth-modal");
    await initSession();

    // Check if user was trying to checkout
    if (pendingCheckoutTourId) {
      const tId = pendingCheckoutTourId;
      pendingCheckoutTourId = null;
      openBookingModal(tId);
    }
  } catch (err) {
    alert(err.message);
  }
};

window.submitRegister = async function() {
  const name = document.getElementById("reg-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  const confirm = document.getElementById("reg-confirm-password").value;

  if (!name || !email || !password) {
    alert("Vui lòng điền đầy đủ thông tin.");
    return;
  }
  if (password !== confirm) {
    alert("Mật khẩu xác nhận không khớp.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: name,
        email: email,
        password: password,
        confirm_password: confirm,
        guest_credential: currentGuestCredential
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || data.detail || "Đăng ký không thành công.");
    }

    currentAuthToken = data.access_token;
    localStorage.setItem("auth_token", currentAuthToken);
    if (currentGuestCredential) {
      localStorage.removeItem("guest_credential");
      currentGuestCredential = null;
    }

    closeModal("auth-modal");
    await initSession();

    if (pendingCheckoutTourId) {
      const tId = pendingCheckoutTourId;
      pendingCheckoutTourId = null;
      openBookingModal(tId);
    }
  } catch (err) {
    alert(err.message);
  }
};

window.logoutUser = async function() {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      headers: getAuthHeaders()
    });
  } catch (e) {}

  localStorage.removeItem("auth_token");
  currentAuthToken = null;
  currentUser = null;
  userEntitledTours = [];

  // Reset to guest session
  await continueAsGuest();
};

async function refreshUserEntitlements() {
  if (!currentAuthToken) return;
  try {
    const res = await fetch(`${API_BASE}/me/tours`, { headers: getAuthHeaders() });
    if (res.ok) {
      const data = await res.json();
      userEntitledTours = data.map(t => t.tour_id);
    }
  } catch (e) {
    console.warn("Could not fetch user entitlements:", e);
  }
}

async function checkTourAccess(tourId) {
  try {
    const res = await fetch(`${API_BASE}/tours/${tourId}/access`, { headers: getAuthHeaders() });
    if (res.ok) {
      const access = await res.json();
      trialRemaining = access.trial_remaining;
      if (access.has_entitlement && !userEntitledTours.includes(tourId)) {
        userEntitledTours.push(tourId);
      }
      return access;
    }
  } catch (e) {
    console.warn("Could not check tour access:", e);
  }
  return null;
}

// ==========================================================================
// MAP, POI & REAL ROUTING INTEGRATION (OSRM ENGINE)
// ==========================================================================

async function initMap() {
  try {
    const configRes = await fetch(`${API_BASE}/map/config`);
    if (configRes.ok) {
      mapConfig = await configRes.json();
      userLocation = {
        lat: mapConfig.center.latitude,
        lng: mapConfig.center.longitude
      };
    }
  } catch (e) {
    console.warn("Could not fetch /map/config, using default District 4 center:", e);
  }

  map = L.map("map", {
    center: [userLocation.lat, userLocation.lng],
    zoom: (mapConfig && mapConfig.default_zoom) || 15
  });

  const tileUrl = (mapConfig && mapConfig.style_url) || "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
  const tileAttrib = (mapConfig && mapConfig.attribution) || "© CartoDB Voyager | OpenStreetMap";

  const defaultBaseLayer = L.tileLayer(tileUrl, {
    maxZoom: 20,
    subdomains: "abcd",
    attribution: tileAttrib
  });

  const osmStandard = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors"
  });

  defaultBaseLayer.addTo(map);

  const baseMaps = {
    "🗺️ Bản Đồ Chi Tiết (Voyager)": defaultBaseLayer,
    "📍 OpenStreetMap (Chuẩn)": osmStandard,
  };
  L.control.layers(baseMaps, null, { position: "topright" }).addTo(map);

  // Dedicated layer groups for real routes
  tourLayerGroup = L.layerGroup().addTo(map);
  routeLayerGroup = L.layerGroup().addTo(map);

  const userIcon = L.divIcon({
    className: "user-marker-container",
    html: '<div class="user-marker"><div class="user-marker-pulse"></div></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });

  userMarker = L.marker([userLocation.lat, userLocation.lng], { icon: userIcon }).addTo(map);

  // Dragging disables auto camera recenter (BR-MAP-03)
  map.on("dragstart", () => {
    followUser = false;
  });

  // Map click handler
  map.on("click", (e) => {
    if (isPickingOriginOnMap) {
      pickedOriginLocation = { lat: e.latlng.lat, lng: e.latlng.lng };
      isPickingOriginOnMap = false;
      const originSelect = document.getElementById("dir-origin-select");
      if (originSelect) {
        let opt = originSelect.querySelector("option[value='picked_map']");
        if (opt) {
          opt.innerText = `📌 Tọa độ chọn (${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)})`;
          originSelect.value = "picked_map";
        }
      }
      calculateRoute();
      return;
    }

    updateUserLocation(e.latlng.lat, e.latlng.lng);
  });

  // Connect standardized LocationService stream (BR-GEO-01 / BR-GEO-02)
  if (window.locationService) {
    window.locationService.startWatching((sample) => {
      onLocationSampleReceived(sample);
    });
  }
}

let userAccuracyCircle = null;

function onLocationSampleReceived(sample) {
  if (!sample) return;
  userLocation = { lat: sample.latitude, lng: sample.longitude };

  if (userMarker) {
    userMarker.setLatLng([sample.latitude, sample.longitude]);
  }

  // Render & update accuracy circle (BR-MAP-02)
  if (userAccuracyCircle) {
    userAccuracyCircle.setLatLng([sample.latitude, sample.longitude]);
    userAccuracyCircle.setRadius(sample.accuracyM || 15);
  } else if (map) {
    userAccuracyCircle = L.circle([sample.latitude, sample.longitude], {
      radius: sample.accuracyM || 15,
      color: "#38bdf8",
      weight: 1,
      fillColor: "#38bdf8",
      fillOpacity: 0.15,
      interactive: false
    }).addTo(map);
  }

  const coordsEl = document.getElementById("current-coords");
  if (coordsEl) {
    const accStr = sample.accuracyM ? ` (±${Math.round(sample.accuracyM)}m)` : "";
    coordsEl.innerText = `${sample.longitude.toFixed(4)}, ${sample.latitude.toFixed(4)}${accStr}`;
  }

  if (followUser && map) {
    map.setView([sample.latitude, sample.longitude]);
  }

  checkGeofences(sample.latitude, sample.longitude);
}

// ==========================================================================
// REAL WALKING TOUR ROUTING (OSRM Leg Stitched)
// ==========================================================================

async function loadTourRouteLine(tourId) {
  if (!tourLayerGroup) return;
  tourLayerGroup.clearLayers();

  try {
    const res = await fetch(`${API_BASE}/routes/tour/${tourId}?locale=${currentLang}`);
    if (res.ok) {
      const data = await res.json();
      const coords = data.geometry && data.geometry.coordinates;
      if (coords && coords.length > 1) {
        // GeoJSON uses [lon, lat], Leaflet uses [lat, lon]
        const latLngs = coords.map(pt => [pt[1], pt[0]]);
        const tourPolyline = L.polyline(latLngs, {
          color: "#ff6b35",
          weight: 5,
          opacity: 0.85,
          dashArray: "6, 8"
        }).addTo(tourLayerGroup);

        tourPolyline.bindPopup(`
          <div style="font-family: 'Outfit', sans-serif;">
            <strong style="color: #ff6b35;">🚶 ${data.tour_name}</strong><br>
            Quãng đường thực tế: <strong>${data.total_distance_display}</strong><br>
            Thời gian ước tính: <strong>${data.total_duration_display}</strong><br>
            <em>(Tính toán qua OSRM Foot Engine Quận 4)</em>
          </div>
        `);
      }
    }
  } catch (e) {
    console.warn("Could not load dynamic tour route line:", e);
  }
}

// ==========================================================================
// POI FETCHING, SEARCH & RENDERING
// ==========================================================================

async function fetchPOIs() {
  try {
    const res = await fetch(`${API_BASE}/pois/nearby?latitude=${userLocation.lat}&longitude=${userLocation.lng}&max_distance_meters=5000&lang=${currentLang}&limit=50`);
    if (res.ok) {
      const data = await res.json();
      poiDataList = Array.isArray(data) ? data : (data.items || []);
      renderPOIList(poiDataList);
      renderPOIsOnMap(poiDataList);
      populateDirectionsDropdowns(poiDataList);
      populateQRModal(poiDataList);
    }
  } catch (err) {
    console.error("Failed to fetch POIs:", err);
  }
}

function renderPOIsOnMap(pois) {
  poiLayers.forEach(l => map.removeLayer(l));
  poiLayers = [];

  pois.forEach(poi => {
    if (!poi || !poi.location || !poi.location.coordinates) return;
    const [lng, lat] = poi.location.coordinates;
    const poiId = poi._id || poi.id;
    const codeName = poi.code || poi.name || "POI";
    const address = poi.address || "";
    const enterRadius = poi.radius_enter_m || poi.trigger_radius || 30;
    const exitRadius = poi.radius_exit_m || (enterRadius * 1.5) || 45;
    const distStr = poi.distance_display || (poi.straight_line_distance_m ? `${Math.round(poi.straight_line_distance_m)} m` : "Gần bạn");

    const exitCircle = L.circle([lat, lng], {
      radius: exitRadius,
      color: "#ff833a",
      weight: 1,
      dashArray: "4, 6",
      fillOpacity: 0.05,
      interactive: false
    }).addTo(map);
    poiLayers.push(exitCircle);

    const enterCircle = L.circle([lat, lng], {
      radius: enterRadius,
      color: "#00b4d8",
      weight: 2,
      fillColor: "#00b4d8",
      fillOpacity: 0.15
    }).addTo(map);
    poiLayers.push(enterCircle);

    const iconEmoji = poi.category === "food" ? "🍲" : (poi.category === "historical" ? "🏛️" : (poi.category === "culture" ? "⛩️" : "🌉"));
    const markerIcon = L.divIcon({
      className: "custom-poi-marker",
      html: `<div style="background:#ff6b35; color:white; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; border:2px solid white; box-shadow:0 2px 8px rgba(0,0,0,0.4); font-size:16px;">${iconEmoji}</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const marker = L.marker([lat, lng], { icon: markerIcon }).addTo(map);
    marker.bindPopup(`
      <div style="font-family: 'Outfit', sans-serif; min-width: 190px;">
        <h4 style="margin: 0; color: #ff6b35; font-size: 14px;">${codeName}</h4>
        <p style="margin: 4px 0; font-size: 11px; color: #64748b;">${address}</p>
        <div style="margin: 4px 0; font-size: 11px; color: #0284c7; font-weight: 700;">
          📏 Khoảng cách thẳng: ${distStr}
        </div>
        <div style="display: flex; gap: 4px; margin-top: 8px;">
          <button onclick="playPoiNarration('${poiId}', 'MANUAL')" style="flex: 1; background:#ff6b35; color:white; border:none; padding:5px 8px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:bold;">▶ Nghe</button>
          <button onclick="openDirectionsToPoi('${poiId}')" style="flex: 1; background:#0284c7; color:white; border:none; padding:5px 8px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:bold;">🧭 Chỉ Đường</button>
        </div>
      </div>
    `);
    poiLayers.push(marker);
  });
}

function renderPOIList(pois) {
  const container = document.getElementById("poi-list");
  if (!container) return;
  container.innerHTML = "";

  if (pois.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 2rem 1rem; color: #94a3b8; font-size: 0.85rem;">
        🔍 Không tìm thấy điểm tham quan phù hợp.<br>Vui lòng thử từ khóa hoặc danh mục khác.
      </div>
    `;
    return;
  }

  pois.forEach(poi => {
    if (!poi || !poi.location || !poi.location.coordinates) return;
    const poiId = poi._id || poi.id;
    const codeName = poi.code || poi.name || "POI";
    const address = poi.address || "";
    const enterRadius = poi.radius_enter_m || poi.trigger_radius || 30;
    const distStr = poi.distance_display || (poi.straight_line_distance_m ? `${Math.round(poi.straight_line_distance_m)} m` : null);

    const card = document.createElement("div");
    card.className = "poi-card";
    card.onclick = () => {
      const [lng, lat] = poi.location.coordinates;
      map.flyTo([lat, lng], 17, { duration: 0.8 });
      playPoiNarration(poiId, "MANUAL");
    };

    const imgUrl = (poi.images && poi.images.length > 0 ? poi.images[0] : null) || poi.image_key || "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500";
    card.innerHTML = `
      <img src="${imgUrl}" class="poi-img" alt="${codeName}" onerror="this.src='https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500'">
      <div class="poi-body">
        <div class="poi-badge-cat">${poi.category || 'Điểm tham quan'}</div>
        <div class="poi-title">${codeName}</div>
        <div class="poi-desc">${address}</div>
        ${distStr ? `<div class="poi-dist-badge">📏 Cách bạn: ${distStr}</div>` : ''}
        <div class="poi-meta" style="margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.7rem; color: #94a3b8;">🎯 Vào: ${enterRadius}m</span>
          <div style="display: flex; gap: 4px;">
            <button class="btn-book-poi" onclick="event.stopPropagation(); openDirectionsToPoi('${poiId}')">🧭 Đường đi</button>
            <button style="background:#ff6b35; color:white; border:none; padding:3px 8px; border-radius:4px; cursor:pointer; font-size:10px; font-weight: 700;" onclick="event.stopPropagation(); playPoiNarration('${poiId}', 'MANUAL')">▶ Nghe</button>
          </div>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

function updateUserLocation(lat, lng) {
  userLocation = { lat, lng };
  userMarker.setLatLng([lat, lng]);
  document.getElementById("current-coords").innerText = `${lng.toFixed(4)}, ${lat.toFixed(4)}`;
  if (followUser) {
    map.setView([lat, lng]);
  }
  checkGeofences(lat, lng);
}

window.teleportTo = function(lng, lat, name) {
  updateUserLocation(lat, lng);
  map.flyTo([lat, lng], 17, { duration: 0.6 });
};

window.recenterMap = function() {
  followUser = true;
  map.flyTo([userLocation.lat, userLocation.lng], 16, { duration: 0.6 });
};

// ==========================================================================
// REAL DIRECTIONS & ROUTE PREVIEW (OSRM Engine)
// ==========================================================================

function populateDirectionsDropdowns(pois) {
  const originSelect = document.getElementById("dir-origin-select");
  const destSelect = document.getElementById("dir-dest-select");
  if (!destSelect || !originSelect) return;

  // Clear existing POI options
  const defaultDest = '<option value="">-- Chọn điểm đến --</option>';
  destSelect.innerHTML = defaultDest;

  // Preserve first two origin options
  const origFirstTwo = `
    <option value="current_gps">📍 Vị trí hiện tại (GPS của tôi)</option>
    <option value="picked_map">📌 Bấm chọn điểm trên bản đồ</option>
  `;
  originSelect.innerHTML = origFirstTwo;

  pois.forEach(p => {
    const pId = p._id || p.id;
    const pName = p.name || p.code || pId;

    const optDest = document.createElement("option");
    optDest.value = pId;
    optDest.innerText = `${p.category === 'food' ? '🍲' : '🏛️'} ${pName}`;
    destSelect.appendChild(optDest);

    const optOrig = document.createElement("option");
    optOrig.value = `poi:${pId}`;
    optOrig.innerText = `🏛️ POI: ${pName}`;
    originSelect.appendChild(optOrig);
  });
}

window.toggleDirectionsPanel = function(forceState) {
  const panel = document.getElementById("directions-panel");
  if (!panel) return;
  if (typeof forceState === "boolean") {
    panel.style.display = forceState ? "flex" : "none";
  } else {
    panel.style.display = (panel.style.display === "none" || !panel.style.display) ? "flex" : "none";
  }
};

window.setRoutingMode = function(mode) {
  activeRoutingMode = mode;
  document.getElementById("btn-mode-walking").classList.toggle("active", mode === "walking");
  document.getElementById("btn-mode-driving").classList.toggle("active", mode === "driving");
  // Recalculate if destination already selected
  const destVal = document.getElementById("dir-dest-select").value;
  if (destVal) {
    calculateRoute();
  }
};

window.handleOriginChange = function() {
  const originVal = document.getElementById("dir-origin-select").value;
  if (originVal === "picked_map") {
    isPickingOriginOnMap = true;
    alert("👉 Vui lòng bấm vào vị trí bất kỳ trên bản đồ để chọn điểm xuất phát!");
  } else {
    isPickingOriginOnMap = false;
  }
};

window.openDirectionsToPoi = function(poiId) {
  toggleDirectionsPanel(true);
  const destSelect = document.getElementById("dir-dest-select");
  if (destSelect) {
    destSelect.value = poiId;
    calculateRoute();
  }
};

window.calculateRoute = async function() {
  const originVal = document.getElementById("dir-origin-select").value;
  const destPoiId = document.getElementById("dir-dest-select").value;

  if (!destPoiId) {
    alert("Vui lòng chọn điểm đến!");
    return;
  }

  const payload = {
    mode: activeRoutingMode,
    locale: currentLang,
    destination_poi_id: destPoiId
  };

  if (originVal === "current_gps") {
    payload.origin = {
      latitude: userLocation.lat,
      longitude: userLocation.lng
    };
  } else if (originVal === "picked_map" && pickedOriginLocation) {
    payload.origin = {
      latitude: pickedOriginLocation.lat,
      longitude: pickedOriginLocation.lng
    };
  } else if (originVal.startsWith("poi:")) {
    payload.origin_poi_id = originVal.replace("poi:", "");
  } else {
    payload.origin = {
      latitude: userLocation.lat,
      longitude: userLocation.lng
    };
  }

  const btnCalc = document.getElementById("btn-calc-route");
  if (btnCalc) btnCalc.innerText = "⏳ Đang tính...";

  try {
    const res = await fetch(`${API_BASE}/routes/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Không thể tìm tuyến đường: ${err.detail || 'Lỗi hệ thống'}`);
      return;
    }

    activeRouteResult = await res.json();
    renderRouteOnMap(activeRouteResult);
  } catch (err) {
    console.error("Route calculation error:", err);
    alert("Không thể kết nối đến hệ thống chỉ đường.");
  } finally {
    if (btnCalc) btnCalc.innerText = "⚡ Tìm Lộ Trình";
  }
};

function renderRouteOnMap(routeData) {
  if (!routeLayerGroup) return;
  routeLayerGroup.clearLayers();

  const coords = routeData.coordinates || (routeData.geometry && routeData.geometry.coordinates);
  if (!coords || coords.length === 0) return;

  // Leaflet uses [lat, lon], GeoJSON uses [lon, lat]
  const latLngs = coords.map(pt => [pt[1], pt[0]]);

  const polyline = L.polyline(latLngs, {
    color: activeRoutingMode === "walking" ? "#0284c7" : "#10b981",
    weight: 6,
    opacity: 0.9,
    lineJoin: "round"
  }).addTo(routeLayerGroup);

  // Fit bounds to entire route with padding
  map.fitBounds(polyline.getBounds(), { padding: [60, 60] });
  followUser = false;

  // Update summary card UI
  const card = document.getElementById("route-summary-card");
  if (card) card.style.display = "flex";

  document.getElementById("route-dist-text").innerText = routeData.distance_display;
  document.getElementById("route-dur-text").innerText = routeData.duration_display;

  // Straight line distance calculation for comparison
  const origPt = latLngs[0];
  const destPt = latLngs[latLngs.length - 1];
  const straightM = calculateDistanceMeters(origPt[0], origPt[1], destPt[0], destPt[1]);
  document.getElementById("route-straight-text").innerText = straightM < 1000 ? `${Math.round(straightM)} m` : `${(straightM / 1000).toFixed(1)} km`;

  // Populate turn steps
  const stepsList = document.getElementById("route-steps-list");
  const stepCountSpan = document.getElementById("route-step-count");
  if (stepsList) {
    stepsList.innerHTML = "";
    const steps = routeData.steps || [];
    if (stepCountSpan) stepCountSpan.innerText = steps.length;

    steps.forEach((s, idx) => {
      const li = document.createElement("li");
      li.className = "step-item";
      li.innerHTML = `
        <span style="color: #38bdf8; font-weight: 700;">${idx + 1}.</span>
        <div style="flex: 1;">
          <div>${s.instruction}</div>
          <div style="font-size: 0.65rem; color: #94a3b8;">${s.distance_display} (~${s.duration_display})</div>
        </div>
      `;
      stepsList.appendChild(li);
    });
  }
}

window.clearActiveRoute = function() {
  if (routeLayerGroup) routeLayerGroup.clearLayers();
  activeRouteResult = null;
  const card = document.getElementById("route-summary-card");
  if (card) card.style.display = "none";
};

window.openExternalGoogleMaps = function() {
  const destPoiId = document.getElementById("dir-dest-select").value;
  const targetPoi = poiDataList.find(p => (p._id || p.id) === destPoiId);
  if (!targetPoi || !targetPoi.location) {
    alert("Vui lòng chọn điểm đến!");
    return;
  }
  const [destLon, destLat] = targetPoi.location.coordinates;
  const travelMode = activeRoutingMode === "walking" ? "walking" : "driving";
  const url = `https://www.google.com/maps/dir/?api=1&origin=${userLocation.lat},${userLocation.lng}&destination=${destLat},${destLon}&travelmode=${travelMode}`;
  window.open(url, "_blank");
};

// ==========================================================================
// POI SEARCH & FILTERING (Debounced 300ms)
// ==========================================================================

function setupSearchAndFilters() {
  const searchInput = document.getElementById("poi-search-input");
  const clearBtn = document.getElementById("btn-clear-search");

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const val = e.target.value.trim();
      if (clearBtn) clearBtn.style.display = val ? "block" : "none";

      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        executePOISearch(val, currentCategoryFilter);
      }, 300);
    });
  }
}

window.setCategoryFilter = function(cat, btnElement) {
  currentCategoryFilter = cat;
  document.querySelectorAll(".category-filter-chips .chip-btn").forEach(b => b.classList.remove("active"));
  if (btnElement) btnElement.classList.add("active");

  const query = document.getElementById("poi-search-input")?.value.trim() || "";
  executePOISearch(query, cat);
};

window.clearSearch = function() {
  const input = document.getElementById("poi-search-input");
  const clearBtn = document.getElementById("btn-clear-search");
  if (input) input.value = "";
  if (clearBtn) clearBtn.style.display = "none";
  executePOISearch("", currentCategoryFilter);
};

async function executePOISearch(query, category) {
  try {
    let url = "";
    if (query) {
      url = `${API_BASE}/pois/search?q=${encodeURIComponent(query)}&origin_lat=${userLocation.lat}&origin_lon=${userLocation.lng}&lang=${currentLang}&limit=30`;
      if (category && category !== "all") {
        url += `&category=${encodeURIComponent(category)}`;
      }
    } else {
      url = `${API_BASE}/pois/nearby?latitude=${userLocation.lat}&longitude=${userLocation.lng}&max_distance_meters=5000&lang=${currentLang}&limit=50`;
      if (category && category !== "all") {
        url += `&category=${encodeURIComponent(category)}`;
      }
    }

    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      const list = Array.isArray(data) ? data : (data.items || []);
      renderPOIList(list);
      renderPOIsOnMap(list);
    }
  } catch (err) {
    console.error("POI search failed:", err);
  }
}

function updateUserLocation(lat, lng) {
  userLocation = { lat, lng };
  userMarker.setLatLng([lat, lng]);
  document.getElementById("current-coords").innerText = `${lng.toFixed(4)}, ${lat.toFixed(4)}`;
  checkGeofences(lat, lng);
}

window.teleportTo = function(lng, lat, name) {
  updateUserLocation(lat, lng);
  map.setView([lat, lng], 17);
};

function calculateDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371e3;
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaPhi = ((lat2 - lat1) * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

  const a = Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
            Math.cos(phi1) * Math.cos(phi2) *
            Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function checkGeofences(lat, lng) {
  const now = Date.now();
  for (const poi of poiDataList) {
    if (!poi.location || !poi.location.coordinates) continue;
    const [poiLng, poiLat] = poi.location.coordinates;
    const enterRadius = poi.radius_enter_m || poi.trigger_radius || 30;
    const dist = calculateDistanceMeters(lat, lng, poiLat, poiLng);

    if (dist <= enterRadius) {
      const cooldownSec = poi.cooldown_seconds || 60;
      const lastTrigger = poiCooldowns[poi._id] || 0;
      if (now - lastTrigger > cooldownSec * 1000) {
        poiCooldowns[poi._id] = now;
        lastTriggeredPoiId = poi._id;
        playPoiNarration(poi._id, "GPS");
        break;
      }
    }
  }
}

// ==========================================================================
// NARRATION & PLAYBACK GRANTS (SECTION 5 & 8)
// ==========================================================================

window.playPoiNarration = async function(poiId, triggerType = "MANUAL", consentTrial = false) {
  const poi = poiDataList.find(p => (p._id || p.id) === poiId);
  if (!poi) return;

  const poiTitle = poi.code || poi.name || "Điểm tham quan";

  // Request Playback Grant from Backend
  try {
    const res = await fetch(`${API_BASE}/playback-grants`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        tour_id: activeTourId,
        poi_id: poiId,
        lang: currentLang,
        trigger_source: triggerType.toLowerCase(),
        consent_trial: consentTrial,
        idempotency_key: `playback-${poiId}-${Date.now()}`
      })
    });

    const grantData = await res.json();

    if (!res.ok) {
      const errCode = grantData.detail?.error || grantData.detail;

      // BR-TRIAL-03: GPS must not burn trial silently; ask user
      if (errCode === "TRIAL_CONSENT_REQUIRED") {
        if (triggerType === "GPS") {
          showGpsTrialConsentBanner(poi, poiTitle);
        } else {
          openTrialConsentModal(poiId, poiTitle);
        }
        return;
      }

      // Trial exhausted or tour purchase required -> Open Paywall
      if (errCode === "TRIAL_EXHAUSTED" || errCode === "TOUR_PURCHASE_REQUIRED") {
        openPaywallModal(activeTourId, poiTitle);
        return;
      }

      alert("Từ chối truy cập: " + (grantData.detail?.message || "Không thể phát âm thanh."));
      return;
    }

    // Grant successful! Play streaming audio
    currentPlaybackId = grantData.playback_id || (`pb_${Date.now()}`);
    currentActivePoiId = poiId;

    const streamUrl = grantData.stream_url.startsWith("http")
      ? grantData.stream_url
      : (grantData.stream_url.startsWith("/") ? grantData.stream_url : `/${grantData.stream_url}`);
    audioElement.src = streamUrl;
    audioElement.play().then(() => {
      btnPlayPause.innerText = "⏸";
    }).catch(e => console.warn("Autoplay notice:", e));

    playerBar.style.display = "flex";
    playerTitle.innerText = poiTitle;
    playerDesc.innerText = `Thuyết minh [${currentLang.toUpperCase()}] • ${grantData.scope === 'entitled' ? 'Đã sở hữu' : 'Nghe thử miễn phí'}`;
    triggerTypeLabel.innerText = triggerType;

    if (grantData.trial_consumed) {
      trialRemaining = 0;
      updateIdentityUI();
    }

  } catch (err) {
    console.error("Playback request failed:", err);
    alert("Lỗi kết nối máy chủ khi cấp quyền âm thanh.");
  }
};

function showGpsTrialConsentBanner(poi, poiTitle) {
  if (confirm(`📍 GPS: Bạn đã bước vào vùng "${poiTitle}". Bạn có muốn kích hoạt lượt nghe thử miễn phí không?`)) {
    playPoiNarration(poi._id, "MANUAL", true);
  }
}

function openTrialConsentModal(poiId, poiTitle) {
  pendingTrialPoiId = poiId;
  document.getElementById("trial-target-poi-title").innerText = poiTitle;
  openModal("trial-consent-modal");
}

window.confirmConsumeTrial = function() {
  closeModal("trial-consent-modal");
  if (pendingTrialPoiId) {
    playPoiNarration(pendingTrialPoiId, "MANUAL", true);
    pendingTrialPoiId = null;
  }
};

function openPaywallModal(tourId, poiTitle) {
  document.getElementById("paywall-tour-title").innerText = "Tour Di Sản Bến Cảng Quận 4";
  document.getElementById("paywall-price-display").innerText = "99.000 ₫";
  openModal("paywall-modal");
}

window.proceedFromPaywallToCheckout = function() {
  closeModal("paywall-modal");

  // Rule BR-PAY-01: Must be logged in to purchase tour
  if (!currentUser) {
    alert("Vui lòng đăng nhập hoặc đăng ký tài khoản du khách để thanh toán và lưu trữ quyền sở hữu tour.");
    pendingCheckoutTourId = activeTourId;
    openAuthModal("login");
  } else {
    openBookingModal(activeTourId);
  }
};

// ==========================================================================
// CHECKOUT & PAYMENT FLOW (SECTION 6 & 7)
// ==========================================================================

window.openTourBookingModal = function() {
  if (!currentUser) {
    alert("Vui lòng đăng nhập tài khoản để mua tour.");
    pendingCheckoutTourId = activeTourId;
    openAuthModal("login");
    return;
  }
  openBookingModal(activeTourId);
};

window.openBookingModal = function(tourId) {
  activeOrderId = null;
  selectedPaymentMethod = "vietqr";

  document.getElementById("pay-item-title").innerText = "Hành Trình Di Sản Bến Cảng Quận 4";
  document.getElementById("pay-total-display").innerText = "99.000 ₫";

  selectPaymentMethod("vietqr");

  document.getElementById("pay-step-form").style.display = "block";
  document.getElementById("pay-step-qr").style.display = "none";
  document.getElementById("pay-step-success").style.display = "none";

  openModal("payment-modal");
};

window.selectPaymentMethod = function(method) {
  selectedPaymentMethod = method;
  const btnQr = document.getElementById("method-btn-vietqr");
  const btnVisa = document.getElementById("method-btn-visa");

  if (method === "vietqr") {
    btnQr.style.border = "2px solid #ff6b35";
    btnVisa.style.border = "1px solid #475569";
  } else {
    btnVisa.style.border = "2px solid #ff6b35";
    btnQr.style.border = "1px solid #475569";
  }
};

window.submitCreatePaymentOrder = async function() {
  const btn = document.getElementById("btn-submit-checkout");
  btn.disabled = true;
  btn.innerText = "Đang khởi tạo đơn hàng...";

  try {
    // 1. Create order
    const orderRes = await fetch(`${API_BASE}/orders`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        tour_id: activeTourId,
        idempotency_key: `order-${activeTourId}-${Date.now()}`
      })
    });
    const orderData = await orderRes.json();
    if (!orderRes.ok) {
      throw new Error(orderData.detail || "Không thể tạo đơn hàng.");
    }

    activeOrderId = orderData.order_id;

    // 2. Create payment attempt
    const attemptRes = await fetch(`${API_BASE}/orders/${activeOrderId}/payment-attempts`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        payment_method: selectedPaymentMethod,
        return_url: window.location.href
      })
    });
    const attemptData = await attemptRes.json();
    if (!attemptRes.ok) {
      throw new Error(attemptData.detail || "Không thể khởi tạo phiên thanh toán.");
    }

    if (selectedPaymentMethod === "visa") {
      // VNPAY Hosted redirect
      if (attemptData.checkout_url) {
        window.open(attemptData.checkout_url, "_blank");
      }
    }

    // Display QR Code step
    document.getElementById("vietqr-image").src = attemptData.qr_code_data || attemptData.checkout_url;
    document.getElementById("pay-qr-amount").innerText = Number(attemptData.amount_vnd).toLocaleString("vi-VN") + " ₫";
    document.getElementById("pay-qr-content").innerText = attemptData.provider_reference;

    if (attemptData.bank_account_info) {
      document.getElementById("qr-bank-name").innerText = attemptData.bank_account_info.bank_name || "MB Bank";
      document.getElementById("qr-acc-no").innerText = attemptData.bank_account_info.account_number || "0909123456";
    }

    const mockBadge = document.getElementById("mock-warning-badge");
    if (attemptData.mock_mode) {
      mockBadge.style.display = "block";
    } else {
      mockBadge.style.display = "none";
    }

    document.getElementById("pay-step-form").style.display = "none";
    document.getElementById("pay-step-qr").style.display = "block";

    // Auto-poll reconciliation every 3 seconds
    if (reconcileInterval) clearInterval(reconcileInterval);
    reconcileInterval = setInterval(async () => {
      await pollReconcileQuietly();
    }, 3000);

  } catch (err) {
    alert("Lỗi thanh toán: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = "🚀 Tiến Hành Thanh Toán";
  }
};

async function pollReconcileQuietly() {
  if (!activeOrderId) return;
  try {
    const res = await fetch(`${API_BASE}/orders/${activeOrderId}/reconcile`, {
      method: "POST",
      headers: getAuthHeaders()
    });
    if (res.ok) {
      const data = await res.json();
      if (data.is_paid) {
        clearInterval(reconcileInterval);
        reconcileInterval = null;
        showPaymentSuccess(data);
      }
    }
  } catch (e) {}
}

window.reconcileActiveOrder = async function() {
  if (!activeOrderId) return;
  try {
    const res = await fetch(`${API_BASE}/orders/${activeOrderId}/reconcile`, {
      method: "POST",
      headers: getAuthHeaders()
    });
    const data = await res.json();
    if (data.is_paid) {
      if (reconcileInterval) clearInterval(reconcileInterval);
      showPaymentSuccess(data);
    } else {
      alert(data.message || "Giao dịch chưa hoàn tất. Vui lòng kiểm tra lại sau khi đã chuyển khoản.");
    }
  } catch (err) {
    alert("Lỗi khi kiểm tra đối soát.");
  }
};

function showPaymentSuccess(data) {
  document.getElementById("ticket-code-display").innerText = activeOrderId;
  document.getElementById("ticket-qr-img").src = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(activeOrderId)}`;

  document.getElementById("pay-step-qr").style.display = "none";
  document.getElementById("pay-step-success").style.display = "block";

  if (!userEntitledTours.includes(activeTourId)) {
    userEntitledTours.push(activeTourId);
  }
  updateIdentityUI();
}

window.finishCheckoutAndExplore = function() {
  closeModal("payment-modal");
  alert("🎉 Chúc mừng! Bạn đã sở hữu trọn bộ tour. Hãy thoải mái bấm nghe bất kỳ điểm đến nào trên bản đồ!");
};

window.copyTransferInfo = function() {
  const content = document.getElementById("pay-qr-content").innerText;
  const amount = document.getElementById("pay-qr-amount").innerText;
  navigator.clipboard.writeText(`CK ${content} ${amount}`).then(() => {
    alert("Đã sao chép nội dung chuyển khoản vào bộ nhớ tạm!");
  });
};

window.cancelPaymentStep = function() {
  if (reconcileInterval) clearInterval(reconcileInterval);
  document.getElementById("pay-step-qr").style.display = "none";
  document.getElementById("pay-step-form").style.display = "block";
};

// ==========================================================================
// MY TOURS & MY ORDERS (P04 & P05)
// ==========================================================================

window.openMyToursModal = async function() {
  if (!currentUser) {
    alert("Vui lòng đăng nhập tài khoản để xem các tour đã mua.");
    openAuthModal("login");
    return;
  }

  openModal("my-tours-modal");
  const listEl = document.getElementById("my-tours-list");
  listEl.innerHTML = '<div style="color:#94a3b8; text-align:center; padding:1.5rem;">Đang tải danh sách tour đã mua...</div>';

  try {
    const res = await fetch(`${API_BASE}/me/tours`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("Lỗi tải danh sách tour.");
    const tours = await res.json();

    if (!tours || tours.length === 0) {
      listEl.innerHTML = `
        <div style="text-align:center; padding:2rem; color:#94a3b8;">
          <div style="font-size:2rem; margin-bottom:0.5rem;">🎟️</div>
          <p>Bạn chưa mua tour nào.</p>
          <button class="btn-primary" style="margin-top:1rem;" onclick="closeModal('my-tours-modal'); openBookingModal(activeTourId);">Mua Tour Đầu Tiên</button>
        </div>
      `;
      return;
    }

    listEl.innerHTML = tours.map(t => `
      <div style="background:#0f172a; border-radius:8px; padding:12px; border-left:4px solid #10b981; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <strong style="color:white; font-size:0.95rem;">${t.tour_title}</strong>
          <div style="font-size:0.75rem; color:#10b981; margin-top:2px;">✨ Đã sở hữu trọn đời • ${t.poi_ids.length} Điểm đến</div>
        </div>
        <div style="display:flex; gap:6px;">
          <button class="btn-sim" style="background:#ff6b35; color:white; font-size:0.75rem; padding:6px 10px;" onclick="closeModal('my-tours-modal');">▶ Nghe</button>
          <button class="btn-sim" style="background:#334155; color:white; font-size:0.75rem; padding:6px 10px;" onclick="downloadOfflinePackForTour('${t.tour_id}')">💾 Tải</button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    listEl.innerHTML = `<div style="color:#ef4444; text-align:center;">${err.message}</div>`;
  }
};

window.openMyOrdersModal = async function() {
  if (!currentUser) {
    alert("Vui lòng đăng nhập để xem lịch sử đơn hàng.");
    openAuthModal("login");
    return;
  }

  openModal("my-orders-modal");
  const listEl = document.getElementById("my-orders-list");
  listEl.innerHTML = '<div style="color:#94a3b8; text-align:center; padding:1.5rem;">Đang tải danh sách đơn hàng...</div>';

  try {
    const res = await fetch(`${API_BASE}/me/orders`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("Lỗi tải danh sách đơn hàng.");
    const orders = await res.json();

    if (!orders || orders.length === 0) {
      listEl.innerHTML = '<div style="text-align:center; padding:2rem; color:#94a3b8;">Bạn chưa có đơn hàng nào.</div>';
      return;
    }

    listEl.innerHTML = orders.map(o => {
      const isPaid = o.status === "paid";
      const statusColor = isPaid ? "#10b981" : "#f59e0b";
      const statusText = isPaid ? "ĐÃ THANH TOÁN" : "CHỜ THANH TOÁN";
      return `
        <div style="background:#0f172a; padding:10px 14px; border-radius:8px; border-left: 3px solid ${statusColor};">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:white; font-size:0.9rem;">${o.tour_title || 'Tour Di Sản Quận 4'}</strong>
            <span style="font-size:0.7rem; font-weight:800; color:${statusColor};">${statusText}</span>
          </div>
          <div style="font-size:0.75rem; color:#94a3b8; margin-top:2px;">
            Số tiền: <strong style="color:#10b981;">${Number(o.amount_vnd).toLocaleString("vi-VN")} ₫</strong>
          </div>
          <div style="font-size:0.7rem; color:#64748b; margin-top:4px;">
            Mã đơn: ${o.order_id} | ${new Date(o.created_at).toLocaleString("vi-VN")}
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    listEl.innerHTML = `<div style="color:#ef4444; text-align:center;">${err.message}</div>`;
  }
};

window.downloadOfflinePack = async function() {
  await downloadOfflinePackForTour(activeTourId);
};

window.downloadOfflinePackForTour = async function(tourId) {
  if (!currentUser) {
    alert("Vui lòng đăng nhập tài khoản sở hữu tour để tải gói ngoại tuyến.");
    openAuthModal("login");
    return;
  }

  const btn = document.getElementById("btn-download-pack");
  if (btn) btn.innerText = "Đang tải gói ngoại tuyến...";

  try {
    const res = await fetch(`${API_BASE}/packages/tours/${tourId}/offline-pack?language_code=${currentLang}`, {
      method: "POST",
      headers: getAuthHeaders()
    });
    const pack = await res.json();
    if (!res.ok) {
      throw new Error(pack.detail || "Không thể tải gói ngoại tuyến.");
    }

    localStorage.setItem(`offline_pack_${tourId}`, JSON.stringify(pack));
    alert(`🎉 Tải gói ngoại tuyến thành công!\nGiấy phép ngoại tuyến có hiệu lực ${pack.offline_license?.valid_days || 7} ngày.`);
    closeModal("offline-modal");
  } catch (err) {
    alert("Lỗi tải gói ngoại tuyến: " + err.message);
  } finally {
    if (btn) btn.innerText = "💾 Tải và Lưu Vào Bộ Nhớ Trình Duyệt";
  }
};

// ==========================================================================
// MODAL CONTROLS & HELPERS
// ==========================================================================

function populateQRModal(pois) {
  const container = document.getElementById("qr-options");
  if (!container) return;
  container.innerHTML = "";

  pois.forEach(poi => {
    const btn = document.createElement("button");
    btn.className = "btn-sim";
    btn.innerText = `Quét QR: ${poi.name || poi.code}`;
    btn.onclick = () => {
      closeModal("qr-modal");
      playPoiNarration(poi._id, "QR");
    };
    container.appendChild(btn);
  });
}

function setupEventListeners() {
  btnPlayPause.addEventListener("click", () => {
    if (audioElement.paused) {
      audioElement.play();
      btnPlayPause.innerText = "⏸";
    } else {
      audioElement.pause();
      btnPlayPause.innerText = "▶";
    }
  });

  // BR-LISTEN-01: Enqueue narration_started when player genuinely starts playing
  audioElement.addEventListener("playing", () => {
    btnPlayPause.innerText = "⏸";
    if (window.analyticsOutbox && currentPlaybackId) {
      window.analyticsOutbox.enqueue({
        event_type: "narration_started",
        playback_id: currentPlaybackId,
        poi_id: currentActivePoiId,
        tour_id: activeTourId,
        source: (triggerTypeLabel ? triggerTypeLabel.innerText.toLowerCase() : "manual"),
        properties: { lang: currentLang }
      });
    }
  });

  // BR-LISTEN-01: Enqueue narration_completed when audio reaches end
  audioElement.addEventListener("ended", () => {
    btnPlayPause.innerText = "▶";
    if (window.analyticsOutbox && currentPlaybackId) {
      window.analyticsOutbox.enqueue({
        event_type: "narration_completed",
        playback_id: currentPlaybackId,
        poi_id: currentActivePoiId,
        tour_id: activeTourId,
        source: (triggerTypeLabel ? triggerTypeLabel.innerText.toLowerCase() : "manual"),
        properties: { lang: currentLang }
      });
    }
  });

  audioElement.addEventListener("timeupdate", () => {
    if (!audioElement.duration) return;
    const progress = (audioElement.currentTime / audioElement.duration) * 100;
    progressFill.style.width = `${progress}%`;
    currentTimeLabel.innerText = formatTime(audioElement.currentTime);
    totalTimeLabel.innerText = formatTime(audioElement.duration);
  });

  document.getElementById("btn-open-qr").onclick = () => openModal("qr-modal");
  document.getElementById("btn-open-offline").onclick = () => openModal("offline-modal");

  document.getElementById("select-language").addEventListener("change", (e) => {
    currentLang = e.target.value;
    fetchPOIs();
  });
}

function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("active");
}

window.closeModal = function(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("active");
};

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}
