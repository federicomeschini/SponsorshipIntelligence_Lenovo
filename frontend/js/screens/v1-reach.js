/* V1 — FIFA Reach: cumulative exposure, carryover, channel mix and FIFA activations. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.reach = function (root) {
  const D = window.SRMP_DEMO, C = COPY.reach, T = THEME, { el } = UI;
  const E = D.exposure;

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

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
  hp.panel.append(el("p", "panel-note", C.heroNote));
  UI.source(hp.panel, COPY.src.exposure);
  hp.bindExport(heroChart, "fifa-reach-cumulative-exposure");

  const grid = el("div", "panel-grid");
  const cp = UI.panel(grid, { label: "Chart 2", title: C.adstock, height: 260 });
  const delta = Math.pow(0.5, 1 / E.adstockHalfLifeWeeks);
  let ad = 0;
  const adstock = E.fifaDigital.map((v) => (ad = v + ad * delta));
  const cChart = CH.line(cp.canvas, {
    weeks: E.week,
    series: [
      { label: "Weekly FIFA exposure", data: E.fifaDigital, color: T.seriesBenchmark, width: 1.5 },
      { label: "Attention carryover", data: adstock, color: T.seriesHeadline, fill: true, fillColor: T.ribbonConfidence },
    ],
  });
  cChart.options.scales.y.ticks = { callback: (v) => FMT.big(v) };
  cChart.update();
  cp.panel.append(el("p", "panel-note", C.adstockNote));
  UI.source(cp.panel, COPY.src.blinkfire);
  cp.bindExport(cChart, "fifa-reach-attention-carryover");

  const dp = UI.panel(grid, { label: "Chart 3", title: C.share, height: 260 });
  const fifaDigital = E.fifaDigital.reduce((a, v) => a + v, 0);
  const fifaBroadcast = E.broadcast.reduce((a, v) => a + v, 0);
  const dChart = CH.donut(dp.canvas, {
    labels: ["Digital impressions", "Broadcast audience"],
    values: [fifaDigital, fifaBroadcast],
    colors: [T.seriesHeadlineDeep, T.stackBroadcast],
    centerText: [FMT.big(fifaDigital + fifaBroadcast), "Total FIFA exposure"],
  });
  UI.source(dp.panel, COPY.src.exposure);
  dp.bindExport(dChart, "fifa-reach-channel-mix");
  root.append(grid);

  const engagementGrid = el("div", "panel-grid panel-grid--hero");
  const ep = UI.panel(engagementGrid, { label: "Chart 4", title: C.engagement, height: 220 });
  const eChart = CH.line(ep.canvas, {
    weeks: E.week,
    series: [{ label: "Weekly engagements", data: E.engagements, color: T.seriesSecondary, fill: true, fillColor: "rgba(195,0,195,.08)" }],
  });
  eChart.options.scales.y.ticks = { callback: (v) => FMT.big(v) };
  eChart.update();
  ep.panel.append(el("p", "panel-note", C.engagementNote));
  UI.source(ep.panel, COPY.src.blinkfire);
  ep.bindExport(eChart, "fifa-reach-engagement");
  root.append(engagementGrid);

  const activationHead = el("div", "section-intro section-intro--compact reveal");
  activationHead.append(el("span", "oe-eyebrow", C.byProperty));
  activationHead.append(el("p", "", "Lenovo exposure measured across FIFA competitions and official FIFA channels."));
  root.append(activationHead);

  const fifaIds = new Set(["fifa", "fwc", "fwwc", "fcwc", "fifae", "fifaewc", "infantino"]);
  const order = Object.entries(D.exposureByProperty)
    .filter(([pid]) => fifaIds.has(pid))
    .map(([pid, p]) => [pid, p.impressions.reduce((a, v) => a + v, 0)])
    .sort((a, b) => b[1] - a[1]);

  const mm = el("div", "multiples reveal");
  order.forEach(([pid, total]) => {
    const p = D.exposureByProperty[pid];
    const item = el("div", "multiple");
    item.append(el("h4", "", UI.PROP_NAMES[pid] || pid));
    item.append(el("div", "mult-total oe-num", FMT.big(total) + " impressions"));
    const spark = el("div", "spark");
    const cv = document.createElement("canvas");
    spark.append(cv);
    item.append(spark);
    mm.append(item);
    requestAnimationFrame(() => CH.sparkline(cv, { data: p.impressions, color: T.seriesHeadline }));
  });
  root.append(mm);
  UI.source(root, COPY.src.blinkfire);
};