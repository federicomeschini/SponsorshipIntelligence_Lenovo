/* V2 — Attention: Brand Index hero with ribbon + survey dots, earned media,
   commercial intent. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.attention = function (root) {
  const D = window.SRMP_DEMO, C = COPY.attention, T = THEME, { el } = UI;
  const I = D.index;

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  /* survey dots mapped to nearest week on the grid */
  const dots = new Array(I.week.length).fill(null);
  D.surveyQuarterly.date.forEach((d, k) => {
    if (d < I.week[0]) return;
    let best = 0, bd = Infinity;
    I.week.forEach((w, i) => {
      const diff = Math.abs(new Date(w) - new Date(d));
      if (diff < bd) { bd = diff; best = i; }
    });
    dots[best] = D.surveyQuarterly.composite[k];
  });

  const heroGrid = el("div", "panel-grid panel-grid--hero");
  const hp = UI.panel(heroGrid, { label: "Chart 1", title: C.hero, height: 400 });
  root.append(heroGrid);
  const simFrom = I.week.indexOf(I.simulatedFrom);
  const hChart = CH.line(hp.canvas, {
    weeks: I.week,
    ribbon: {
      upper: I.level.map((v, i) => v + 1.28 * I.se[i]),
      lower: I.level.map((v, i) => v - 1.28 * I.se[i]),
    },
    series: [
      { label: "Brand Index", data: I.level, color: T.seriesHeadline, width: 2, simFrom },
      { label: C.surveyDots, data: dots, color: T.seriesSecondary, width: 0, points: 4.5, showLine: false },
    ],
    milestones: UI.milestonesFor(I.week, ["fifa_partner_announcement_2024", "fcwc_opening_2025", "wc_opening_2026", "wc_final_2026"]),
  });
  hp.panel.append(el("p", "panel-note", C.surveyNote));
  UI.source(hp.panel, COPY.src.index);
  hp.bindExport(hChart, "attention-brand-index");

  /* earned media + commercial intent */
  const grid = el("div", "panel-grid");
  const mp = UI.panel(grid, { label: "Chart 2", title: C.media, height: 240 });
  const EM = D.earnedMedia;
  /* GDELT's mean-tone score for Lenovo runs almost entirely positive here
     (observed range roughly -0.06 to +2.7, median ~1.4) — it is not a
     symmetric -1..+1 sentiment scale, and coverage is basically never
     net-negative. A "dips below zero" bar treatment would almost never
     fire and would misrepresent the data, so volume stays a plain bar and
     the tone line (auto-scaled to its own real range) carries the signal
     of how positive coverage was, week to week. */
  const mChart = new Chart(mp.canvas.getContext("2d"), {
    data: {
      labels: EM.week,
      datasets: [
        {
          type: "bar",
          label: "News volume",
          data: EM.volume,
          backgroundColor: T.seriesHeadlineDeep,
          barPercentage: 1, categoryPercentage: 0.9,
          order: 2,
        },
        {
          type: "line",
          label: "Mean tone",
          data: EM.tone,
          yAxisID: "y2",
          borderColor: T.textPrimary,
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.15,
          spanGaps: true,
          order: 1,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { autoSkip: false, maxRotation: 0, callback: (v) => { const w = EM.week[v]; return w && w.slice(5, 10) <= "01-07" ? w.slice(0, 4) : ""; } } },
        y: { grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => FMT.big(v) } },
        y2: { position: "right", grid: { display: false }, border: { display: false }, ticks: { callback: (v) => v.toFixed(1) } },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (i) => (i.dataset.type === "line"
              ? ` Mean tone: ${i.parsed.y.toFixed(2)}`
              : ` ${FMT.big(i.parsed.y)} articles`),
          },
        },
      },
    },
  });
  mp.panel.append(el("p", "panel-note", C.mediaNote +
    ' <span class="oe-num" style="color:var(--oe-accent)">■</span> weekly volume · <span class="oe-num" style="color:var(--app-ink)">—</span> mean tone (higher = more positive coverage)'));
  UI.source(mp.panel, COPY.src.news);
  mp.bindExport(mChart, "attention-earned-media");

  const ip = UI.panel(grid, { label: "Chart 3", title: C.intent, height: 240 });
  const CI = D.commercialIntent;
  const ciSim = CI.simulatedFrom ? CI.week.indexOf(CI.simulatedFrom) : null;
  const iChart = CH.line(ip.canvas, {
    weeks: CI.week,
    series: [{ label: "Commercial-intent search", data: CI.interest, color: T.seriesTertiary, fill: true, fillColor: "rgba(0,0,255,.07)", simFrom: ciSim }],
  });
  ip.panel.append(el("p", "panel-note", C.intentNote));
  UI.source(ip.panel, COPY.src.search);
  ip.bindExport(iChart, "attention-commercial-intent");
  root.append(grid);
};
