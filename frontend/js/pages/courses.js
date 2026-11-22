/**
 * Courses page — list, add, detail with sessions.
 */
const CoursesPage = {
  async render() {
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const courses = await API.getCourses();
      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <div>
              <h1 class="page-title">🎓 Мої курси</h1>
              <div class="page-subtitle">${courses.length} ${courses.length === 1 ? 'курс' : 'курсів'}</div>
            </div>
            <button class="btn btn-primary btn-sm" onclick="CoursesPage._showAddModal()">+ Курс</button>
          </div>
          ${courses.length === 0
            ? `<div class="empty-state">
                 <div class="empty-state-icon">🎓</div>
                 <div class="empty-state-title">Курсів ще немає</div>
                 <div class="empty-state-text">Додай перший курс з Prometheus, Coursera або іншої платформи</div>
                 <button class="btn btn-primary" style="margin-top:16px" onclick="CoursesPage._showAddModal()">
                   Додати курс
                 </button>
               </div>`
            : `<div>${courses.map(c => renderCourseCard(c)).join('')}</div>`
          }
        </div>`;
    } catch (err) { content.innerHTML = renderError(err); }
  },

  _showAddModal() {
    const today = new Date().toISOString().split('T')[0];
    showModal(`
      <div class="modal-title">Новий курс</div>
      <div class="form-group">
        <label class="form-label">Назва курсу *</label>
        <input type="text" id="c-name" class="form-input" placeholder="Python для початківців" />
      </div>
      <div class="form-group">
        <label class="form-label">Посилання</label>
        <input type="url" id="c-url" class="form-input" placeholder="https://prometheus.org.ua/..." />
      </div>
      <div class="form-group">
        <label class="form-label">Загальна тривалість (год) *</label>
        <input type="number" id="c-hours" class="form-input" placeholder="12" min="0.5" step="0.5" />
      </div>
      <div class="form-group">
        <label class="form-label">Годин на тиждень</label>
        <input type="number" id="c-weekly" class="form-input" placeholder="4" min="0.5" step="0.5" value="4" />
      </div>
      <div class="form-group">
        <label class="form-label">Дедлайн (необов'язково)</label>
        <input type="date" id="c-deadline" class="form-input" min="${today}" />
      </div>
      <div class="form-group">
        <label class="form-label">Опис</label>
        <textarea id="c-desc" class="form-textarea" placeholder="Додатковий опис..."></textarea>
      </div>
      <div style="background:var(--bg-elevated); padding:10px 12px; border-radius:var(--radius-md); font-size:12px; color:var(--text-secondary); margin-bottom:var(--space-md); border-left:3px solid var(--color-primary);">
        💡 Розклад занять буде складено автоматично за твоїм <b>базовим графіком</b> (обрані дні та час). Змінити графік можна у вкладці «Розклад».
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" style="flex:1" onclick="closeModal()">Скасувати</button>
        <button class="btn btn-primary" style="flex:1" onclick="CoursesPage._saveCourse()">Зберегти</button>
      </div>`);
  },

  async _saveCourse() {
    const name = document.getElementById('c-name').value.trim();
    const url = document.getElementById('c-url').value.trim();
    const hours = parseFloat(document.getElementById('c-hours').value);
    const weekly = parseFloat(document.getElementById('c-weekly').value);
    const deadlineVal = document.getElementById('c-deadline').value;
    const desc = document.getElementById('c-desc').value.trim();

    if (!name) { showToast('Введи назву курсу', 'error'); return; }
    if (isNaN(hours) || hours <= 0) { showToast('Введи тривалість курсу', 'error'); return; }

    const saveBtn = document.querySelector('.modal-actions .btn-primary');
    if (saveBtn) saveBtn.disabled = true;

    try {
      const course = await API.createCourse({
        name,
        url: url || null,
        total_hours: hours,
        hours_per_week: isNaN(weekly) ? 4 : weekly,
        deadline: deadlineVal ? new Date(deadlineVal + 'T23:59:00').toISOString() : null,
        description: desc || null,
      });
      closeModal();
      showToast('Курс додано!', 'success');

      // Auto-generate schedule
      try {
        const result = await API.generateSchedule(course.id);
        if (result?.warning) {
          showToast(result.warning, 'warning');
        } else if (result) {
          showToast(`Розклад створено: ${result.sessions_created} занять 📅`, 'success');
        }
      } catch (schedErr) {
        showToast('Курс додано, але розклад не вдалося створити: ' + schedErr.message, 'warning');
      }

      await this.render();
    } catch (err) {
      showToast(err.message, 'error');
      if (saveBtn) saveBtn.disabled = false;
    }
  },

  async _openDetail(courseId) {
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const [sessions, progress] = await Promise.all([
        API.getCourseSessions(courseId),
        API.getCourseProgress(courseId),
      ]);

      const pct = progress.time_progress_percent || 0;
      const manualPct = progress.manual_progress_percent;

      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <button class="btn back-btn" onclick="CoursesPage.render()">‹</button>
            <div>
              <h1 class="page-title" style="font-size:18px">${escHtml(progress.course_name)}</h1>
            </div>
          </div>

          <!-- Progress card -->
          <div class="card" style="margin-bottom:var(--space-lg)">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:var(--space-md)">
              <div>
                <div style="font-size:13px;color:var(--text-muted)">За витраченим часом</div>
                <div style="font-size:28px;font-weight:700">${pct.toFixed(0)}%</div>
                <div style="font-size:12px;color:var(--text-secondary)">${progress.completed_hours.toFixed(1)} / ${progress.total_hours} год</div>
              </div>
              ${manualPct != null ? `
              <div style="text-align:right">
                <div style="font-size:13px;color:var(--text-muted)">Ваша оцінка</div>
                <div style="font-size:28px;font-weight:700;color:var(--color-success)">${manualPct.toFixed(0)}%</div>
              </div>` : ''}
            </div>
            ${ProgressBar.render(pct, { color: 'auto', animated: true })}
            <div style="display:flex;gap:8px;margin-top:var(--space-md);flex-wrap:wrap">
              <span class="badge badge-success">✓ ${progress.completed_sessions} виконано</span>
              <span class="badge">${progress.total_sessions} всього</span>
              ${progress.missed_sessions > 0 ? `<span class="badge badge-danger">! ${progress.missed_sessions} пропущено</span>` : ''}
            </div>
            <div style="display:flex;gap:8px;margin-top:var(--space-md)">
              <button class="btn btn-secondary btn-sm" style="flex:1"
                onclick="CoursesPage._setManualProgress(${courseId})">
                Оновити % пройденого
              </button>
              <button class="btn btn-secondary btn-sm" style="flex:1"
                onclick="CoursesPage._regenerateSchedule(${courseId})">
                ↺ Перепланувати
              </button>
            </div>
          </div>

          <!-- Sessions -->
          <div class="section-header">
            <span class="section-title">Заняття</span>
            <span class="badge">${sessions.length}</span>
          </div>

          <div id="sessions-list">
            ${sessions.length === 0
              ? `<div class="empty-state">
                   <div class="empty-state-icon">📅</div>
                   <div class="empty-state-title">Занять не заплановано</div>
                 </div>`
              : sessions.map(s => renderCourseSession(s)).join('')
            }
          </div>
        </div>`;

      ProgressBar.animateAll(content);
    } catch (err) { content.innerHTML = renderError(err); }
  },

  async _regenerateSchedule(courseId) {
    if (!confirm('Перепланувати незавершені заняття?')) return;
    try {
      const result = await API.generateSchedule(courseId);
      if (result?.warning) showToast(result.warning, 'warning');
      else showToast(`Розклад оновлено: ${result.sessions_created} занять`, 'success');
      await this._openDetail(courseId);
    } catch (err) { showToast(err.message, 'error'); }
  },

  _setManualProgress(courseId) {
    showModal(`
      <div class="modal-title">% пройденого матеріалу</div>
      <p style="font-size:14px;color:var(--text-secondary);margin-bottom:var(--space-md);line-height:1.6">
        Скільки відсотків курсу реально пройдено? Це ваша власна оцінка, незалежно від витраченого часу.
      </p>
      <div class="form-group">
        <label class="form-label">Відсоток (0–100)</label>
        <input type="number" id="manual-pct" class="form-input" placeholder="50" min="0" max="100" />
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" style="flex:1" onclick="closeModal()">Скасувати</button>
        <button class="btn btn-primary" style="flex:1" onclick="CoursesPage._saveManualProgress(${courseId})">Зберегти</button>
      </div>`);
  },

  async _saveManualProgress(courseId) {
    const pct = parseFloat(document.getElementById('manual-pct').value);
    if (isNaN(pct) || pct < 0 || pct > 100) {
      showToast('Введи відсоток від 0 до 100', 'error'); return;
    }
    try {
      await API.setManualProgress(courseId, { manual_progress_percent: pct });
      closeModal();
      showToast('Прогрес оновлено! ✓', 'success');
      await this._openDetail(courseId);
    } catch (err) { showToast(err.message, 'error'); }
  },
};

function renderCourseCard(c) {
  return `
    <div class="card" style="margin-bottom:var(--space-md);cursor:pointer"
      onclick="CoursesPage._openDetail(${c.id})">
      <div class="card-header">
        <div>
          <div class="card-title">${escHtml(c.name)}</div>
          <div class="card-subtitle">${c.total_hours} год · ${c.hours_per_week} год/тиждень</div>
        </div>
        <span style="color:var(--text-muted)">›</span>
      </div>
      ${c.deadline ? `
        <div style="font-size:12px;color:var(--color-warning);margin-bottom:8px">
          ⏰ Дедлайн: ${formatDate(new Date(c.deadline))}
        </div>` : ''}
      ${c.url ? `
        <a href="${escHtml(c.url)}" target="_blank" class="badge badge-primary"
           onclick="event.stopPropagation()">
          🔗 Відкрити курс
        </a>` : ''}
    </div>`;
}

function renderCourseSession(s) {
  const dt = new Date(s.scheduled_at);
  const day = dt.getDate();
  const month = dt.toLocaleString('uk-UA', { month: 'short' });
  const time = dt.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
  const statusClass = s.is_completed ? 'completed' : s.is_missed ? 'missed' : '';
  const elemId = `cs-${s.id}`;
  return `
    <div class="session-item ${statusClass}" id="${elemId}">
      <div class="session-date-col">
        <div class="session-day">${day}</div>
        <div class="session-month">${month}</div>
      </div>
      <div class="session-info">
        <div class="session-title">${s.is_completed ? '✓ ' : ''}${s.planned_minutes} хв</div>
        <div class="session-meta">${time}${s.is_missed ? ' · Пропущено' : ''}${s.is_completed ? ` · Виконано ${s.actual_minutes || s.planned_minutes} хв` : ''}${s.is_rescheduled ? ' · Перенесено' : ''}</div>
      </div>
      <div class="session-actions">
        ${!s.is_completed && !s.is_missed ? `
          <button class="btn btn-sm btn-success"
            onclick="SchedulePage.completeSessionUI(${s.id}, '${elemId}')"
            title="Виконано">✓</button>
          <button class="btn btn-sm btn-secondary"
            onclick="SchedulePage.rescheduleUI(${s.id}, '${elemId}')"
            title="Перенести">↷</button>` : ''}
        ${s.is_missed ? `
          <button class="btn btn-sm btn-secondary"
            onclick="SchedulePage.rescheduleUI(${s.id}, '${elemId}')"
            title="Перенести">↷</button>` : ''}
        ${s.is_completed ? '<span class="badge badge-success">✓</span>' : ''}
      </div>
    </div>`;
}

window.CoursesPage = CoursesPage;
window.renderCourseCard = renderCourseCard;
window.renderCourseSession = renderCourseSession;
