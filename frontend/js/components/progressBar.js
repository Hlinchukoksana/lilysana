/**
 * Progress bar component.
 * Usage: ProgressBar.render(percent, options)
 */
const ProgressBar = {
  render(percent, { color = 'primary', showLabel = true, animated = true } = {}) {
    const pct = Math.min(100, Math.max(0, percent));
    const colorClass = pct >= 95 ? 'success' : pct >= 71 ? '' : 'warning';
    const cls = color === 'auto' ? colorClass : (color === 'success' ? 'success' : color === 'warning' ? 'warning' : '');
    return `
      <div class="progress-bar-wrapper">
        <div class="progress-bar-track">
          <div class="progress-bar-fill ${cls}"
               style="width: ${animated ? 0 : pct}%; --target-width: ${pct}%"
               data-animate="${animated ? pct : ''}"
          ></div>
        </div>
        ${showLabel ? `<span class="progress-label">${pct.toFixed(0)}%</span>` : ''}
      </div>`;
  },

  animateAll(container) {
    const fills = container.querySelectorAll('.progress-bar-fill[data-animate]');
    fills.forEach(el => {
      const target = el.dataset.animate;
      if (target) {
        requestAnimationFrame(() => {
          el.style.width = target + '%';
        });
      }
    });
  }
};

window.ProgressBar = ProgressBar;
