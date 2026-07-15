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
  hp.bindExport(hChart, "attention-brand-index");

  /* earned media + commercial intent */
  const grid = el("div", "panel-grid");
  const mp = UI.panel(grid, { label: "Chart 2", title: C.media, height: 240 });
  const EM = D.earnedMedia;
  const mChart = new Chart(mp.canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: EM.week,
      datasets: [{
        label: "News volume",
        data: EM.volume,
        backgroundColor: EM.tone.map((t) => (t == null ? T.seriesBenchmark : t >= 0.5 ? T.tonePositive : t <= -0.5 ? T.toneNegative : T.seriesBenchmark)),
        barPercentage: 1, categoryPercentage: 0.9,
      }],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { autoSkip: false, maxRotation: 0, callback: (v) => { const w = EM.week[v]; return w && w.slice(5, 10) <= "01-07" ? w.slice(0, 4) : ""; } } },
        y: { grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => FMT.big(v) } },
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (i) => ` ${FMT.big(i.parsed.y)} articles · tone ${EM.tone[i.dataIndex] >= 0 ? "positive" : "negative"}` } },
      },
    },
  });
  mp.panel.append(el("p", "panel-note", C.mediaNote + ' <span class="oe-num" style="color:var(--oe-accent)">■</span> positive · <span class="oe-num" style="color:#C300C3">■</span> negative'));
  mp.bindExport(mChart, "attention-earned-media");

  const ip = UI.panel(grid, { label: "Chart 3", title: C.intent, height: 240 });
  const CI = D.commercialIntent;
  const ciSim = CI.simulatedFrom ? CI.week.indexOf(CI.simulatedFrom) : null;
  const iChart = CH.line(ip.canvas, {
    weeks: CI.week,
    series: [{ label: "Commercial-intent search", data: CI.interest, color: T.seriesTertiary, fill: true, fillColor: "rgba(0,0,255,.07)", simFrom: ciSim }],
  });
  ip.panel.append(el("p", "panel-note", C.intentNote));
  ip.bindExport(iChart, "attention-commercial-intent");
  root.append(grid);
};
