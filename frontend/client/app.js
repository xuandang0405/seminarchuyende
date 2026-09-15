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

function initMap() {
  // Center on District 4, Ho Chi Minh City
  map = L.map("map").setView([userLocation.lat, userLocation.lng], 15);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors"
  }).addTo(map);

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
    const res = await fetch(`${API_BASE}/pois`);
    if (res.ok) {
      poiDataList = await res.json();
      renderPOIList(poiDataList);
      renderPOIsOnMap(poiDataList);
      populateQRModal(poiDataList);
    }
  } catch (err) {
    console.error("Failed to fetch POIs:", err);
  }
}

function renderPOIsOnMap(pois) {
  // Clear existing
  poiLayers.forEach(l => map.removeLayer(l));
  poiLayers = [];

  pois.forEach(poi => {
    const [lng, lat] = poi.location.coordinates;

    // Geofence exit radius circle (outer dashed circle)
    const exitCircle = L.circle([lat, lng], {
      radius: poi.radius_exit_m,
      color: "#ff833a",
      weight: 1,
      dashArray: "4, 6",
      fillOpacity: 0.05,
      interactive: false
    }).addTo(map);
    poiLayers.push(exitCircle);

    // Geofence enter radius circle (inner solid trigger zone)
    const enterCircle = L.circle([lat, lng], {
      radius: poi.radius_enter_m,
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
        <h4 style="margin: 0; color: #ff6b35;">${poi.code}</h4>
        <p style="margin: 4px 0; font-size: 12px;">${poi.address}</p>
        <p style="margin: 4px 0; font-size: 11px; color: #00b4d8;">Vùng kích hoạt: ${poi.radius_enter_m}m</p>
        <button onclick="playPoiNarration('${poi._id}', 'MANUAL')" style="background:#ff6b35; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:bold;">▶ Nghe Thuyết Minh</button>
      </div>
    `);
    poiLayers.push(marker);
  });
}

function renderPOIList(pois) {
  const container = document.getElementById("poi-list");
  container.innerHTML = "";

  pois.forEach(poi => {
    const card = document.createElement("div");
    card.className = "poi-card";
    card.onclick = () => {
      const [lng, lat] = poi.location.coordinates;
      map.setView([lat, lng], 17);
      playPoiNarration(poi._id, "MANUAL");
    };

    const imgUrl = poi.image_key || "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500";
    card.innerHTML = `
      <img src="${imgUrl}" class="poi-img" alt="${poi.code}" onerror="this.src='https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500'">
      <div class="poi-body">
        <div class="poi-badge-cat">${poi.category}</div>
        <div class="poi-title">${poi.code}</div>
        <div class="poi-desc">${poi.address}</div>
        <div class="poi-meta">
          <span>🎯 Bán kính vào: ${poi.radius_enter_m}m</span>
          <span>⏱️ Cooldown: ${poi.cooldown_seconds}s</span>
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
  const now = Date.now();

  poiDataList.forEach(poi => {
    const [poiLng, poiLat] = poi.location.coordinates;
    const distanceMeters = calculateDistanceMeters(userLat, userLng, poiLat, poiLng);

    // Enter radius condition
    if (distanceMeters <= poi.radius_enter_m) {
      const lastTriggered = poiCooldowns[poi._id] || 0;
      const cooldownMs = (poi.cooldown_seconds || 60) * 1000;

      if (now - lastTriggered > cooldownMs && lastTriggeredPoiId !== poi._id) {
        console.log(`[GEOFENCE ENTER] Inside ${poi.code} (dist: ${distanceMeters.toFixed(1)}m <= ${poi.radius_enter_m}m)`);
        poiCooldowns[poi._id] = now;
        lastTriggeredPoiId = poi._id;
        
        // Auto trigger narration!
        playPoiNarration(poi._id, "GPS AUTO");
      }
    } else if (distanceMeters > poi.radius_exit_m) {
      // User exited the hysteresis exit radius
      if (lastTriggeredPoiId === poi._id) {
        console.log(`[GEOFENCE EXIT] Left ${poi.code} (dist: ${distanceMeters.toFixed(1)}m > ${poi.radius_exit_m}m)`);
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
  const poi = poiDataList.find(p => p._id === poiId);
  if (!poi) return;

  try {
    // 1. Fetch active localized content
    const contentRes = await fetch(`${API_BASE}/pois/${poiId}/contents/${currentLang}/active`);
    let content = null;
    if (contentRes.ok) {
      content = await contentRes.json();
    }

    const titleText = content?.title || poi.code;
    const descText = content?.narration_text || content?.description || poi.address;

    playerTitle.innerText = titleText;
    playerDesc.innerText = descText;
    triggerTypeLabel.innerText = triggerType;
    playerBar.style.display = "flex";

    // 2. Play audio stream if audio asset exists, or use Web Speech Synthesis fallback
    let audioPlayed = false;
    if (poi.published_contents && poi.published_contents[currentLang]) {
      const audioAssetId = poi.published_contents[currentLang].audio_asset_id;
      try {
        const audioInfoRes = await fetch(`${API_BASE}/audio/info/${audioAssetId}`);
        if (audioInfoRes.ok) {
          const audioInfo = await audioInfoRes.json();
          audioElement.src = `${API_BASE}/audio/${audioInfo.storage_key}/stream`;
          audioElement.play();
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
  const container = document.getElementById("qr-options");
  container.innerHTML = "";

  pois.forEach(poi => {
    const btn = document.createElement("button");
    btn.className = "btn-sim";
    btn.style.padding = "10px";
    btn.innerHTML = `<strong>📷 Quét QR: ${poi.code}</strong><span>${poi.address}</span>`;
    btn.onclick = () => {
      closeModal("qr-modal");
      playPoiNarration(poi._id, "QR CODE");
    };
    container.appendChild(btn);
  });
}

async function loadOfflineManifest() {
  const detailsDiv = document.getElementById("offline-details");
  try {
    const toursRes = await fetch(`${API_BASE}/tours`);
    const tours = await toursRes.json();
    if (tours.length > 0) {
      const tour = tours[0];
      const pkgRes = await fetch(`${API_BASE}/packages/tours/${tour._id}?language_code=${currentLang}`);
      const pkg = await pkgRes.json();
      const manifest = pkg.manifest;

      detailsDiv.innerHTML = `
        <div><strong>Tour:</strong> ${manifest.tour_code}</div>
        <div><strong>Ngôn ngữ:</strong> ${manifest.language_code.toUpperCase()}</div>
        <div><strong>Số điểm dừng (Stops):</strong> ${manifest.stops_count} điểm</div>
        <div><strong>Tổng file âm thanh:</strong> ${manifest.total_files} file</div>
        <div><strong>Dung lượng tải:</strong> ${(manifest.total_bytes / 1024).toFixed(1)} KB</div>
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
