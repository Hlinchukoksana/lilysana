/**
 * Schedule page — unified view of all sessions + NMT repetitions, grouped by date.
 */
const SchedulePage = {
  async render() {
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const [schedule, settings, busySlots] = await Promise.all([
        API.getSchedule(),
        API.getSettings().catch(() => ({ study_days: '0,1,2,3,4', preferred_start_hour: 18, preferred_start_minute: 0 })),
        API.getBusySlots().catch(() => []),
      ]);

      const grouped = groupByDate(schedule);
      const dateKeys = Object.keys(grouped).sort();

      const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'];
      const activeDays = (settings.study_days || '0,1,2,3,4')
        .split(',')
        .map(s => parseInt(s.trim()))
        .filter(n => !isNaN(n));

      const activeDaysLabels = activeDays.map(d => dayNames[d]).join(', ') || 'Не обрано';
      const startTimeStr = `${String(settings.preferred_start_hour ?? 18).padStart(2, '0')}:${String(settings.preferred_start_minute ?? 0).padStart(2, '0')}`;

      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <div>
              <h1 class="page-title">📅 Мій розклад</h1>
              <div class="page-subtitle">Наступні 30 днів · ${schedule.length} занять</div>
            </div>
          </div>

          <!-- Base Weekly Schedule Card -->
          <div class="card card-sm" style="margin-bottom:var(--space-lg); border-left: 3px solid var(--color-primary);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:700; font-size:15px; color:var(--text-primary)">🗓 Базовий графік на тиждень</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px">
                  ${activeDaysLabels} з <b>${startTimeStr}</b>
                </div>
              </div>
              <button class="btn btn-ghost btn-sm" id="sched-toggle-btn" onclick="SchedulePage.toggleScheduleSettings()">
                Змінити ▾
              </button>
            </div>

            <!-- Expandable edit form -->
            <div id="sched-edit-form" style="display:none; margin-top:var(--space-md); padding-top:var(--space-md); border-top:1px solid var(--border-subtle)">
              <div class="form-group">
                <label class="form-label" style="font-size:12px">Обери навчальні дні (натисни щоб увімкнути/вимкнути):</label>
                <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:4px;" id="sched-day-chips">
                  ${dayNames.map((name, idx) => {
                    const isActive = activeDays.includes(idx);
                    return `<button type="button" class="chip ${isActive ? 'active' : ''}" data-day="${idx}" onclick="SchedulePage.toggleDayChip(this)">${name}</button>`;
                  }).join('')}
                </div>
                <div class="form-hint" style="font-size:11px">AI підлаштовуватиме всі курси та НМТ виключно під ці дні</div>
              </div>

              <div class="form-group">
                <label class="form-label" style="font-size:12px">Зручний час початку занять:</label>
                <div style="display:flex; gap:var(--space-sm); align-items:center;">
                  <select id="sched-start-hour" class="form-select" style="max-width:130px;">
                    ${Array.from({length: 16}, (_, i) => i + 7).map(h => `
                      <option value="${h}" ${(settings.preferred_start_hour ?? 18) === h ? 'selected' : ''}>
                        ${String(h).padStart(2, '0')}:00
                      </option>
                    `).join('')}
                  </select>
                  <select id="sched-start-minute" class="form-select" style="max-width:110px;">
                    <option value="0" ${(settings.preferred_start_minute ?? 0) === 0 ? 'selected' : ''}>00 хв</option>
                    <option value="15" ${(settings.preferred_start_minute ?? 0) === 15 ? 'selected' : ''}>15 хв</option>
                    <option value="30" ${(settings.preferred_start_minute ?? 0) === 30 ? 'selected' : ''}>30 хв</option>
                    <option value="45" ${(settings.preferred_start_minute ?? 0) === 45 ? 'selected' : ''}>45 хв</option>
                  </select>
                </div>
              </div>

              <div style="display:flex; gap:var(--space-sm); flex-wrap:wrap;">
                <button class="btn btn-primary btn-sm" style="flex:1" onclick="SchedulePage.saveSchedulePrefs()">
                  Зберегти графік ✓
                </button>
                <button class="btn btn-ghost btn-sm" onclick="SettingsPage.openAddBusyModal()">
                  🚫 Заблокувати зайнятий час
                </button>
              </div>
            </div>
          </div>

          <div id="schedule-list">
            ${dateKeys.length === 0
              ? `<div class="empty-state">
                   <div class="empty-state-icon">📅</div>
                   <div class="empty-state-title">Розклад вільний</div>
                   <div class="empty-state-text">Додай курс або тему НМТ, і AI автоматично розмістить їх за твоїм графіком (${activeDaysLabels})</div>
                 </div>`
              : dateKeys.map(date => `
                  <div style="margin-bottom:var(--space-lg)">
                    <div class="section-title" style="margin-bottom:var(--space-sm)">
                      ${formatDateLong(new Date(date + 'T12:00:00'))}
                    </div>
                    ${grouped[date].map(s => renderScheduleItem(s)).join('')}
                  </div>`).join('')
            }
          </div>
        </div>`;
    } catch (err) { content.innerHTML = renderError(err); }
  },

  toggleScheduleSettings() {
    const form = document.getElementById('sched-edit-form');
    const btn = document.getElementById('sched-toggle-btn');
    if (!form) return;
    const isHidden = form.style.display === 'none';
    form.style.display = isHidden ? 'block' : 'none';
    if (btn) btn.textContent = isHidden ? 'Згорнути ▴' : 'Змінити ▾';
  },

  toggleDayChip(btn) {
    btn.classList.toggle('active');
  },

  async saveSchedulePrefs() {
    const activeBtns = document.querySelectorAll('#sched-day-chips .chip.active');
    const selectedDays = Array.from(activeBtns).map(b => b.dataset.day);
    if (selectedDays.length === 0) {
      showToast('Обери хоча б один день для навчання', 'error');
      return;
    }
    const hour = parseInt(document.getElementById('sched-start-hour').value);
    const minute = parseInt(document.getElementById('sched-start-minute').value);

    try {
      await API.updateSettings({
        study_days: selectedDays.join(','),
        preferred_start_hour: hour,
        preferred_start_minute: minute,
      });
      showToast('Базовий графік оновлено! ✓', 'success');
      await this.render();
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async completeSessionUI(sessionId, elemId) {
    const actualStr = prompt('Скільки хвилин зайняло заняття? (Enter = за планом)');
    const actual = actualStr && !isNaN(parseInt(actualStr)) ? parseInt(actualStr) : null;
    try {
      await API.completeSession(sessionId, actual ? { actual_minutes: actual } : {});
      showToast('Заняття виконано! 🎉', 'success');
      const el = document.getElementById(elemId);
      if (el) {
        el.classList.remove('missed');
        el.classList.add('completed');
        el.querySelector('.session-actions').innerHTML =
          '<span class="badge badge-success">✓ Виконано</span>';
      }
    } catch (err) {
      showToast(err.message === 'Заняття вже відмічено як виконане'
        ? 'Вже виконано' : err.message, 'error');
    }
  },

  async completeSessionFromHome(sessionId) {
    await this.completeSessionUI(sessionId, `session-course_session-${sessionId}`);
  },

  async rescheduleUI(sessionId, elemId) {
    const dateStr = prompt('Нова дата (РРРР-ММ-ДД):');
    if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      if (dateStr !== null) showToast('Невірний формат дати (потрібно РРРР-ММ-ДД)', 'error');
      return;
    }
    const timeStr = prompt('Час (ГГ:ХХ):', '10:00') || '10:00';
    const newDate = new Date(`${dateStr}T${timeStr}:00`);
    if (isNaN(newDate.getTime())) { showToast('Невірна дата або час', 'error'); return; }
    if (newDate <= new Date()) { showToast('Дата має бути в майбутньому', 'error'); return; }
    try {
      await API.rescheduleSession(sessionId, newDate.toISOString());
      showToast('Заняття перенесено! 📅', 'success');
      // Reload schedule
      await this.render();
    } catch (err) { showToast(err.message, 'error'); }
  },

  async completeNMTRep(repId, elemId) {
    try {
      await API.completeRepetition(repId);
      showToast('Повторення виконано! 🎯', 'success');
      const el = document.getElementById(elemId);
      if (el) {
        el.classList.add('completed');
        el.querySelector('.session-actions').innerHTML =
          '<span class="badge badge-success">✓ Виконано</span>';
      }
    } catch (err) { showToast(err.message, 'error'); }
  },
};

function renderScheduleItem(s) {
  const dt = new Date(s.scheduled_at);
  const day = dt.getDate();
  const month = dt.toLocaleString('uk-UA', { month: 'short' });
  const time = dt.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
  const icon = s.type === 'nmt_repetition' ? '🎯' : '🎓';
  const statusClass = s.is_completed ? 'completed' : s.is_missed ? 'missed' : '';
  const elemId = `sched-${s.type}-${s.id}`;

  return `
    <div class="session-item ${statusClass}" id="${elemId}">
      <div class="session-date-col">
        <div class="session-day">${day}</div>
        <div class="session-month">${month}</div>
      </div>
      <div class="session-info">
        <div class="session-title">${icon} ${escHtml(s.title)}</div>
        <div class="session-meta">${time} · ${s.duration_minutes} хв${s.subtitle ? ' · ' + escHtml(s.subtitle) : ''}</div>
      </div>
      <div class="session-actions">
        ${s.is_completed ? '<span class="badge badge-success">✓</span>' : ''}
        ${s.is_missed ? '<span class="badge badge-danger">Пропущено</span>' : ''}
        ${!s.is_completed && !s.is_missed ? `
          ${s.type === 'course_session' ? `
            <button class="btn btn-sm btn-success"
              onclick="SchedulePage.completeSessionUI(${s.id}, '${elemId}')"
              title="Виконано">✓</button>
            <button class="btn btn-sm btn-secondary"
              onclick="SchedulePage.rescheduleUI(${s.id}, '${elemId}')"
              title="Перенести">↷</button>` : ''}
          ${s.type === 'nmt_repetition' ? `
            <button class="btn btn-sm btn-success"
              onclick="SchedulePage.completeNMTRep(${s.id}, '${elemId}')"
              title="Виконано">✓</button>` : ''}
        ` : ''}
      </div>
    </div>`;
}

function groupByDate(items) {
  const groups = {};
  items.forEach(item => {
    const dateKey = item.scheduled_at.split('T')[0];
    if (!groups[dateKey]) groups[dateKey] = [];
    groups[dateKey].push(item);
  });
  return groups;
}

window.SchedulePage = SchedulePage;
window.renderScheduleItem = renderScheduleItem;
window.groupByDate = groupByDate;
