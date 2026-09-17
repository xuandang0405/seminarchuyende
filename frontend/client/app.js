const API_BASE = "/api/v1";

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
  initMap();
  await initSession();
  await fetchPOIs();
  setupEventListeners();
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
// MAP & POI RENDERING
// ==========================================================================

function initMap() {
  map = L.map("map", {
    center: [userLocation.lat, userLocation.lng],
    zoom: 15
  });

  const cartoVoyager = L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    maxZoom: 20,
    subdomains: "abcd",
    attribution: "© CartoDB Voyager | OpenStreetMap"
  });

  const googleStreets = L.tileLayer("https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", {
    maxZoom: 20,
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    attribution: "© Google Maps"
  });

  cartoVoyager.addTo(map);

  const baseMaps = {
    "🗺️ Đường Phố Chi Tiết (Voyager)": cartoVoyager,
    "📍 Đường Phố Google (Google Maps)": googleStreets,
  };
  L.control.layers(baseMaps, null, { position: "topright" }).addTo(map);

  // Walking Tour Route Line
  const tourWalkingRoute = [
    [10.76814, 106.70678], // Bến Nhà Rồng
    [10.76740, 106.70610],
    [10.76850, 106.70550],
    [10.76895, 106.70488], // Cầu Mống
    [10.76720, 106.70320],
    [10.76450, 106.70380],
    [10.76135, 106.70425], // Chợ Xóm Chiếu
    [10.76020, 106.70180],
    [10.75882, 106.70012], // Phố Ốc Vĩnh Khánh
  ];

  L.polyline(tourWalkingRoute, {
    color: "#ff6b35",
    weight: 5,
    opacity: 0.85,
    dashArray: "6, 8"
  }).addTo(map).bindPopup("<strong>🚶 Lộ Trình Tour Di Sản Quận 4</strong><br>Dài ~2.8 km");

  const userIcon = L.divIcon({
    className: "user-marker-container",
    html: '<div class="user-marker"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });

  userMarker = L.marker([userLocation.lat, userLocation.lng], { icon: userIcon }).addTo(map);

  map.on("click", (e) => {
    updateUserLocation(e.latlng.lat, e.latlng.lng);
  });
}

async function fetchPOIs() {
  try {
    const res = await fetch(`${API_BASE}/pois?lang=${currentLang}`);
    if (res.ok) {
      const data = await res.json();
      poiDataList = Array.isArray(data) ? data : (data.items || []);
      renderPOIList(poiDataList);
      renderPOIsOnMap(poiDataList);
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

    const iconEmoji = poi.category === "food" ? "🍲" : (poi.category === "attraction" ? "🏛️" : "🚏");
    const markerIcon = L.divIcon({
      className: "custom-poi-marker",
      html: `<div style="background:#ff6b35; color:white; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; border:2px solid white; box-shadow:0 2px 8px rgba(0,0,0,0.4); font-size:16px;">${iconEmoji}</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const marker = L.marker([lat, lng], { icon: markerIcon }).addTo(map);
    marker.bindPopup(`
      <div style="font-family: 'Outfit', sans-serif;">
        <h4 style="margin: 0; color: #ff6b35;">${codeName}</h4>
        <p style="margin: 4px 0; font-size: 12px;">${address}</p>
        <p style="margin: 4px 0; font-size: 11px; color: #00b4d8;">Bán kính kích hoạt: ${enterRadius}m</p>
        <button onclick="playPoiNarration('${poiId}', 'MANUAL')" style="background:#ff6b35; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:bold;">▶ Nghe Thuyết Minh</button>
      </div>
    `);
    poiLayers.push(marker);
  });
}

function renderPOIList(pois) {
  const container = document.getElementById("poi-list");
  if (!container) return;
  container.innerHTML = "";

  pois.forEach(poi => {
    if (!poi || !poi.location || !poi.location.coordinates) return;
    const poiId = poi._id || poi.id;
    const codeName = poi.code || poi.name || "POI";
    const address = poi.address || "";
    const enterRadius = poi.radius_enter_m || poi.trigger_radius || 30;

    const card = document.createElement("div");
    card.className = "poi-card";
    card.onclick = () => {
      const [lng, lat] = poi.location.coordinates;
      map.setView([lat, lng], 17);
      playPoiNarration(poiId, "MANUAL");
    };

    const imgUrl = (poi.images && poi.images.length > 0 ? poi.images[0] : null) || poi.image_key || "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500";
    card.innerHTML = `
      <img src="${imgUrl}" class="poi-img" alt="${codeName}" onerror="this.src='https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500'">
      <div class="poi-body">
        <div class="poi-badge-cat">${poi.category || 'Điểm tham quan'}</div>
        <div class="poi-title">${codeName}</div>
        <div class="poi-desc">${address}</div>
        <div class="poi-meta">
          <span>🎯 Vào: ${enterRadius}m</span>
          <button style="background:#ff6b35; color:white; border:none; padding:2px 8px; border-radius:4px; cursor:pointer; font-size:10px;" onclick="event.stopPropagation(); playPoiNarration('${poiId}', 'MANUAL')">▶ Nghe</button>
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
    const streamUrl = grantData.stream_url.startsWith("http") ? grantData.stream_url : `http://localhost:8000${grantData.stream_url}`;
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
