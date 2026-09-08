/* ==========================================================================
   Apex Linux CTF — Terminal Engine (terminal.js)
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  const termInput        = document.getElementById("term-input");
  const termOutputBuffer = document.getElementById("terminal-output-buffer");
  const termCwdDisplay   = document.getElementById("term-cwd-display");
  const termPromptPath   = document.getElementById("term-prompt-path");
  const termPromptLabel  = document.getElementById("term-prompt-label");
  const lblUserDisplay   = document.getElementById("lbl-user-display");
  const promptUsername   = document.getElementById("prompt-username");
  const termHeaderUser   = document.getElementById("term-username-display");
  const tabHints         = document.getElementById("tab-hints");

  // Nano Modal elements
  const nanoModal      = document.getElementById("nanoModal");
  const editorFilename = document.getElementById("editor-filename");
  const editorFilepath = document.getElementById("editor-filepath");
  const editorContent  = document.getElementById("editor-content");
  const btnEditorSave  = document.getElementById("btn-editor-save");
  const btnEditorCancel = document.getElementById("btn-editor-cancel");

  let commandHistory = [];
  let historyIndex   = -1;
  let currentCwd     = `/home/${lblUserDisplay.textContent.trim()}`;
  let activeEditorPath = "";

  // ── Path formatting ──────────────────────────────────────
  function formatPromptPath(path, username) {
    const home = `/home/${username}`;
    if (path === home) return "~";
    if (path.startsWith(home + "/")) return "~" + path.slice(home.length);
    return path;
  }

  function updatePromptDisplay() {
    const username = lblUserDisplay.textContent.trim();
    const fmt = formatPromptPath(currentCwd, username);
    termPromptPath.textContent = fmt;
    termCwdDisplay.textContent = fmt;
    if (promptUsername) promptUsername.textContent = username;
    if (termHeaderUser) termHeaderUser.textContent = username;
  }

  updatePromptDisplay();

  // Click anywhere in terminal body → focus input
  document.getElementById("terminal-body").addEventListener("click", (e) => {
    if (!window.getSelection().toString()) {
      termInput.focus();
    }
  });

  // ── Append output ─────────────────────────────────────────
  function appendLine(content, opts = {}) {
    const div = document.createElement("div");
    div.className = "term-line";

    if (opts.isInput) {
      div.innerHTML = content;
    } else if (opts.color) {
      div.style.color = opts.color;
      div.textContent = content;
    } else {
      div.textContent = content;
    }

    termOutputBuffer.appendChild(div);
    scrollBottom();
  }

  function scrollBottom() {
    const body = document.getElementById("terminal-body");
    body.scrollTop = body.scrollHeight;
  }

  function appendInputLine(cmdStr) {
    const username = lblUserDisplay.textContent.trim();
    const fmt = formatPromptPath(currentCwd, username);
    const html = `<span class="term-prompt"><span class="prompt-user">${escapeHtml(username)}</span><span class="prompt-at">@ctf-linux:</span><span class="term-path">${escapeHtml(fmt)}</span><span class="prompt-dollar">$&nbsp;</span></span>${escapeHtml(cmdStr)}`;
    appendLine(html, { isInput: true });
  }

  // ── Execute command via API ───────────────────────────────
  async function executeCommand(cmdStr) {
    const trimmed = cmdStr.trim();
    hideTabHints();

    appendInputLine(trimmed);

    if (!trimmed) return;

    commandHistory.push(trimmed);
    historyIndex = commandHistory.length;

    try {
      const response = await fetch("/api/terminal/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: trimmed, cwd: currentCwd })
      });

      if (response.status === 401) {
        if (window.handleAuthExpired) window.handleAuthExpired();
        return;
      }

      const data = await response.json();

      if (data.action === "open_editor") {
        openNanoEditor(data.path, data.filename, data.content);
        if (data.cwd) { currentCwd = data.cwd; updatePromptDisplay(); }
        return;
      }

      if (data.cwd) {
        currentCwd = data.cwd;
        updatePromptDisplay();
      }

      if (data.output === "__CLEAR__") {
        termOutputBuffer.innerHTML = "";
      } else if (data.output) {
        // Output may be multi-line — render each line with tailored color
        out.split("\n").forEach(line => {
          let lineColor = null;
          if (line.includes("💡 Maslahat")) {
            lineColor = "#fbbf24"; // yellow hint
          } else if (line.includes("🚨 So'nggi maslahat")) {
            lineColor = "#fb923c"; // orange last hint
          } else if (line.includes("⚠️ DIQQAT") || line.includes("⚠️ Noto'g'ri")) {
            lineColor = "#f87171"; // warning red
          } else if (line.includes("✅") || line.includes("🎉") || line.includes("🏆") || line.includes("🔓")) {
            lineColor = "#00ff88"; // success green
          } else if (line.includes("❌")) {
            lineColor = "#f87171"; // error red
          }
          appendLine(line, lineColor ? { color: lineColor } : {});
        });
      }

      // After check command — sync stage badge
      if (trimmed === "check") {
        if (window.syncStageBadge) window.syncStageBadge();
      }

    } catch (err) {
      appendLine(`❌ Tarmoq xatosi: ${err.message}`, { color: "#f87171" });
    }
  }

  // ── HTML escape ───────────────────────────────────────────
  function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, m => map[m]);
  }

  // ── Tab Completion ────────────────────────────────────────
  async function handleTab() {
    const val = termInput.value;
    if (!val && !val.endsWith(" ")) return;

    try {
      const res = await fetch("/api/terminal/autocomplete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: val, cwd: currentCwd })
      });
      const data = await res.json();
      const matches = data.matches || [];

      hideTabHints();

      if (matches.length === 0) return;

      if (matches.length === 1) {
        // Single match → complete directly
        const isTrailing = val.endsWith(" ");
        const parts = val.split(" ");
        const completed = matches[0];
        if (isTrailing) {
          termInput.value = val + completed;
        } else {
          parts[parts.length - 1] = completed;
          termInput.value = parts.join(" ");
        }
      } else {
        // Multiple matches → find longest common prefix
        let lcp = matches[0];
        for (let i = 1; i < matches.length; i++) {
          while (!matches[i].startsWith(lcp) && lcp.length > 0) {
            lcp = lcp.slice(0, -1);
          }
        }

        const isTrailing = val.endsWith(" ");
        const parts = val.split(" ");
        const lastTok = isTrailing ? "" : parts[parts.length - 1];

        if (lcp.length > lastTok.length) {
          // Can extend partial token
          if (isTrailing) {
            termInput.value = val + lcp;
          } else {
            parts[parts.length - 1] = lcp;
            termInput.value = parts.join(" ");
          }
        }

        // Show all matches in popup
        showTabHints(matches);
      }
    } catch (err) {
      console.error("Tab autocomplete error:", err);
    }
  }

  function showTabHints(matches) {
    tabHints.innerHTML = "";
    matches.forEach(m => {
      const span = document.createElement("span");
      span.className = "tab-hint-item" + (m.endsWith("/") ? " is-dir" : "");
      span.textContent = m;
      tabHints.appendChild(span);
    });
    tabHints.style.display = "flex";
  }

  function hideTabHints() {
    tabHints.style.display = "none";
    tabHints.innerHTML = "";
  }

  // ── Keyboard handling ─────────────────────────────────────
  termInput.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      const val = termInput.value;
      termInput.value = "";
      await executeCommand(val);

    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIndex > 0) {
        historyIndex--;
        termInput.value = commandHistory[historyIndex];
      }

    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        historyIndex++;
        termInput.value = commandHistory[historyIndex];
      } else {
        historyIndex = commandHistory.length;
        termInput.value = "";
      }

    } else if (e.key === "Tab") {
      e.preventDefault();
      await handleTab();

    } else if (e.key === "Escape") {
      hideTabHints();

    } else if (e.key === "l" && e.ctrlKey) {
      e.preventDefault();
      termOutputBuffer.innerHTML = "";
      hideTabHints();

    } else if (e.key === "c" && e.ctrlKey) {
      e.preventDefault();
      appendInputLine(termInput.value + "^C");
      termInput.value = "";
      hideTabHints();
    }
  });

  // Hide hints when clicking elsewhere
  document.addEventListener("click", (e) => {
    if (!tabHints.contains(e.target) && e.target !== termInput) {
      hideTabHints();
    }
  });

  // ── Quick Toolbar Buttons ─────────────────────────────────
  document.getElementById("btn-quick-check").addEventListener("click", () => executeCommand("check"));
  document.getElementById("btn-quick-status").addEventListener("click", () => executeCommand("status"));
  document.getElementById("btn-quick-help").addEventListener("click", () => executeCommand("help"));
  document.getElementById("btn-quick-clear").addEventListener("click", () => {
    termOutputBuffer.innerHTML = "";
    hideTabHints();
    termInput.focus();
  });

  // ── Nano Editor ───────────────────────────────────────────
  function openNanoEditor(path, filename, content) {
    activeEditorPath = path;
    editorFilename.textContent = filename;
    editorFilepath.textContent = path;
    editorContent.value = content;
    nanoModal.classList.add("active");
    editorContent.focus();
  }

  function closeNanoEditor() {
    nanoModal.classList.remove("active");
    activeEditorPath = "";
    termInput.focus();
  }

  btnEditorCancel.addEventListener("click", closeNanoEditor);

  // Close on Escape key inside editor
  editorContent.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeNanoEditor();
    if (e.key === "s" && e.ctrlKey) { e.preventDefault(); btnEditorSave.click(); }
  });

  btnEditorSave.addEventListener("click", async () => {
    if (!activeEditorPath) return;
    const content = editorContent.value;
    try {
      const res = await fetch("/api/file/write", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: activeEditorPath, content })
      });
      const data = await res.json();
      if (data.status === "ok") {
        appendLine(`[ nano ] ${data.message}`, { color: "#00ff88" });
      } else {
        appendLine(`[ nano xatosi ] ${data.message}`, { color: "#f87171" });
      }
    } catch (err) {
      appendLine(`[ nano xatosi ] ${err.message}`, { color: "#f87171" });
    } finally {
      closeNanoEditor();
    }
  });

  // ── Expose terminal API ───────────────────────────────────
  window.terminalEngine = {
    executeCommand,
    updatePromptDisplay,
    setCurrentCwd(cwd) {
      currentCwd = cwd;
      updatePromptDisplay();
    }
  };
});
