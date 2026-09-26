/**
 * MedTrack Main Client Script
 * Handles global theme switching, notifications bell, command palette (Ctrl+K),
 * system diagnostics modal, toast alerts, and modal operations.
 */

// Initialize Theme immediately to prevent theme flicker
(function () {
  const savedTheme = localStorage.getItem("medtrack_theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const activeTheme = savedTheme || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", activeTheme);
})();

document.addEventListener("DOMContentLoaded", () => {
  // Update Theme Toggle Button Icon
  updateThemeIcon();

  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) {
    themeBtn.addEventListener("click", toggleTheme);
  }


  // Command Palette Trigger Button (Ctrl + K)
  const cmdBtn = document.getElementById("cmdPaletteBtn");
  if (cmdBtn) {
    cmdBtn.addEventListener("click", () => {
      openModal("cmdPaletteModal");
      const input = document.getElementById("cmdPaletteInput");
      if (input) setTimeout(() => input.focus(), 100);
    });
  }

  // Command Palette Keyboard Shortcut: Ctrl+K or Cmd+K
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      const modal = document.getElementById("cmdPaletteModal");
      if (modal && modal.classList.contains("active")) {
        closeModal("cmdPaletteModal");
      } else {
        openModal("cmdPaletteModal");
        const input = document.getElementById("cmdPaletteInput");
        if (input) setTimeout(() => input.focus(), 100);
      }
    }
  });

  // Command Palette Search Filter
  const cmdInput = document.getElementById("cmdPaletteInput");
  if (cmdInput) {
    cmdInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      const items = document.querySelectorAll("#cmdPaletteList .cmd-item");
      items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(q) ? "flex" : "none";
      });
    });
  }

  // Auto-dismiss flash alerts after 6 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = "0";
      alert.style.transform = "translateX(50px)";
      alert.style.transition = "all 0.4s ease";
      setTimeout(() => alert.remove(), 400);
    }, 6000);
  });

  // Modal Open/Close listeners
  document.querySelectorAll("[data-modal-target]").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-modal-target");
      openModal(targetId);
    });
  });

  document.querySelectorAll(".modal-close, [data-modal-close]").forEach(btn => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal-overlay");
      if (modal) closeModal(modal.id);
    });
  });

  // Close modal when clicking backdrop
  document.querySelectorAll(".modal-overlay").forEach(modal => {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        closeModal(modal.id);
      }
    });
  });

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const activeModal = document.querySelector(".modal-overlay.active");
      if (activeModal) closeModal(activeModal.id);
    }
  });

  // Notification Bell Click
  const notifBtn = document.getElementById("notifBellBtn");
  if (notifBtn) {
    notifBtn.addEventListener("click", () => {
      fetchNotifications();
      openModal("notifModal");
    });
  }
});

// --------------------------------------------------------
// THEME SWITCHING (DARK / LIGHT)
// --------------------------------------------------------
function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const newTheme = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("medtrack_theme", newTheme);
  updateThemeIcon();
  showToast(`Switched to ${newTheme === "dark" ? "Dark Obsidian" : "Light Clinical"} theme!`, "info");
}

function updateThemeIcon() {
  const themeBtn = document.getElementById("themeToggleBtn");
  if (!themeBtn) return;
  const current = document.documentElement.getAttribute("data-theme");
  themeBtn.innerHTML = current === "dark" ? "☀️" : "🌙";
  themeBtn.title = current === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode";
}

// --------------------------------------------------------
// MODAL CONTROLLERS
// --------------------------------------------------------
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

// --------------------------------------------------------
// TOAST NOTIFICATIONS
// --------------------------------------------------------
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const icons = {
    success: "✓",
    info: "ℹ",
    warning: "⚠",
    danger: "✕"
  };

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span style="font-weight: 800; font-size: 1.1rem; color: var(--${type === 'danger' ? 'danger' : type === 'info' ? 'info' : 'success'});">
      ${icons[type] || "✓"}
    </span>
    <div style="flex: 1;">${message}</div>
    <button type="button" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.1rem;" onclick="this.parentElement.remove()">×</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// --------------------------------------------------------
// NOTIFICATIONS API FETCHER
// --------------------------------------------------------
async function fetchNotifications() {
  const container = document.getElementById("notifListContainer");
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted);">
    <div class="badge-dot" style="display:inline-block; margin-right: 8px;"></div> Fetching latest notifications...
  </div>`;

  try {
    const res = await fetch("/api/notifications");
    const data = await res.json();
    if (data.success && data.notifications.length > 0) {
      container.innerHTML = data.notifications.map(n => `
        <div style="background: var(--bg-main); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 1.1rem; margin-bottom: 0.85rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
            <span style="font-weight: 700; font-size: 0.95rem; color: var(--text-main);">${n.Subject}</span>
            <span style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono); font-weight: 500;">${n.Timestamp}</span>
          </div>
          <p style="font-size: 0.88rem; color: var(--text-body); white-space: pre-line; line-height: 1.5; margin-bottom: 0.5rem;">${n.Message}</p>
          <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-muted); padding-top: 0.35rem; border-top: 1px solid var(--border-subtle);">
            <span>Recipient: <strong style="color: var(--text-main);">${n.Recipient}</strong></span>
            <span style="font-weight: 600; color: var(--success);">${n.Status}</span>
          </div>
        </div>
      `).join("");
    } else {
      container.innerHTML = `<div style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
        <p style="font-weight: 500;">No recent notifications found.</p>
        <p style="font-size: 0.82rem; margin-top: 0.35rem;">Notifications trigger automatically when appointments are booked or clinical reports are saved.</p>
      </div>`;
    }
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger); padding: 1rem;">Failed to load notifications: ${err.message}</div>`;
  }
}
