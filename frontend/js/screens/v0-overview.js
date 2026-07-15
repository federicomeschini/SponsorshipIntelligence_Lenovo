/* V0 — Overview: dark hero + KPI count-up strip, section previews, timeline. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.overview = function (root) {
  const D = window.SRMP_DEMO, C = COPY.overview, K = D.kpi, T = THEME, { el } = UI;

  /* hero */
  const hero = el("section", "hero reveal");
  hero.append(el("span", "oe-tag-chip oe-tag-chip--lime", C.kicker));
  hero.append(el("h1", "", C.title));
  hero.append(el("p", "insight-line", C.insight));
  const strip = el("div", "hero-kpis");
  [
    { value: K.digitalImpressions, fmt: FMT.big, label: C.kpis.impressions, note: "cumulative, 13 properties" },
    { value: K.broadcastAudience, fmt: FMT.big, label: C.kpis.broadcast, note: "cumulative audience" },
    { value: K.indexLift, fmt: (v) => FMT.pts(v), label: C.kpis.lift, note: "vs. without sponsorship" },
    { value: K.annualValueUsd, fmt: FMT.usd, label: C.kpis.value, note: "earnings-equivalent / year" },
    { value: K.roiMultiple, fmt: FMT.mult, label: C.kpis.roi, note: "brand value per US$1 invested" },
  ].forEach((k) => strip.append(UI.kpi({ ...k, dark: true })));
  hero.append(strip);
  root.append(hero);

  /* section previews with sparklines */
  const row = el("div", "preview-row");
  const cum = [];
  let acc = 0;
  D.exposure.week.forEach((w, i) => { acc += D.exposure.fifaDigital[i] + D.exposure.broadcast[i]; cum.push(acc); });
  const idxTail = D.index.level.slice(-160);
  const gapTail = D.counterfactual.gap.slice(D.counterfactual.week.indexOf(D.counterfactual.announcementWeek));
  const fwcAppeal = D.funnel.filter((r) => r.property === "fwc" && r.stage === "appeal").map((r) => r.lift);
  const nets = [D.roi.scenarios.conservative.netUsd, D.roi.scenarios.base.netUsd, D.roi.scenarios.ambitious.netUsd];
  const previews = [
    { id: "reach", c: C.sections.reach, data: cum, stat: FMT.big(K.totalExposure) },
    { id: "attention", c: C.sections.attention, data: idxTail, stat: FMT.pts(K.peakLift) + " peak" },
    { id: "perception", c: C.sections.perception, data: fwcAppeal, stat: "+" + K.appealLiftRange[1] + " pp" },
    { id: "proof", c: C.sections.value, data: gapTail, stat: FMT.pts(K.indexLift) },
    { id: "return", c: C.sections.return, data: nets, stat: FMT.mult(K.roiMultiple) },
  ];
  previews.forEach((p) => {
    const card = el("div", "preview-card reveal");
    card.setAttribute("role", "button");
    card.tabIndex = 0;
    card.addEventListener("keydown", (e) => { if (e.key === "Enter") location.hash = "#/" + p.id; });
    card.append(el("div", "preview-sub", p.c[1]));
    card.append(el("h3", "", p.c[0]));
    const spark = el("div", "spark");
    const cv = document.createElement("canvas");
    spark.append(cv);
    card.append(spark, el("div", "preview-stat oe-num", p.stat));
    card.addEventListener("click", () => (location.hash = "#/" + p.id));
    row.append(card);
    requestAnimationFrame(() => CH.sparkline(cv, { data: p.data, color: T.seriesHeadline, fill: T.ribbonConfidence }));
  });
  root.append(row);

  /* partnership timeline ribbon */
  const tl = el("div", "reveal");
  tl.append(el("span", "oe-eyebrow", C.timelineTitle));
  root.append(tl);
  UI.milestoneRibbon(root);
};
