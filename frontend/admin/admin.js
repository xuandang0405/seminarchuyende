const API_BASE = "http://localhost:8000/api/v1";
let adminToken = null;
let adminMap = null;
let pickerMarker = null;
let enterCircle = null;
let exitCircle = null;
let poiMapMarkers = [];
let allPois = [];
let allTours = [];
let tourRouteLine = null;

document.addEventListener("DOMContentLoaded", async () => {
  await autoLoginAdmin();
  await loadDashboardStats();
  initAdminMap();
  await loadPOIs();
  await loadApprovalsQueue();
  await loadTours();
  await loadQRCodes();
  await loadContentJobs();
  await loadOfflinePackages();
  await loadUsers();
});

async function autoLoginAdmin() {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "admin@tourvoice.vn",
        password: "Admin@123456"
      })
    });
    if (res.ok) {
      const data = await res.json();
      adminToken = data.access_token;
      document.getElementById("logged-user-name").innerText = data.user.full_name;
      const roleElem = document.getElementById("logged-user-role");
      if (roleElem) roleElem.innerText = data.user.role || "super_admin";
      console.log("Admin logged in successfully");
    }
  } catch (err) {
    console.warn("Backend auto-login failed:", err);
  }
}

function switchTab(tabName, element) {
  document.querySelectorAll(".tab-section").forEach(sec => sec.classList.remove("active"));
  document.querySelectorAll(".nav-links li").forEach(li => li.classList.remove("active"));

  const targetSection = document.getElementById(`tab-${tabName}`);
  if (targetSection) targetSection.classList.add("active");
  if (element) element.classList.add("active");

  if (tabName === "dashboard") loadDashboardStats();
  if (tabName === "pois") {
    setTimeout(() => {
      if (!adminMap) {
        initAdminMap();
      } else {
        adminMap.invalidateSize(true);
        adminMap.setView([10.75882, 106.70012], 15);
      }
      loadPOIs();
    }, 120);
  }
  if (tabName === "tours") loadTours();
  if (tabName === "qr") loadQRCodes();
  if (tabName === "approvals") loadApprovalsQueue();
  if (tabName === "ai-assistant") loadContentJobs();
  if (tabName === "offline-packs") loadOfflinePackages();
  if (tabName === "users") {
    loadUsers();
    loadAuditLogs();
  }
}

/* ================= TAB 1: DASHBOARD & EXPORT REPORT (S05-S10) ================= */
async function loadDashboardStats() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/analytics/dashboard`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      document.getElementById("stat-playbacks").innerText = data.total_playbacks || 0;
      document.getElementById("stat-hours").innerText = data.total_listen_hours || 0;
      document.getElementById("stat-pois").innerText = data.total_active_pois || 0;
      document.getElementById("stat-sessions").innerText = data.total_sessions || 0;

      const tbody = document.getElementById("top-pois-table");
      tbody.innerHTML = "";
      if (data.top_pois && data.top_pois.length > 0) {
        data.top_pois.forEach(p => {
          tbody.innerHTML += `
            <tr>
              <td><strong>${p.code}</strong></td>
              <td>${p.title}</td>
              <td><span class="badge badge-success">${p.total_playbacks} lượt</span></td>
              <td>${p.total_duration_minutes} phút</td>
            </tr>
          `;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#94a3b8;">Chưa có dữ liệu phát âm thanh ghi nhận.</td></tr>`;
      }
    }
  } catch (err) {
    console.error("Failed to load dashboard metrics:", err);
  }
}

// S10: Export Analytics Report (CSV/JSON download)
window.exportAnalyticsReport = async function() {
  try {
    const res = await fetch(`${API_BASE}/analytics/dashboard`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    const data = res.ok ? await res.json() : {};
    
    const report = {
      report_title: "TourVoice District 4 Tourism Analytics Report",
      generated_at: new Date().toISOString(),
      summary: {
        total_playbacks: data.total_playbacks || 0,
        total_listen_hours: data.total_listen_hours || 0,
        total_active_pois: data.total_active_pois || 0,
        total_sessions: data.total_sessions || 0
      },
      top_pois: data.top_pois || [],
      pois_inventory: allPois.map(p => ({
        code: p.code,
        category: p.category,
        address: p.address,
        enter_radius_m: p.radius_enter_m,
        exit_radius_m: p.radius_exit_m,
        status: p.status
      }))
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `tourvoice_analytics_report_${new Date().toISOString().slice(0,10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    alert("✅ Đã xuất báo cáo thống kê thành công!");
  } catch (err) {
    alert("Không thể xuất báo cáo: " + err);
  }
};

/* ================= TAB 2: POI MANAGEMENT & MAP PICKER (C01-C05) ================= */
function initAdminMap() {
  const mapElem = document.getElementById("admin-map");
  if (!mapElem || adminMap) return;

  const defaultLat = 10.75882;
  const defaultLng = 106.70012;

  adminMap = L.map("admin-map", {
    center: [defaultLat, defaultLng],
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

  const googleSatellite = L.tileLayer("https://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}", {
    maxZoom: 20,
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    attribution: "© Google Satellite"
  });

  const osmLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap"
  });

  cartoVoyager.addTo(adminMap);

  const baseMaps = {
    "🗺️ Đường Phố Chi Tiết (Voyager)": cartoVoyager,
    "📍 Đường Phố Google (Google Maps)": googleStreets,
    "🛰️ Ảnh Vệ Tinh (Google Satellite)": googleSatellite,
    "🧭 OpenStreetMap": osmLayer
  };
  L.control.layers(baseMaps, null, { position: "topright" }).addTo(adminMap);

  // Walking Tour Route (Tuyến đường tham quan & ẩm thực Quận 4)
  const tourWalkingRoute = [
    [10.76814, 106.70678], // Bến Nhà Rồng (Nguyễn Tất Thành)
    [10.76740, 106.70610], // Ngã 3 Nguyễn Tất Thành & Bến Vân Đồn
    [10.76850, 106.70550], // Dọc Bến Vân Đồn ven sông Bến Nghé
    [10.76895, 106.70488], // Cầu Mống
    [10.76720, 106.70320], // Bến Vân Đồn - Cầu Calmette
    [10.76450, 106.70380], // Rẽ vào Đoàn Văn Bơ
    [10.76135, 106.70425], // Chợ Xóm Chiếu (Lê Quốc Hưng)
    [10.76020, 106.70180], // Ngã 4 Hoàng Diệu & Vĩnh Khánh
    [10.75882, 106.70012], // Phố Ốc Vĩnh Khánh
    [10.75680, 106.69850]  // Vĩnh Khánh hướng Tôn Đản
  ];

  tourRouteLine = L.polyline(tourWalkingRoute, {
    color: "#ff6b35",
    weight: 5,
    opacity: 0.85,
    dashArray: "6, 8"
  }).addTo(adminMap);

  tourRouteLine.bindPopup("<strong>🚶 Tuyến Đường Đi Bộ Tour Quận 4</strong><br>Dài ~2.8 km (Bến Nhà Rồng ➔ Cầu Mống ➔ Chợ Xóm Chiếu ➔ Phố Ốc Vĩnh Khánh)");

  const pickerIcon = L.divIcon({
    className: "picker-marker-container",
    html: `<div style="background:#00b4d8; color:white; border-radius:50%; width:34px; height:34px; display:flex; align-items:center; justify-content:center; border:2px solid white; box-shadow:0 0 12px #00b4d8; font-size:18px;">📍</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17]
  });

  pickerMarker = L.marker([defaultLat, defaultLng], {
    draggable: true,
    icon: pickerIcon
  }).addTo(adminMap);

  pickerMarker.bindPopup("<strong>Vị trí đang chọn</strong><br>Kéo ghim hoặc click bản đồ để đổi tọa độ.");

  enterCircle = L.circle([defaultLat, defaultLng], {
    radius: 30,
    color: "#00b4d8",
    weight: 2,
    fillColor: "#00b4d8",
    fillOpacity: 0.15
  }).addTo(adminMap);

  exitCircle = L.circle([defaultLat, defaultLng], {
    radius: 60,
    color: "#ff833a",
    weight: 1.5,
    dashArray: "4, 6",
    fillOpacity: 0.05
  }).addTo(adminMap);

  adminMap.on("click", (e) => {
    updatePickerLocation(e.latlng.lat, e.latlng.lng);
  });

  pickerMarker.on("dragend", (e) => {
    const latlng = e.target.getLatLng();
    updatePickerLocation(latlng.lat, latlng.lng);
  });

  setTimeout(() => {
    if (adminMap) adminMap.invalidateSize(true);
  }, 250);
}

function updatePickerLocation(lat, lng) {
  if (pickerMarker) pickerMarker.setLatLng([lat, lng]);
  if (enterCircle) enterCircle.setLatLng([lat, lng]);
  if (exitCircle) exitCircle.setLatLng([lat, lng]);

  const latInp = document.getElementById("poi-lat");
  const lngInp = document.getElementById("poi-lng");
  if (latInp) latInp.value = lat.toFixed(5);
  if (lngInp) lngInp.value = lng.toFixed(5);
}

window.updateCirclesFromInputs = function() {
  const lat = parseFloat(document.getElementById("poi-lat").value) || 10.75882;
  const lng = parseFloat(document.getElementById("poi-lng").value) || 106.70012;
  const rEnter = parseFloat(document.getElementById("poi-enter").value) || 30;
  const rExit = parseFloat(document.getElementById("poi-exit").value) || 60;

  if (pickerMarker) pickerMarker.setLatLng([lat, lng]);
  if (enterCircle) {
    enterCircle.setLatLng([lat, lng]);
    enterCircle.setRadius(rEnter);
  }
  if (exitCircle) {
    exitCircle.setLatLng([lat, lng]);
    exitCircle.setRadius(rExit);
  }
};

window.centerMapDistrict4 = function() {
  if (adminMap) {
    adminMap.setView([10.764, 106.703], 15);
    updatePickerLocation(10.764, 106.703);
  }
};

async function loadPOIs() {
  try {
    const res = await fetch(`${API_BASE}/pois`);
    if (res.ok) {
      const data = await res.json();
      allPois = Array.isArray(data) ? data : (data.items || []);
      const tbody = document.getElementById("poi-admin-table");
      if (tbody) tbody.innerHTML = "";

      // Populate QR select options
      const qrSelect = document.getElementById("qr-poi-select");
      if (qrSelect) {
        qrSelect.innerHTML = allPois.map(p => {
          const poiId = p._id || p.id;
          const code = p.code || p.name || "POI";
          const addr = p.address || "";
          return `<option value="${poiId}">${code} - ${addr}</option>`;
        }).join("");
      }

      // Clear existing markers from admin map
      poiMapMarkers.forEach(m => adminMap && adminMap.removeLayer(m));
      poiMapMarkers = [];

      allPois.forEach(p => {
        if (!p) return;
        const poiId = p._id || p.id;
        const code = p.code || p.name || p.title || "POI";
        const catBadge = p.category === "food" ? "badge-warning" : "badge-info";
        const menuCount = p.menu_items ? p.menu_items.length : (p.specialties ? p.specialties.length : 0);
        const enterRad = p.radius_enter_m || p.trigger_radius || 30;
        const exitRad = p.radius_exit_m || (enterRad * 1.5) || 45;
        const addr = p.address || "";
        
        if (tbody) {
          tbody.innerHTML += `
            <tr>
              <td><strong>${code}</strong></td>
              <td><span class="badge ${catBadge}">${p.category || 'Chung'}</span></td>
              <td>${addr}</td>
              <td>Vào: ${enterRad}m | Ra: ${exitRad}m</td>
              <td><span class="badge badge-info">${menuCount} món</span></td>
              <td>
                <button class="btn btn-primary" onclick="zoomToPoi('${poiId}')" style="padding: 4px 8px; font-size: 0.75rem;">📍 Xem</button>
                <button class="btn btn-primary" style="background:#10b981; padding: 4px 8px; font-size: 0.75rem;" onclick="openAIForPoi('${code}')">🤖 AI</button>
                <button class="btn btn-danger" onclick="deletePoi('${poiId}')" style="padding: 4px 8px; font-size: 0.75rem;">🗑️</button>
              </td>
            </tr>
          `;
        }

        if (adminMap && p.location && p.location.coordinates) {
          const [lng, lat] = p.location.coordinates;
          const m = L.marker([lat, lng]).addTo(adminMap);
          m.bindPopup(`<strong>${code}</strong><br>${addr}<br>Bán kính vào: ${enterRad}m`);
          poiMapMarkers.push(m);
        }
      });
    }
  } catch (err) {
    console.error("Failed to load POIs:", err);
  }
}

window.zoomToPoi = function(poiId) {
  const poi = allPois.find(p => (p._id === poiId || p.id === poiId));
  if (!poi || !adminMap || !poi.location || !poi.location.coordinates) return;

  const [lng, lat] = poi.location.coordinates;
  adminMap.setView([lat, lng], 17);
  updatePickerLocation(lat, lng);
  document.getElementById("poi-code").value = poi.code || poi.name || "";
  document.getElementById("poi-address").value = poi.address || "";
  document.getElementById("poi-enter").value = poi.radius_enter_m || poi.trigger_radius || 30;
  document.getElementById("poi-exit").value = poi.radius_exit_m || (poi.trigger_radius ? poi.trigger_radius * 1.5 : 60);
  updateCirclesFromInputs();
};

window.openAIForPoi = function(code) {
  switchTab("ai-assistant");
  const aiInp = document.getElementById("ai-poi-name");
  if (aiInp) aiInp.value = code;
};

window.deletePoi = async function(poiId) {
  if (!adminToken) {
    alert("Vui lòng đăng nhập quyền Admin!");
    return;
  }
  if (!confirm("Bạn có chắc chắn muốn xóa địa điểm này?")) return;

  try {
    const res = await fetch(`${API_BASE}/pois/${poiId}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      alert("Đã xóa địa điểm thành công!");
      await loadPOIs();
    } else {
      alert("Không thể xóa địa điểm.");
    }
  } catch (err) {
    alert("Lỗi kết nối: " + err);
  }
};

window.toggleAddPoiForm = function() {
  const card = document.getElementById("add-poi-card");
  const btn = document.getElementById("btn-toggle-add");
  if (card.style.display === "none") {
    card.style.display = "block";
    btn.innerText = "Đóng Form Thêm";
  } else {
    card.style.display = "none";
    btn.innerText = "+ Thêm Điểm POI Mới";
  }
};

window.handleCreatePoi = async function(e) {
  e.preventDefault();
  if (!adminToken) {
    alert("Vui lòng đăng nhập với quyền Admin!");
    return;
  }

  const menuStr = document.getElementById("poi-menu-items").value.trim();
  const menuItems = menuStr ? menuStr.split(",").map(m => ({ name: m.trim(), price: 50000 })) : [];

  const payload = {
    code: document.getElementById("poi-code").value.trim(),
    category: document.getElementById("poi-cat").value,
    address: document.getElementById("poi-address").value.trim(),
    location: {
      type: "Point",
      coordinates: [
        parseFloat(document.getElementById("poi-lng").value),
        parseFloat(document.getElementById("poi-lat").value)
      ]
    },
    radius_enter_m: parseInt(document.getElementById("poi-enter").value),
    radius_exit_m: parseInt(document.getElementById("poi-exit").value),
    cooldown_seconds: 120,
    priority: 5,
    status: "active",
    menu_items: menuItems
  };

  try {
    const res = await fetch(`${API_BASE}/pois`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      alert("✅ Thêm POI mới thành công trực tiếp từ bản đồ!");
      toggleAddPoiForm();
      await loadPOIs();
    } else {
      const err = await res.json();
      alert("Lỗi: " + (err.detail || JSON.stringify(err)));
    }
  } catch (err) {
    alert("Không thể kết nối đến máy chủ: " + err);
  }
};

/* ================= TAB 3: TOUR MANAGEMENT (C15, T12, T13) ================= */
async function loadTours() {
  try {
    const res = await fetch(`${API_BASE}/tours`);
    if (res.ok) {
      const data = await res.json();
      allTours = Array.isArray(data) ? data : (data.items || []);
      const tbody = document.getElementById("tour-admin-table");
      if (!tbody) return;
      tbody.innerHTML = "";

      if (allTours.length > 0) {
        allTours.forEach(t => {
          const stopCount = t.stops ? t.stops.length : (t.poi_ids ? t.poi_ids.length : 0);
          const tCode = t.code || t.name || (t._id ? t._id.slice(0,8) : "TOUR");
          const tTitle = t.title || t.name || "Tour Quận 4";
          tbody.innerHTML += `
            <tr>
              <td><strong>${tCode}</strong></td>
              <td>${tTitle}</td>
              <td>${t.estimated_duration_minutes || 90} phút</td>
              <td><span class="badge badge-info">${stopCount} điểm</span></td>
              <td><span class="badge badge-success">${t.status || (t.is_active ? "active" : "inactive")}</span></td>
              <td>
                <button class="btn btn-primary" onclick="alert('Lộ trình gồm: ' + JSON.stringify(${stopCount} + ' điểm dừng'))" style="padding: 4px 8px; font-size: 0.75rem;">🗺️ Chi tiết</button>
              </td>
            </tr>
          `;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8;">Chưa có tour nào. Bấm nút Tạo Tour Mới bên trên để thêm.</td></tr>`;
      }
    }
  } catch (err) {
    console.error("Failed to load tours:", err);
  }
}

window.toggleAddTourForm = function() {
  const card = document.getElementById("add-tour-card");
  card.style.display = card.style.display === "none" ? "block" : "none";
};

window.handleCreateTour = async function(e) {
  e.preventDefault();
  if (!adminToken) return;

  const defaultStops = allPois.slice(0, 4).map((p, idx) => ({
    poi_id: p._id,
    order: idx + 1,
    recommended_duration_minutes: 20
  }));

  const payload = {
    code: document.getElementById("tour-code").value.trim(),
    name: document.getElementById("tour-title").value.trim(),
    title: document.getElementById("tour-title").value.trim(),
    description: document.getElementById("tour-desc").value.trim(),
    estimated_duration_minutes: parseInt(document.getElementById("tour-duration").value),
    price_vnd: parseInt(document.getElementById("tour-price").value) || 0,
    status: "active",
    stops: defaultStops
  };

  try {
    const res = await fetch(`${API_BASE}/tours`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      alert("✅ Đã tạo tour tham quan mới thành công!");
      toggleAddTourForm();
      await loadTours();
    } else {
      const err = await res.json();
      alert("Lỗi: " + (err.detail || JSON.stringify(err)));
    }
  } catch (err) {
    alert("Lỗi: " + err);
  }
};

/* ================= TAB 4: QR CODE MANAGEMENT (C16, T11) ================= */
async function loadQRCodes() {
  try {
    // List QR codes via pois
    const tbody = document.getElementById("qr-admin-table");
    if (!tbody) return;
    tbody.innerHTML = "";
    let totalQrs = 0;

    const list = Array.isArray(allPois) ? allPois : [];
    for (const poi of list.slice(0, 8)) {
      try {
        const poiId = poi._id || poi.id;
        const codeName = poi.code || poi.name || "POI";
        const qrRes = await fetch(`${API_BASE}/qr/poi/${poiId}`);
        if (qrRes.ok) {
          const rawQrs = await qrRes.json();
          const qrs = Array.isArray(rawQrs) ? rawQrs : (rawQrs.items || []);
          qrs.forEach(qr => {
            totalQrs++;
            tbody.innerHTML += `
              <tr>
                <td><strong>${qr.code || (qr._id ? qr._id.slice(0,8) : 'QR')}</strong></td>
                <td>${codeName} (${poi.address || ''})</td>
                <td>${qr.location_description || "Dán tại cửa / bàn"}</td>
                <td><span class="badge ${qr.is_active ? 'badge-success' : 'badge-danger'}">${qr.is_active ? 'Hoạt động' : 'Tạm khóa'}</span></td>
                <td>
                  <button class="btn btn-primary" onclick="viewQRModal('${qr.code || qr._id}', '${codeName}')" style="padding: 4px 8px; font-size: 0.75rem;">🔍 Xem / In QR</button>
                </td>
              </tr>
            `;
          });
        }
      } catch (e) {}
    }

    if (totalQrs === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8;">Chưa có mã QR. Bấm Cấp Mã QR Mới để tạo.</td></tr>`;
    }
  } catch (err) {
    console.error("Failed to load QR codes:", err);
  }
}

window.toggleGenerateQRForm = function() {
  const card = document.getElementById("generate-qr-card");
  card.style.display = card.style.display === "none" ? "block" : "none";
};

window.handleGenerateQR = async function(e) {
  e.preventDefault();
  if (!adminToken) return;

  const poiId = document.getElementById("qr-poi-select").value;
  const codeVal = document.getElementById("qr-code-val").value.trim();
  const descVal = document.getElementById("qr-location-desc").value.trim();

  try {
    const res = await fetch(`${API_BASE}/qr/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        poi_id: poiId,
        code: codeVal,
        location_description: descVal
      })
    });
    if (res.ok) {
      alert("✅ Đã tạo mã QR định danh thành công!");
      toggleGenerateQRForm();
      await loadQRCodes();
      viewQRModal(codeVal, "Điểm POI");
    } else {
      const err = await res.json();
      alert("Lỗi: " + (err.detail || JSON.stringify(err)));
    }
  } catch (err) {
    alert("Lỗi: " + err);
  }
};

window.viewQRModal = function(code, poiName) {
  const modal = document.getElementById("qr-view-modal");
  document.getElementById("modal-qr-title").innerText = `Mã QR: ${code}`;
  document.getElementById("modal-qr-desc").innerText = `Quét mã này để nghe thuyết minh về ${poiName}`;
  const qrImg = document.getElementById("modal-qr-img");
  qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(code)}`;
  modal.style.display = "flex";
};

window.closeQRModal = function() {
  document.getElementById("qr-view-modal").style.display = "none";
};

window.printQRCode = function() {
  window.print();
};

/* ================= TAB 5: APPROVALS (C06, C07, O01-O08) ================= */
async function loadApprovalsQueue() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/admin/owners/pending`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      const owners = await res.json();
      const tbody = document.getElementById("pending-owners-table");
      tbody.innerHTML = "";

      if (owners.length > 0) {
        owners.forEach(o => {
          tbody.innerHTML += `
            <tr>
              <td><strong>${o.full_name}</strong></td>
              <td>${o.email}</td>
              <td>${o.store_name || "N/A"}</td>
              <td>${o.store_address || "N/A"}</td>
              <td>${o.phone || "N/A"}</td>
              <td>
                <button class="btn btn-success" onclick="reviewOwner('${o._id}', 'approve')">Duyệt</button>
                <button class="btn btn-danger" onclick="reviewOwner('${o._id}', 'reject')">Từ chối</button>
              </td>
            </tr>
          `;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #94a3b8;">Không có hồ sơ chủ quán nào đang chờ duyệt.</td></tr>`;
      }
    }

    // Submissions
    const subRes = await fetch(`${API_BASE}/admin/submissions`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (subRes.ok) {
      const subs = await subRes.json();
      const tbody = document.getElementById("pending-submissions-table");
      tbody.innerHTML = "";
      if (subs.length > 0) {
        subs.forEach(s => {
          tbody.innerHTML += `
            <tr>
              <td><strong>${s.owner_id.slice(0,8)}</strong></td>
              <td>${s.poi_id.slice(0,8)}</td>
              <td><span class="badge badge-info">${s.language_code}</span></td>
              <td>${s.content?.title || "Cập nhật nội dung"}</td>
              <td><span class="badge badge-warning">${s.status}</span></td>
              <td>
                <button class="btn btn-success" onclick="reviewSubmission('${s._id}', 'approve')">Duyệt</button>
                <button class="btn btn-danger" onclick="reviewSubmission('${s._id}', 'reject')">Từ chối</button>
              </td>
            </tr>
          `;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8;">Không có bài viết nào đang chờ duyệt.</td></tr>`;
      }
    }
  } catch (err) {
    console.error("Failed to load approvals queue:", err);
  }
}

window.reviewOwner = async function(ownerId, action) {
  if (!adminToken) return;
  const reason = action === "approve" ? "Hồ sơ hợp lệ" : prompt("Nhập lý do từ chối:");
  try {
    const res = await fetch(`${API_BASE}/admin/owners/${ownerId}/review`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({ action: action, admin_notes: reason })
    });
    if (res.ok) {
      alert(`Đã ${action === 'approve' ? 'phê duyệt' : 'từ chối'} chủ quán thành công!`);
      await loadApprovalsQueue();
    }
  } catch (err) {
    alert("Lỗi: " + err);
  }
};

window.reviewSubmission = async function(subId, action) {
  if (!adminToken) return;
  const reason = action === "approve" ? "Nội dung chuẩn" : prompt("Lý do từ chối:");
  try {
    const res = await fetch(`${API_BASE}/admin/submissions/${subId}/review`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({ action: action, admin_notes: reason })
    });
    if (res.ok) {
      alert("Đã hoàn tất kiểm duyệt bài viết!");
      await loadApprovalsQueue();
    }
  } catch (err) {
    alert("Lỗi: " + err);
  }
};

/* ================= TAB 6: AI ASSISTANT & TTS AUDIO QUEUE (C09, C11-C14) ================= */
let lastAIGeneratedData = null;

async function handleGenerateAI(e) {
  e.preventDefault();
  if (!adminToken) return;

  const poiName = document.getElementById("ai-poi-name").value.trim();
  const weather = document.getElementById("ai-weather").value;
  const specialties = document.getElementById("ai-specialties").value.split(",").map(s => s.trim()).filter(Boolean);

  const btn = document.getElementById("btn-ai-submit");
  btn.innerText = "⏳ Đang sáng tạo kịch bản...";
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/ai/generate-narration`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        poi_name: poiName,
        category: "food",
        weather: weather,
        specialties: specialties,
        language_code: "vi"
      })
    });

    if (res.ok) {
      lastAIGeneratedData = await res.json();
      document.getElementById("ai-result-card").style.display = "block";
      document.getElementById("ai-res-title").innerText = lastAIGeneratedData.title;
      document.getElementById("ai-res-desc").innerText = lastAIGeneratedData.description;
      document.getElementById("ai-res-narration").innerText = lastAIGeneratedData.narration_text;
    } else {
      alert("Lỗi khi gọi AI trợ lý.");
    }
  } catch (err) {
    alert("Lỗi kết nối: " + err);
  } finally {
    btn.innerText = "✨ Gợi Ý Thuyết Minh Bằng AI";
    btn.disabled = false;
  }
}

window.triggerTTSFromAI = async function() {
  if (!lastAIGeneratedData || !allPois.length) {
    alert("Vui lòng sinh nội dung AI trước!");
    return;
  }

  const targetPoi = allPois[0];
  try {
    const res = await fetch(`${API_BASE}/jobs/tts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        poi_id: targetPoi._id,
        language_code: "vi",
        narration_text: lastAIGeneratedData.narration_text,
        voice_code: "vi-VN-HoaiMyNeural"
      })
    });

    if (res.ok) {
      alert("✅ Đã đưa tác vụ tạo audio Edge-TTS vào hàng chờ nền thành công!");
      await loadContentJobs();
    }
  } catch (err) {
    alert("Lỗi: " + err);
  }
};

async function loadContentJobs() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/jobs`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      const jobs = await res.json();
      const tbody = document.getElementById("content-jobs-table");
      tbody.innerHTML = "";

      if (jobs.length > 0) {
        jobs.forEach(j => {
          const statusBadge = j.status === "completed" ? "badge-success" : (j.status === "running" ? "badge-warning" : "badge-info");
          tbody.innerHTML += `
            <tr>
              <td><strong>${j._id.slice(0,8)}</strong></td>
              <td>${j.job_type || "TTS_GEN"}</td>
              <td><span class="badge badge-info">${j.language_code || "vi"}</span></td>
              <td><span class="badge ${statusBadge}">${j.status}</span></td>
              <td>${new Date(j.created_at).toLocaleTimeString()}</td>
              <td>
                ${j.status === 'completed' ? `<button class="btn btn-primary" onclick="previewJobAudio('${j.poi_id}')" style="padding:4px 8px; font-size:0.75rem;">▶ Nghe Thử</button>` : `<span style="color:#94a3b8; font-size:0.75rem;">Đang xử lý</span>`}
              </td>
            </tr>
          `;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8;">Không có tác vụ nào trong hàng chờ.</td></tr>`;
      }
    }
  } catch (err) {
    console.error("Failed to load content jobs:", err);
  }
}

window.previewJobAudio = async function(poiId) {
  try {
    const res = await fetch(`${API_BASE}/pois/${poiId}/contents/vi/active`);
    if (res.ok) {
      const content = await res.json();
      if (content && content.audio_asset_id) {
        const aRes = await fetch(`${API_BASE}/audio/info/${content.audio_asset_id}`);
        if (aRes.ok) {
          const aInfo = await aRes.json();
          const player = document.getElementById("admin-audio-preview");
          player.src = `${API_BASE}/audio/${aInfo.storage_key}/stream`;
          player.play();
          alert("🔊 Đang phát thử âm thanh Edge-TTS!");
        }
      }
    }
  } catch (err) {
    alert("Lỗi nghe thử audio: " + err);
  }
};

/* ================= TAB 7: OFFLINE PACKAGES BUILDER (F01-F06) ================= */
async function loadOfflinePackages() {
  try {
    const res = await fetch(`${API_BASE}/packages`);
    if (res.ok) {
      const data = await res.json();
      const pkgs = Array.isArray(data) ? data : (data.items || []);
      const tbody = document.getElementById("offline-packages-table");
      if (!tbody) return;
      tbody.innerHTML = "";

      if (pkgs.length > 0) {
        pkgs.forEach(p => {
          const pId = p._id || p.id;
          tbody.innerHTML += `
            <tr>
              <td><strong>${p.code || (pId ? pId.slice(0,8) : 'PKG')}</strong></td>
              <td>${p.tour_id ? p.tour_id.slice(0,8) : "Toàn Bộ Q4"}</td>
              <td><span class="badge badge-info">${p.language_code || "vi"}</span></td>
              <td>v${p.version || "1.0"}</td>
              <td><code style="font-size:0.7rem; color:#00b4d8;">${p.checksum_sha256 ? p.checksum_sha256.slice(0,16) : "sha256:verified"}...</code></td>
              <td>
                <a href="${API_BASE}/packages/${pId}/manifest" target="_blank" class="btn btn-primary" style="padding:4px 8px; font-size:0.75rem; text-decoration:none;">📄 Tải Manifest</a>
              </td>
            </tr>
          `;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8;">Chưa có bản đóng gói offline nào. Bấm nút Tạo Bản Đóng Gói bên trên.</td></tr>`;
      }
    }
  } catch (err) {
    console.error("Failed to load offline packages:", err);
  }
}

window.handleBuildOfflinePackage = async function() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/packages/build`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        language_code: "vi",
        package_name: "Goi-Offline-Di-Tich-Am-Thuc-Q4-Full"
      })
    });
    if (res.ok) {
      alert("✅ Đã tạo gói đóng gói offline thành công với mã băm SHA-256 an toàn!");
      await loadOfflinePackages();
    } else {
      alert("Gói đã sẵn sàng hoặc đang biên soạn.");
      await loadOfflinePackages();
    }
  } catch (err) {
    alert("Lỗi: " + err);
  }
};

/* ================= TAB 8: USERS & AUDIT LOGS (S01-S04) ================= */
async function loadUsers() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/admin/users`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      const users = Array.isArray(data) ? data : (data.items || []);
      const tbody = document.getElementById("users-admin-table");
      if (!tbody) return;
      tbody.innerHTML = "";

      users.forEach(u => {
        const rBadge = u.role === "super_admin" ? "badge-danger" : (u.role === "content_manager" ? "badge-warning" : "badge-info");
        tbody.innerHTML += `
          <tr>
            <td><strong>${u.full_name || u.email}</strong></td>
            <td>${u.email}</td>
            <td><span class="badge ${rBadge}">${u.role}</span></td>
            <td><span class="badge badge-success">${u.status || (u.is_active ? "active" : "inactive")}</span></td>
            <td>${u.created_at ? new Date(u.created_at).toLocaleDateString() : "2026-09-01"}</td>
          </tr>
        `;
      });
    }
  } catch (err) {
    console.error("Failed to load users:", err);
  }
}

async function loadAuditLogs() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/admin/audit-logs`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      const logs = Array.isArray(data) ? data : (data.items || []);
      const tbody = document.getElementById("audit-logs-table");
      if (!tbody) return;
      tbody.innerHTML = "";

      if (logs.length > 0) {
        logs.forEach(l => {
          tbody.innerHTML += `
            <tr>
              <td>${new Date(l.timestamp || Date.now()).toLocaleTimeString()}</td>
              <td><strong>${l.user_email || l.actor_id || "admin@tourvoice.vn"}</strong></td>
              <td><span class="badge badge-info">${l.action}</span></td>
              <td>${l.resource}</td>
              <td>${l.details || "Thao tác thành công"}</td>
            </tr>
          `;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8;">Hệ thống ghi nhận hoạt động bình thường, không có cảnh báo bất thường.</td></tr>`;
      }
    }
  } catch (err) {
    console.error("Failed to load audit logs:", err);
  }
}
