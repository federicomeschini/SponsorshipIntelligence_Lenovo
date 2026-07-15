/* V1 — Reach: cumulative exposure hero, carryover, small multiples, share. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.reach = function (root) {
  const D = window.SRMP_DEMO, C = COPY.reach, K = D.kpi, T = THEME, { el } = UI;
  const E = D.exposure;

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  /* hero: cumulative digital + broadcast stacked area */
  let cd = 0, cb = 0;
  const cumDigital = E.fifaDigital.map((v) => (cd += v));
  const cumBroadcast = E.broadcast.map((v) => (cb += v));
  const heroGrid = el("div", "panel-grid panel-grid--hero");
  const hp = UI.panel(heroGrid, { label: "Chart 1", title: C.hero, height: 380 });
  root.append(heroGrid);
  const heroChart = CH.stackedArea(hp.canvas, {
    weeks: E.week,
    layers: [
      { label: "Broadcast audience", data: cumBroadcast, color: T.stackBroadcast },
      { label: "Digital impressions", data: cumDigital, color: T.stackDigital },
    ],
    milestones: UI.milestonesFor(E.week, ["fifa_partner_announcement_2024", "fcwc_opening_2025", "wc_opening_2026", "wc_final_2026"]),
  });
  hp.bindExport(heroChart, "reach-cumulative-exposure");

  /* supporting: carryover + share donut */
  const grid = el("div", "panel-grid");
  const cp = UI.panel(grid, { label: "Chart 2", title: C.adstock, height: 260 });
  const delta = Math.pow(0.5, 1 / E.adstockHalfLifeWeeks);
  let ad = 0;
  const adstock = E.fifaDigital.map((v) => (ad = v + ad * delta));
  const cChart = CH.line(cp.canvas, {
    weeks: E.week,
    series: [
      { label: "Weekly exposure", data: E.fifaDigital, color: T.seriesBenchmark, width: 1.5 },
      { label: "Attention carryover", data: adstock, color: T.seriesHeadline, fill: true, fillColor: T.ribbonConfidence },
    ],
  });
  cChart.options.scales.y.ticks = { callback: (v) => FMT.big(v) };
  cChart.update();
  cp.panel.append(el("p", "panel-note", C.adstockNote));
  cp.bindExport(cChart, "reach-attention-carryover");

  const dp = UI.panel(grid, { label: "Chart 3", title: C.share, height: 260 });
  const restImpr = D.portfolio.filter((p) => !p.fifa).reduce((a, p) => a + p.impressions, 0);
  const fifaImpr = D.portfolio.find((p) => p.fifa).impressions;
  const dChart = CH.donut(dp.canvas, {
    labels: ["FIFA partnership", "Rest of portfolio"],
    values: [fifaImpr, restImpr],
    colors: [T.seriesHeadlineDeep, THEME.seriesBenchmark],
    centerText: [FMT.big(fifaImpr), "FIFA impressions"],
  });
  dp.bindExport(dChart, "reach-portfolio-share");
  root.append(grid);

  /* engagement */
  const g2 = el("div", "panel-grid panel-grid--hero");
  const ep = UI.panel(g2, { label: "Chart 4", title: C.engagement, height: 220 });
  const eChart = CH.line(ep.canvas, {
    weeks: E.week,
    series: [{ label: "Weekly engagements", data: E.engagements, color: T.seriesSecondary, fill: true, fillColor: "rgba(195,0,195,.08)" }],
  });
  eChart.options.scales.y.ticks = { callback: (v) => FMT.big(v) };
  eChart.update();
  ep.panel.append(el("p", "panel-note", C.engagementNote));
  ep.bindExport(eChart, "reach-engagement");
  root.append(g2);

  /* per-property small multiples (13 properties) */
  const mHead = el("div", "reveal");
  mHead.append(el("span", "oe-eyebrow", C.byProperty));
  root.append(mHead);
  const mm = el("div", "multiples reveal");
  const order = Object.entries(D.exposureByProperty)
    .map(([pid, p]) => [pid, p.impressions.reduce((a, v) => a + v, 0)])
    .sort((a, b) => b[1] - a[1]);
  order.forEach(([pid, total]) => {
    const p = D.exposureByProperty[pid];
    const m = el("div", "multiple");
    m.append(el("h4", "", UI.PROP_NAMES[pid] || pid));
    m.append(el("div", "mult-total oe-num", FMT.big(total) + " impressions"));
    const spark = el("div", "spark");
    const cv = document.createElement("canvas");
    spark.append(cv);
    m.append(spark);
    mm.append(m);
    const fifa = window.SRMP_DEMO.events && ["fifa","fwc","fwwc","fcwc","fifae","fifaewc","infantino"].includes(pid);
    requestAnimationFrame(() => CH.sparkline(cv, { data: p.impressions, color: fifa ? T.seriesHeadline : T.seriesBenchmark }));
  });
  root.append(mm);
};
