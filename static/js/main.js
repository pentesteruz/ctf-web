/* ==========================================================================
   Apex Linux CTF — Main UI Manager (main.js)
   ========================================================================== */

document.addEventListener("DOMContentLoaded", async () => {
  const lblUserDisplay = document.getElementById("lbl-user-display");
  const btnReset       = document.getElementById("btn-reset");
  const btnLogout      = document.getElementById("btn-logout");
  const btnRefreshLb   = document.getElementById("btn-refresh-leaderboard");
  const stagePill      = document.getElementById("stage-pill");

  // ── Auth check on page load ───────────────────────────────
  // If session expired while on the page, redirect to /login
  const meRes = await fetch("/api/auth/me");
  if (!meRes.ok) {
    window.location.href = "/login";
    return;
  }
  const meData = await meRes.json();
  if (!meData.logged_in) {
    window.location.href = "/login";
    return;
  }
  // Ensure displayed username matches session
  if (lblUserDisplay) lblUserDisplay.textContent = meData.username;
  if (window.terminalEngine) {
    window.terminalEngine.setCurrentCwd(`/home/${meData.username}`);
  }

  // ── Tab switching ─────────────────────────────────────────
  const tabs        = document.querySelectorAll(".nav-tab");
  const tabContents = document.querySelectorAll(".tab-content");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.getAttribute("data-tab");
      document.getElementById(target).classList.add("active");
      if (target === "leaderboard-tab") fetchLeaderboard();
      if (target === "terminal-tab") {
        const inp = document.getElementById("term-input");
        if (inp) inp.focus();
      }
    });
  });

  // ── Logout ────────────────────────────────────────────────
  if (btnLogout) {
    btnLogout.addEventListener("click", async () => {
      if (!confirm("Chiqishni xohlaysizmi? Progress saqlanib qoladi.")) return;
      try {
        await fetch("/api/auth/logout", { method: "POST" });
      } catch (e) { /* ignore */ }
      window.location.href = "/login";
    });
  }

  // ── Reset Progress ────────────────────────────────────────
  if (btnReset) {
    btnReset.addEventListener("click", async () => {
      if (!confirm("Barcha progressni o'chirib, 1-bosqichdan boshlaysizmi?\n⚠️ Bu amalni qaytarib bo'lmaydi!")) return;
      try {
        const res = await fetch("/api/reset", { method: "POST" });
        const data = await res.json();
        alert(data.message);
        const username = lblUserDisplay ? lblUserDisplay.textContent.trim() : "";
        if (window.terminalEngine) {
          window.terminalEngine.setCurrentCwd(`/home/${username}`);
        }
        syncStageBadge();
      } catch (err) {
        alert("Reset xatoligi: " + err.message);
      }
    });
  }

  // ── Stage Badge Sync ──────────────────────────────────────
  async function syncStageBadge() {
    try {
      const res = await fetch("/api/status");
      if (res.status === 401) { window.location.href = "/login"; return; }
      const data = await res.json();
      const stage = data.current_stage;
      if (stagePill) {
        stagePill.textContent = stage > 10 ? "✅ Tugallandi!" : `Stage ${stage}/10`;
      }
    } catch (err) {
      console.error("Stage sync error:", err);
    }
  }

  window.syncStageBadge = syncStageBadge;
  syncStageBadge();

  // ── Leaderboard ───────────────────────────────────────────
  async function fetchLeaderboard() {
    const tbody = document.getElementById("leaderboard-tbody");
    try {
      const res = await fetch("/api/leaderboard");
      if (res.status === 401) { window.location.href = "/login"; return; }
      const data = await res.json();
      const board = data.leaderboard || [];

      // Reset podium
      ["1","2","3"].forEach(n => {
        document.getElementById(`podium-${n}-name`).textContent  = "--";
        document.getElementById(`podium-${n}-stage`).textContent = "Stage 0";
        document.getElementById(`podium-${n}-flag`).textContent  = "Kutilmoqda...";
      });

      const fill = (n, item) => {
        document.getElementById(`podium-${n}-name`).textContent  = item.username;
        document.getElementById(`podium-${n}-stage`).textContent =
          item.current_stage > 10 ? "✅ Barcha bosqichlar" : `Stage ${item.current_stage}/10`;
        document.getElementById(`podium-${n}-flag`).textContent  =
          item.flag || `Stage ${item.current_stage}`;
      };

      if (board[0]) fill("1", board[0]);
      if (board[1]) fill("2", board[1]);
      if (board[2]) fill("3", board[2]);

      // Table
      if (board.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted); padding: 2rem;">Hech qanday ma'lumot yo'q</td></tr>`;
        return;
      }

      tbody.innerHTML = board.map((item, idx) => {
        const rank   = idx + 1;
        const medal  = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `#${rank}`;
        const pct    = item.current_stage > 10 ? 100 : Math.round((item.current_stage - 1) / 10 * 100);
        const color  = pct === 100 ? "linear-gradient(90deg,#00ff88,#00dc88)"
                     : pct >= 60   ? "linear-gradient(90deg,#3b82f6,#60a5fa)"
                     : pct >= 30   ? "linear-gradient(90deg,#f59e0b,#fbbf24)"
                     :               "#4a5a7a";
        const stageStr = item.current_stage > 10
          ? `<span style="color:var(--color-accent-green);font-weight:700;">10/10 ✅</span>`
          : `Quiz ${item.current_stage}/10`;
        const flagStr  = item.flag
          ? `<span style="color:var(--color-accent-green);font-size:0.75rem;">${item.flag}</span>`
          : `<span style="color:var(--text-muted);">—</span>`;
        const timeStr  = item.updated_at ? item.updated_at.substring(11,19) : "—";

        return `
          <tr>
            <td style="font-size:1.1rem;">${medal}</td>
            <td style="color:var(--color-accent-cyan);font-weight:600;">${item.username}</td>
            <td>${stageStr}</td>
            <td>
              <div class="progress-bar-wrap">
                <div class="progress-bar-track">
                  <div class="progress-bar-fill" style="width:${pct}%;background:${color};"></div>
                </div>
                <span style="font-size:0.75rem;color:var(--text-secondary);min-width:36px;">${pct}%</span>
              </div>
            </td>
            <td>
              <span style="color:var(--color-accent-green);">${item.pass_count}✓</span>
              <span style="color:#f87171; margin-left:6px;">${item.fail_count}✗</span>
            </td>
            <td>${flagStr}</td>
            <td style="color:var(--text-muted);font-size:0.8rem;">${timeStr}</td>
          </tr>
        `;
      }).join("");

    } catch (err) {
      console.error("Leaderboard error:", err);
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#f87171; padding:2rem;">Xatolik yuz berdi</td></tr>`;
    }
  }

  if (btnRefreshLb) btnRefreshLb.addEventListener("click", fetchLeaderboard);

  // ── Handle 401 from terminal API (session expired mid-session) ──
  // This is called from terminal.js when execute returns 401
  window.handleAuthExpired = () => {
    alert("Sessiya muddati tugadi. Qayta kirishingiz kerak.");
    window.location.href = "/login";
  };
});
