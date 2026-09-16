const API_BASE = "http://localhost:8000/api/v1";

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

// Audio
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

let clientTourRouteLine = null;
let userGuidanceLine = null;

function initMap() {
  // Center on District 4, Ho Chi Minh City
  map = L.map("map", {
    center: [userLocation.lat, userLocation.lng],
    zoom: 15
  });

  // Base Layers (Voyager as default for 100% guaranteed streets and roads in VN)
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

  const googleSatellite = L.tileLayer("https://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}", {
    maxZoom: 20,
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    attribution: "© Google Satellite"
  });

  const osmLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap"
  });

  cartoVoyager.addTo(map);

  // Layer control switcher
  const baseMaps = {
    "🗺️ Đường Phố Chi Tiết (Voyager)": cartoVoyager,
    "📍 Đường Phố Google (Google Maps)": googleStreets,
    "🛰️ Ảnh Vệ Tinh (Google Satellite)": googleSatellite,
    "🧭 OpenStreetMap": osmLayer
  };
  L.control.layers(baseMaps, null, { position: "topright" }).addTo(map);

  // Walking Tour Route (Tuyến đường tham quan & ẩm thực Quận 4)
  const tourWalkingRoute = [
    [10.76814, 106.70678], // Bến Nhà Rồng
    [10.76740, 106.70610], // Ngã 3 Nguyễn Tất Thành - Bến Vân Đồn
    [10.76850, 106.70550], // Dọc Bến Vân Đồn
    [10.76895, 106.70488], // Cầu Mống
    [10.76720, 106.70320], // Cầu Calmette - Bến Vân Đồn
    [10.76450, 106.70380], // Rẽ vào Đoàn Văn Bơ
    [10.76135, 106.70425], // Chợ Xóm Chiếu
    [10.76020, 106.70180], // Ngã 4 Hoàng Diệu & Vĩnh Khánh
    [10.75882, 106.70012], // Phố Ốc Vĩnh Khánh
    [10.75680, 106.69850]  // Vĩnh Khánh hướng Tôn Đản
  ];

  clientTourRouteLine = L.polyline(tourWalkingRoute, {
    color: "#ff6b35",
    weight: 5,
    opacity: 0.85,
    dashArray: "6, 8"
  }).addTo(map);

  clientTourRouteLine.bindPopup("<strong>🚶 Lộ Trình Tham Quan Đi Bộ Tour Q4</strong><br>Dài ~2.8 km (Bến Nhà Rồng ➔ Cầu Mống ➔ Chợ Xóm Chiếu ➔ Phố Ốc Vĩnh Khánh)");

  // User simulated GPS marker with pulse styling
  const userIcon = L.divIcon({
    className: "user-marker-container",
    html: '<div class="user-marker"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });

  userMarker = L.marker([userLocation.lat, userLocation.lng], { icon: userIcon }).addTo(map);

  // Allow clicking anywhere on map to move simulated GPS location
  map.on("click", (e) => {
    updateUserLocation(e.latlng.lat, e.latlng.lng);
  });

  // Re-check size after DOM renders
  window.addEventListener("resize", () => {
    if (map) map.invalidateSize();
  });
  setTimeout(() => {
    if (map) map.invalidateSize(true);
  }, 200);
}

async function initSession() {
  try {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initial_language_code: currentLang })
    });
    if (res.ok) {
      const data = await res.json();
      activeSessionId = data._id;
      console.log("Visit Session initialized:", activeSessionId);
    }
  } catch (err) {
    console.warn("Backend not available, running in local fallback mode.");
    activeSessionId = "local-session-" + Date.now();
  }
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
  const list = Array.isArray(pois) ? pois : (pois && pois.items ? pois.items : []);
  // Clear existing
  poiLayers.forEach(l => map.removeLayer(l));
  poiLayers = [];

  list.forEach(poi => {
    if (!poi || !poi.location || !poi.location.coordinates) return;
    const [lng, lat] = poi.location.coordinates;
    const poiId = poi._id || poi.id;
    const codeName = poi.code || poi.name || poi.title || "POI";
    const address = poi.address || "";
    const enterRadius = poi.radius_enter_m || poi.trigger_radius || 30;
    const exitRadius = poi.radius_exit_m || (enterRadius * 1.5) || 45;

    // Geofence exit radius circle (outer dashed circle)
    const exitCircle = L.circle([lat, lng], {
      radius: exitRadius,
      color: "#ff833a",
      weight: 1,
      dashArray: "4, 6",
      fillOpacity: 0.05,
      interactive: false
    }).addTo(map);
    poiLayers.push(exitCircle);

    // Geofence enter radius circle (inner solid trigger zone)
    const enterCircle = L.circle([lat, lng], {
      radius: enterRadius,
      color: "#00b4d8",
      weight: 2,
      fillColor: "#00b4d8",
      fillOpacity: 0.15
    }).addTo(map);
    poiLayers.push(enterCircle);

    // POI Pin Marker
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
        <p style="margin: 4px 0; font-size: 11px; color: #00b4d8;">Vùng kích hoạt: ${enterRadius}m</p>
        <button onclick="playPoiNarration('${poiId}', 'MANUAL')" style="background:#ff6b35; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:bold;">▶ Nghe Thuyết Minh</button>
      </div>
    `);
    poiLayers.push(marker);
  });
}

function renderPOIList(pois) {
  const list = Array.isArray(pois) ? pois : (pois && pois.items ? pois.items : []);
  const container = document.getElementById("poi-list");
  if (!container) return;
  container.innerHTML = "";

  list.forEach(poi => {
    if (!poi || !poi.location || !poi.location.coordinates) return;
    const poiId = poi._id || poi.id;
    const codeName = poi.code || poi.name || poi.title || "POI";
    const address = poi.address || "";
    const enterRadius = poi.radius_enter_m || poi.trigger_radius || 30;
    const cooldownSec = poi.cooldown_seconds || 60;

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
          <span>🎯 Bán kính vào: ${enterRadius}m</span>
          <span>⏱️ Cooldown: ${cooldownSec}s</span>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

// Teleport simulated user GPS location
window.teleportTo = function(lng, lat, name) {
  updateUserLocation(lat, lng);
  map.setView([lat, lng], 17);
  console.log(`Teleported GPS to ${name}: [${lat}, ${lng}]`);
};

function updateUserLocation(lat, lng) {
  userLocation = { lat, lng };
  userMarker.setLatLng([lat, lng]);
  document.getElementById("current-coords").innerText = `${lng.toFixed(5)}, ${lat.toFixed(5)}`;

  // Run client-side geofencing check!
  checkGeofences(lat, lng);
}

// Client-Side Geofencing Engine (Hysteresis & Cooldown)
function checkGeofences(userLat, userLng) {
  if (!Array.isArray(poiDataList)) return;
  const now = Date.now();

  poiDataList.forEach(poi => {
    if (!poi || !poi.location || !poi.location.coordinates) return;
    const [poiLng, poiLat] = poi.location.coordinates;
    const distanceMeters = calculateDistanceMeters(userLat, userLng, poiLat, poiLng);
    const poiId = poi._id || poi.id;
    const codeName = poi.code || poi.name || poi.title || "POI";
    const enterRadius = poi.radius_enter_m || poi.trigger_radius || 30;
    const exitRadius = poi.radius_exit_m || (enterRadius * 1.5) || 45;

    // Enter radius condition
    if (distanceMeters <= enterRadius) {
      const lastTriggered = poiCooldowns[poiId] || 0;
      const cooldownMs = (poi.cooldown_seconds || 60) * 1000;

      if (now - lastTriggered > cooldownMs && lastTriggeredPoiId !== poiId) {
        console.log(`[GEOFENCE ENTER] Inside ${codeName} (dist: ${distanceMeters.toFixed(1)}m <= ${enterRadius}m)`);
        poiCooldowns[poiId] = now;
        lastTriggeredPoiId = poiId;
        
        // Auto trigger narration!
        playPoiNarration(poiId, "GPS AUTO");
      }
    } else if (distanceMeters > exitRadius) {
      // User exited the hysteresis exit radius
      if (lastTriggeredPoiId === poiId) {
        console.log(`[GEOFENCE EXIT] Left ${codeName} (dist: ${distanceMeters.toFixed(1)}m > ${exitRadius}m)`);
        lastTriggeredPoiId = null;
      }
    }
  });
}

// Haversine formula
function calculateDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // Earth radius in meters
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

// Play Narration
window.playPoiNarration = async function(poiId, triggerType = "MANUAL") {
  const poi = poiDataList.find(p => (p._id === poiId || p.id === poiId));
  if (!poi) return;

  try {
    // 1. Fetch active localized content
    const contentRes = await fetch(`${API_BASE}/pois/${poiId}/contents/${currentLang}/active`);
    let content = null;
    if (contentRes.ok) {
      content = await contentRes.json();
    }

    const titleText = content?.title || poi.title || poi.name || poi.code || "Điểm tham quan";
    const descText = content?.narration_text || content?.description || poi.description || poi.address || "";

    playerTitle.innerText = titleText;
    playerDesc.innerText = descText;
    triggerTypeLabel.innerText = triggerType;
    playerBar.style.display = "flex";

    // Draw visual guidance navigation line from user to this POI
    const [poiLng, poiLat] = poi.location.coordinates;
    if (userGuidanceLine) {
      map.removeLayer(userGuidanceLine);
    }
    const dist = calculateDistanceMeters(userLocation.lat, userLocation.lng, poiLat, poiLng).toFixed(0);
    userGuidanceLine = L.polyline([[userLocation.lat, userLocation.lng], [poiLat, poiLng]], {
      color: "#00b4d8",
      weight: 3,
      dashArray: "5, 8",
      opacity: 0.9
    }).addTo(map);
    userGuidanceLine.bindTooltip(`🚶 Hướng dẫn đường đi: ${dist}m`, { permanent: false, direction: "center" });

    // 2. Play audio stream if audio asset exists, or use Web Speech Synthesis fallback
    let audioPlayed = false;
    const targetAudioUrl = content?.audio_url || poi.audio_url;
    if (targetAudioUrl) {
      audioElement.src = targetAudioUrl.startsWith("http") ? targetAudioUrl : `http://localhost:8000${targetAudioUrl}`;
      audioElement.play().then(() => {
        btnPlayPause.innerText = "⏸";
        audioPlayed = true;
      }).catch(e => {
        console.warn("Audio autoplay blocked or failed:", e);
      });
      audioPlayed = true;
    } else if (poi.published_contents && poi.published_contents[currentLang]) {
      const audioAssetId = poi.published_contents[currentLang].audio_asset_id;
      try {
        const audioInfoRes = await fetch(`${API_BASE}/audio/info/${audioAssetId}`);
        if (audioInfoRes.ok) {
          const audioInfo = await audioInfoRes.json();
          audioElement.src = `${API_BASE}/audio/${audioInfo.storage_key}/stream`;
          audioElement.play().catch(e => console.warn("Stream playback:", e));
          btnPlayPause.innerText = "⏸";
          audioPlayed = true;
        }
      } catch (e) {
        console.warn("Could not stream MP3, falling back to speech synthesis");
      }
    }

    if (!audioPlayed) {
      // Browser Web Speech Synthesis fallback
      if ('speechSynthesis' in window && descText) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(descText);
        utterance.lang = currentLang === "vi" ? "vi-VN" : (currentLang === "en" ? "en-US" : currentLang);
        window.speechSynthesis.speak(utterance);
        btnPlayPause.innerText = "⏸";
      }
    }

    // 3. Send Telemetry to backend (Sequence Diagram 11)
    if (activeSessionId) {
      try {
        const pbRes = await fetch(`${API_BASE}/analytics/playbacks`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: activeSessionId,
            audio_asset_id: poi.published_contents?.[currentLang]?.audio_asset_id || "fallback-audio",
            trigger_type: triggerType.toLowerCase().includes("gps") ? "gps" : (triggerType.toLowerCase().includes("qr") ? "qr" : "manual")
          })
        });
        if (pbRes.ok) {
          const pbData = await pbRes.json();
          currentPlaybackId = pbData._id;

          // Ingest start telemetry event
          await fetch(`${API_BASE}/analytics/playback-events`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              events: [{
                playback_id: currentPlaybackId,
                seq_no: 1,
                event_type: "start",
                listened_ms_total: 0,
                position_ms: 0,
                occurred_at: new Date().toISOString()
              }]
            })
          });
        }
      } catch (err) {
        console.warn("Telemetry ingestion failed (offline):", err);
      }
    }

  } catch (err) {
    console.error("Error playing narration:", err);
  }
};

function setupEventListeners() {
  // Play/Pause button
  btnPlayPause.addEventListener("click", () => {
    if (audioElement.paused) {
      audioElement.play();
      btnPlayPause.innerText = "⏸";
    } else {
      audioElement.pause();
      if ('speechSynthesis' in window) window.speechSynthesis.pause();
      btnPlayPause.innerText = "▶";
    }
  });

  // Audio time update
  audioElement.addEventListener("timeupdate", () => {
    if (audioElement.duration) {
      const progress = (audioElement.currentTime / audioElement.duration) * 100;
      progressFill.style.width = `${progress}%`;
      currentTimeLabel.innerText = formatTime(audioElement.currentTime);
      totalTimeLabel.innerText = formatTime(audioElement.duration);
    }
  });

  audioElement.addEventListener("ended", () => {
    btnPlayPause.innerText = "▶";
    progressFill.style.width = "0%";
  });

  // Seek bar
  seekBar.addEventListener("click", (e) => {
    const rect = seekBar.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    if (audioElement.duration) {
      audioElement.currentTime = pos * audioElement.duration;
    }
  });

  // Language switcher
  document.getElementById("select-language").addEventListener("change", async (e) => {
    currentLang = e.target.value;
    console.log("Language switched to:", currentLang);
    await fetchPOIs();
  });

  // Modals
  document.getElementById("btn-open-qr").addEventListener("click", () => {
    document.getElementById("qr-modal").classList.add("active");
  });

  document.getElementById("btn-open-offline").addEventListener("click", async () => {
    document.getElementById("offline-modal").classList.add("active");
    await loadOfflineManifest();
  });

  document.getElementById("btn-download-pack").addEventListener("click", () => {
    localStorage.setItem("tourvoice_offline_pois", JSON.stringify(poiDataList));
    alert("✅ Gói Tour Quận 4 đã được lưu thành công vào bộ nhớ trình duyệt! Bạn có thể sử dụng mượt mà cả khi offline.");
    closeModal("offline-modal");
  });
}

function populateQRModal(pois) {
  const list = Array.isArray(pois) ? pois : (pois && pois.items ? pois.items : []);
  const container = document.getElementById("qr-options");
  if (!container) return;
  container.innerHTML = "";

  list.forEach(poi => {
    if (!poi) return;
    const poiId = poi._id || poi.id;
    const codeName = poi.code || poi.name || poi.title || "POI";
    const address = poi.address || "";

    const btn = document.createElement("button");
    btn.className = "btn-sim";
    btn.style.padding = "10px";
    btn.innerHTML = `<strong>📷 Quét QR: ${codeName}</strong><span>${address}</span>`;
    btn.onclick = () => {
      closeModal("qr-modal");
      playPoiNarration(poiId, "QR CODE");
    };
    container.appendChild(btn);
  });
}

async function loadOfflineManifest() {
  const detailsDiv = document.getElementById("offline-details");
  if (!detailsDiv) return;
  try {
    const toursRes = await fetch(`${API_BASE}/tours`);
    const tourData = await toursRes.json();
    const tours = Array.isArray(tourData) ? tourData : (tourData.items || []);
    if (tours.length > 0) {
      const tour = tours[0];
      const tourId = tour._id || tour.id;
      const pkgRes = await fetch(`${API_BASE}/packages/tours/${tourId}?language_code=${currentLang}`);
      const pkg = await pkgRes.json();
      const manifest = pkg.manifest || pkg;

      detailsDiv.innerHTML = `
        <div><strong>Tour:</strong> ${manifest.tour_code || tour.name || tourId}</div>
        <div><strong>Ngôn ngữ:</strong> ${(manifest.language_code || currentLang).toUpperCase()}</div>
        <div><strong>Số điểm dừng (Stops):</strong> ${manifest.stops_count || 0} điểm</div>
        <div><strong>Tổng file âm thanh:</strong> ${manifest.total_files || 0} file</div>
        <div><strong>Dung lượng tải:</strong> ${((manifest.total_bytes || 120000) / 1024).toFixed(1)} KB</div>
        <div style="margin-top: 6px; color: #10b981;">✓ Đã sẵn sàng nén để lưu trữ offline</div>
      `;
    }
  } catch (err) {
    detailsDiv.innerText = "Chế độ offline sẵn sàng với dữ liệu POI cục bộ.";
  }
}

window.closeModal = function(id) {
  document.getElementById(id).classList.remove("active");
};

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}
