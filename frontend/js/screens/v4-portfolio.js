/* V4 — Portfolio: per-property return, exposure-vs-return scatter, mix. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.portfolio = function (root) {
  const D = window.SRMP_DEMO, C = COPY.portfolio, T = THEME, { el } = UI;
  const P = [...D.portfolio].sort((a, b) => b.valuePerM - a.valuePerM);

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  /* hero: value per million impressions */
  const heroGrid = el("div", "panel-grid panel-grid--hero");
  const hp = UI.panel(heroGrid, { label: "Chart 1", title: C.hero, height: 320 });
  root.append(heroGrid);
  const hChart = CH.barsH(hp.canvas, {
    labels: P.map((p) => p.label),
    datasets: [{
      label: "Value per 1M impressions",
      data: P.map((p) => p.valuePerM),
      backgroundColor: P.map((p) => (p.fifa ? T.seriesHeadlineDeep : T.seriesBenchmark)),
      barPercentage: 0.7,
    }],
    xFmt: (v) => FMT.usd(v),
    xTitle: "USD per million impressions",
  });
  hp.panel.append(el("p", "panel-note",
    `FIFA returns <b>${FMT.usd(P.find((p) => p.fifa).valuePerM)}</b> per million impressions — ` +
    `${D.kpi.fifaVsMedianMultiple.toFixed(1)}× the portfolio median of ${FMT.usd(D.portfolioMedianVpm)}.`));
  hp.bindExport(hChart, "portfolio-value-per-impression");

  /* scatter + mix */
  const grid = el("div", "panel-grid");
  const sp = UI.panel(grid, { label: "Chart 2", title: C.scatter, height: 280 });
  const sChart = CH.scatter(sp.canvas, {
    points: P.map((p) => ({
      label: p.label, x: p.impressions, y: p.valuePerM,
      r: 6 + p.feeTier * 5,
      color: p.fifa ? T.seriesHeadlineDeep : T.seriesBenchmark,
    })),
    xTitle: "Cumulative impressions (log)",
    yTitle: "Value per 1M impressions",
    xFmt: FMT.big,
    yFmt: FMT.usd,
  });
  sp.panel.append(el("p", "panel-note", C.scatterNote));
  sp.bindExport(sChart, "portfolio-exposure-vs-return");

  const mp = UI.panel(grid, { label: "Chart 3", title: C.mix, height: 280 });
  const totalValue = P.reduce((a, p) => a + p.valueUsd, 0);
  const tierW = { 3: 3.2, 2: 2.2, 1: 1 };
  const totalSpend = P.reduce((a, p) => a + tierW[p.feeTier], 0);
  const fifa = P.find((p) => p.fifa);
  const valueShare = fifa.valueUsd / totalValue;
  const spendShare = tierW[fifa.feeTier] / totalSpend;
  const mChart = CH.barsH(mp.canvas, {
    labels: ["Share of portfolio value", "Share of portfolio spend"],
    datasets: [
      { label: "FIFA partnership", data: [valueShare * 100, spendShare * 100], backgroundColor: T.seriesHeadlineDeep, barPercentage: 0.55 },
      { label: "Rest of portfolio", data: [(1 - valueShare) * 100, (1 - spendShare) * 100], backgroundColor: T.seriesBenchmark, barPercentage: 0.55 },
    ],
    stacked: true,
    xFmt: (v) => Math.round(v) + "%",
  });
  mp.panel.append(el("p", "panel-note", C.mixNote));
  mp.bindExport(mChart, "portfolio-mix");
  root.append(grid);

  /* property signature cards */
  const cards = el("div", "stat-cards");
  [
    { stat: FMT.big(fifa.impressions), text: "FIFA partnership impressions — the portfolio's premium reach." },
    { stat: FMT.usd(fifa.valueUsd), text: "Brand value created by the FIFA partnership over the persistence horizon." },
    { stat: Math.round(valueShare * 100) + "% vs " + Math.round(spendShare * 100) + "%", text: "FIFA's share of portfolio value against its share of portfolio spend." },
  ].forEach((c) => {
    const card = el("div", "stat-card reveal");
    card.append(el("div", "stat-num oe-num", c.stat));
    card.append(el("p", "", c.text));
    cards.append(card);
  });
  root.append(cards);
};
