/**
 * SVG Line Chart for test score history.
 * No external dependencies.
 */
const Chart = {
  render(containerId, scores, dates) {
    if (!scores || scores.length < 2) {
      return `<p style="color: var(--text-muted); font-size:13px; text-align:center; padding: 20px 0;">
        Потрібно щонайменше 2 результати для графіку
      </p>`;
    }

    const W = 300, H = 120, PAD = 20;
    const minY = 0, maxY = 100;
    const stepX = (W - PAD * 2) / (scores.length - 1);

    const points = scores.map((s, i) => {
      const x = PAD + i * stepX;
      const y = PAD + (1 - (s - minY) / (maxY - minY)) * (H - PAD * 2);
      return { x, y, s };
    });

    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const areaD = `${pathD} L${points[points.length-1].x},${H - PAD} L${PAD},${H - PAD} Z`;

    const circles = points.map((p, i) => `
      <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4"
        fill="var(--color-primary)" stroke="var(--bg-base)" stroke-width="2">
        <title>${dates ? dates[i] : `Спроба ${i+1}`}: ${p.s}%</title>
      </circle>
    `).join('');

    // Grid lines
    const gridLines = [25, 50, 75, 100].map(val => {
      const y = PAD + (1 - val / 100) * (H - PAD * 2);
      return `
        <line x1="${PAD}" y1="${y.toFixed(1)}" x2="${W - PAD}" y2="${y.toFixed(1)}"
          stroke="var(--border-subtle)" stroke-width="1" />
        <text x="${PAD - 4}" y="${(y + 4).toFixed(1)}" fill="var(--text-muted)"
          font-size="9" text-anchor="end">${val}</text>`;
    }).join('');

    return `
      <div class="chart-container">
        <svg class="chart-svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
          <defs>
            <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--color-primary)" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="var(--color-primary)" stop-opacity="0.02"/>
            </linearGradient>
          </defs>
          ${gridLines}
          <path d="${areaD}" fill="url(#chart-grad)" />
          <path d="${pathD}" fill="none" stroke="var(--color-primary)" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round"/>
          ${circles}
        </svg>
      </div>`;
  }
};

window.Chart = Chart;
