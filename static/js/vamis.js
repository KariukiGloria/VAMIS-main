/**
 * VAMIS — Vaccine Availability Management Information System
 * Main JavaScript  |  Version 1.0
 * Colors: White · Light Blue · Pink
 */

'use strict';

/* ================================================================
   TOAST NOTIFICATIONS
   Usage: VAMIS.toast('Your message', 'success' | 'error' | 'warning' | 'info')
================================================================ */
const VAMIS = (function () {

  const ICONS = {
    success: 'fa-check-circle',
    error:   'fa-times-circle',
    warning: 'fa-exclamation-triangle',
    info:    'fa-info-circle',
  };

  const TITLES = {
    success: 'Success',
    error:   'Error',
    warning: 'Warning',
    info:    'Info',
  };

  // Duration in ms before auto-dismiss
  const TOAST_DURATION = 5000;

  function getContainer() {
    let c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  function toast(message, type = 'info', title = null) {
    const container = getContainer();
    const icon      = ICONS[type]  || ICONS.info;
    const heading   = title || TITLES[type] || TITLES.info;

    const el = document.createElement('div');
    el.className = `toast-vamis ${type}`;
    el.style.position = 'relative';
    el.innerHTML = `
      <i class="fas ${icon} toast-icon"></i>
      <div class="toast-body">
        <div class="toast-title">${heading}</div>
        <div class="toast-msg">${message}</div>
      </div>
      <button class="toast-close" aria-label="Close">
        <i class="fas fa-times"></i>
      </button>
    `;

    // Close button
    el.querySelector('.toast-close').addEventListener('click', () => dismissToast(el));

    container.appendChild(el);

    // Auto dismiss
    const timer = setTimeout(() => dismissToast(el), TOAST_DURATION);
    el._timer = timer;

    // Pause on hover
    el.addEventListener('mouseenter', () => clearTimeout(el._timer));
    el.addEventListener('mouseleave', () => {
      el._timer = setTimeout(() => dismissToast(el), 2000);
    });

    return el;
  }

  function dismissToast(el) {
    if (!el || el._dismissing) return;
    el._dismissing = true;
    clearTimeout(el._timer);
    el.classList.add('hiding');
    el.addEventListener('animationend', () => el.remove(), { once: true });
    // Fallback removal
    setTimeout(() => { if (el.parentNode) el.remove(); }, 400);
  }

  // Render Django messages injected as hidden spans
  function renderDjangoMessages() {
    document.querySelectorAll('[data-toast]').forEach(el => {
      toast(el.dataset.message, el.dataset.type || 'info');
      el.remove();
    });
  }

  return { toast, dismissToast, renderDjangoMessages };
})();

/* ================================================================
   SIDEBAR
================================================================ */
(function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const toggle  = document.getElementById('sidebarToggle');

  if (!sidebar) return;

  // Mobile toggle
  if (toggle) {
    toggle.addEventListener('click', e => {
      e.stopPropagation();
      sidebar.classList.toggle('open');
    });
  }

  // Close on outside click (mobile)
  document.addEventListener('click', e => {
    if (
      sidebar.classList.contains('open') &&
      !sidebar.contains(e.target) &&
      (!toggle || !toggle.contains(e.target))
    ) {
      sidebar.classList.remove('open');
    }
  });

  // Close on swipe left (mobile)
  let touchStartX = 0;
  sidebar.addEventListener('touchstart', e => {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });
  sidebar.addEventListener('touchend', e => {
    const diff = touchStartX - e.changedTouches[0].screenX;
    if (diff > 50) sidebar.classList.remove('open');
  }, { passive: true });

  // Active link highlighting
  const path = window.location.pathname;
  sidebar.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (!href || href === '/') return;
    // Exact or prefix match (but not root)
    if (path === href || (path.startsWith(href) && href.length > 1)) {
      link.classList.add('active');
    }
  });
})();

/* ================================================================
   SCROLL TO TOP BUTTON
================================================================ */
(function initScrollTop() {
  const btn = document.createElement('button');
  btn.id = 'scroll-top';
  btn.setAttribute('aria-label', 'Scroll to top');
  btn.innerHTML = '<i class="fas fa-chevron-up"></i>';
  document.body.appendChild(btn);

  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 320);
  }, { passive: true });

  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();

/* ================================================================
   CONFIRM DIALOGS
   Add data-confirm="Are you sure?" to any link or button
================================================================ */
document.addEventListener('click', function (e) {
  const el = e.target.closest('[data-confirm]');
  if (!el) return;
  const msg = el.dataset.confirm || 'Are you sure you want to do this?';
  if (!window.confirm(msg)) {
    e.preventDefault();
    e.stopImmediatePropagation();
  }
});

/* ================================================================
   FORM ENHANCEMENTS
================================================================ */
document.addEventListener('DOMContentLoaded', function () {

  // ── Render Django messages as toasts
  VAMIS.renderDjangoMessages();

  // ── Auto-dismiss alert banners with class .auto-dismiss
  setTimeout(() => {
    document.querySelectorAll('.alert-banner.auto-dismiss').forEach(el => {
      el.style.transition = 'opacity .5s, max-height .5s, margin .5s, padding .5s';
      el.style.opacity = '0';
      el.style.maxHeight = '0';
      el.style.marginBottom = '0';
      el.style.padding = '0';
      setTimeout(() => el.remove(), 500);
    });
  }, 5000);

  // ── Submit button loading state
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function (e) {
      // Don't lock if HTML5 validation will fail
      if (!form.checkValidity()) return;

      const submitBtn = form.querySelector('[type="submit"]');
      if (submitBtn) {
        // Small delay so validation errors still show
        setTimeout(() => {
          submitBtn.classList.add('btn-loading');
          submitBtn.disabled = true;
        }, 50);
      }
    });
  });

  // ── Client-side table search (data-search-table attribute)
  //    Add data-search-table="table-id" to an input to filter that table live
  document.querySelectorAll('[data-search-table]').forEach(input => {
    const tableId = input.dataset.searchTable;
    const table   = document.getElementById(tableId);
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tbody tr'));

    input.addEventListener('input', () => {
      const query = input.value.trim().toLowerCase();
      let visible = 0;

      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const show = !query || text.includes(query);
        row.style.display = show ? '' : 'none';
        if (show) visible++;
      });

      // Show/hide no-results row
      let noResults = table.querySelector('.no-results-row');
      if (!visible && query) {
        if (!noResults) {
          const cols = table.querySelector('thead tr')?.children.length || 1;
          noResults = document.createElement('tr');
          noResults.className = 'no-results-row';
          noResults.innerHTML = `<td colspan="${cols}" style="text-align:center;padding:32px;color:var(--text-muted);">
            <i class="fas fa-search" style="margin-right:8px;opacity:.4;"></i>No results for "<strong>${escapeHtml(input.value)}</strong>"
          </td>`;
          table.querySelector('tbody').appendChild(noResults);
        } else {
          noResults.style.display = '';
        }
      } else if (noResults) {
        noResults.style.display = 'none';
      }
    });
  });

  // ── Fade-in page body
  const pageBody = document.querySelector('.page-body');
  if (pageBody) pageBody.classList.add('fade-in');

  // ── Tooltip-style title display for truncated cells
  document.querySelectorAll('.table-vamis td').forEach(td => {
    if (td.scrollWidth > td.clientWidth && !td.title) {
      td.title = td.textContent.trim();
    }
  });

  // ── Auto-select search input text on focus
  document.querySelectorAll('.search-box input').forEach(input => {
    input.addEventListener('focus', () => input.select());
  });

  // ── Number input: prevent negative values
  document.querySelectorAll('input[type="number"]').forEach(input => {
    if (!input.min) input.min = '0';
    input.addEventListener('blur', () => {
      if (parseFloat(input.value) < 0) input.value = 0;
    });
  });

  // ── Date inputs: set max to reasonable future date
  document.querySelectorAll('input[type="date"]').forEach(input => {
    if (input.name && input.name.toLowerCase().includes('expiry') && !input.max) {
      const future = new Date();
      future.setFullYear(future.getFullYear() + 10);
      input.max = future.toISOString().split('T')[0];
    }
  });

});

/* ================================================================
   STATUS UPDATE FORMS (restock fulfill, alert resolve etc.)
   Show inline spinner when form submits via POST
================================================================ */
document.addEventListener('submit', function (e) {
  const form = e.target;
  if (!form.dataset.statusForm) return;

  const btn = form.querySelector('[type="submit"]');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }
});

/* ================================================================
   PRINT HELPER
   Usage: <button onclick="VAMIS.print()">Print</button>
================================================================ */
VAMIS.print = function (title) {
  if (title) document.title = title + ' — VAMIS';
  window.print();
};

/* ================================================================
   UTILITY HELPERS
================================================================ */
function escapeHtml(str) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(str).replace(/[&<>"']/g, m => map[m]);
}

// Format numbers with commas
VAMIS.formatNumber = function (n) {
  return Number(n).toLocaleString('en-KE');
};

// Format date to local Kenyan style
VAMIS.formatDate = function (dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-KE', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
};

/* ================================================================
   LIVE CLOCK  (call once, updates every minute)
   Usage: VAMIS.startClock('element-id')
================================================================ */
VAMIS.startClock = function (elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;

  function update() {
    el.textContent = new Date().toLocaleString('en-KE', {
      weekday: 'short', year: 'numeric', month: 'short',
      day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  }

  update();
  setInterval(update, 30000);
};

/* ================================================================
   ALPINE.JS DATA HELPERS
   Pre-built Alpine component data objects for use in templates
================================================================ */

// Dropdown with search
window.dropdownSearch = function (items = []) {
  return {
    open: false,
    query: '',
    items,
    get filtered() {
      if (!this.query) return this.items;
      return this.items.filter(i =>
        i.label.toLowerCase().includes(this.query.toLowerCase())
      );
    },
    toggle() { this.open = !this.open; },
    close()  { this.open = false; this.query = ''; },
  };
};

// Confirm modal
window.confirmModal = function () {
  return {
    open: false,
    title: '',
    message: '',
    action: null,
    ask(title, message, action) {
      this.title   = title;
      this.message = message;
      this.action  = action;
      this.open    = true;
    },
    confirm() {
      if (typeof this.action === 'function') this.action();
      else if (typeof this.action === 'string') window.location.href = this.action;
      this.open = false;
    },
    cancel() { this.open = false; },
  };
};

// Tab switcher
window.tabSwitcher = function (defaultTab = '') {
  return {
    active: defaultTab,
    setTab(tab) { this.active = tab; },
    isActive(tab) { return this.active === tab; },
  };
};


/* ================================================================
   SESSION INACTIVITY TIMER
   Warns user 2 minutes before auto-logout, then redirects to /login/
   Timeout matches settings.SESSION_INACTIVITY_TIMEOUT (15 min)
================================================================ */
(function () {
  const TIMEOUT_MS    = 15 * 60 * 1000;  // 15 minutes — must match settings
  const WARNING_MS    = 13 * 60 * 1000;  // warn 2 minutes before
  const EVENTS        = ['mousemove', 'keydown', 'mousedown', 'touchstart', 'scroll'];

  let warningTimer, logoutTimer, warningShown = false;

  function resetTimers() {
    clearTimeout(warningTimer);
    clearTimeout(logoutTimer);
    if (warningShown) {
      const w = document.getElementById('session-warning');
      if (w) w.remove();
      warningShown = false;
    }
    warningTimer = setTimeout(showWarning, WARNING_MS);
    logoutTimer  = setTimeout(doLogout,    TIMEOUT_MS);
  }

  function showWarning() {
    warningShown = true;
    const div = document.createElement('div');
    div.id = 'session-warning';
    div.style.cssText = [
      'position:fixed','bottom:24px','right:24px','z-index:9999',
      'background:#1e3a5f','color:#fff','padding:16px 20px',
      'border-radius:12px','max-width:320px','box-shadow:0 8px 24px rgba(0,0,0,.3)',
      'font-family:Nunito,sans-serif','font-size:14px','line-height:1.5',
    ].join(';');
    div.innerHTML = `
      <div style="font-weight:700;margin-bottom:6px;">
        <i class="fas fa-clock" style="color:#fde68a;margin-right:6px;"></i>Session expiring soon
      </div>
      <div style="color:rgba(255,255,255,.8);font-size:13px;">
        You will be logged out in 2 minutes due to inactivity.
      </div>
      <button onclick="document.getElementById('session-warning').remove()" style="
        margin-top:12px;background:rgba(255,255,255,.15);color:#fff;
        border:1px solid rgba(255,255,255,.3);padding:6px 16px;
        border-radius:6px;cursor:pointer;font-family:Nunito,sans-serif;font-size:13px;">
        Keep me logged in
      </button>`;
    document.body.appendChild(div);
    // "Keep me logged in" button resets timers
    div.querySelector('button').addEventListener('click', resetTimers);
  }

  function doLogout() {
    window.location.href = '/logout/';
  }

  // Only run for authenticated pages (check for logout link in sidebar)
  if (document.querySelector('.logout-btn') || document.querySelector('[href*="logout"]')) {
    EVENTS.forEach(e => document.addEventListener(e, resetTimers, { passive: true }));
    resetTimers();
  }
})();

/* ================================================================
   EXPOSE GLOBALLY
================================================================ */
window.VAMIS = VAMIS;