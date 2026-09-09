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

  // ── CTF Module Switching ─────────────────────────────────
  const btnSwitchCtf1 = document.getElementById("btn-switch-ctf1");
  const btnSwitchCtf2 = document.getElementById("btn-switch-ctf2");
  const badgeCtf1     = document.getElementById("badge-ctf1");
  const badgeCtf2     = document.getElementById("badge-ctf2");

  async function switchCTF(targetCtf) {
    try {
      const res = await fetch("/api/switch_ctf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ctf: targetCtf })
      });
      const data = await res.json();
      if (!res.ok) {
        if (data.error && data.error.includes("qulflangan")) {
          alert("🔒 CTF 2 qulflangan!\n\nCTF 2 ga o'tish uchun avval CTF 1 ning barcha 10 ta bosqichini muvaffaqiyatli tugatib, 1-Flagni olishingiz shart!");
        } else {
          alert(data.error || "Modulni almashtirishda xatolik yuz berdi");
        }
        return false;
      }

      const username = lblUserDisplay ? lblUserDisplay.textContent.trim() : "";
      if (window.terminalEngine) {
        window.terminalEngine.setCurrentCwd(`/home/${username}`);
      }

      await syncStageBadge();

      // Notify in terminal
      if (window.terminalEngine && window.terminalEngine.appendInfoLine) {
        window.terminalEngine.appendInfoLine(
          `\n🔄 [ CTF Moduli O'zgartirildi ] Siz CTF ${targetCtf} moduliga o'tdingiz.\n💡 Boshlash: cat ~/ROADMAP.txt | Holat: status\n`
        );
      }

      return true;
    } catch (err) {
      alert("Aloqa xatosi: " + err.message);
      return false;
    }
  }

  window.switchCTF = switchCTF;

  if (btnSwitchCtf1) {
    btnSwitchCtf1.addEventListener("click", () => switchCTF(1));
  }
  if (btnSwitchCtf2) {
    btnSwitchCtf2.addEventListener("click", () => {
      if (btnSwitchCtf2.classList.contains("locked")) {
        alert("🔒 CTF 2 qulflangan!\n\nCTF 2 ga o'tish uchun avval CTF 1 ning barcha 10 ta bosqichini muvaffaqiyatli tugatib, 1-Flagni olishingiz shart!");
        return;
      }
      switchCTF(2);
    });
  }

  // ── Stage Badge & CTF Status Sync ────────────────────────
  async function syncStageBadge() {
    try {
      const res = await fetch("/api/ctf_status");
      if (res.status === 401) { window.location.href = "/login"; return; }
      const data = await res.json();
      const activeCtf = data.active_ctf || 1;
      const ctf1Stage = data.ctf1_stage || 1;
      const ctf2Stage = data.ctf2_stage || 1;
      const ctf2Unlocked = !!data.ctf2_unlocked;

      // Update stage pill in terminal header
      if (stagePill) {
        if (activeCtf === 1) {
          stagePill.textContent = ctf1Stage <= 10
            ? `CTF 1: Stage ${ctf1Stage}/10`
            : `CTF 1: 10/10 ✅`;
        } else {
          stagePill.textContent = ctf2Stage <= 10
            ? `CTF 2: Stage ${ctf2Stage}/10`
            : `CTF 2: 10/10 🏆`;
        }
      }

      // Update CTF 1 button
      if (btnSwitchCtf1) {
        if (activeCtf === 1) {
          btnSwitchCtf1.classList.add("active");
        } else {
          btnSwitchCtf1.classList.remove("active");
        }
      }
      if (badgeCtf1) {
        badgeCtf1.textContent = ctf1Stage > 10 ? "10/10 ✅" : `Stage ${ctf1Stage}/10`;
      }

      // Update CTF 2 button
      if (btnSwitchCtf2) {
        if (activeCtf === 2) {
          btnSwitchCtf2.classList.add("active");
        } else {
          btnSwitchCtf2.classList.remove("active");
        }

        if (ctf2Unlocked) {
          btnSwitchCtf2.classList.remove("locked");
          btnSwitchCtf2.title = "CTF 2 ga o'tish";
          if (badgeCtf2) {
            badgeCtf2.textContent = ctf2Stage > 10 ? "10/10 🏆" : `Stage ${ctf2Stage}/10`;
          }
        } else {
          btnSwitchCtf2.classList.add("locked");
          btnSwitchCtf2.title = "CTF 1 to'liq tugatilgach ochiladi";
          if (badgeCtf2) {
            badgeCtf2.textContent = "🔒 Qulflangan";
          }
        }
      }

    } catch (err) {
      console.error("CTF status sync error:", err);
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
        document.getElementById(`podium-${n}-name`).textContent = item.username;
        const ctf1 = item.ctf1_stage || 1;
        const ctf2 = item.ctf2_stage || 1;
        let podiumDesc = "";
        if (ctf1 > 10 && ctf2 > 10) {
          podiumDesc = "👑 CTF 1 & 2 To'liq Tugatildi!";
        } else if (ctf1 > 10) {
          podiumDesc = `CTF 1: 10/10 ✅ | CTF 2: ${Math.min(ctf2, 10)}/10`;
        } else {
          podiumDesc = `CTF 1: ${Math.min(ctf1, 10)}/10`;
        }
        document.getElementById(`podium-${n}-stage`).textContent = podiumDesc;
        const flagEl = document.getElementById(`podium-${n}-flag`);
        if (item.flag) {
          flagEl.innerHTML = item.flag.split("|").map(f => {
            const clean = f.trim();
            const colorCode = clean.startsWith("CTF2") ? "var(--color-accent-cyan)" : "var(--color-accent-green)";
            return `<span style="display:block; font-size:0.7rem; color:${colorCode};">${clean}</span>`;
          }).join("");
        } else {
          flagEl.textContent = "Flag yo'q";
        }
      };

      if (board[0]) fill("1", board[0]);
      if (board[1]) fill("2", board[1]);
      if (board[2]) fill("3", board[2]);

      // Table
      if (board.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-muted); padding: 2rem;">Hech qanday ma'lumot yo'q</td></tr>`;
        return;
      }

      tbody.innerHTML = board.map((item, idx) => {
        const rank   = idx + 1;
        const medal  = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `#${rank}`;
        const ctf1   = Math.min(item.ctf1_stage || 1, 11);
        const ctf2   = Math.min(item.ctf2_stage || 1, 11);

        // Progress percentage across all 20 stages (10 in CTF1 + 10 in CTF2)
        const completedStages = (ctf1 > 10 ? 10 : ctf1 - 1) + (ctf2 > 10 ? 10 : ctf2 - 1);
        const pct = Math.round((completedStages / 20) * 100);

        const color  = pct === 100 ? "linear-gradient(90deg,#00ff88,#00dc88)"
                     : pct >= 50   ? "linear-gradient(90deg,#3b82f6,#60a5fa)"
                     : pct >= 25   ? "linear-gradient(90deg,#f59e0b,#fbbf24)"
                     :               "#4a5a7a";

        const ctf1Str = ctf1 > 10
          ? `<span style="color:var(--color-accent-green);font-weight:700;">10/10 ✅</span>`
          : `Stage ${ctf1}/10`;

        const ctf2Str = ctf1 <= 10
          ? `<span style="color:var(--text-muted);">🔒 Qulflangan</span>`
          : ctf2 > 10
            ? `<span style="color:var(--color-accent-cyan);font-weight:700;">10/10 🏆</span>`
            : `<span style="color:var(--color-accent-cyan);">Stage ${ctf2}/10</span>`;

        let flagStr = `<span style="color:var(--text-muted);">—</span>`;
        if (item.flag) {
          flagStr = item.flag.split("|").map(f => {
            const clean = f.trim();
            const isGold = clean.startsWith("CTF2");
            const colorCode = isGold ? "var(--color-accent-cyan)" : "var(--color-accent-green)";
            return `<span style="display:inline-block; font-family:var(--font-mono); font-size:0.75rem; color:${colorCode}; margin:2px 0;">${clean}</span>`;
          }).join("<br>");
        }

        let timeStr = "—";
        if (item.updated_at) {
          const parts = item.updated_at.split(" ");
          if (parts.length >= 2) {
            const d = parts[0].substring(5); // MM-DD
            const t = parts[1].substring(0, 5); // HH:MM
            timeStr = `${d} ${t}`;
          } else {
            timeStr = item.updated_at.substring(11, 16);
          }
        }

        return `
          <tr>
            <td style="font-size:1.1rem;">${medal}</td>
            <td style="color:var(--color-accent-cyan);font-weight:600;">${item.username}</td>
            <td>${ctf1Str}</td>
            <td>${ctf2Str}</td>
            <td>
              <div class="progress-bar-wrap">
                <div class="progress-bar-track">
                  <div class="progress-bar-fill" style="width:${pct}%;background:${color};"></div>
                </div>
                <span style="font-size:0.75rem;color:var(--text-secondary);min-width:36px;">${pct}%</span>
              </div>
            </td>
            <td>
              <span style="color:var(--color-accent-green); font-weight:700;">${item.pass_count || 0} / 20</span>
            </td>
            <td>${flagStr}</td>
            <td style="color:var(--text-muted);font-size:0.8rem;">${timeStr}</td>
          </tr>
        `;
      }).join("");

    } catch (err) {
      console.error("Leaderboard error:", err);
      if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#f87171; padding:2rem;">Xatolik yuz berdi</td></tr>`;
    }
  }

  if (btnRefreshLb) btnRefreshLb.addEventListener("click", fetchLeaderboard);

  // ── Cheatsheet copy protection ──
  const cheatsheetTab = document.getElementById("cheatsheet-tab");
  if (cheatsheetTab) {
    cheatsheetTab.addEventListener("copy", (e) => e.preventDefault());
    cheatsheetTab.addEventListener("cut", (e) => e.preventDefault());
    cheatsheetTab.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  // ── Handle 401 from terminal API (session expired mid-session) ──
  window.handleAuthExpired = () => {
    alert("Sessiya muddati tugadi. Qayta kirishingiz kerak.");
    window.location.href = "/login";
  };
});
