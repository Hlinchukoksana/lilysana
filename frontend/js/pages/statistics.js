/**
 * Statistics page — overall learning progress and NMT results.
 */
const StatisticsPage = {
  async render() {
    const content = document.getElementById('page-content');
    content.innerHTML = `<div class="page"><div class="loading-spinner" style="margin:auto"></div></div>`;
    try {
      const stats = await API.getStatistics();
      const repPct = stats.nmt_repetitions_total > 0
        ? (stats.nmt_repetitions_completed / stats.nmt_repetitions_total * 100)
        : 0;

      content.innerHTML = `
        <div class="page animate-in">
          <div class="page-header">
            <div>
              <h1 class="page-title">📊 Статистика</h1>
              <div class="page-subtitle">Загальний прогрес</div>
            </div>
          </div>

          <!-- Study hours -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">Навчальні години</div>
            <div class="stat-grid">
              <div class="stat-card">
                <div class="stat-value">${stats.total_study_hours.toFixed(1)}</div>
                <div class="stat-label">год загалом</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${stats.week_hours_completed.toFixed(1)}</div>
                <div class="stat-label">год цього тижня</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${stats.week_hours_planned.toFixed(1)}</div>
                <div class="stat-label">год заплановано</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${stats.courses_active}</div>
                <div class="stat-label">активних курсів</div>
              </div>
            </div>
          </div>

          <!-- Session completion -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">Виконання занять</div>
            <div class="card card-sm">
              <div style="display:flex;justify-content:space-between;margin-bottom:10px">
                <span style="font-size:14px;color:var(--text-secondary)">Завершено</span>
                <span style="font-weight:600">${stats.completed_sessions} / ${stats.total_sessions}</span>
              </div>
              ${ProgressBar.render(stats.completion_rate_percent || 0, { color: 'auto', animated: true })}
              ${stats.missed_sessions > 0 ? `
                <div style="font-size:12px;color:var(--color-danger);margin-top:8px">
                  ⚠️ Пропущено занять: ${stats.missed_sessions}
                </div>` : ''}
            </div>
          </div>

          <!-- NMT scores -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">НМТ Результати</div>
            <div class="stat-grid">
              <div class="stat-card">
                <div class="stat-value" style="color:${stats.avg_nmt_score != null ? (stats.avg_nmt_score >= 71 ? 'var(--color-success)' : 'var(--color-warning)') : 'var(--text-muted)'}">
                  ${stats.avg_nmt_score != null ? stats.avg_nmt_score + '%' : '—'}
                </div>
                <div class="stat-label">середній бал</div>
              </div>
              <div class="stat-card">
                <div class="stat-value" style="color:var(--color-success)">
                  ${stats.best_nmt_score != null ? stats.best_nmt_score + '%' : '—'}
                </div>
                <div class="stat-label">найкращий бал</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${stats.nmt_tests_total || 0}</div>
                <div class="stat-label">тестів проведено</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${stats.nmt_subjects_active || 0}</div>
                <div class="stat-label">активних предметів</div>
              </div>
            </div>
            ${stats.avg_nmt_score != null ? `
              <div class="card card-sm" style="margin-top:var(--space-md)">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                  <span style="font-size:14px;color:var(--text-secondary)">Середній результат</span>
                  <span style="font-weight:600">${stats.avg_nmt_score}%</span>
                </div>
                ${ProgressBar.render(stats.avg_nmt_score, { color: 'auto', animated: true })}
              </div>` : ''}
          </div>

          <!-- NMT Repetitions -->
          <div class="section">
            <div class="section-title" style="margin-bottom:var(--space-md)">НМТ Повторення</div>
            <div class="card card-sm">
              <div style="display:flex;justify-content:space-between;margin-bottom:10px">
                <span style="font-size:14px;color:var(--text-secondary)">Виконано</span>
                <span style="font-weight:600">${stats.nmt_repetitions_completed} / ${stats.nmt_repetitions_total}</span>
              </div>
              ${ProgressBar.render(repPct, { color: 'success', animated: true })}
              ${stats.nmt_repetitions_pending > 0 ? `
                <div style="font-size:12px;color:var(--color-warning);margin-top:8px">
                  ⏳ Очікує: ${stats.nmt_repetitions_pending} повторень
                </div>` : ''}
            </div>
          </div>

          <!-- Streak / streak info -->
          ${stats.study_streak_days != null ? `
            <div class="section">
              <div class="section-title" style="margin-bottom:var(--space-md)">Серія</div>
              <div class="card card-sm" style="text-align:center;padding:var(--space-xl)">
                <div style="font-size:48px">🔥</div>
                <div style="font-size:36px;font-weight:700;margin-top:8px">${stats.study_streak_days}</div>
                <div style="font-size:14px;color:var(--text-secondary)">днів поспіль</div>
              </div>
            </div>` : ''}
        </div>`;

      ProgressBar.animateAll(content);
    } catch (err) { content.innerHTML = renderError(err); }
  }
};

window.StatisticsPage = StatisticsPage;
