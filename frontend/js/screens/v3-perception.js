/* V3 — Perception: aware-vs-unaware funnel with lift chips, heat strip,
   stat cards. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.perception = function (root) {
  const D = window.SRMP_DEMO, C = COPY.perception, T = THEME, { el } = UI;

  UI.screenHead(root, { kicker: C.kicker, title: C.title, insight: C.insight });

  /* hero funnel */
  const grid = el("div", "panel-grid panel-grid--hero");
  const fp = UI.panel(grid, { label: "Chart 1", title: C.hero, height: 0 });
  fp.panel.querySelector(".chart-box").remove();
  fp.hideExport();
  const legend = el("div", "funnel-legend",
    `<span><i style="background:var(--oe-accent)"></i>${C.aware}</span>` +
    `<span><i style="background:var(--oe-gray-300)"></i>${C.unaware}</span>`);
  const funnel = el("div", "funnel");
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
  root.append(grid);

  /* heat strip: lift by property × wave */
  const waves = [...new Set(D.funnel.map((r) => r.wave))].sort();
  const rows = [];
  ["fwc", "fwwc", "fcwc"].forEach((p) =>
    ["appeal", "purchase_intent"].forEach((s) => rows.push([p, s])));
  const hpPanel = UI.panel(root, { label: "Chart 2", title: C.heat, height: 0 });
  hpPanel.panel.querySelector(".chart-box").remove();
  hpPanel.hideExport();
  const heat = el("div", "heat");
  heat.style.gridTemplateColumns = `200px repeat(${waves.length}, 1fr)`;
  heat.append(el("div", "heat-head", ""));
  waves.forEach((w) => heat.append(el("div", "heat-head", FMT.monthYear(w + "-01"))));
  const all = D.funnel.filter((r) => r.stage !== "awareness").map((r) => r.lift);
  const lo = Math.min(...all), hi = Math.max(...all);
  rows.forEach(([p, s]) => {
    heat.append(el("div", "heat-rowhead", `${UI.PROP_NAMES[p]} · ${UI.STAGE_NAMES[s]}`));
    waves.forEach((w) => {
      const r = D.funnel.find((x) => x.wave === w && x.property === p && x.stage === s);
      const cell = el("div", "heat-cell oe-num");
      if (r) {
        const f = (r.lift - lo) / (hi - lo);
        const ramp = T.seqRamp;
        cell.style.background = ramp[Math.min(ramp.length - 1, Math.round(f * (ramp.length - 1)))];
        cell.style.color = f > 0.55 ? "#fff" : "var(--oe-gray-900)";
        cell.textContent = FMT.pp(r.lift);
        cell.title = `${UI.PROP_NAMES[p]} · ${UI.STAGE_NAMES[s]} · wave ${w}`;
      } else {
        cell.style.background = "var(--oe-gray-100)";
        cell.textContent = "·";
        cell.style.color = "var(--oe-gray-400)";
      }
      heat.append(cell);
    });
  });
  hpPanel.panel.append(heat, el("p", "panel-note", C.heatNote));

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
