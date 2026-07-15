/* V5 — Proof: executive verdict, counterfactual breakaway and market check. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.proof = function (root) {
  const D = window.SRMP_DEMO, C = COPY.proof, T = THEME, { el } = UI;
  const CF = D.counterfactual;

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  const proofHero = el("div", "proof-hero reveal");
  const chartPanel = el("div", "oe-panel proof-chart");
  chartPanel.append(el("div", "oe-panel__head",
    `<div><div class="oe-panel__label">Primary test</div><p class="oe-panel__title">${C.hero}</p></div>`));
  const chartBox = el("div", "chart-box");
  chartBox.style.height = "410px";
  const canvas = document.createElement("canvas");
  chartBox.append(canvas);
  chartPanel.append(chartBox);

  const verdict = el("aside", "proof-verdict");
  verdict.append(el("span", "oe-tag-chip oe-tag-chip--lime", "Counterfactual verdict"));
  verdict.append(el("strong", "proof-verdict__number oe-num", FMT.pts(D.kpi.indexLift)));
  verdict.append(el("span", "proof-verdict__label", C.calloutSub));
  verdict.append(el("p", "", C.verdict));
  const verdictMeta = el("dl", "proof-verdict__meta");
  [
    ["Comparison", D.kpi.donorCount + " non-sponsor brands"],
    ["Intervention", "FIFA partnership announcement"],
    ["Extension", "Dashed where illustrative"],
  ].forEach(([term, value]) => {
    verdictMeta.append(el("div", "", `<dt>${term}</dt><dd>${value}</dd>`));
  });
  verdict.append(verdictMeta);
  proofHero.append(chartPanel, verdict);
  root.append(proofHero);

  const simFrom = CF.week.indexOf(CF.simulatedFrom);
  const hChart = CH.line(canvas, {
    weeks: CF.week,
    series: [
      { label: C.synthetic, data: CF.synthetic, color: T.seriesCounterfactual, dash: [6, 4], width: 1.8, simFrom },
      { label: C.actual, data: CF.actual, color: T.seriesHeadline, width: 2.2, fill: "-1", fillColor: T.gapFill, simFrom },
    ],
    milestones: UI.milestonesFor(CF.week, ["fifa_partner_announcement_2024", "fcwc_opening_2025", "wc_opening_2026", "wc_final_2026"]),
  });
  if (!FMT.reduced) {
    hChart.options.animation = { duration: 900, easing: "easeOutQuart" };
    hChart.options.animations = {
      ...hChart.options.animations,
      y: { delay: (ctx) => (ctx.datasetIndex === 1 && ctx.type === "data" ? 650 : 0) },
    };
    hChart.update();
  }
  chartPanel.append(el("p", "panel-note proof-gap-key",
    `<span aria-hidden="true"></span>${C.gapLabel}`));

  const marketGrid = el("div", "panel-grid panel-grid--hero");
  const mp = UI.panel(marketGrid, { label: "Robustness check", title: C.market, height: 310 });
  root.append(marketGrid);

  const donorNames = Object.keys(D.donorPanel);
  const wSun = D.donorPanel[donorNames[0]].week;
  const wSet = wSun.map((w) => new Date(new Date(w + "T00:00:00Z").getTime() + 864e5).toISOString().slice(0, 10));
  const annPos = wSet.findIndex((w) => w >= CF.announcementWeek);
  const quant = (arr, q) => {
    const s = [...arr].sort((a, b) => a - b);
    const p = (s.length - 1) * q, lo = Math.floor(p);
    return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (p - lo);
  };
  const ma = (arr, n) => arr.map((_, i) => {
    const s = arr.slice(Math.max(0, i - n + 1), i + 1).filter((v) => v != null);
    return s.length ? s.reduce((a, v) => a + v, 0) / s.length : null;
  });
  const zSeries = (values, pos) => {
    const pre = values.slice(0, pos).filter((v) => v != null);
    const mean = pre.reduce((a, v) => a + v, 0) / pre.length;
    const sd = Math.sqrt(pre.reduce((a, v) => a + (v - mean) ** 2, 0) / pre.length) || 1;
    return ma(values.map((v) => (v == null ? null : (v - mean) / sd)), 4);
  };
  const donorZ = donorNames.map((n) => zSeries(D.donorPanel[n].value, annPos));
  const donorMed = wSet.map((_, i) => quant(donorZ.map((d) => d[i]), 0.5));
  const donorLo = wSet.map((_, i) => quant(donorZ.map((d) => d[i]), 0.25));
  const donorHi = wSet.map((_, i) => quant(donorZ.map((d) => d[i]), 0.75));
  const lenovoOnDonorGrid = wSet.map((w) => {
    const i = CF.week.indexOf(w);
    return i >= 0 ? CF.actual[i] : null;
  });
  const lenovoZ = zSeries(lenovoOnDonorGrid, annPos);
  const mChart = CH.line(mp.canvas, {
    weeks: wSet,
    ribbon: { upper: donorHi, lower: donorLo },
    series: [
      { label: "Non-sponsor market median", data: donorMed, color: T.seriesBenchmark, width: 1.8 },
      { label: "Lenovo", data: lenovoZ, color: T.seriesHeadline, width: 2.2 },
    ],
    milestones: UI.milestonesFor(wSet, ["fifa_partner_announcement_2024", "wc_opening_2026"]),
    yTitle: "Standard deviations vs pre-announcement baseline",
  });
  mp.panel.append(el("p", "panel-note", C.marketNote));
  mp.bindExport(mChart, "fifa-proof-versus-market");

  const evidenceHead = el("div", "section-intro section-intro--compact reveal");
  evidenceHead.append(el("span", "oe-eyebrow", "How to read the evidence"));
  root.append(evidenceHead);
  const ledger = el("div", "evidence-ledger");
  C.evidence.forEach(([status, description], i) => {
    const item = el("div", "evidence-ledger__item reveal");
    item.append(el("span", "evidence-ledger__index oe-num", "0" + (i + 1)));
    item.append(el("strong", "", status));
    item.append(el("p", "", description));
    ledger.append(item);
  });
  root.append(ledger);
  root.append(el("p", "credential reveal", C.credential));
};