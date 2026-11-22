/**
 * App.js — Main router, global utilities, app initialization.
 */

// ── Global Utilities ─────────────────────────────────────────────────────────

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatDate(date) {
  if (!(date instanceof Date) || isNaN(date)) return '';
  return date.toLocaleDateString('uk-UA', { day: 'numeric', month: 'long' });
}

function formatDateLong(date) {
  if (!(date instanceof Date) || isNaN(date)) return '';
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);

  if (date.toDateString() === today.toDateString()) return 'Сьогодні';
  if (date.toDateString() === tomorrow.toDateString()) return 'Завтра';

  return date.toLocaleDateString('uk-UA', {
    weekday: 'long', day: 'numeric', month: 'long'
  });
}

function renderError(err) {
  const msg = err instanceof APIError ? err.message : 'Не вдалося завантажити дані';
  return `
    <div class="page">
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Помилка</div>
        <div class="empty-state-text">${escHtml(msg)}</div>
        <button class="btn btn-secondary" style="margin-top:16px" onclick="location.reload()">
          Перезавантажити
        </button>
      </div>
    </div>`;
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${escHtml(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function showModal(html) {
  const overlay = document.getElementById('modal-overlay');
  const content = document.getElementById('modal-content');
  content.innerHTML = html;
  overlay.classList.remove('hidden');

  // Close on overlay click
  overlay.onclick = (e) => {
    if (e.target === overlay) closeModal();
  };
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

window.escHtml = escHtml;
window.formatDate = formatDate;
window.formatDateLong = formatDateLong;
window.renderError = renderError;
window.showToast = showToast;
window.showModal = showModal;
window.closeModal = closeModal;


// ── Router ───────────────────────────────────────────────────────────────────

const Router = {
  _current: null,
  _pages: {
    home: () => HomePage.render(),
    nmt: () => NMTPage.render(),
    courses: () => CoursesPage.render(),
    schedule: () => SchedulePage.render(),
    statistics: () => StatisticsPage.render(),
    settings: () => SettingsPage.render(),
  },

  navigate(page) {
    if (!this._pages[page]) page = 'home';
    this._current = page;
    Navbar.setActive(page);
    this._pages[page]();
    // Scroll to top
    document.getElementById('page-content').scrollTo(0, 0);
  }
};

window.Router = Router;


// ── App Init ─────────────────────────────────────────────────────────────────

async function initApp() {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    // Apply Telegram theme colors if available
    if (tg.colorScheme === 'light') {
      // We use dark theme always for consistency, but could adapt here
    }
  }

  const loadingScreen = document.getElementById('loading-screen');
  const welcomeOverlay = document.getElementById('welcome-overlay');
  const moduleSelectOverlay = document.getElementById('module-select-overlay');
  const appShell = document.getElementById('app');

  try {
    // Check backend health
    await API.health();
  } catch (err) {
    loadingScreen.innerHTML = `
      <div class="loading-logo">⚠️</div>
      <div class="loading-text" style="color:var(--color-danger)">Сервер недоступний</div>
      <div style="font-size:13px;color:var(--text-muted);margin-top:8px;text-align:center;padding:0 32px">
        Переконайся, що backend запущено на порту 8000.<br>
        <code style="font-size:11px">python run.py</code>
      </div>`;
    return;
  }

  // Load user data
  let user, modules;
  try {
    user = await API.getMe();
    modules = await API.getModules().catch(() => ({ nmt_enabled: false, courses_enabled: false }));
  } catch (err) {
    loadingScreen.innerHTML = renderError(err);
    return;
  }

  // Hide loading
  loadingScreen.style.opacity = '0';
  setTimeout(() => loadingScreen.classList.add('hidden'), 400);

  // Show welcome overlay on first Mini App visit
  if (!user.mini_app_welcomed) {
    welcomeOverlay.classList.remove('hidden');
    document.getElementById('welcome-start-btn').onclick = async () => {
      await API.markWelcomeSeen().catch(() => {});
      welcomeOverlay.classList.add('hidden');
      await checkModuleSelection(modules, moduleSelectOverlay, appShell);
    };
    return;
  }

  await checkModuleSelection(modules, moduleSelectOverlay, appShell);
}

async function checkModuleSelection(modules, moduleSelectOverlay, appShell) {
  if (!modules.nmt_enabled && !modules.courses_enabled) {
    moduleSelectOverlay.classList.remove('hidden');

    // Handle checkbox visual feedback
    document.querySelectorAll('.module-choice-card').forEach(card => {
      const cb = card.querySelector('input[type="checkbox"]');
      cb.addEventListener('change', () => {
        card.classList.toggle('selected', cb.checked);
      });
    });

    document.getElementById('module-select-btn').onclick = async () => {
      const nmtEnabled = document.getElementById('module-nmt-cb').checked;
      const coursesEnabled = document.getElementById('module-courses-cb').checked;

      if (!nmtEnabled && !coursesEnabled) {
        showToast('Обери хоча б один модуль', 'error');
        return;
      }

      try {
        const updatedModules = await API.updateModules({
          nmt_enabled: nmtEnabled,
          courses_enabled: coursesEnabled,
        });

        // If NMT enabled and user not onboarded, complete onboarding
        const user = await API.getMe();
        if (!user.onboarded) {
          await API.completeOnboarding({ learning_time_choice: '3-5' }).catch(() => {});
        }

        moduleSelectOverlay.classList.add('hidden');
        launchApp(updatedModules);
      } catch (err) {
        showToast(err.message, 'error');
      }
    };
    return;
  }

  launchApp(modules);
}

function launchApp(modules) {
  const appShell = document.getElementById('app');
  appShell.classList.remove('hidden');
  Navbar.init();
  Navbar.updateModuleVisibility(modules);
  Router.navigate('home');
}

// Start the app
document.addEventListener('DOMContentLoaded', initApp);
