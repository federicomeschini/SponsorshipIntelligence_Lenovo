/* V0 — FIFA-first executive overview: investment thesis, decision chapters,
   supporting evidence and partnership timeline. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.overview = function (root) {
  const D = window.SRMP_DEMO, C = COPY.overview, K = D.kpi, T = THEME, { el } = UI;
  const base = D.roi.scenarios.base;

  const hero = el("section", "hero reveal");
  hero.append(el("span", "oe-tag-chip oe-tag-chip--lime", C.kicker));
  hero.append(el("h1", "", C.title));
  hero.append(el("p", "insight-line", C.insight));
  root.append(hero);

  const decisionHead = el("div", "section-intro reveal");
  decisionHead.append(el("span", "oe-eyebrow", "The decision in two chapters"));
  decisionHead.append(el("p", "", "Start with value. Then inspect the evidence that makes the value defensible."));
  root.append(decisionHead);

  const cum = [];
  let acc = 0;
  D.exposure.week.forEach((w, i) => {
    acc += D.exposure.fifaDigital[i] + D.exposure.broadcast[i];
    cum.push(acc);
  });
  const idxTail = D.index.level.slice(-160);
  const gapTail = D.counterfactual.gap.slice(D.counterfactual.week.indexOf(D.counterfactual.announcementWeek));
  const fwcAppeal = D.funnel.filter((r) => r.property === "fwc" && r.stage === "appeal").map((r) => r.lift);
  const nets = [D.roi.scenarios.conservative.netUsd, D.roi.scenarios.base.netUsd, D.roi.scenarios.ambitious.netUsd];

  const decisionRow = el("div", "decision-row");
  [
    { id: "return", c: C.sections.financial, data: nets, stat: FMT.mult(K.roiMultiple), note: FMT.usd(base.netUsd) + " net value", kind: "financial" },
    { id: "proof", c: C.sections.proof, data: gapTail, stat: FMT.pts(K.indexLift), note: "above without-FIFA", kind: "proof" },
  ].forEach((p) => {
    const card = el("button", `decision-card decision-card--${p.kind} reveal`);
    card.type = "button";
    card.addEventListener("click", () => (location.hash = "#/" + p.id));
    card.append(el("span", "decision-card__chapter", p.c[1]));
    card.append(el("h2", "", p.c[0]));
    card.append(el("strong", "decision-card__stat oe-num", p.stat));
    card.append(el("span", "decision-card__note", p.note));
    const spark = el("span", "decision-card__spark");
    const cv = document.createElement("canvas");
    spark.append(cv);
    card.append(spark, el("span", "decision-card__action", "Open chapter \u2192"));
    decisionRow.append(card);
    requestAnimationFrame(() => CH.sparkline(cv, {
      data: p.data,
      color: p.kind === "financial" ? T.heroAccent : T.seriesHeadline,
      fill: p.kind === "financial" ? "rgba(185,255,105,.12)" : T.ribbonConfidence,
    }));
  });
  root.append(decisionRow);

  const supportHead = el("div", "section-intro section-intro--compact reveal");
  supportHead.append(el("span", "oe-eyebrow", "Supporting FIFA evidence"));
  root.append(supportHead);

  const supportRow = el("div", "support-row");
  [
    { id: "reach", c: C.sections.reach, data: cum, stat: FMT.big(K.totalExposure) },
    { id: "attention", c: C.sections.attention, data: idxTail, stat: FMT.pts(K.peakLift) + " peak" },
    { id: "perception", c: C.sections.perception, data: fwcAppeal, stat: "+" + K.appealLiftRange[1] + " pp appeal" },
  ].forEach((p) => {
    const card = el("button", "support-card reveal");
    card.type = "button";
    card.addEventListener("click", () => (location.hash = "#/" + p.id));
    card.append(el("span", "support-card__chapter", p.c[1]));
    card.append(el("h3", "", p.c[0]));
    card.append(el("strong", "support-card__stat oe-num", p.stat));
    const spark = el("span", "support-card__spark");
    const cv = document.createElement("canvas");
    spark.append(cv);
    card.append(spark);
    supportRow.append(card);
    requestAnimationFrame(() => CH.sparkline(cv, { data: p.data, color: T.seriesHeadline, fill: T.ribbonConfidence }));
  });
  root.append(supportRow);

  const tl = el("div", "section-intro section-intro--compact reveal");
  tl.append(el("span", "oe-eyebrow", C.timelineTitle));
  root.append(tl);
  UI.milestoneRibbon(root);
};