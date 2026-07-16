/* V3 — Perception: exposed-vs-non-exposed funnel, lift trajectory by wave,
   full competition × wave heat matrix, stat cards. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.perception = function (root) {
  const D = window.SRMP_DEMO, C = COPY.perception, T = THEME, { el } = UI;
  const waves = D.funnelWaves;
  const waveLabel = (w) => FMT.monthYear(w + "-01");

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  /* hero funnel — latest FWC wave */
  const grid = el("div", "panel-grid panel-grid--hero");
  const fp = UI.panel(grid, { label: "Chart 1", title: C.hero, height: 0 });
  fp.panel.querySelector(".chart-box").remove();
  fp.hideExport();
  fp.panel.querySelector(".oe-panel__head").append(
    el("span", "funnel-wave-chip", "Wave " + waves.length + " · " + waveLabel(D.funnelHeroWave)));
  const legend = el("div", "funnel-legend",
    `<span><i style="background:var(--oe-accent)"></i>${C.aware}</span>` +
    `<span><i style="background:var(--oe-gray-300)"></i>${C.unaware}</span>`);
  const funnel = el("div", "funnel");
  const headRow = el("div", "funnel-row funnel-row--head");
  [C.stageHead, C.shareHead, C.liftHead].forEach((h) =>
    headRow.append(el("div", "funnel-col", h)));
  funnel.append(headRow);
  D.funnelHero.forEach((s) => {
    const row = el("div", "funnel-row");
    row.append(el("div", "stage", UI.STAGE_NAMES[s.stage] + (s.stage === "awareness" ? "<small>of the Lenovo brand</small>" : "")));
    const bars = el("div", "funnel-bars");
    [["aware", s.aware], ["unaware", s.unaware]].forEach(([k, v]) => {
      const bar = el("div", "funnel-bar funnel-bar--" + k);
      const fill = el("i");
      fill.style.width = "0%";
      bar.append(fill, el("b", "oe-num", FMT.pct(v)));
      bars.append(bar);
      requestAnimationFrame(() => requestAnimationFrame(() => { fill.style.width = v * 100 + "%"; }));
    });
    row.append(bars);
    row.append(el("div", "", UI.deltaChip(FMT.pp(s.lift))));
    funnel.append(row);
  });
  fp.panel.append(legend, funnel);
  fp.panel.append(el("p", "panel-note", C.funnelNote));
  UI.source(fp.panel, COPY.src.waves);
  root.append(grid);

  const midGrid = el("div", "panel-grid panel-grid--hero");

  /* lift trajectory by wave (flagship World Cup audience) */
  const tpPanel = UI.panel(midGrid, { label: "Chart 2", title: C.trend, height: 280 });
  const liftSeries = (stage) => waves.map((w) =>
    Math.round(D.funnel.find((r) => r.wave === w && r.property === "fwc" && r.stage === stage).lift * 100));
  const trendChart = new Chart(tpPanel.canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: waves.map(waveLabel),
      datasets: [
        { label: "Appeal lift", data: liftSeries("appeal"), borderColor: T.seriesHeadline, backgroundColor: T.seriesHeadline, pointRadius: 4, borderWidth: 2, tension: 0.25 },
        { label: "Purchase-intent lift", data: liftSeries("purchase_intent"), borderColor: T.seriesSecondary, backgroundColor: T.seriesSecondary, pointRadius: 4, borderWidth: 2, tension: 0.25 },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: false, font: { size: 11 } } },
        y: { beginAtZero: true, grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => "+" + v + " pp" } },
      },
      plugins: {
        legend: { display: true },
        tooltip: { callbacks: { label: (i) => ` ${i.dataset.label}: +${i.parsed.y} pp` } },
      },
    },
  });
  tpPanel.panel.append(el("p", "panel-note", C.trendNote));
  UI.source(tpPanel.panel, COPY.src.waves);
  tpPanel.bindExport(trendChart, "perception-lift-by-wave");

  /* heat matrix: lift by competition × wave */
  const rows = [];
  ["fwc", "fwwc", "fcwc"].forEach((p) =>
    ["appeal", "purchase_intent"].forEach((s) => rows.push([p, s])));
  const hpPanel = UI.panel(midGrid, { label: "Chart 3", title: C.heat, height: 0 });
  hpPanel.panel.querySelector(".chart-box").remove();
  hpPanel.hideExport();
  const heat = el("div", "heat");
  heat.style.gridTemplateColumns = `200px repeat(${waves.length}, 1fr)`;
  heat.append(el("div", "heat-head", ""));
  waves.forEach((w) => heat.append(el("div", "heat-head", waveLabel(w))));
  const all = D.funnel.filter((r) => r.stage !== "awareness").map((r) => r.lift);
  const lo = Math.min(...all), hi = Math.max(...all);
  rows.forEach(([p, s]) => {
    heat.append(el("div", "heat-rowhead", `${UI.PROP_NAMES[p]} · ${UI.STAGE_NAMES[s]}`));
    waves.forEach((w) => {
      const r = D.funnel.find((x) => x.wave === w && x.property === p && x.stage === s);
      const cell = el("div", "heat-cell oe-num");
      const f = (r.lift - lo) / (hi - lo);
      const ramp = T.seqRamp;
      cell.style.background = ramp[Math.min(ramp.length - 1, Math.round(f * (ramp.length - 1)))];
      cell.style.color = f > 0.55 ? "#fff" : "var(--oe-gray-900)";
      cell.textContent = FMT.pp(r.lift);
      cell.title = `${UI.PROP_NAMES[p]} · ${UI.STAGE_NAMES[s]} · ${waveLabel(w)} wave`;
      heat.append(cell);
    });
  });
  hpPanel.panel.append(heat, el("p", "panel-note", C.heatNote));
  UI.source(hpPanel.panel, COPY.src.waves);
  root.append(midGrid);

  /* stat cards */
  const cards = el("div", "stat-cards");
  C.cards.forEach((c) => {
    const card = el("div", "stat-card reveal");
    card.append(el("div", "stat-num oe-num", c.stat));
    card.append(el("p", "", c.text));
    cards.append(card);
  });
  root.append(cards);
};
