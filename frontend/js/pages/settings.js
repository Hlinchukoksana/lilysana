/**
 * Settings page — modules, limits, notifications, profile.
 */
const SettingsPage = {
  async render() {
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const [limits, settings, modules, user, busySlots] = await Promise.all([
        API.getLimits(),
        API.getSettings(),
        API.getModules(),
        API.getMe(),
        API.getBusySlots().catch(() => []),
      ]);

      const timeChoices = [
        { value: '1-2', label: '1–2 години на день' },
        { value: '3-5', label: '3–5 годин на день' },
        { value: '5-8', label: '5–8 годин на день' },
      ];

      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <div>
              <h1 class="page-title">⚙️ Налаштування</h1>
            </div>
          </div>

          <!-- Active Modules -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">Активні модулі</div>
            <div class="card card-sm">
              <div class="toggle-row">
                <div>
                  <div class="toggle-label">🎯 НМТ</div>
                  <div class="toggle-desc">Підготовка до національного тесту</div>
                </div>
                <label class="toggle">
                  <input type="checkbox" id="mod-nmt" ${modules.nmt_enabled ? 'checked' : ''}
                    onchange="SettingsPage._saveModules()" />
                  <span class="toggle-slider"></span>
                </label>
              </div>
              <div class="toggle-row">
                <div>
                  <div class="toggle-label">🎓 Мої курси</div>
                  <div class="toggle-desc">Prometheus, Coursera та інші платформи</div>
                </div>
                <label class="toggle">
                  <input type="checkbox" id="mod-courses" ${modules.courses_enabled ? 'checked' : ''}
                    onchange="SettingsPage._saveModules()" />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>

          <!-- Personal Study Schedule -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">🗓 Мій власний графік навчання</div>
            <div class="card card-sm">
              <div class="form-group">
                <label class="form-label">У які дні ти навчаєшся?</label>
                <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:6px;" id="study-days-chips">
                  ${[
                    { d: 0, l: 'Пн' },
                    { d: 1, l: 'Вт' },
                    { d: 2, l: 'Ср' },
                    { d: 3, l: 'Чт' },
                    { d: 4, l: 'Пт' },
                    { d: 5, l: 'Сб' },
                    { d: 6, l: 'Нд' },
                  ].map(day => {
                    const activeDays = (settings.study_days || '0,1,2,3,4').split(',').map(s => parseInt(s.trim()));
                    const isActive = activeDays.includes(day.d);
                    return `<button type="button" class="chip ${isActive ? 'active' : ''}" data-day="${day.d}" onclick="SettingsPage.toggleDay(this)">${day.l}</button>`;
                  }).join('')}
                </div>
                <div class="form-hint">AI призначатиме заняття курсів та повторення НМТ тільки у ці дні</div>
              </div>

              <div class="form-group">
                <label class="form-label">Зручний час початку занять</label>
                <div style="display:flex; gap:var(--space-sm); align-items:center;">
                  <select id="study-hour" class="form-select" style="max-width:130px;">
                    ${Array.from({length: 16}, (_, i) => i + 7).map(h => `
                      <option value="${h}" ${(settings.preferred_start_hour ?? 18) === h ? 'selected' : ''}>
                        ${String(h).padStart(2, '0')}:00
                      </option>
                    `).join('')}
                  </select>
                  <select id="study-minute" class="form-select" style="max-width:110px;">
                    <option value="0" ${(settings.preferred_start_minute ?? 0) === 0 ? 'selected' : ''}>00 хв</option>
                    <option value="15" ${(settings.preferred_start_minute ?? 0) === 15 ? 'selected' : ''}>15 хв</option>
                    <option value="30" ${(settings.preferred_start_minute ?? 0) === 30 ? 'selected' : ''}>30 хв</option>
                    <option value="45" ${(settings.preferred_start_minute ?? 0) === 45 ? 'selected' : ''}>45 хв</option>
                  </select>
                </div>
                <div class="form-hint">Час, о котрій зазвичай починаються твої навчальні сесії</div>
              </div>

              <button class="btn btn-primary" style="width:100%" onclick="SettingsPage._saveStudySchedule()">
                Зберегти мій графік
              </button>
            </div>
          </div>

          <!-- Busy Slots (Unavailability) -->
          <div class="section">
            <div class="section-header" style="margin-bottom:var(--space-md)">
              <span class="section-title">🚫 Зайнятий час (школа, репетитор)</span>
              <button class="btn btn-ghost btn-sm" onclick="SettingsPage.openAddBusyModal()">+ Додати</button>
            </div>
            <div class="card card-sm">
              <div id="busy-slots-container">
                ${busySlots.length === 0 ? `
                  <div style="color:var(--text-muted); font-size:13px; text-align:center; padding:var(--space-xs) 0">
                    Немає заблокованого часу. Всі обрані навчальні дні вільні.
                  </div>
                ` : busySlots.map(b => `
                  <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-subtle)">
                    <div>
                      <div style="font-weight:600; font-size:14px">${escHtml(b.label || 'Зайнятий час')}</div>
                      <div style="font-size:12px; color:var(--text-secondary)">
                        ${b.day_of_week != null ? ['Пн','Вт','Ср','Чт','Пт','Сб','Нд'][b.day_of_week] : 'Одноразово'},
                        ${String(b.start_hour).padStart(2,'0')}:${String(b.start_minute).padStart(2,'0')} (${b.duration_minutes} хв)
                      </div>
                    </div>
                    <button class="btn btn-danger btn-sm" onclick="SettingsPage.deleteBusySlot(${b.id})">✕</button>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>

          <!-- Learning time preference -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">Час на навчання</div>
            <div class="card card-sm">
              <div class="form-group" style="margin-bottom:0">
                <label class="form-label">Скільки часу на день готовий(-а) навчатися?</label>
                <select id="time-choice" class="form-select" onchange="SettingsPage._saveTimeChoice()">
                  ${timeChoices.map(c => `
                    <option value="${c.value}" ${user.learning_time_choice === c.value ? 'selected' : ''}>
                      ${c.label}
                    </option>`).join('')}
                </select>
                <div class="form-hint">Це орієнтир для планування, а не обов'язкова норма</div>
              </div>
            </div>
          </div>

          <!-- Learning Limits -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">Навчальні ліміти</div>
            <div class="card card-sm">
              <div class="form-group">
                <label class="form-label">НМТ — годин на тиждень</label>
                <input type="number" id="lim-nmt" class="form-input"
                  value="${limits.nmt_hours_per_week}" min="0" max="40" step="0.5" />
              </div>
              <div class="form-group">
                <label class="form-label">Курси — годин на тиждень</label>
                <input type="number" id="lim-courses" class="form-input"
                  value="${limits.course_hours_per_week}" min="0" max="40" step="0.5" />
              </div>
              <div class="form-group">
                <label class="form-label">Денний орієнтир (хвилин)</label>
                <input type="number" id="lim-daily" class="form-input"
                  value="${limits.daily_limit_minutes}" min="30" max="720" step="30" />
              </div>
              <div class="form-group">
                <label class="form-label">Резерв часу (%)</label>
                <input type="number" id="lim-reserve" class="form-input"
                  value="${limits.reserve_percent}" min="0" max="50" />
                <div class="form-hint">Залишати незаповненим для відпочинку та несподіваних справ</div>
              </div>
              <button class="btn btn-primary" style="width:100%" onclick="SettingsPage._saveLimits()">
                Зберегти ліміти
              </button>
            </div>
          </div>

          <!-- Notifications -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">Сповіщення</div>
            <div class="card card-sm">
              <div class="toggle-row">
                <div>
                  <div class="toggle-label">Нагадування увімкнено</div>
                </div>
                <label class="toggle">
                  <input type="checkbox" id="notif-enabled"
                    ${settings.reminders_enabled ? 'checked' : ''}
                    onchange="SettingsPage._saveSettings()" />
                  <span class="toggle-slider"></span>
                </label>
              </div>
              <div class="toggle-row">
                <div>
                  <div class="toggle-label">НМТ повторення</div>
                  <div class="toggle-desc">Нагадувати про заплановані повторення</div>
                </div>
                <label class="toggle">
                  <input type="checkbox" id="notif-nmt"
                    ${settings.nmt_reminders ? 'checked' : ''}
                    onchange="SettingsPage._saveSettings()" />
                  <span class="toggle-slider"></span>
                </label>
              </div>
              <div class="toggle-row">
                <div>
                  <div class="toggle-label">Зміни в розкладі</div>
                  <div class="toggle-desc">Сповіщати про перенесені або нові заняття</div>
                </div>
                <label class="toggle">
                  <input type="checkbox" id="notif-schedule"
                    ${settings.schedule_change_notifications ? 'checked' : ''}
                    onchange="SettingsPage._saveSettings()" />
                  <span class="toggle-slider"></span>
                </label>
              </div>
              <div class="form-group" style="margin-top:var(--space-md);margin-bottom:0">
                <label class="form-label">Нагадувати за (хвилин)</label>
                <select id="notif-before" class="form-select" onchange="SettingsPage._saveSettings()">
                  <option value="10" ${settings.reminder_before_min === 10 ? 'selected' : ''}>10 хвилин</option>
                  <option value="15" ${settings.reminder_before_min === 15 ? 'selected' : ''}>15 хвилин</option>
                  <option value="30" ${settings.reminder_before_min === 30 ? 'selected' : ''}>30 хвилин</option>
                  <option value="60" ${settings.reminder_before_min === 60 ? 'selected' : ''}>1 година</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Profile info -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">Профіль</div>
            <div class="card card-sm">
              <div style="font-size:15px;font-weight:500">${escHtml(user.first_name || '')}${user.last_name ? ' ' + escHtml(user.last_name) : ''}</div>
              ${user.username ? `<div style="font-size:13px;color:var(--text-secondary);margin-top:3px">@${escHtml(user.username)}</div>` : ''}
              <div class="divider"></div>
              <div style="font-size:12px;color:var(--text-muted)">ID: ${user.id}</div>
              <div style="font-size:12px;color:var(--text-muted)">Часовий пояс: ${user.timezone || 'UTC'}</div>
              <div style="font-size:12px;color:var(--text-muted)">Зареєстровано: ${formatDate(new Date(user.created_at))}</div>
            </div>
          </div>

          <div style="height:var(--space-lg)"></div>
        </div>`;
    } catch (err) { content.innerHTML = renderError(err); }
  },

  async _saveModules() {
    try {
      const updatedModules = await API.updateModules({
        nmt_enabled: document.getElementById('mod-nmt').checked,
        courses_enabled: document.getElementById('mod-courses').checked,
      });
      Navbar.updateModuleVisibility(updatedModules);
      showToast('Модулі оновлено ✓', 'success');
    } catch (err) { showToast(err.message, 'error'); }
  },

  async _saveTimeChoice() {
    const choice = document.getElementById('time-choice').value;
    try {
      await API.completeOnboarding({ learning_time_choice: choice });
      showToast('Вибір збережено ✓', 'success');
    } catch (err) { showToast(err.message, 'error'); }
  },

  async _saveLimits() {
    const nmt = parseFloat(document.getElementById('lim-nmt').value);
    const courses = parseFloat(document.getElementById('lim-courses').value);
    const daily = parseInt(document.getElementById('lim-daily').value);
    const reserve = parseInt(document.getElementById('lim-reserve').value);

    if ([nmt, courses, daily, reserve].some(v => isNaN(v) || v < 0)) {
      showToast('Перевір значення лімітів', 'error'); return;
    }

    try {
      await API.updateLimits({
        nmt_hours_per_week: nmt,
        course_hours_per_week: courses,
        daily_limit_minutes: daily,
        reserve_percent: reserve,
      });
      showToast('Ліміти збережено! ✓', 'success');
    } catch (err) { showToast(err.message, 'error'); }
  },

  async _saveSettings() {
    try {
      await API.updateSettings({
        reminders_enabled: document.getElementById('notif-enabled').checked,
        nmt_reminders: document.getElementById('notif-nmt').checked,
        schedule_change_notifications: document.getElementById('notif-schedule').checked,
        reminder_before_min: parseInt(document.getElementById('notif-before').value),
      });
      showToast('Налаштування збережено ✓', 'success');
    } catch (err) { showToast(err.message, 'error'); }
  },

  toggleDay(btn) {
    btn.classList.toggle('active');
  },

  async _saveStudySchedule() {
    const activeBtns = document.querySelectorAll('#study-days-chips .chip.active');
    const selectedDays = Array.from(activeBtns).map(b => b.dataset.day);
    if (selectedDays.length === 0) {
      showToast('Обери хоча б один навчальний день', 'error');
      return;
    }
    const hour = parseInt(document.getElementById('study-hour').value);
    const minute = parseInt(document.getElementById('study-minute').value);

    try {
      await API.updateSettings({
        study_days: selectedDays.join(','),
        preferred_start_hour: hour,
        preferred_start_minute: minute,
      });
      showToast('Графік навчання збережено! ✓', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  openAddBusyModal() {
    const days = [
      { d: 0, l: 'Понеділок' },
      { d: 1, l: 'Вівторок' },
      { d: 2, l: 'Середа' },
      { d: 3, l: 'Четвер' },
      { d: 4, l: 'Пʼятниця' },
      { d: 5, l: 'Субота' },
      { d: 6, l: 'Неділя' },
    ];
    Modal.open(`
      <div class="modal-title">🚫 Додати зайнятий час</div>
      <form id="busy-form" onsubmit="SettingsPage._submitBusySlot(event)">
        <div class="form-group">
          <label class="form-label">Назва (наприклад: Школа, Репетитор, Спорт)</label>
          <input type="text" id="busy-label" class="form-input" placeholder="Школа" required />
        </div>
        <div class="form-group">
          <label class="form-label">День тижня</label>
          <select id="busy-day" class="form-select">
            ${days.map(d => `<option value="${d.d}">${d.l}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Час початку (година)</label>
          <div style="display:flex; gap:var(--space-sm);">
            <select id="busy-hour" class="form-select">
              ${Array.from({length: 24}, (_, i) => `<option value="${i}">${String(i).padStart(2,'0')}:00</option>`).join('')}
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Тривалість (хвилин)</label>
          <input type="number" id="busy-duration" class="form-input" value="60" min="15" max="480" step="15" required />
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" onclick="Modal.close()">Скасувати</button>
          <button type="submit" class="btn btn-primary" style="flex:1">Додати</button>
        </div>
      </form>
    `);
  },

  async _submitBusySlot(e) {
    e.preventDefault();
    const label = document.getElementById('busy-label').value.trim();
    const day = parseInt(document.getElementById('busy-day').value);
    const hour = parseInt(document.getElementById('busy-hour').value);
    const duration = parseInt(document.getElementById('busy-duration').value);

    try {
      await API.createBusySlot({
        label,
        day_of_week: day,
        start_hour: hour,
        start_minute: 0,
        duration_minutes: duration,
        is_recurring: true,
      });
      Modal.close();
      showToast('Зайнятий час додано ✓', 'success');
      SettingsPage.render();
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async deleteBusySlot(id) {
    if (!confirm('Видалити цей заблокований час?')) return;
    try {
      await API.deleteBusySlot(id);
      showToast('Видалено ✓', 'success');
      SettingsPage.render();
    } catch (err) {
      showToast(err.message, 'error');
    }
  },
};

window.SettingsPage = SettingsPage;
