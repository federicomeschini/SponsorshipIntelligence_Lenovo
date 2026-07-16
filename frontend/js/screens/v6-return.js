/* V6 — Financial case: scenario decision surface, value bridge and checks. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.return = function (root) {
  const D = window.SRMP_DEMO, C = COPY.return, T = THEME, { el } = UI;
  const R = D.roi;

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  const scenarioBar = el("div", "scenario-bar reveal");
  scenarioBar.append(el("span", "lbl", C.scenario));
  const seg = el("div", "oe-segment");
  seg.setAttribute("role", "group");
  seg.setAttribute("aria-label", "Financial scenario");
  const formula = el("span", "scenario-formula credential");
  ["conservative", "base", "ambitious"].forEach((k) => {
    const button = el("button", "oe-segment__btn" + (k === "base" ? " is-active" : ""), C.scenarios[k]);
    button.type = "button";
    button.dataset.k = k;
    button.setAttribute("aria-pressed", k === "base" ? "true" : "false");
    seg.append(button);
  });
  scenarioBar.append(seg, formula);
  root.append(scenarioBar);

  const heroRow = el("div", "roi-hero reveal");
  const wfPanel = el("div", "oe-panel");
  wfPanel.append(el("div", "oe-panel__head",
    `<div><div class="oe-panel__label">Value bridge</div><p class="oe-panel__title">${C.hero}</p></div>`));
  const wfBox = el("div", "chart-box");
  wfBox.style.height = "370px";
  const wfCanvas = document.createElement("canvas");
  wfBox.append(wfCanvas);
  wfPanel.append(wfBox);

  const terminal = el("aside", "roi-terminal");
  terminal.append(el("span", "oe-tag-chip oe-tag-chip--lime", C.decisionLabel));
  const roiMult = el("div", "roi-mult oe-num");
  const roiStatement = el("h2", "roi-statement");
  const roiNet = el("div", "roi-net");
  terminal.append(roiMult, roiStatement, roiNet);
  terminal.append(el("p", "roi-terminal__note", C.decisionText));
  heroRow.append(wfPanel, terminal);
  root.append(heroRow);

  const ledger = el("div", "finance-ledger reveal");
  const ledgerValues = {};
  [
    ["gross", "Gross brand value"],
    ["investment", "Fee + activation"],
    ["net", "Net value created"],
  ].forEach(([key, label], i) => {
    const item = el("div", "finance-ledger__item");
    item.append(el("span", "finance-ledger__index oe-num", "0" + (i + 1)));
    const value = el("strong", "oe-num");
    ledgerValues[key] = value;
    item.append(value, el("span", "", label));
    ledger.append(item);
  });
  root.append(ledger);

  let wfChart = null;
  function renderScenario(k) {
    const s = R.scenarios[k];
    formula.textContent = C.formulaNote(s.deltaIndex);
    const steps = [
      { label: C.steps.annual, range: [0, s.annualUsd], color: T.seriesHeadlineDeep, printed: FMT.usd(s.annualUsd) + "/yr" },
      { label: C.steps.persistence + " \u00d7" + s.persistenceYears, range: [s.annualUsd, s.grossUsd], color: T.seriesHeadline, printed: "+" + FMT.usd(s.grossUsd - s.annualUsd) },
      { label: C.steps.investment, range: [s.grossUsd - s.investmentUsd, s.grossUsd], color: T.seriesSecondary, printed: "\u2212" + FMT.usd(s.investmentUsd) },
      { label: C.steps.net, range: [0, s.netUsd], color: T.seriesHeadlineDeep, printed: FMT.usd(s.netUsd) },
    ];
    if (wfChart) wfChart.destroy();
    wfChart = CH.waterfall(wfCanvas, { steps, yFmt: FMT.usd });
    roiMult.textContent = FMT.mult(s.roiMultiple);
    roiStatement.textContent = C.scenarios[k] + " case";
    roiNet.innerHTML = `Every US$1 invested returns <b>US$${s.roiMultiple.toFixed(2)}</b> in gross brand value.`;
    ledgerValues.gross.textContent = FMT.usd(s.grossUsd);
    ledgerValues.investment.textContent = FMT.usd(s.investmentUsd);
    ledgerValues.net.textContent = FMT.usd(s.netUsd);
  }
  seg.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    seg.querySelectorAll("button").forEach((item) => {
      const active = item === button;
      item.classList.toggle("is-active", active);
      item.setAttribute("aria-pressed", active ? "true" : "false");
    });
    renderScenario(button.dataset.k);
  });
  renderScenario("base");

  const supportHead = el("div", "section-intro section-intro--compact reveal");
  supportHead.append(el("span", "oe-eyebrow", "Stress-test the conclusion"));
  supportHead.append(el("p", "", "Two independent views show what supports the valuation and what can move it."));
  root.append(supportHead);

  const grid = el("div", "panel-grid finance-support");
  const rc = el("div", "oe-panel reveal");
  rc.append(el("div", "oe-panel__head",
    `<div><div class="oe-panel__label">Cross-check</div><p class="oe-panel__title">${C.royalty}</p></div>`));
  const rv = R.royaltyView;
  rc.append(el("div", "stat-num oe-num", FMT.usd(rv.lowUsd) + " \u2013 " + FMT.usd(rv.highUsd)));
  rc.append(el("p", "panel-note", C.royaltyNote(rv.lowUsd, rv.highUsd) + " Schedule: " +
    rv.schedule.map((p) => `${p.indexPoints.toFixed(1)} pts \u2192 ${FMT.usd(p.usdPerYear)}/yr`).join(" \u00b7 ")));
  grid.append(rc);

  const tp = UI.panel(grid, { label: "Sensitivity", title: C.tornado, height: 230 });
  /* widest-impact assumption on top (classic tornado shape); bars are keyed
     to which END of the stated range moved (low estimate vs high estimate),
     not to the dollar sign \u2014 the old "Downside/Upside" split grouped bars by
     sign instead, which silently flipped which color meant what for
     Investment (where a *higher* input is worse, not better). */
  const sorted = [...R.tornado].sort((a, b) => Math.abs(b.hi - b.lo) - Math.abs(a.hi - a.lo));
  const tChart = CH.barsH(tp.canvas, {
    labels: sorted.map((t) => t.label),
    datasets: [
      { label: "Low estimate", data: sorted.map((t) => t.lo), backgroundColor: T.seriesBenchmark, barPercentage: 0.6 },
      { label: "High estimate", data: sorted.map((t) => t.hi), backgroundColor: T.seriesHeadline, barPercentage: 0.6 },
    ],
    xFmt: (v) => (v > 0 ? "+" : v < 0 ? "\u2212" : "") + FMT.usd(Math.abs(v)),
  });
  tChart.options.scales.x.grid.color = T.grid;
  tChart.update();
  tp.panel.append(el("p", "panel-note",
    "Each bar re-runs the base case with one assumption moved to the low or high end of its stated range (shown in parentheses), holding everything else fixed. Sorted by size of swing in net value."));
  tp.bindExport(tChart, "fifa-financial-sensitivity");
  root.append(grid);
};