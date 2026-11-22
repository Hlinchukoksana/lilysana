/**
 * NMT Tracker page.
 * Flow: Subjects list → Topics list → Tests list → Test detail (history + add result)
 */
const NMTPage = {
  _selectedSubject: null,
  _selectedTopic: null,
  _selectedTest: null,

  async render() {
    await this._renderSubjects();
  },

  async _renderSubjects() {
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const subjects = await API.getSubjects();
      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <div>
              <h1 class="page-title">🎯 НМТ</h1>
              <div class="page-subtitle">Оберіть предмет</div>
            </div>
          </div>
          <div>
            ${subjects.length === 0
              ? `<div class="empty-state">
                   <div class="empty-state-icon">📚</div>
                   <div class="empty-state-title">Предмети не додані</div>
                   <div class="empty-state-text">Натисни «+ Додати предмет», щоб розпочати</div>
                 </div>`
              : subjects.map(s => `
                <div class="list-item" onclick="NMTPage._openTopics(${s.id}, '${escHtml(s.name)}')" style="cursor:pointer">
                  <span class="list-item-icon">${getSubjectEmoji(s.name)}</span>
                  <div class="list-item-content">
                    <div class="list-item-title">${escHtml(s.name)}</div>
                    <div class="list-item-subtitle">${s.is_optional ? 'Вибірковий предмет' : "Обов'язковий предмет"}</div>
                  </div>
                  <span style="color:var(--text-muted)">›</span>
                </div>`).join('')
            }
          </div>
          <div style="margin-top:var(--space-lg)">
            <button class="btn btn-secondary" style="width:100%" onclick="NMTPage._showAddSubjectModal()">
              + Додати предмет
            </button>
          </div>
        </div>`;
    } catch (err) { content.innerHTML = renderError(err); }
  },

  async _openTopics(subjectId, subjectName) {
    this._selectedSubject = { id: subjectId, name: subjectName };
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const topics = await API.getTopics(subjectId);
      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <button class="btn back-btn" onclick="NMTPage._renderSubjects()">‹</button>
            <div>
              <h1 class="page-title">${escHtml(subjectName)}</h1>
              <div class="page-subtitle">Теми</div>
            </div>
          </div>
          <div>
            ${topics.length === 0
              ? `<div class="empty-state">
                   <div class="empty-state-icon">📝</div>
                   <div class="empty-state-title">Тем ще немає</div>
                   <div class="empty-state-text">Додай першу тему для цього предмету</div>
                 </div>`
              : topics.map(t => `
                <div class="list-item" onclick="NMTPage._openTests(${t.id}, '${escHtml(t.name)}')" style="cursor:pointer">
                  <span class="list-item-icon">📝</span>
                  <div class="list-item-content">
                    <div class="list-item-title">${escHtml(t.name)}</div>
                    <div class="list-item-subtitle">${formatDate(new Date(t.created_at))}</div>
                  </div>
                  <span style="color:var(--text-muted)">›</span>
                </div>`).join('')
            }
          </div>
          <div style="margin-top:var(--space-lg)">
            <button class="btn btn-secondary" style="width:100%" onclick="NMTPage._showAddTopicModal(${subjectId})">
              + Додати тему
            </button>
          </div>
        </div>`;
    } catch (err) { content.innerHTML = renderError(err); }
  },

  async _openTests(topicId, topicName) {
    this._selectedTopic = { id: topicId, name: topicName };
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const tests = await API.getTests(topicId);
      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <button class="btn back-btn" onclick="NMTPage._openTopics(${this._selectedSubject.id}, '${escHtml(this._selectedSubject.name)}')">‹</button>
            <div>
              <h1 class="page-title">${escHtml(topicName)}</h1>
              <div class="page-subtitle">Тести</div>
            </div>
          </div>
          <div>
            ${tests.length === 0
              ? `<div class="empty-state">
                   <div class="empty-state-icon">📋</div>
                   <div class="empty-state-title">Тестів ще немає</div>
                   <div class="empty-state-text">Додай перший тест для цієї теми</div>
                 </div>`
              : tests.map(t => `
                <div class="list-item" onclick="NMTPage._openTestDetail(${t.id}, '${escHtml(t.name)}', '${escHtml(t.url || '')}')" style="cursor:pointer">
                  <span class="list-item-icon">📋</span>
                  <div class="list-item-content">
                    <div class="list-item-title">${escHtml(t.name)}</div>
                    <div class="list-item-subtitle">${t.url ? '🔗 Є посилання' : 'Без посилання'}</div>
                  </div>
                  <span style="color:var(--text-muted)">›</span>
                </div>`).join('')
            }
          </div>
          <div style="margin-top:var(--space-lg)">
            <button class="btn btn-secondary" style="width:100%" onclick="NMTPage._showAddTestModal(${topicId})">
              + Додати тест
            </button>
          </div>
        </div>`;
    } catch (err) { content.innerHTML = renderError(err); }
  },

  async _openTestDetail(testId, testName, testUrl) {
    this._selectedTest = { id: testId, name: testName, url: testUrl };
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const history = await API.getTestHistory(testId);
      const scores = history.results.map(r => r.score_percent);
      const dates = history.results.map(r => formatDate(new Date(r.taken_at)));

      const scoreColorClass = (s) => s <= 70 ? 'low' : s <= 94 ? 'mid' : 'high';

      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <button class="btn back-btn" onclick="NMTPage._openTests(${this._selectedTopic.id}, '${escHtml(this._selectedTopic.name)}')">‹</button>
            <div>
              <h1 class="page-title" style="font-size:18px">${escHtml(testName)}</h1>
              <div class="page-subtitle">${history.attempts} спроб${history.attempts === 1 ? 'а' : ''}</div>
            </div>
          </div>

          ${testUrl ? `
            <div class="card card-sm" style="margin-bottom:var(--space-md)">
              <div style="display:flex;align-items:center;justify-content:space-between">
                <span style="font-size:14px;color:var(--text-secondary)">🔗 Посилання на тест</span>
                <a href="${escHtml(testUrl)}" target="_blank" class="btn btn-primary btn-sm">Відкрити тест</a>
              </div>
            </div>` : ''}

          ${history.attempts > 0 ? `
            <div class="card" style="margin-bottom:var(--space-lg)">
              <div style="display:flex;gap:var(--space-lg);margin-bottom:var(--space-md)">
                <div class="score-circle ${scoreColorClass(history.last_score)}">
                  <span class="score-value">${history.last_score.toFixed(0)}</span>
                  <span class="score-unit">%</span>
                </div>
                <div>
                  <div style="font-size:13px;color:var(--text-muted)">Останній результат</div>
                  <div style="font-size:13px;margin-top:8px">🏆 Найкращий: <strong>${history.best_score.toFixed(0)}%</strong></div>
                  <div style="font-size:13px">🥇 Перший: <strong>${history.first_score.toFixed(0)}%</strong></div>
                  <div style="font-size:13px">${history.attempts} спроб загалом</div>
                </div>
              </div>
              ${Chart.render('chart', scores, dates)}
            </div>` : ''}

          <div class="card" style="margin-bottom:var(--space-md)">
            <div class="card-title" style="margin-bottom:var(--space-md)">Внести результат</div>
            <div class="form-group">
              <label class="form-label">Результат (%)</label>
              <input type="number" id="score-input" class="form-input"
                placeholder="0–100" min="0" max="100" step="1" />
              <div class="form-hint">Введи результат після проходження тесту</div>
            </div>
            <div class="form-group">
              <label class="form-label">Нотатки (необов'язково)</label>
              <textarea id="notes-input" class="form-textarea" placeholder="Коментар до результату..."></textarea>
            </div>
            <button class="btn btn-primary" style="width:100%" onclick="NMTPage._submitResult(${testId})">
              Зберегти результат
            </button>
          </div>

          <div id="recommendation-card" class="hidden"></div>
        </div>`;
    } catch (err) { content.innerHTML = renderError(err); }
  },

  async _submitResult(testId) {
    const scoreInput = document.getElementById('score-input');
    const notesInput = document.getElementById('notes-input');
    const score = parseFloat(scoreInput.value);

    if (isNaN(score) || score < 0 || score > 100) {
      showToast('Введи результат від 0 до 100', 'error');
      return;
    }

    const btn = document.querySelector('#add-result-card button, .card button[onclick*="submitResult"]');
    if (btn) btn.disabled = true;

    try {
      const { result, recommendation } = await API.addResult(testId, {
        score_percent: score,
        notes: notesInput.value.trim() || null,
      });

      showToast('Результат збережено! 🎉', 'success');
      scoreInput.value = '';
      notesInput.value = '';

      const recCard = document.getElementById('recommendation-card');
      recCard.classList.remove('hidden');
      recCard.innerHTML = renderRecommendation(recommendation, result.id);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async _showAddSubjectModal() {
    let optionalsHtml = '';
    try {
      const optionals = await API.getOptionalSubjects();
      optionalsHtml = optionals.subjects.map(s =>
        `<option value="${escHtml(s)}">${escHtml(s)}</option>`
      ).join('');
    } catch (_) {}

    showModal(`
      <div class="modal-title">Додати предмет</div>
      ${optionalsHtml ? `
        <div class="form-group">
          <label class="form-label">Вибір зі списку</label>
          <select id="subject-select" class="form-select">
            <option value="">— або введіть вручну —</option>
            ${optionalsHtml}
          </select>
        </div>` : ''}
      <div class="form-group">
        <label class="form-label">Назва предмету</label>
        <input type="text" id="subject-name-input" class="form-input" placeholder="Наприклад: Англійська мова" />
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" style="flex:1" onclick="closeModal()">Скасувати</button>
        <button class="btn btn-primary" style="flex:1" onclick="NMTPage._saveSubject()">Додати</button>
      </div>`);

    document.getElementById('subject-select')?.addEventListener('change', (e) => {
      if (e.target.value) document.getElementById('subject-name-input').value = e.target.value;
    });
  },

  async _saveSubject() {
    const name = document.getElementById('subject-name-input').value.trim();
    if (!name) { showToast('Введи назву предмету', 'error'); return; }
    try {
      await API.createSubject({ name, is_optional: true });
      closeModal();
      showToast('Предмет додано!', 'success');
      await this._renderSubjects();
    } catch (err) { showToast(err.message, 'error'); }
  },

  _showAddTopicModal(subjectId) {
    showModal(`
      <div class="modal-title">Нова тема</div>
      <div class="form-group">
        <label class="form-label">Назва теми</label>
        <input type="text" id="topic-name" class="form-input"
          placeholder="Наприклад: Козацька доба" autofocus />
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" style="flex:1" onclick="closeModal()">Скасувати</button>
        <button class="btn btn-primary" style="flex:1" onclick="NMTPage._saveTopic(${subjectId})">Додати</button>
      </div>`);
  },

  async _saveTopic(subjectId) {
    const name = document.getElementById('topic-name').value.trim();
    if (!name) { showToast('Введи назву теми', 'error'); return; }
    try {
      await API.createTopic(subjectId, { name });
      closeModal();
      showToast('Тему додано!', 'success');
      await this._openTopics(subjectId, this._selectedSubject?.name || '');
    } catch (err) { showToast(err.message, 'error'); }
  },

  _showAddTestModal(topicId) {
    showModal(`
      <div class="modal-title">Новий тест</div>
      <div class="form-group">
        <label class="form-label">Назва тесту</label>
        <input type="text" id="test-name" class="form-input" placeholder="Назва" autofocus />
      </div>
      <div class="form-group">
        <label class="form-label">Посилання (необов'язково)</label>
        <input type="url" id="test-url" class="form-input" placeholder="https://..." />
        <div class="form-hint">Вставте посилання на зовнішній тест</div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" style="flex:1" onclick="closeModal()">Скасувати</button>
        <button class="btn btn-primary" style="flex:1" onclick="NMTPage._saveTest(${topicId})">Додати</button>
      </div>`);
  },

  async _saveTest(topicId) {
    const name = document.getElementById('test-name').value.trim();
    const url = document.getElementById('test-url').value.trim();
    if (!name) { showToast('Введи назву тесту', 'error'); return; }
    try {
      await API.createTest(topicId, { name, url: url || null });
      closeModal();
      showToast('Тест додано!', 'success');
      await this._openTests(topicId, this._selectedTopic?.name || '');
    } catch (err) { showToast(err.message, 'error'); }
  },

  async _scheduleRepetition(resultId, choiceId) {
    try {
      await API.scheduleRepetition(resultId, { choice_id: choiceId });
      showToast('Повторення заплановано! 📅', 'success');
      const recCard = document.getElementById('recommendation-card');
      if (recCard) {
        recCard.insertAdjacentHTML('beforeend',
          `<div class="badge badge-success" style="margin-top:8px;display:inline-flex">✓ Заплановано</div>`);
      }
      // Disable schedule buttons
      recCard?.querySelectorAll('button[onclick*="scheduleRepetition"]').forEach(b => b.disabled = true);
    } catch (err) {
      const msg = err.message || '';
      showToast(msg.includes('вже') ? 'Вже заплановано' : err.message, 'error');
    }
  }
};

function renderRecommendation(rec, resultId) {
  const icons = { low: '📚', mid: '✨', high: '🏆' };
  const colors = {
    low: 'var(--color-warning)',
    mid: 'var(--color-primary-light)',
    high: 'var(--color-success)'
  };

  let actionsHtml = '';
  if (rec.user_choice_required && rec.choices) {
    actionsHtml = rec.choices.map(c => `
      <button class="btn btn-secondary" style="width:100%;margin-top:8px"
        onclick="NMTPage._scheduleRepetition(${resultId}, '${c.id}')">
        ${escHtml(c.label)}
      </button>`).join('');
  } else {
    actionsHtml = `
      <button class="btn btn-primary" style="width:100%;margin-top:12px"
        onclick="NMTPage._scheduleRepetition(${resultId}, null)">
        📅 Запланувати повторення
      </button>`;
  }

  return `
    <div class="card" style="border-color:${colors[rec.category] || colors.mid};margin-top:0">
      <div style="font-size:28px;margin-bottom:8px">${icons[rec.category] || '📚'}</div>
      <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin-bottom:var(--space-md)">
        ${escHtml(rec.message)}
      </p>
      ${rec.days_until_review && !rec.user_choice_required ? `
        <div style="font-size:13px;color:var(--text-muted);margin-bottom:8px">
          Рекомендоване повторення: через ${rec.days_until_review} дн. · ${rec.duration_minutes || 90} хв
        </div>` : ''}
      ${actionsHtml}
    </div>`;
}

function getSubjectEmoji(name) {
  if (!name) return '📚';
  if (name.includes('Матем')) return '📐';
  if (name.includes('Украї') && name.includes('мова')) return '🇺🇦';
  if (name.includes('Украї') && name.includes('літ')) return '📖';
  if (name.includes('Іст')) return '🏛';
  if (name.includes('Англ')) return '🇬🇧';
  if (name.includes('Біол')) return '🧬';
  if (name.includes('Хім')) return '🧪';
  if (name.includes('Геогр')) return '🌍';
  if (name.includes('Фіз')) return '⚡';
  return '📚';
}

window.NMTPage = NMTPage;
window.renderRecommendation = renderRecommendation;
window.getSubjectEmoji = getSubjectEmoji;
