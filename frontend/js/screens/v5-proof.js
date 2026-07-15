/* V5 — Proof: counterfactual break-away reveal + versus-the-market panel.
   Signature moment: the without-sponsorship line draws first, then actual
   pulls away and the created-value gap fills lime. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.proof = function (root) {
  const D = window.SRMP_DEMO, C = COPY.proof, T = THEME, { el } = UI;
  const CF = D.counterfactual;

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  /* hero: actual vs synthetic with shaded gap */
  const heroGrid = el("div", "panel-grid panel-grid--hero");
  const hp = UI.panel(heroGrid, { label: "Chart 1", title: C.hero, height: 400 });
  root.append(heroGrid);
  const simFrom = CF.week.indexOf(CF.simulatedFrom);
  const annIdx = CF.week.indexOf(CF.announcementWeek);
  const reduced = FMT.reduced;
  const hChart = CH.line(hp.canvas, {
    weeks: CF.week,
    series: [
      { label: C.synthetic, data: CF.synthetic, color: T.seriesCounterfactual, dash: [6, 4], width: 1.8, simFrom },
      { label: C.actual, data: CF.actual, color: T.seriesHeadline, width: 2.2, fill: "-1", fillColor: T.gapFill, simFrom },
    ],
    milestones: UI.milestonesFor(CF.week, ["fifa_partner_announcement_2024", "fcwc_opening_2025", "wc_opening_2026", "wc_final_2026"]),
  });
  /* break-away reveal: synthetic first, actual + gap after */
  if (!reduced) {
    hChart.options.animation = { duration: 900, easing: "easeOutQuart" };
    hChart.options.animations = {
      ...hChart.options.animations,
      y: { delay: (ctx) => (ctx.datasetIndex === 1 && ctx.type === "data" ? 650 : 0) },
    };
    hChart.update();
  }
  const callout = el("div", "gap-callout");
  callout.append(el("span", "n oe-num", C.callout));
  callout.append(el("span", "s", C.calloutSub));
  hp.panel.querySelector(".chart-box").append(callout);
  hp.panel.append(el("p", "panel-note", `<span style="background:${T.gapFill};padding:1px 8px">&nbsp;</span> ${C.gapLabel}`));
  hp.bindExport(hChart, "proof-counterfactual");

  /* versus the market: Lenovo vs donor benchmark, indexed to announcement */
  const grid = el("div", "panel-grid panel-grid--hero");
  const mp = UI.panel(grid, { label: "Chart 2", title: C.market, height: 300 });
  root.append(grid);
  /* donor weeks are W-SUN (Trends); the index grid is W-MON — shift +1 day */
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
  /* standardize every brand on its own pre-announcement mean/sd, smooth 4w —
     puts quantized low-volume donors and Lenovo on one fair scale */
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
      { label: "Competitor market (median of " + D.kpi.donorCount + ")", data: donorMed, color: T.seriesBenchmark, width: 1.8 },
      { label: "Lenovo", data: lenovoZ, color: T.seriesHeadline, width: 2.2 },
    ],
    milestones: UI.milestonesFor(wSet, ["fifa_partner_announcement_2024", "wc_opening_2026"]),
    yTitle: "σ vs pre-announcement baseline",
  });
  mp.panel.append(el("p", "panel-note", C.marketNote));
  mp.bindExport(mChart, "proof-versus-market");

  root.append(el("p", "credential reveal", C.credential));
};
