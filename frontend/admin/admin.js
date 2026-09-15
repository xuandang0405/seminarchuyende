const API_BASE = "http://localhost:8000/api/v1";
let adminToken = null;

document.addEventListener("DOMContentLoaded", async () => {
  await autoLoginAdmin();
  await loadDashboardStats();
  await loadPOIs();
  await loadApprovalsQueue();
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
      console.log("Admin logged in successfully");
    }
  } catch (err) {
    console.warn("Backend not running or auto-login failed:", err);
  }
}

function switchTab(tabName, element) {
  document.querySelectorAll(".tab-section").forEach(sec => sec.classList.remove("active"));
  document.querySelectorAll(".nav-links li").forEach(li => li.classList.remove("active"));

  document.getElementById(`tab-${tabName}`).classList.add("active");
  element.classList.add("active");

  if (tabName === "dashboard") loadDashboardStats();
  if (tabName === "pois") loadPOIs();
  if (tabName === "approvals") loadApprovalsQueue();
}

async function loadDashboardStats() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/analytics/dashboard`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      document.getElementById("stat-playbacks").innerText = data.total_playbacks;
      document.getElementById("stat-hours").innerText = data.total_listen_hours;
      document.getElementById("stat-pois").innerText = data.total_active_pois;
      document.getElementById("stat-sessions").innerText = data.total_sessions;

      // Render top POIs table
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

async function loadPOIs() {
  try {
    const res = await fetch(`${API_BASE}/pois`);
    if (res.ok) {
      const pois = await res.json();
      const tbody = document.getElementById("poi-admin-table");
      tbody.innerHTML = "";

      pois.forEach(p => {
        const catBadge = p.category === "food" ? "badge-warning" : "badge-info";
        tbody.innerHTML += `
          <tr>
            <td><strong>${p.code}</strong></td>
            <td><span class="badge ${catBadge}">${p.category}</span></td>
            <td>[${p.location.coordinates[0].toFixed(4)}, ${p.location.coordinates[1].toFixed(4)}]</td>
            <td>Enter: ${p.radius_enter_m}m | Exit: ${p.radius_exit_m}m</td>
            <td><span class="badge badge-success">${p.status}</span></td>
          </tr>
        `;
      });
    }
  } catch (err) {
    console.error("Failed to load POIs:", err);
  }
}

function toggleAddPoiForm() {
  const card = document.getElementById("add-poi-card");
  card.style.display = card.style.display === "none" ? "block" : "none";
}

async function handleCreatePoi(e) {
  e.preventDefault();
  if (!adminToken) {
    alert("Vui lòng đăng nhập với quyền Admin!");
    return;
  }

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
    status: "active"
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
      alert("✅ Thêm POI mới thành công!");
      toggleAddPoiForm();
      await loadPOIs();
    } else {
      const err = await res.json();
      alert("Lỗi: " + (err.detail || JSON.stringify(err)));
    }
  } catch (err) {
    alert("Không thể kết nối đến máy chủ: " + err);
  }
}

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
  } catch (err) {
    console.error("Failed to load pending owners:", err);
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
    alert("Lỗi thao tác: " + err);
  }
};

async function handleGenerateAI(e) {
  e.preventDefault();
  if (!adminToken) {
    alert("Vui lòng đợi hệ thống đăng nhập tài khoản!");
    return;
  }

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
      const data = await res.json();
      document.getElementById("ai-result-card").style.display = "block";
      document.getElementById("ai-res-title").innerText = data.title;
      document.getElementById("ai-res-desc").innerText = data.description;
      document.getElementById("ai-res-narration").innerText = data.narration_text;
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
