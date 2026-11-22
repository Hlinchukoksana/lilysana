/**
 * Home page — dashboard overview.
 */
const HomePage = {
  async render() {
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;

    try {
      const [user, stats, schedule, modules, settings] = await Promise.all([
        API.getMe(),
        API.getStatistics().catch(() => ({
          week_hours_completed: 0,
          week_hours_planned: 0,
          completed_sessions: 0,
          avg_nmt_score: null,
        })),
        API.getSchedule().catch(() => []),
        API.getModules().catch(() => ({ nmt_enabled: false, courses_enabled: false })),
        API.getSettings().catch(() => ({ study_days: '0,1,2,3,4', preferred_start_hour: 18, preferred_start_minute: 0 })),
      ]);

      const upcoming = (schedule || []).slice(0, 3);
      const timeChoice = { '1-2': '1–2 год/день', '3-5': '3–5 год/день', '5-8': '5–8 год/день' };

      const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'];
      let scheduleText = '';
      if (settings && settings.study_days) {
        const days = settings.study_days.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n)).map(d => dayNames[d]);
        const time = `${String(settings.preferred_start_hour ?? 18).padStart(2, '0')}:${String(settings.preferred_start_minute ?? 0).padStart(2, '0')}`;
        if (days.length > 0) {
          scheduleText = `🗓 ${days.join(', ')} з ${time}`;
        }
      }

      content.innerHTML = `
        <div class="page animate-in">
          <div class="greeting-card">
            <div class="greeting-name">Привіт, ${user.first_name || 'друже'} 👋</div>
            <div class="greeting-sub">Сьогодні ${formatDate(new Date())}</div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
              ${user.learning_time_choice ? `
                <div class="greeting-time-badge">
                  ⏱ ${timeChoice[user.learning_time_choice] || user.learning_time_choice}
                </div>` : ''}
              ${scheduleText ? `
                <div class="greeting-time-badge" style="cursor:pointer" onclick="Router.navigate('settings')">
                  ${scheduleText} ⚙️
                </div>` : ''}
            </div>
          </div>

          <div class="section">
            <div class="section-header">
              <span class="section-title">Цей тиждень</span>
            </div>
            <div class="stat-grid">
              <div class="stat-card">
                <div class="stat-value">${stats.week_hours_completed.toFixed(1)}</div>
                <div class="stat-label">год виконано</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${stats.week_hours_planned.toFixed(1)}</div>
                <div class="stat-label">год заплановано</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${stats.completed_sessions}</div>
                <div class="stat-label">занять виконано</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${stats.avg_nmt_score != null ? stats.avg_nmt_score + '%' : '—'}</div>
                <div class="stat-label">середній НМТ</div>
              </div>
            </div>
          </div>

          <div class="section">
            <div class="section-header">
              <span class="section-title">Найближчі заняття</span>
              <button class="btn btn-ghost btn-sm" onclick="Router.navigate('schedule')">Всі →</button>
            </div>
            ${upcoming.length === 0 ? `
              <div class="empty-state">
                <div class="empty-state-icon">📅</div>
                <div class="empty-state-title">Занять не заплановано</div>
                <div class="empty-state-text">Додай курс або НМТ-тест, щоб почати планування</div>
              </div>` : upcoming.map(s => renderSessionItem(s, false)).join('')
            }
          </div>

          <div class="section">
            <div class="section-header">
              <span class="section-title">Активні модулі</span>
              <button class="btn btn-ghost btn-sm" onclick="Router.navigate('settings')">Змінити →</button>
            </div>
            <div style="display:flex; gap:var(--space-sm); flex-wrap:wrap;">
              ${modules.nmt_enabled ? '<span class="badge badge-primary">🎯 НМТ</span>' : ''}
              ${modules.courses_enabled ? '<span class="badge badge-success">🎓 Курси</span>' : ''}
              ${!modules.nmt_enabled && !modules.courses_enabled ? '<span class="badge">Немає активних модулів</span>' : ''}
            </div>
          </div>
        </div>`;

      ProgressBar.animateAll(content);
    } catch (err) {
      content.innerHTML = renderError(err);
    }
  }
};

function renderSessionItem(s, showComplete = true) {
  const dt = new Date(s.scheduled_at);
  const day = dt.getDate();
  const month = dt.toLocaleString('uk-UA', { month: 'short' });
  const time = dt.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
  const dur = Math.round(s.duration_minutes);
  const icon = s.type === 'nmt_repetition' ? '🎯' : '🎓';
  const statusClass = s.is_completed ? 'completed' : s.is_missed ? 'missed' : '';

  return `
    <div class="session-item ${statusClass}" id="session-${s.type}-${s.id}">
      <div class="session-date-col">
        <div class="session-day">${day}</div>
        <div class="session-month">${month}</div>
      </div>
      <div class="session-info">
        <div class="session-title">${icon} ${s.title}</div>
        <div class="session-meta">${time} · ${dur} хв${s.subtitle ? ' · ' + s.subtitle : ''}</div>
      </div>
      <div class="session-actions">
        ${s.is_completed ? '<span class="badge badge-success">✓</span>' : ''}
        ${s.is_missed ? '<span class="badge badge-danger">Пропущено</span>' : ''}
        ${showComplete && !s.is_completed && !s.is_missed && s.type === 'course_session' ? `
          <button class="btn btn-sm btn-success" onclick="SchedulePage.completeSessionFromHome(${s.id})">
            ✓
          </button>` : ''}
      </div>
    </div>`;
}

window.HomePage = HomePage;
window.renderSessionItem = renderSessionItem;
