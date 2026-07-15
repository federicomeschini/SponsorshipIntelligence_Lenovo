/* V6 — Return: value waterfall + terminal ROI, live scenario control,
   licensing cross-check, sensitivity tornado. Signature moment: the
   scenario control re-runs the waterfall live. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.return = function (root) {
  const D = window.SRMP_DEMO, C = COPY.return, T = THEME, { el } = UI;
  const R = D.roi;

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  /* scenario control */
  const bar = el("div", "scenario-bar reveal");
  bar.append(el("span", "lbl", C.scenario));
  const seg = el("div", "oe-segment");
  seg.setAttribute("role", "group");
  const formula = el("span", "credential");
  ["conservative", "base", "ambitious"].forEach((k) => {
    const b = el("button", "oe-segment__btn" + (k === "base" ? " is-active" : ""), C.scenarios[k]);
    b.type = "button";
    b.dataset.k = k;
    seg.append(b);
  });
  bar.append(seg, formula);
  root.append(bar);

  /* hero: waterfall + terminal panel */
  const heroRow = el("div", "roi-hero reveal");
  const wfPanel = el("div", "oe-panel");
  wfPanel.append(el("div", "oe-panel__head", `<div><div class="oe-panel__label">Chart 1</div><p class="oe-panel__title">${C.hero}</p></div>`));
  const wfBox = el("div", "chart-box");
  wfBox.style.height = "360px";
  const wfCanvas = document.createElement("canvas");
  wfBox.append(wfCanvas);
  wfPanel.append(wfBox);
  const terminal = el("div", "roi-terminal");
  const roiMult = el("div", "roi-mult oe-num");
  const roiNet = el("div", "roi-net");
  terminal.append(el("span", "oe-tag-chip oe-tag-chip--on-dark", "Return multiple"), roiMult, roiNet);
  heroRow.append(wfPanel, terminal);
  root.append(heroRow);

  let wfChart = null;
  function renderScenario(k) {
    const s = R.scenarios[k];
    formula.textContent = C.formulaNote(s.deltaIndex);
    const steps = [
      { label: C.steps.annual, range: [0, s.annualUsd], color: T.seriesHeadlineDeep, printed: FMT.usd(s.annualUsd) + "/yr" },
      { label: C.steps.persistence + " ×" + s.persistenceYears, range: [s.annualUsd, s.grossUsd], color: T.seriesHeadline, printed: "+" + FMT.usd(s.grossUsd - s.annualUsd) },
      { label: C.steps.gross, range: [0, s.grossUsd], color: T.seriesHeadlineDeep, printed: FMT.usd(s.grossUsd) },
      { label: C.steps.investment, range: [s.grossUsd - s.investmentUsd, s.grossUsd], color: T.seriesSecondary, printed: "−" + FMT.usd(s.investmentUsd) },
      { label: C.steps.net, range: [0, s.netUsd], color: "#270065", printed: FMT.usd(s.netUsd) },
    ];
    if (wfChart) wfChart.destroy();
    wfChart = CH.waterfall(wfCanvas, { steps, yFmt: FMT.usd });
    FMT.countUp(roiMult, s.roiMultiple, FMT.mult, 700);
    roiNet.innerHTML = `<b>${FMT.usd(s.netUsd)}</b> net brand value created — every US$1 invested returned <b>US$${s.roiMultiple.toFixed(2)}</b>.`;
  }
  seg.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    seg.querySelectorAll("button").forEach((x) => x.classList.toggle("is-active", x === b));
    renderScenario(b.dataset.k);
  });
  renderScenario("base");

  /* supporting: licensing cross-check + tornado */
  const grid = el("div", "panel-grid");
  const rc = el("div", "oe-panel reveal");
  rc.append(el("div", "oe-panel__head", `<div><div class="oe-panel__label">Cross-check</div><p class="oe-panel__title">${C.royalty}</p></div>`));
  const rv = R.royaltyView;
  rc.append(el("div", "stat-num oe-num", FMT.usd(rv.lowUsd) + " – " + FMT.usd(rv.highUsd)));
  rc.append(el("p", "panel-note", C.royaltyNote(rv.lowUsd, rv.highUsd) + " Schedule: " +
    rv.schedule.map((p) => `${p.indexPoints.toFixed(1)} pts → ${FMT.usd(p.usdPerYear)}/yr`).join(" · ")));
  grid.append(rc);

  const tp = UI.panel(grid, { label: "Chart 2", title: C.tornado, height: 220 });
  const tChart = CH.barsH(tp.canvas, {
    labels: R.tornado.map((t) => t.label),
    datasets: [
      { label: "Downside", data: R.tornado.map((t) => Math.min(t.lo, t.hi)), backgroundColor: T.seriesBenchmark, barPercentage: 0.6 },
      { label: "Upside", data: R.tornado.map((t) => Math.max(t.lo, t.hi)), backgroundColor: T.seriesHeadline, barPercentage: 0.6 },
    ],
    xFmt: (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + FMT.usd(Math.abs(v)).replace("US$", "US$"),
  });
  tChart.options.scales.x.grid.color = T.grid;
  tChart.update();
  tp.panel.append(el("p", "panel-note", "Change in net value vs. the base case."));
  tp.bindExport(tChart, "return-sensitivity");
  root.append(grid);
};
