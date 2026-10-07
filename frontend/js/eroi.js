/* ==========================================================================
   EROI — Event Return on Investment · Lenovo × FIFA case (FE-009)
   A Summary landing view plus three sequential chapters (Exposure ->
   Evaluation -> Monetization) and a Method page, navigated through a
   horizontal process-arrow bar. Every figure comes from window.EROI, which
   frontend/scripts/build_eroi_data.py builds from the production pipeline;
   the page formats and draws, it does not estimate. The only arithmetic here
   is the optional programme-cost multiple the viewer types in.
   ========================================================================== */
(function () {
  "use strict";
  const E = window.EROI;
  const X = E.exposure, V = E.evaluation, M = E.monetization;
  const FS = X.fifaSpecific;

  /* ------------------------------------------------------------- theme --- */
  const T = {
    ink: "#000000", muted: "#6E6E6E", grid: "#E7E7E7",
    brand: "#5902EE", brandDeep: "#4400B3", brandLight: "#B991FF", brandPale: "#EFE5FF",
    counterfactual: "#999999", peer: "#D2D2D2", peerLine: "#545454",
    lime: "#B9FF69", limeInk: "#458300", gap: "rgba(185,255,105,.55)",
    magenta: "#C300C3", deep: "#270065",
    mono: '"Atkinson Hyperlegible Mono", ui-monospace, Menlo, monospace',
    sans: '"Atkinson Hyperlegible Next", -apple-system, Arial, sans-serif',
  };

  /* ------------------------------------------------------------ format --- */
  function trim(x) {
    const s = Math.abs(x) >= 100 ? Math.round(x).toString() : x.toFixed(1);
    return s.endsWith(".0") ? s.slice(0, -2) : s;
  }
  const F = {
    big(v) {
      const a = Math.abs(v);
      if (a >= 1e9) return trim(v / 1e9) + "B";
      if (a >= 1e6) return trim(v / 1e6) + "M";
      if (a >= 1e3) return trim(v / 1e3) + "K";
      return String(Math.round(v));
    },
    usd: (v) => (v < 0 ? "−US$" + F.big(-v) : "US$" + F.big(v)),
    pts: (v, s = true) => (s && v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(2) + " pts",
    pctv: (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d) + "%",
    pct: (v, d = 1) => (v * 100).toFixed(d) + "%",
    pp: (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(2) + " pp",
    mult: (v) => v.toFixed(1) + "×",
    p: (v) => (v < 0.001 ? "< 0.001" : v.toFixed(3)),
    month(w) { return new Date(w + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" }); },
    day(w) { return new Date(w + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }); },
  };

  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------------------ charts --- */
  Chart.defaults.locale = "en-US";
  Chart.defaults.font.family = T.mono;
  Chart.defaults.font.size = 11;
  Chart.defaults.color = T.muted;
  Chart.defaults.borderColor = T.grid;
  Chart.defaults.animation.duration = reduced ? 0 : 650;
  Chart.defaults.plugins.legend.display = false;
  Chart.defaults.plugins.tooltip.backgroundColor = T.deep;
  Chart.defaults.plugins.tooltip.cornerRadius = 0;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.titleFont = { family: T.mono, size: 11 };
  Chart.defaults.plugins.tooltip.bodyFont = { family: T.mono, size: 12 };
  Chart.defaults.plugins.tooltip.displayColors = false;

  /* dashed verticals for the milestones that anchor the whole story */
  Chart.register({
    id: "milestones",
    afterDatasetsDraw(chart, _a, opts) {
      if (!opts || !opts.items) return;
      const { ctx, chartArea, scales } = chart;
      ctx.save();
      ctx.font = "700 10px " + T.mono;
      let lane = 0, lastEnd = -1e9;
      opts.items.forEach((m) => {
        const px = scales.x.getPixelForValue(m.i);
        if (px < chartArea.left || px > chartArea.right) return;
        ctx.strokeStyle = T.brandLight;
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(px, chartArea.top + 22); ctx.lineTo(px, chartArea.bottom); ctx.stroke();
        ctx.setLineDash([]);
        const label = m.label.toUpperCase();
        const w = ctx.measureText(label).width;
        const right = px > chartArea.right - w - 8;
        const x0 = right ? px - w - 4 : px + 4;
        lane = x0 <= lastEnd + 6 ? (lane + 1) % 2 : 0;
        lastEnd = x0 + w;
        ctx.fillStyle = T.brandDeep;
        ctx.fillText(label, x0, chartArea.top + 8 + lane * 12);
      });
      ctx.restore();
    },
  });

  const live = [];
  const make = (canvas, cfg) => { const c = new Chart(canvas.getContext("2d"), cfg); live.push(c); return c; };
  const killAll = () => { while (live.length) live.pop().destroy(); };

  function weekTicks(weeks) {
    return {
      autoSkip: false, maxRotation: 0,
      callback(v) {
        const w = weeks[v];
        if (!w) return "";
        const d = new Date(w + "T00:00:00");
        if (weeks.length > 130) return d.getMonth() === 0 && d.getDate() <= 7 ? d.getFullYear() : "";
        if (weeks.length <= 40) return v % 4 === 0 ? d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "";
        return d.getDate() <= 7 && d.getMonth() % 3 === 0 ? d.toLocaleDateString("en-US", { month: "short", year: "2-digit" }) : "";
      },
    };
  }

  function lineChart(canvas, o) {
    const ds = (o.series || []).map((s) => ({
      label: s.label, data: s.data,
      borderColor: s.color, backgroundColor: s.fillColor || "transparent",
      fill: s.fill || false, borderDash: s.dash || [], borderWidth: s.width || 2,
      pointRadius: 0, pointHitRadius: 8, tension: s.tension != null ? s.tension : 0.25,
      spanGaps: true, order: s.order || 0,
    }));
    return make(canvas, {
      type: "line",
      data: { labels: o.weeks, datasets: ds },
      options: {
        maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: weekTicks(o.weeks) },
          y: {
            min: o.min, max: o.max, grid: { color: T.grid }, border: { display: false },
            title: o.yTitle ? { display: true, text: o.yTitle, color: T.muted, font: { family: T.mono, size: 10 } } : undefined,
            ticks: o.yFmt ? { callback: o.yFmt } : undefined,
          },
        },
        plugins: {
          milestones: { items: o.milestones || [] },
          tooltip: {
            filter: (i) => !String(i.dataset.label || "").startsWith("_"),
            callbacks: {
              title: (i) => F.month(o.weeks[i[0].dataIndex]),
              label: (c) => c.dataset.label + "  " + (o.tip ? o.tip(c.parsed.y) : c.parsed.y),
            },
          },
        },
      },
    });
  }

  function barsH(canvas, o) {
    return make(canvas, {
      type: "bar",
      data: { labels: o.labels, datasets: [{ data: o.values, backgroundColor: o.colors || T.brandDeep, borderWidth: 0, barPercentage: 0.72 }] },
      options: {
        indexAxis: "y", maintainAspectRatio: false,
        scales: {
          x: { grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => (o.xFmt ? o.xFmt(v) : v) } },
          y: { grid: { display: false }, border: { display: false }, ticks: { font: { family: T.sans, size: 12 }, color: T.ink } },
        },
        plugins: { tooltip: { callbacks: { label: (c) => (o.xFmt ? o.xFmt(c.parsed.x) : c.parsed.x) } } },
      },
    });
  }

  function barsV(canvas, o) {
    return make(canvas, {
      type: "bar",
      data: { labels: o.labels, datasets: [{ data: o.values, backgroundColor: o.colors || T.brandDeep, borderWidth: 0, barPercentage: 0.7 }] },
      options: {
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, border: { display: false }, ticks: o.xTicks || { maxRotation: 0, autoSkip: true } },
          y: { grid: { color: T.grid }, border: { display: false }, beginAtZero: true, ticks: { callback: (v) => (o.yFmt ? o.yFmt(v) : v) },
               title: o.yTitle ? { display: true, text: o.yTitle, color: T.muted, font: { family: T.mono, size: 10 } } : undefined },
        },
        plugins: {
          milestones: { items: o.milestones || [] },
          tooltip: { callbacks: { title: (i) => (o.tipTitle ? o.tipTitle(i[0].dataIndex) : i[0].label), label: (c) => (o.yFmt ? o.yFmt(c.parsed.y) : c.parsed.y) } },
        },
      },
    });
  }

  /* break a label into lines of about n characters, on word boundaries */
  function wrap(label, n) {
    const lines = [];
    label.split(" ").forEach((w) => {
      const last = lines[lines.length - 1];
      if (last && (last + " " + w).length <= n) lines[lines.length - 1] = last + " " + w;
      else lines.push(w);
    });
    return lines.length > 1 ? lines : label;
  }

  /* waterfall: floating bars carrying a running total */
  function waterfall(canvas, o) {
    let run = 0;
    const bars = o.steps.map((s) => {
      if (s.total) { run = s.value; return { x: [0, s.value], c: s.color, v: s.value }; }
      const from = run; run += s.value;
      return { x: [from, run], c: s.color, v: s.value };
    });
    const labelPlugin = {
      id: "wfLabels",
      afterDatasetsDraw(chart) {
        const { ctx, scales } = chart;
        ctx.save();
        ctx.font = "700 11px " + T.mono; ctx.textAlign = "center"; ctx.fillStyle = T.ink;
        chart.getDatasetMeta(0).data.forEach((bar, i) => {
          const s = o.steps[i], b = bars[i];
          const top = Math.min(scales.y.getPixelForValue(b.x[0]), scales.y.getPixelForValue(b.x[1]));
          const txt = (s.total ? "" : b.v > 0 ? "+" : "−") + o.fmt(Math.abs(b.v));
          ctx.fillText(txt, bar.x, top - 8);
        });
        ctx.restore();
      },
    };
    return make(canvas, {
      type: "bar",
      data: { labels: o.steps.map((s) => s.label), datasets: [{ data: bars.map((b) => b.x), backgroundColor: bars.map((b) => b.c), borderWidth: 0, barPercentage: 0.62 }] },
      options: {
        maintainAspectRatio: false, layout: { padding: { top: 26 } },
        scales: {
          x: { grid: { display: false }, border: { display: false }, ticks: { font: { family: T.sans, size: 12 }, color: T.ink, maxRotation: 0, autoSkip: false, callback(v) { return wrap(this.getLabelForValue(v), 14); } } },
          y: { grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => o.fmt(v) }, beginAtZero: true },
        },
        plugins: { tooltip: { callbacks: { label: (c) => o.fmt(Math.abs(bars[c.dataIndex].v)) } } },
      },
      plugins: [labelPlugin],
    });
  }

  function scatter(canvas, o) {
    return make(canvas, {
      type: "scatter",
      data: {
        datasets: [
          { type: "scatter", label: "Weekly observation", data: o.points, pointRadius: 3, pointHoverRadius: 5, borderWidth: 0,
            backgroundColor: (c) => (o.points[c.dataIndex] && o.points[c.dataIndex].post ? "rgba(89,2,238,.7)" : "rgba(153,153,153,.55)") },
          { type: "line", label: "_fit", data: o.fit, borderColor: T.brandDeep, borderWidth: 2.5, pointRadius: 0, fill: false },
        ],
      },
      options: {
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: T.grid }, border: { display: false }, title: { display: true, text: o.xTitle, color: T.muted, font: { family: T.mono, size: 10 } } },
          y: { grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => (v * 100).toFixed(0) + "%" }, title: { display: true, text: o.yTitle, color: T.muted, font: { family: T.mono, size: 10 } } },
        },
        plugins: {
          tooltip: {
            filter: (i) => !String(i.dataset.label || "").startsWith("_"),
            callbacks: {
              title: (i) => (o.points[i[0].dataIndex] ? F.month(o.points[i[0].dataIndex].w) : ""),
              label: (c) => "Unexpected BI move " + c.parsed.x.toFixed(2) + " pts  ·  abnormal return " + (c.parsed.y * 100).toFixed(2) + "%",
            },
          },
        },
      },
    });
  }

  function sparkline(canvas, data, color, fillColor) {
    return make(canvas, {
      type: "line",
      data: { labels: data.map((_, i) => i), datasets: [{ data, borderColor: color, backgroundColor: fillColor, fill: !!fillColor, borderWidth: 1.6, pointRadius: 0, tension: 0.3, spanGaps: true }] },
      options: { maintainAspectRatio: false, animation: false, scales: { x: { display: false }, y: { display: false } }, plugins: { tooltip: { enabled: false } } },
    });
  }

  /* -------------------------------------------------------- milestones --- */
  const SHORT = {
    fifa_partner_announcement_2024: "Deal announced",
    fcwc_partner_announcement_2025: "FCWC deal",
    fcwc_opening_2025: "Club WC",
    wc_opening_2026: "World Cup",
    wc_final_2026: "Final",
  };
  const ev = (id) => E.events.find((e) => e.id === id);
  function marksFor(weeks, ids) {
    return E.events.filter((e) => ids.includes(e.id)).map((e) => {
      const i = weeks.findIndex((w) => w >= e.date);
      return i < 0 ? null : { i, label: SHORT[e.id] || e.name };
    }).filter(Boolean);
  }
  const KEY_MARKS = ["fifa_partner_announcement_2024", "fcwc_opening_2025", "wc_opening_2026"];

  /* ------------------------------------------------------------ blocks --- */
  function head(root, o) {
    const h = el("section", "head reveal");
    h.append(el("span", "head-kicker", o.kicker));
    h.append(el("h2", null, o.title));
    if (o.lead) h.append(el("p", "head-lead", o.lead));
    root.append(h);
  }
  function flow(root, cells, opts) {
    const f = el("div", "flow reveal" + (opts && opts.tall ? " flow--tall" : ""));
    cells.forEach((cell) => {
      const d = el("div", "flow-cell " + (cell.cls || ""));
      d.append(el("div", "flow-k", cell.k));
      if (cell.v) d.append(el("div", "flow-v", cell.v));
      if (cell.d) d.append(el("div", "flow-d", cell.d));
      f.append(d);
    });
    root.append(f);
    return f;
  }
  function panel(root, o) {
    const p = el("div", "panel reveal " + (o.cls || ""));
    if (o.label) p.append(el("div", "panel-label", o.label));
    if (o.title) p.append(el("h3", "panel-title", o.title));
    if (o.sub) p.append(el("p", "panel-sub", o.sub));
    root.append(p);
    return p;
  }
  function chartIn(p, height) {
    const box = el("div", "chart");
    box.style.height = height + "px";
    const cv = document.createElement("canvas");
    box.append(cv);
    p.append(box);
    return cv;
  }
  function legend(p, items) {
    const l = el("div", "legend");
    items.forEach((it) => {
      const s = el("span");
      const i = el("i", it.dash ? "dash" : it.square ? "sq" : "");
      i.style.background = it.dash ? "none" : it.color;
      i.style.color = it.color;
      if (it.dash) i.style.backgroundImage = `repeating-linear-gradient(90deg, ${it.color} 0 4px, transparent 4px 8px)`;
      s.append(i, document.createTextNode(it.label));
      l.append(s);
    });
    p.append(l);
  }
  const note = (p, html) => p.append(el("p", "panel-note", html));
  const src = (p, txt) => p.append(el("p", "panel-src", txt));
  function readout(p, rows) {
    const r = el("div", "readout");
    rows.forEach(([k, v]) => { const d = el("div"); d.append(el("span", "k", k), el("span", "v", v)); r.append(d); });
    p.append(r);
  }
  function kpiRow(root, items) {
    const g = el("div", "kpis reveal");
    items.forEach((it) => {
      const c = el("div", "kpi");
      c.append(el("div", "kpi-v", it.v), el("div", "kpi-k", it.k));
      if (it.n) c.append(el("div", "kpi-n", it.n));
      g.append(c);
    });
    root.append(g);
  }
  function table(p, headers, rows, opts) {
    const tb = el("table", "tbl");
    tb.innerHTML = "<thead><tr>" + headers.map((h) => `<th${h.num ? " class='num'" : ""}>${h.t || h}</th>`).join("") + "</tr></thead>";
    const body = el("tbody");
    rows.forEach((r, i) => {
      const tr = el("tr", opts && opts.primary === i ? "is-primary" : "");
      tr.innerHTML = r.map((c, j) => `<td${headers[j].num ? " class='num'" : ""}>${c}</td>`).join("");
      body.append(tr);
    });
    tb.append(body);
    p.append(tb);
  }
  function grid(root) { const g = el("div", "grid"); root.append(g); return g; }
  function col(g, span) { const c = el("div", "c" + span); g.append(c); return c; }

  /* uncertainty band for the primary estimate, drawn in the brand's own figure language */
  function bandFigure(p) {
    const lo = FS.statistical_band_95_index_points[0], hi = FS.statistical_band_95_index_points[1];
    const up = FS.attribution_band_upper_index_points, mid = FS.primary_index_points;
    const max = Math.max(hi, up) * 1.12;
    const at = (v) => (Math.max(0, v) / max) * 100 + "%";
    const b = el("div", "band");
    b.append(el("div", "band-track"));
    const rg = el("div", "band-range"); rg.style.left = at(lo); rg.style.width = `calc(${at(hi)} - ${at(lo)})`; b.append(rg);
    const u = el("div", "band-upper"); u.style.left = at(up); b.append(u);
    const d = el("div", "band-dot"); d.style.left = at(mid); b.append(d);
    p.append(b);
    p.append(el("div", "band-labels", `<span>0</span><span>95% band ${lo.toFixed(1)}–${hi.toFixed(1)} · whole gap ${up.toFixed(1)}</span>`));
  }

  /* ------------------------------------------------- shared state & text --- */
  let scenarioKey = "base";
  let programmeCost = null;
  const LAB = { conservative: "Conservative", base: "Base", ambitious: "Ambitious" };
  const D = V.dcf, FAC = V.factor;               // ADR-0045: every money figure comes from the income split
  const B = { brandValue: D.brandValue, valuePerPoint: D.valuePerPoint };
  const S = () => M.scenarios[scenarioKey];

  /* ============================================================ VIEW 1 === */
  function viewExposure(root) {
    const K = X.kpi, D = X.design, d = FS.decomposition_index_points;

    head(root, {
      kicker: "Step 01 · Exposure",
      title: "How much more did Lenovo stand out because of FIFA?",
      lead: `FIFA properties delivered ${F.big(K.eventImpressions)} measured digital impressions for Lenovo. Because the whole PC market moved in these two years, the brand is measured as its <em>share</em> of attention against rival brands and compared with a synthetic Lenovo built from ${D.donors.length} rivals with no part in the FIFA deal. The part of that gap explained by FIFA exposure is then isolated.`,
    });

    flow(root, [
      { k: "The event", v: F.big(K.eventImpressions) + " impressions", d: "FIFA-family digital and social exposure (Blinkfire)" },
      { k: "The control", v: D.donors.length + " rival brands", d: "A synthetic, no-sponsorship Lenovo chosen on pre-announcement evidence only", cls: "flow-cell--mid" },
      { k: "Output → Evaluation", v: F.pts(FS.primary_index_points) + " FIFA-specific", d: `≈ ${F.pctv(FS.primary_uplift_pct)} brand share of attention · total gap ${F.pts(X.total.lift)} is the ceiling`, cls: "flow-cell--out" },
    ]);

    kpiRow(root, [
      { v: F.big(K.eventImpressions), k: "FIFA exposure delivered", n: `${F.big(K.eventViews)} video views across FIFA properties, ${F.day(X.event.weeks[0])} to ${F.day(X.event.coverageEnd)}.` },
      { v: F.pctv(K.brandDrift), k: "Lenovo searches vs own baseline", n: "Average since the announcement, against Lenovo's own pre-announcement mean." },
      { v: F.pctv(K.peerDrift), k: "Rival brands, same window", n: `Median of ${K.peerCount} rival brands, each against its own pre-announcement mean.` },
      { v: F.pts(K.netDrift), k: "Lenovo ahead of its rivals", n: `Rising to ${F.pts(K.netDriftLate)} over the latest six months.` },
    ]);

    /* --- brand vs rivals --------------------------------------------------- */
    const g1 = grid(root);
    const pA = panel(col(g1, 12), {
      label: "The comparable test",
      title: `Lenovo, and ${K.peerCount} rival brands the FIFA deal never touched`,
      sub: "Worldwide weekly search interest, each series re-based to 100 on its own average before the announcement (4-week averages). The whole market rose; what matters is how much further Lenovo went.",
    });
    const cvA = chartIn(pA, 380);
    lineChart(cvA, {
      weeks: X.peerWeeks,
      series: [
        ...X.peers.map((p) => ({ label: p.name, data: p.series, color: "rgba(175,175,175,.5)", width: 1, tension: 0.3, order: 5 })),
        { label: "Rival median", data: X.peerComposite, color: T.peerLine, width: 2.4, dash: [6, 4], order: 2 },
        { label: "Lenovo", data: X.brandSearch, color: T.brand, width: 3, order: 1 },
      ],
      milestones: marksFor(X.peerWeeks, KEY_MARKS),
      yTitle: "Search index · 100 = own pre-announcement mean",
      tip: (v) => (v == null ? "—" : v.toFixed(0)),
    });
    legend(pA, [
      { color: T.brand, label: "Lenovo" },
      { color: T.peerLine, label: "Median of the rival brands", dash: true },
      { color: "#AFAFAF", label: K.peerCount + " individual rival brands" },
    ]);
    note(pA, `<b>How to read it.</b> Searches for every PC brand rose after 2024 (Windows 10 end of support, the spring 2026 price surge). Lenovo rose more: <b>${F.pctv(K.brandDrift)}</b> against ${F.pctv(K.peerDrift)} for the rival median since the announcement, ${F.pctv(K.brandDriftLate)} against ${F.pctv(K.peerDriftLate)} in the latest six months. The Brand Index measures exactly that difference: Lenovo's share of the attention its rivals also receive.`);
    src(pA, "Source: Google Trends, jointly scaled panels with a common Lenovo anchor · Elaboration: OpenEconomics");

    /* --- the platform ------------------------------------------------------ */
    const g2 = grid(root);
    const pB = panel(col(g2, 7), { label: "The platform", title: "Exposure delivered by FIFA properties", sub: "Weekly digital and social impressions in which Lenovo is visible across the FIFA property portfolio." });
    const cvB = chartIn(pB, 300);
    barsV(cvB, {
      labels: X.event.weeks, values: X.event.impressions, colors: T.brandDeep,
      xTicks: weekTicks(X.event.weeks), yFmt: (v) => F.big(v), tipTitle: (i) => F.month(X.event.weeks[i]),
      milestones: marksFor(X.event.weeks, KEY_MARKS),
    });
    note(pB, `Exposure is concentrated in tournament windows; the World Cup alone delivered ${F.big(X.byProperty[0].impressions)} impressions (digital and social, through ${F.day(X.event.coverageEnd)}).`);
    src(pB, "Source: Blinkfire Analytics (client exports) · Elaboration: OpenEconomics");
    const pC = panel(col(g2, 5), { label: "Composition", title: "Which social media delivered it", sub: "Digital impressions by FIFA social media account over the partnership window." });
    const cvC = chartIn(pC, 300);
    barsH(cvC, {
      labels: X.byProperty.map((p) => p.label), values: X.byProperty.map((p) => p.impressions),
      colors: X.byProperty.map((_, i) => (i === 0 ? T.brandDeep : i < 3 ? T.brand : T.brandLight)), xFmt: (v) => F.big(v),
    });
    src(pC, "Source: Blinkfire Analytics · Elaboration: OpenEconomics");

    /* --- synthetic control ------------------------------------------------- */
    const g3 = grid(root);
    const pD = panel(col(g3, 7), {
      label: "From relative attention to a measurable increment",
      title: "The Brand Index against its no-sponsorship twin",
      sub: "Brand Index: Lenovo's weekly share of attention against rival brands, informed by the quarterly GWI survey (100 = pre-announcement average). The twin is a weighted mix of rival brands that reproduces Lenovo before the deal; the shaded distance afterwards is the gap.",
    });
    const cvD = chartIn(pD, 330);
    lineChart(cvD, {
      weeks: X.core.weeks,
      series: [
        { label: "Without the sponsorship", data: X.core.synthetic, color: T.counterfactual, width: 2, dash: [6, 4], order: 2 },
        { label: "Lenovo — actual", data: X.core.actual, color: T.brand, width: 2.6, fill: "-1", fillColor: T.gap, order: 1 },
      ],
      milestones: marksFor(X.core.weeks, [...KEY_MARKS, "wc_final_2026"]),
      yTitle: "Brand Index · 100 = pre-announcement",
      tip: (v) => (v == null ? "—" : v.toFixed(1)),
    });
    legend(pD, [
      { color: T.brand, label: "Lenovo — actual Brand Index" },
      { color: T.counterfactual, label: "Estimated without the sponsorship", dash: true },
      { color: T.lime, label: "Gap", square: true },
    ]);
    note(pD, `Before the announcement the two lines track each other within <b>${D.preRmspe.toFixed(1)} points</b> (root-mean-square). The design (${D.method.replace(/_/g, " ")}, ${D.donors.length} rivals) was chosen on how well it predicted Lenovo before the deal, never on the result.`);
    src(pD, "Sources: Google Trends joint panel · GWI survey · Synthetic control: OpenEconomics (ADR-0038, ADR-0040)");

    const pE = panel(col(g3, 5), { cls: "panel--dark", label: "Total gap · the ceiling" });
    pE.append(el("div", "figure-v lime", F.pts(X.total.lift)));
    pE.append(el("div", "figure-k", `≈ ${F.pctv(X.total.upliftPct)} brand share · ${X.total.weeks} weeks since the announcement`));
    readout(pE, [
      ["Significance against rival brands", `p = ${D.placeboP.toFixed(3)}`],
      ["Leaving out one rival", `${F.pts(D.looRange[0])} to ${F.pts(D.looRange[1])}`],
      ["Specifications positive", `${Math.round(D.sharePositive * 100)}% of ${D.specs}`],
      ["Without the spring 2026 surge", F.pts(D.exSurge.lift)],
      ["Rival brands in the twin", String(D.donors.length)],
    ]);
    note(pE, "This is everything that separates Lenovo from its rivals since the deal, FIFA or otherwise. The next panels split it.");

    /* --- FIFA vs other sponsorships ---------------------------------------- */
    const g4 = grid(root);
    const pF = panel(col(g4, 7), {
      label: "FIFA or Lenovo's other sponsorships?",
      title: "Exposure from FIFA and from F1, MotoGP, Ducati and NHL",
      sub: "Adstocked weekly exposure (impressions carried over at 80% a week). Motorsport ran long before FIFA, so its exposure before Blinkfire coverage is back-cast from its own season profile and co-brand search; the dotted line is its usual, pre-FIFA level.",
    });
    const SP = X.sponsorships;
    const cvF = chartIn(pF, 300);
    lineChart(cvF, {
      weeks: SP.weeks,
      series: [
        { label: "Other sponsorships", data: SP.other, color: T.peerLine, width: 1.8, order: 2 },
        { label: "Other sponsorships · pre-FIFA level", data: SP.otherBaseline, color: T.peerLine, width: 1.4, dash: [2, 3], order: 3 },
        { label: "FIFA", data: SP.fifa, color: T.brand, width: 2.6, order: 1 },
      ],
      milestones: marksFor(SP.weeks, KEY_MARKS),
      yTitle: "Adstock · millions of impressions",
      tip: (v) => (v == null ? "—" : v.toFixed(0) + "M"),
    });
    legend(pF, [
      { color: T.brand, label: "FIFA properties" },
      { color: T.peerLine, label: `Other sponsorships (back-cast to ${F.month(SP.backcastEnd)})` },
      { color: T.peerLine, label: "Other sponsorships at their pre-FIFA level", dash: true },
    ]);
    const tt = X.timingTests;
    note(pF, `Before FIFA existed, motorsport race weeks did not move Lenovo's gap (${tt["pre_period_nonfifa:levels_with_trend"].nonfifa_log_adstock.points_per_sd >= 0 ? "+" : "−"}${Math.abs(tt["pre_period_nonfifa:levels_with_trend"].nonfifa_log_adstock.points_per_sd).toFixed(2)} pts per s.d., p = ${tt["pre_period_nonfifa:levels_with_trend"].nonfifa_log_adstock.p.toFixed(2)}): that exposure is already in the twin. After the deal, other sponsorships ran above their usual level (F1 ${SP.properties.find((p) => p.id === "f1").observedOverBaseline}× after its 2025 upgrade) but never line up with the gap, while accumulated FIFA exposure does (${F.pts(tt["full_sample:levels_with_trend"].fifa_log_adstock.points_per_sd)} per s.d., p = ${F.p(tt["full_sample:levels_with_trend"].fifa_log_adstock.p)}).`);
    src(pF, "Sources: Blinkfire Analytics · co-brand Google search · Diagnostic: sponsorship_exposure_timing_v1 (ADR-0042)");

    const pG = panel(col(g4, 5), { label: "Splitting the gap", title: "What explains the gap", sub: `Average gap over the ${FS.weeks} weeks with exposure data, split by a regression on accumulated FIFA exposure, with controls and a trend.` });
    const cvG = chartIn(pG, 300);
    waterfall(cvG, {
      steps: [
        { label: "Whole gap", value: d.total_gap, total: true, color: T.counterfactual },
        { label: "Not attributed to FIFA", value: d.fifa - d.total_gap, color: T.peer },
        { label: "FIFA-specific", value: d.fifa, total: true, color: T.brandDeep },
      ],
      fmt: (v) => v.toFixed(2),
    });
    note(pG, `Of the ${F.pts(d.total_gap)} gap, <b>${F.pts(d.fifa)}</b> is explained by FIFA exposure and is the primary estimate; the remaining ${F.pts(d.total_gap - d.fifa)} is not attributed to FIFA.`);

    /* --- output ------------------------------------------------------------- */
    const g5 = grid(root);
    const pH = panel(col(g5, 5), { cls: "panel--dark", label: "Output of step 01 · primary estimate" });
    pH.append(el("div", "figure-v lime", F.pts(FS.primary_index_points)));
    pH.append(el("div", "figure-k", `FIFA-specific effect ≈ ${F.pctv(FS.primary_uplift_pct)} brand share of attention`));
    bandFigure(pH);
    readout(pH, [
      ["95% statistical band", `${F.pctv(FS.statistical_band_95_uplift_pct[0])} to ${F.pctv(FS.statistical_band_95_uplift_pct[1])}`],
      ["Ceiling (whole gap, same weeks)", F.pctv(FS.attribution_band_upper_uplift_pct)],
      ["Period", `${F.month(FS.period[0])} – ${F.month(FS.period[1])}`],
      ["No-sponsorship level", FS.counterfactual_index_level.toFixed(1)],
    ]);
    note(pH, "This is the number the rest of the study prices. Step 02 asks what the Lenovo brand is worth; step 03 applies this uplift to it.");

    const pI = panel(col(g5, 7), { label: "Close-up", title: "The World Cup within the sponsorship", sub: "Mean gap to the no-sponsorship twin by period (Brand Index points)." });
    const W = X.worldCup;
    table(pI, [{ t: "Period" }, { t: "Weeks", num: true }, { t: "Gap vs twin", num: true }], [
      ["Sponsorship before the tournament", W.beforeTournament.weeks, F.pts(W.beforeTournament.gap)],
      ["Men's World Cup (tournament weeks)", W.tournament.weeks, F.pts(W.tournament.gap)],
      ["After the final", W.afterFinal.weeks, F.pts(W.afterFinal.gap)],
    ]);
    note(pI, `Against the no-sponsorship twin the tournament weeks sit at ${F.pts(W.tournament.gap)} and the weeks after the final at <b>${F.pts(W.afterFinal.gap)}</b>, against ${F.pts(W.beforeTournament.gap)} earlier. The pre-registered evaluation of the tournament closes on 18 October 2026.`);
    src(pI, "Sources: sponsorship_total_effect_v1 · world_cup_impact_v1 (pre-registered, ADR-0019/0029, amended ADR-0040)");

    const g6 = grid(root);
    const pJ = panel(col(g6, 12), { label: "Robustness", title: "Same design, different outcomes", sub: "The engine re-run on Google share of search alone and on the former search-salience index (each in its own units)." });
    table(pJ, [{ t: "Outcome" }, { t: "Effect", num: true }, { t: "Unit" }],
      X.crossChecks.map((c) => [c.label, (c.lift > 0 ? "+" : "") + c.lift.toFixed(2), c.unit]), { primary: 0 });
    note(pJ, "All three point the same way: Lenovo sits above its no-sponsorship twin whichever way its brand attention is measured.");

    pager(root, "summary", "evaluation");
  }

  /* ============================================================ VIEW 2 === */
  function viewEvaluation(root) {
    const dom = Object.fromEntries(V.dominance.map((g) => [g.group, g]));
    const h0 = V.stockResponse[0], P = V.placebo, W = D.wacc;

    head(root, {
      kicker: "Step 02 · Evaluation",
      title: "What is the Lenovo brand worth?",
      lead: `The brand is valued with the income approach of ISO 10668. Lenovo's economic profit, what its operations earn above the cost of the capital they use, is forecast from the ${D.baseYear} accounts and discounted. The brand's share of it, the brand contribution factor, is read from the share price: of the movement driven by Lenovo's own factors, how much comes from the brand.`,
    });

    flow(root, [
      { k: "Brand contribution factor", v: F.pct(FAC.share, 1), d: "Brand share of the Lenovo-specific share-price drivers" },
      { k: "Economic profit, discounted", v: F.usd(D.epPv), d: `${D.baseYear} base, WACC ${F.pct(W.wacc, 1)}, growth fading to ${F.pct(D.growthTerminal, 0)}`, cls: "flow-cell--mid" },
      { k: "Output → Monetization", v: F.usd(D.brandValue) + " brand value", d: `Factor × discounted economic profit · ${F.usd(D.valuePerPoint)} per Brand Index point`, cls: "flow-cell--out" },
    ]);

    kpiRow(root, [
      { v: F.pct(FAC.share, 1), k: "Brand contribution factor", n: "The brand against PC category demand and Lenovo events, in what moves the share price." },
      { v: F.usd(D.forecast[0].ep), k: "Economic profit, year 1", n: `NOPAT ${F.usd(D.forecast[0].nopat)} less a ${F.usd(D.forecast[0].charge)} charge for the capital employed.` },
      { v: F.pct(W.wacc, 1), k: "Cost of capital (WACC)", n: `Cost of equity ${F.pct(W.costOfEquity, 1)}, after-tax cost of debt ${F.pct(W.costOfDebt, 1)}, debt weight ${F.pct(W.weightDebt, 0)}.` },
      { v: F.usd(D.brandValue), k: "Lenovo brand value", n: `Present value of branded earnings; ${F.pct(D.terminalShare, 0)} of it from beyond year 5.` },
    ]);

    const g0 = grid(root);
    const pW = panel(col(g0, 12), { cls: "panel--tint", label: "The method", title: "Income split: the brand's share of what Lenovo earns above its cost of capital", sub: "ISO 10668 income approach, earnings split." });
    const cols = el("div", "cols2");
    const left = el("div", "assump");
    left.append(el("div", "assump-h", "The reasoning"));
    left.append(el("p", null, `Economic profit is NOPAT less a charge for the capital employed: ${D.baseYear} revenue of ${F.usd(D.revenue)} at a ${F.pct(D.operatingMargin, 1)} operating margin and ${F.pct(D.taxRate, 0)} tax, on ${F.usd(D.investedCapital)} of invested capital (a ${F.pct(D.roic, 0)} after-tax return). Revenue grows ${F.pct(D.growthStart, 1)} (the three-year trend) fading to ${F.pct(D.growthTerminal, 0)}, with margin and capital turnover held.`));
    left.append(el("p", null, `The brand's share of economic profit is the brand contribution factor, read from the share price with a dominance analysis of weekly abnormal returns: market-wide moves are set aside, and the brand takes <b>${F.pct(FAC.share, 1)}</b> of what Lenovo's own drivers explain. Branded earnings are discounted at ${F.pct(W.wacc, 1)} with a terminal value growing at ${F.pct(D.growthTerminal, 0)}.`));
    cols.append(left);
    const right = el("div", "assump");
    right.append(el("div", "assump-h", "Key assumptions"));
    const ul = el("ul");
    [
      ["Role of brand.", `The brand's share of economic profit equals its share of Lenovo's own share-price drivers: ${F.pct(FAC.share, 1)}.`],
      ["Operations.", `The ${D.baseYear} operating margin (${F.pct(D.operatingMargin, 1)}), tax rate (${F.pct(D.taxRate, 0)}) and capital turnover hold over the forecast.`],
      ["Growth.", `Revenue growth starts at ${F.pct(D.growthStart, 1)} and fades to ${F.pct(D.growthTerminal, 0)} a year by year 5, then continues at that rate.`],
      ["Discount rate.", `WACC ${F.pct(W.wacc, 1)}: US 10-year rate ${F.pct(W.riskFree, 1)}, beta ${W.beta.toFixed(2)}, equity risk premium ${F.pct(W.erp, 0)}.`],
    ].forEach(([h, tx]) => ul.append(el("li", null, "<b>" + h + "</b> " + tx)));
    right.append(ul);
    cols.append(right);
    pW.append(cols);
    pW.append(el("div", "verdict-line", `In short: Lenovo earns about <b>${F.usd(D.forecast[0].ep)}</b> a year above its cost of capital; with the brand accounting for ${F.pct(FAC.share, 1)} of it, the brand is worth <b>${F.usd(D.brandValue)}</b>.`));

    const g1 = grid(root);
    const pA = panel(col(g1, 7), { label: "Economic profit", title: "What Lenovo earns above its cost of capital, and the brand's share", sub: `Forecast from the ${D.baseYear} accounts, US$ per year. Branded earnings = brand contribution factor × economic profit.` });
    const cvA = chartIn(pA, 300);
    make(cvA, {
      type: "bar",
      data: {
        labels: D.forecast.map((f) => "Year " + f.year),
        datasets: [
          { label: "Economic profit", data: D.forecast.map((f) => f.ep), backgroundColor: T.peer, borderWidth: 0, barPercentage: 0.7 },
          { label: "Branded earnings", data: D.forecast.map((f) => f.branded), backgroundColor: T.brand, borderWidth: 0, barPercentage: 0.7 },
        ],
      },
      options: {
        maintainAspectRatio: false,
        scales: { x: { grid: { display: false }, border: { display: false } },
                  y: { grid: { color: T.grid }, border: { display: false }, beginAtZero: true, ticks: { callback: (v) => F.usd(v) } } },
        plugins: { tooltip: { callbacks: { label: (c) => c.dataset.label + "  " + F.usd(c.parsed.y) } } },
      },
    });
    legend(pA, [{ color: T.peer, label: "Economic profit", square: true }, { color: T.brand, label: "Branded earnings (brand's share)", square: true }]);
    table(pA, [{ t: "Year" }, { t: "Revenue", num: true }, { t: "NOPAT", num: true }, { t: "Capital charge", num: true }, { t: "Economic profit", num: true }, { t: "Branded earnings", num: true }],
      D.forecast.map((f) => [f.year, F.usd(f.revenue), F.usd(f.nopat), "−" + F.usd(f.charge), F.usd(f.ep), F.usd(f.branded)]));
    note(pA, `Discounted, five years of branded earnings are worth ${F.usd(D.explicitPv)} and the years after ${F.usd(D.terminalPv)}: brand value ${F.usd(D.brandValue)}.`);
    src(pA, `Source: Lenovo ${D.baseYear} results and balance sheet · Valuation: OpenEconomics (brand_value_dcf_v2, ADR-0045)`);

    const pB = panel(col(g1, 5), { label: "Discount rate", title: "Cost of capital", sub: "CAPM cost of equity, after-tax cost of debt, market-value weights." });
    readout(pB, [
      ["Risk-free rate (US 10-year)", F.pct(W.riskFree, 2)],
      ["Equity beta (adjusted)", W.beta.toFixed(2)],
      ["Equity risk premium", F.pct(W.erp, 1)],
      ["Cost of equity", F.pct(W.costOfEquity, 2)],
      ["After-tax cost of debt", F.pct(W.costOfDebt, 2)],
      ["Debt weight", F.pct(W.weightDebt, 1)],
      ["WACC", F.pct(W.wacc, 2)],
    ]);
    pB.append(el("div", "panel-label spaced", "Brand value by contribution factor and WACC"));
    const H = D.heat;
    table(pB, [{ t: "Factor" }, ...H.waccs.map((w) => ({ t: "WACC " + F.pct(w, 1), num: true }))],
      H.roles.map((role) => [F.pct(role, 0), ...H.waccs.map((w) => F.usd(H.values.find((v) => v.role === role && v.wacc === w).value))]));
    note(pB, "Brand value scales one-for-one with the contribution factor; the cost of capital matters far less.");

    const g2 = grid(root);
    const pC = panel(col(g2, 7), { label: "Where the factor comes from", title: "What drives Lenovo's own share-price movement", sub: `Share of the movement explained by Lenovo-specific drivers (general dominance of weekly abnormal returns, ${V.weeksN} weeks), market factors set aside.` });
    const cvC = chartIn(pC, 200);
    const NAMES = { category_demand: "PC category demand", lenovo_events: "Lenovo events", brand: "Brand (Brand Index)" };
    const own = V.dominance.filter((g) => g.group !== "market");
    barsH(cvC, {
      labels: own.map((g) => NAMES[g.group] || g.group), values: own.map((g) => g.shareOfLenovoSpecific * 100),
      colors: own.map((g) => (g.group === "brand" ? T.brand : T.peer)), xFmt: (v) => v.toFixed(0) + "%",
    });
    note(pC, `The brand accounts for <b>${F.pct(FAC.share, 1)}</b> of the movement Lenovo's own drivers explain; its effect on returns is positive. Market factors, set aside, explain ${F.pct(dom.market.share, 0)} of all explained weekly movement.`);
    src(pC, "Source: market data (0992.HK, Hang Seng, Nasdaq-100 in HKD) · Elaboration: OpenEconomics (stock_brand_response_v2, brand_value_dominance_v1)");

    const pD = panel(col(g2, 5), { label: "Assumptions", title: "Valuation inputs at a glance", sub: "Every input of the income split, with its source." });
    table(pD, [{ t: "Input" }, { t: "Source" }, { t: "Value", num: true }], [
      ["Revenue " + D.baseYear, "Lenovo results", F.usd(D.revenue)],
      ["Operating margin", "Lenovo results", F.pct(D.operatingMargin, 2)],
      ["Effective tax rate", "Lenovo results", F.pct(D.taxRate, 1)],
      ["Invested capital", "Balance sheet", F.usd(D.investedCapital)],
      ["Revenue growth, start → long run", "Three-year trend · assumption", `${F.pct(D.growthStart, 1)} → ${F.pct(D.growthTerminal, 0)}`],
      ["Risk-free rate", "US 10-year Treasury", F.pct(W.riskFree, 2)],
      ["Equity beta", "Lenovo vs world equities", W.beta.toFixed(2)],
      ["Equity risk premium", "Assumption", F.pct(W.erp, 1)],
      ["Brand contribution factor", "Share-price analysis", F.pct(FAC.share, 1)],
    ]);

    const g3 = grid(root);
    const pE = panel(col(g3, 7), { label: "The factor's source data", title: "Observed share price vs the path explained by market factors", sub: "A rolling market model, re-estimated each day on the prior 120 trading days only. The residual is what Lenovo's own drivers, the brand among them, have to explain." });
    const cvE = chartIn(pE, 280);
    lineChart(cvE, {
      weeks: V.weeks,
      series: [
        { label: "Explained by market factors", data: V.expectedPath, color: T.counterfactual, width: 2, dash: [6, 4], order: 2 },
        { label: "Observed share price", data: V.actualPath, color: T.brand, width: 2.6, fill: "-1", fillColor: "rgba(89,2,238,.10)", order: 1 },
      ],
      milestones: marksFor(V.weeks, KEY_MARKS),
      yTitle: "Price index · 100 = start of sample",
      tip: (v) => (v == null ? "—" : v.toFixed(1)),
    });
    legend(pE, [{ color: T.brand, label: "Observed share price" }, { color: T.counterfactual, label: "Path explained by market factors", dash: true }]);
    src(pE, `Source: market data · average loadings: Hang Seng ${V.betas.hsi}, Nasdaq-100 ${V.betas.ndx}`);
    const pF = panel(col(g3, 5), { cls: "panel--dark", label: "Output of step 02" });
    pF.append(el("div", "figure-v lime", F.usd(D.brandValue)));
    pF.append(el("div", "figure-k", "Lenovo brand value · income split"));
    readout(pF, [
      ["Brand contribution factor", F.pct(FAC.share, 1)],
      ["Discounted economic profit", F.usd(D.epPv)],
      ["Value from beyond year 5", F.pct(D.terminalShare, 0)],
      ["WACC ±1 point", `${F.usd(D.waccRange[0])} – ${F.usd(D.waccRange[1])}`],
      ["Value per Brand Index point", F.usd(D.valuePerPoint)],
    ]);
    note(pF, "Because the Brand Index is proportional to brand share, a lift of x% is worth x% of this brand value. Step 03 applies the FIFA-specific uplift.");

    pager(root, "exposure", "monetization");
  }

  /* ============================================================ VIEW 3 === */
  function viewMonetization(root) {
    const s = S();
    const value = s.value;

    head(root, {
      kicker: "Step 03 · Monetization",
      title: "What did FIFA add to the brand, and does it cover the cost?",
      lead: "The FIFA-specific uplift in brand share is applied to the brand value from step 02, giving the brand value FIFA added. It is a capitalised value; the same figure is also shown as a yearly flow of branded earnings. Enter the programme cost to read the return on it.",
    });

    const sw = el("div", "switch-row reveal");
    const g1s = el("div", "switch-group");
    g1s.append(el("span", "switch-lab", "Scenario"));
    const sbox = el("div", "switch");
    ["conservative", "base", "ambitious"].forEach((k) => {
      const b = el("button", scenarioKey === k ? "is-on" : "", LAB[k]);
      b.type = "button";
      b.addEventListener("click", () => { scenarioKey = k; render("monetization"); });
      sbox.append(b);
    });
    g1s.append(sbox);
    sw.append(g1s);
    sw.append(el("span", "switch-formula", `${F.pctv(s.upliftPct, 2)} brand share × ${F.usd(B.brandValue)} brand value`));
    root.append(sw);

    flow(root, [
      { k: "Input from step 01", v: F.pctv(s.upliftPct, 2) + " brand share", d: `${LAB[scenarioKey]} case: ${scenarioKey === "base" ? "FIFA-specific primary" : scenarioKey === "conservative" ? "low end of the 95% band" : "whole gap credited to FIFA"}` },
      { k: "Input from step 02", v: F.usd(B.brandValue), d: "Lenovo brand value", cls: "flow-cell--mid" },
      { k: "FIFA's contribution to brand value", v: F.usd(value), d: "Incremental brand value, capitalised", cls: "flow-cell--out" },
    ]);

    const g1 = grid(root);
    const pA = panel(col(g1, 8), { label: "Value bridge", title: "From the whole gap to the FIFA-specific value", sub: `The whole gap to the no-sponsorship twin, priced at ${F.usd(B.brandValue)} of brand value, split into what FIFA exposure explains and the rest.` });
    const cvA = chartIn(pA, 340);
    const br = M.bridge;
    waterfall(cvA, {
      steps: [
        { label: br[0].label, value: br[0].value, total: true, color: T.counterfactual },
        { label: br[1].label, value: br[1].value, color: T.peer },
        { label: br[2].label, value: br[2].value, total: true, color: T.brandDeep },
      ],
      fmt: (v) => F.usd(v),
    });
    note(pA, `<b>How to read it.</b> Lenovo's whole gap to its rivals is worth ${F.usd(br[0].value)}. ${F.usd(-br[1].value)} of it is not attributed to FIFA, leaving <b>${F.usd(br[2].value)}</b> from FIFA.`);
    src(pA, "Elaboration: OpenEconomics · brand_value_dcf_v2, sponsorship_exposure_timing_v1 (ADR-0043, ADR-0045)");

    const pB = panel(col(g1, 4), { cls: "panel--dark", label: "Decision signal" });
    pB.append(el("div", "figure-v lime", F.usd(value)));
    pB.append(el("div", "figure-k", `${LAB[scenarioKey]} case · FIFA-added brand value`));
    readout(pB, [
      ["FIFA-specific uplift", F.pctv(s.upliftPct, 2)],
      ["Brand value", F.usd(B.brandValue)],
      ["Break-even programme cost", F.usd(value)],
    ]);
    const box = el("div", "cost-box");
    box.append(el("label", null, "Programme cost, US$m"));
    const input = el("input");
    input.type = "number"; input.min = "0"; input.step = "1"; input.placeholder = "e.g. 100";
    if (programmeCost != null) input.value = programmeCost;
    box.append(input);
    pB.append(box);
    const out = el("div", "cost-out");
    const showCost = () => {
      const c = parseFloat(input.value);
      programmeCost = isFinite(c) && c > 0 ? c : null;
      out.innerHTML = programmeCost
        ? `<b>${F.mult(value / (programmeCost * 1e6))}</b> brand value per US$ of programme cost · net ${F.usd(value - programmeCost * 1e6)}`
        : `Enter the programme cost (rights fee plus activation) to read the multiple. Break-even: ${F.usd(value)}.`;
    };
    input.addEventListener("input", showCost);
    showCost();
    pB.append(out);

    kpiRow(root, [
      { v: F.usd(value), k: "FIFA-added brand value", n: `${LAB[scenarioKey]} case.` },
      { v: F.pctv(s.upliftPct, 2), k: "Uplift in brand share", n: `${s.indexPoints.toFixed(2)} Brand Index points over a no-sponsorship level of ${FS.counterfactual_index_level.toFixed(1)}.` },
      { v: F.usd(B.brandValue), k: "Lenovo brand value", n: "Income split of economic profit (step 02)." },
      { v: F.usd(M.scenarios.ambitious.value), k: "Ceiling: whole gap credited to FIFA", n: `${F.pctv(M.scenarios.ambitious.upliftPct, 2)} brand share, residual included.` },
    ]);

    const g2 = grid(root);
    const pP = panel(col(g2, 7), { label: "Is the lift holding?", title: "Gap to the no-sponsorship twin, quarter by quarter", sub: "The observed path of the whole gap to the no-sponsorship twin (Brand Index points)." });
    const cvP = chartIn(pP, 280);
    barsV(cvP, {
      labels: M.quarterlyGap.map((q) => q.q), values: M.quarterlyGap.map((q) => q.gap),
      colors: M.quarterlyGap.map((q) => (q.q.startsWith("2026Q3") ? T.brandLight : T.brandDeep)), yFmt: (v) => v.toFixed(0),
      yTitle: "Mean gap · Brand Index points",
    });
    const qs = M.quarterlyGap;
    note(pP, `The gap built through 2025 and has held since: ${qs[qs.length - 2].q} ${F.pts(qs[qs.length - 2].gap)}, ${qs[qs.length - 1].q} so far ${F.pts(qs[qs.length - 1].gap)}.`);

    const pQ = panel(col(g2, 5), { label: "Scenario ladder", title: "Uplift in, brand value out", sub: "The three cases are the primary estimate and its bands." });
    table(pQ, [{ t: "Case" }, { t: "Uplift", num: true }, { t: "Index points", num: true }, { t: "FIFA-added value", num: true }],
      ["conservative", "base", "ambitious"].map((k) => [`<b>${LAB[k]}</b>`, F.pctv(M.scenarios[k].upliftPct, 2), M.scenarios[k].indexPoints.toFixed(2), F.usd(M.scenarios[k].value)]),
      { primary: ["conservative", "base", "ambitious"].indexOf(scenarioKey) });
    note(pQ, "Conservative is the low end of the 95% band; ambitious credits the whole gap, residual included, to FIFA.");

    const g3 = grid(root);
    const pD = panel(col(g3, 12), { label: "The same value as a flow", title: "FIFA's share of branded earnings, year by year", sub: "Base case: the FIFA-specific uplift applied to each forecast year's branded earnings. Discounted and continued beyond year 5, these flows make up the FIFA-added brand value." });
    const fl = M.fifaBrandedEarnings;
    const cvD = chartIn(pD, 230);
    barsV(cvD, { labels: fl.map((f) => "Year " + f.year), values: fl.map((f) => f.value), colors: T.limeInk, yFmt: (v) => F.usd(v) });
    note(pD, `FIFA's contribution is worth about <b>${F.usd(fl[0].value)}</b> of branded earnings in year 1, rising to ${F.usd(fl[fl.length - 1].value)} in year 5; the five forecast years account for ${F.pct(M.fifaExplicitShare, 0)} of the ${F.usd(M.scenarios.base.value)} and the long run for the rest.`);
    src(pD, "Elaboration: OpenEconomics · brand_value_dcf_v2 (ADR-0045)");

    pager(root, "evaluation", "method");
  }

  /* ============================================================ METHOD === */
  function viewMethod(root) {
    head(root, {
      kicker: "Method & evidence",
      title: "How the study is built",
      lead: "Three steps, each producing one number the next consumes. The review notebooks document every calculation behind them.",
    });
    flow(root, [
      { k: "Step 01 · Exposure", v: F.pts(FS.primary_index_points) + " FIFA-specific", d: `Brand Index (share of attention against rivals, with the GWI survey) against a synthetic no-sponsorship Lenovo from ${X.design.donors.length} rival brands; the part of the gap explained by FIFA exposure isolated.` },
      { k: "Step 02 · Evaluation", v: F.usd(B.brandValue) + " brand value", cls: "flow-cell--mid", d: `ISO 10668 income split: the brand contribution factor (${F.pct(FAC.share, 1)}, from the share price) × Lenovo's discounted economic profit (${F.usd(D.epPv)}).` },
      { k: "Step 03 · Monetization", v: F.usd(M.scenarios.base.value) + " added by FIFA", cls: "flow-cell--out", d: "FIFA-specific uplift × brand value, with the 95% band and the whole-gap ceiling as scenarios." },
    ], { tall: true });

    const g = grid(root);
    const p1 = panel(col(g, 6), { label: "Data sources", title: "What the study is built on" });
    table(p1, [{ t: "Source" }, { t: "Contribution" }], [
      ["<b>Google Trends</b>", "Weekly search interest for Lenovo and rival brands in jointly scaled panels; Lenovo product searches as a demand indicator"],
      ["<b>GWI Core</b>", "Quarterly engagement and consideration of Lenovo (2022–2026Q1) in the Brand Index"],
      ["<b>Blinkfire Analytics</b>", "Weekly digital and social impressions by sponsored property"],
      ["<b>Market data</b>", "0992.HK, Hang Seng, Nasdaq-100, USD/HKD daily closes"],
      ["<b>Lenovo annual results</b>", `${D.baseYear} revenue, operating profit, tax, equity, debt and cash (income split)`],
      ["<b>Lenovo</b>", "Results and event calendar"],
      ["<b>FIFA</b>", "Official 2026 match calendar; partnership announcements"],
    ]);
    const p2 = panel(col(g, 6), { label: "Status of the figures", title: "Observed, constructed, estimated, assumed" });
    table(p2, [{ t: "Status" }, { t: "Applies to" }], [
      ["<b>Observed</b>", "Search volumes, survey waves, digital impressions, share prices"],
      ["<b>Constructed</b>", "Brand Index, rival share-of-search series, motorsport exposure before September 2024 (back-cast)"],
      ["<b>Estimated</b>", "Synthetic control, FIFA-specific decomposition, dominance shares, brand value"],
      ["<b>Assumed</b>", "Equity risk premium, debt spread, growth fade and terminal growth; brand value moves one-for-one with brand share; the uplift persists; exposure carries over at 80% a week"],
    ]);

    const g2 = grid(root);
    const p3 = panel(col(g2, 7), { label: "Scope", title: "What the figures cover" });
    const ul = el("ul", "caveats");
    [
      "Exposure: FIFA-family digital and social impressions measured by Blinkfire.",
      "Brand Index: Lenovo's weekly share of attention against rival brands, informed by the quarterly GWI survey (100 = before the announcement).",
      "FIFA-specific effect: the part of Lenovo's gap to its no-sponsorship twin explained by accumulated FIFA exposure, after other sponsorships and events.",
      `Brand value: ISO 10668 income split on Lenovo's ${D.baseYear} accounts, discounted at market rates of ${F.day(E.meta.dataThrough)}.`,
      "Return on investment: computed from the programme cost entered by the viewer.",
      "World Cup: the pre-registered evaluation window closes on 18 October 2026.",
    ].forEach((t) => ul.append(el("li", null, t)));
    p3.append(ul);
    const p4 = panel(col(g2, 5), { label: "Traceability", title: "Where every number comes from" });
    readout(p4, [
      ["Data through", F.day(E.meta.dataThrough)],
      ["Dashboard built", F.day(E.meta.built)],
      ["Decisions", E.meta.decisions],
      ["Review notebooks", "10 · 20 · 35 · 40"],
    ]);
    note(p4, "Figures are generated by <code>frontend/scripts/build_eroi_data.py</code> from the production outputs; the review notebooks in <code>reports/methods_annex/</code> show every calculation.");

    pager(root, "monetization", null);
  }

  /* ============================================================ SUMMARY === */
  function viewSummary(root) {
    const K = X.kpi, base = M.scenarios.base;
    head(root, {
      kicker: "Summary · the answer",
      title: "What did FIFA add to the Lenovo brand?",
      lead: `Three steps answer it, each handing one number to the next. Lenovo's brand share of attention is compared with a synthetic Lenovo built from ${X.design.donors.length} rival brands; the part of the gap that FIFA exposure explains is isolated; the market's view of the brand prices it.`,
    });

    const hero = el("div", "summary-hero reveal");
    const v = el("div", "verdict");
    v.append(el("div", "verdict-kicker", "Primary estimate · FIFA-specific effect"));
    const fig = el("div", "verdict-figure");
    fig.append(el("div", "verdict-mult", F.pctv(FS.primary_uplift_pct)));
    fig.append(el("div", "verdict-net", `<b>${F.usd(base.value)}</b>brand value added by FIFA`));
    v.append(fig);
    v.append(el("p", "verdict-text",
      `Since the partnership was announced, FIFA has added about <b>${F.pctv(FS.primary_uplift_pct)}</b> to Lenovo's brand share of attention against its rivals (95% band ${F.pctv(FS.statistical_band_95_uplift_pct[0])} to ${F.pctv(FS.statistical_band_95_uplift_pct[1])}; the whole gap, ${F.pctv(FS.attribution_band_upper_uplift_pct)}, is the ceiling). Lenovo's other sponsorships do not explain it. Applied to a Lenovo brand worth ${F.usd(B.brandValue)}, that is <b>${F.usd(base.value)}</b> of brand value (band ${F.usd(M.scenarios.conservative.value)} to ${F.usd(M.scenarios.ambitious.value)}).`));
    hero.append(v);
    const st = el("div", "summary-stats");
    [
      ["FIFA exposure delivered", F.big(K.eventImpressions) + " impr."],
      ["Whole gap vs rivals (ceiling)", F.pts(X.total.lift)],
      ["Lenovo brand value", F.usd(B.brandValue)],
      ["Break-even programme cost", F.usd(base.value)],
    ].forEach(([k, val]) => {
      const r = el("div", "stat");
      r.append(el("div", "stat-label", k), el("div", "stat-value", val));
      st.append(r);
    });
    hero.append(st);
    root.append(hero);

    const ch = el("div", "chapters reveal");
    STEPS.forEach((step) => {
      const b = el("button", "chapter");
      b.type = "button";
      const top = el("div", "chapter-top");
      top.append(el("span", "chapter-n", step.n), el("span", "chapter-name", step.name));
      b.append(top);
      b.append(el("p", "chapter-q", step.q));
      const sp = el("div", "chapter-spark");
      const cv = document.createElement("canvas");
      sp.append(cv);
      b.append(sp);
      const out = el("div", "chapter-out");
      out.append(el("span", "k", "Output"), el("span", "v", step.out()));
      b.append(out);
      b.append(el("div", "chapter-go", "Open step " + step.n + " →"));
      b.addEventListener("click", () => go(step.id));
      ch.append(b);
      const cfg = step.spark();
      sparkline(cv, cfg.data, cfg.color, cfg.fill);
    });
    root.append(ch);

    const rib = el("div", "ribbon reveal");
    rib.append(el("div", "panel-label", "Partnership timeline"));
    const track = el("div", "ribbon-track");
    const DAY = 864e5;
    const t0 = new Date(ev("fifa_partner_announcement_2024").date).getTime() - 45 * DAY;
    const t1 = new Date(ev("wc_final_2026").date).getTime() + 100 * DAY;
    const pct = (d) => ((new Date(d).getTime() - t0) / (t1 - t0)) * 100;
    const dataPct = Math.min(100, Math.max(0, pct(E.meta.dataThrough)));
    const done = el("div", "ribbon-done"); done.style.width = dataPct + "%"; track.append(done);
    [{ from: "fcwc_opening_2025", to: "fcwc_final_2025", label: "Club World Cup 2025" },
     { from: "wc_opening_2026", to: "wc_final_2026", label: "World Cup 2026" }].forEach((w) => {
      const span = el("div", "ribbon-win");
      const a = pct(ev(w.from).date), z = pct(ev(w.to).date);
      span.style.left = a + "%"; span.style.width = Math.max(1.5, z - a) + "%";
      span.append(el("span", "ribbon-lab above", `${w.label}<em>${F.month(ev(w.from).date)}</em>`));
      track.append(span);
    });
    [["fifa_partner_announcement_2024", "Partnership announced"], ["fcwc_partner_announcement_2025", "Club WC activation deal"]].forEach(([id, label]) => {
      const d = el("div", "ribbon-dot");
      d.style.left = pct(ev(id).date) + "%";
      d.append(el("span", "ribbon-lab below", `${label}<em>${F.month(ev(id).date)}</em>`));
      track.append(d);
    });
    const td = el("div", "ribbon-today"); td.style.left = dataPct + "%"; td.append(el("span", null, "Data through " + F.month(E.meta.dataThrough))); track.append(td);
    rib.append(track);
    root.append(rib);

    pager(root, null, "exposure");
  }

  /* ------------------------------------------------------------- pager --- */
  const VIEWS = {
    summary: { n: "", label: "Summary", render: viewSummary },
    exposure: { n: "01", label: "Exposure", render: viewExposure },
    evaluation: { n: "02", label: "Evaluation", render: viewEvaluation },
    monetization: { n: "03", label: "Monetization", render: viewMonetization },
    method: { n: "", label: "Method & evidence", render: viewMethod },
  };
  const ORDER = ["summary", "exposure", "evaluation", "monetization"];

  function pager(root, prev, next) {
    const p = el("div", "pager reveal");
    if (prev) {
      const b = el("button", "prev", `<div class="k">← Previous${VIEWS[prev].n ? " · Step " + VIEWS[prev].n : ""}</div><div class="t">${VIEWS[prev].label}</div>`);
      b.type = "button"; b.addEventListener("click", () => go(prev)); p.append(b);
    }
    if (next) {
      const b = el("button", "next", `<div class="k">Next ${VIEWS[next].n ? "· Step " + VIEWS[next].n : ""} →</div><div class="t">${VIEWS[next].label}</div>`);
      b.type = "button"; b.addEventListener("click", () => go(next)); p.append(b);
    }
    root.append(p);
  }

  const STEPS = [
    { id: "exposure", n: "01", name: "Exposure", q: "How much more did Lenovo stand out than rival brands the FIFA deal never touched, and how much of that is FIFA?",
      chev: `Against ${X.design.donors.length} rival brands`, metric: () => F.pts(FS.primary_index_points) + " FIFA-specific", out: () => F.pctv(FS.primary_uplift_pct),
      spark: () => ({ data: X.core.gap, color: T.brand, fill: "rgba(89,2,238,.12)" }) },
    { id: "evaluation", n: "02", name: "Evaluation", q: "What is the Lenovo brand worth: its share of what Lenovo earns above its cost of capital?",
      chev: "Income split of economic profit", metric: () => F.usd(B.brandValue) + " brand value", out: () => F.usd(B.brandValue),
      spark: () => ({ data: V.actualPath, color: T.brandDeep, fill: "rgba(68,0,179,.12)" }) },
    { id: "monetization", n: "03", name: "Monetization", q: "What did FIFA add to that brand value, and what programme cost would it cover?",
      chev: "FIFA uplift × brand value", metric: () => F.usd(M.scenarios.base.value) + " added by FIFA", out: () => F.usd(M.scenarios.base.value),
      spark: () => ({ data: M.quarterlyGap.map((q) => q.gap), color: T.limeInk, fill: "rgba(103,195,0,.18)" }) },
  ];

  function buildMasthead() {
    const built = F.day(E.meta.dataThrough);
    document.getElementById("case-label").textContent = E.meta.caseLabel;
    document.getElementById("updated-chip").textContent = "Data through " + built;
    document.getElementById("foot-updated").textContent = "Data through " + built + " · built " + F.day(E.meta.built);
    document.getElementById("method-link").addEventListener("click", () => go("method"));
    const nav = document.getElementById("process");
    [{ id: "summary", n: "", name: "Summary", metric: () => F.pctv(FS.primary_uplift_pct) + " brand share from FIFA", sub: "The answer and the chain behind it" },
     ...STEPS.map((s) => ({ id: s.id, n: s.n, name: s.name, metric: s.metric, sub: s.chev }))].forEach((c) => {
      const b = el("button", "chev");
      b.type = "button"; b.dataset.step = c.id;
      const top = el("div", "chev-top");
      if (c.n) top.append(el("span", "chev-n", c.n));
      top.append(el("span", "chev-name", c.name));
      b.append(top, el("div", "chev-metric", c.metric()), el("div", "chev-sub", c.sub));
      b.addEventListener("click", () => go(c.id));
      nav.append(b);
    });
  }

  function animateIn(root) {
    root.querySelectorAll(".reveal").forEach((n, i) => {
      if (reduced) { n.classList.add("is-in"); return; }
      setTimeout(() => n.classList.add("is-in"), Math.min(i * 60, 420));
    });
  }

  function render(id) {
    const view = VIEWS[id] ? id : "summary";
    const pos = ORDER.indexOf(view);
    document.querySelectorAll(".chev").forEach((b) => {
      const i = ORDER.indexOf(b.dataset.step);
      b.classList.toggle("is-active", b.dataset.step === view);
      b.classList.toggle("is-done", pos > -1 && i > -1 && i < pos);
    });
    document.getElementById("method-link").classList.toggle("is-active", view === "method");
    document.title = (VIEWS[view].n ? "Step " + VIEWS[view].n + " · " : "") + VIEWS[view].label + " — EROI · " + E.meta.caseLabel + " · OpenEconomics";
    killAll();
    const root = document.getElementById("view");
    root.innerHTML = "";
    VIEWS[view].render(root);
    animateIn(root);
    return view;
  }
  function go(id) { if (location.hash === "#/" + id) render(id); else location.hash = "#/" + id; }
  function route() { render((location.hash.replace(/^#\/?/, "") || "summary").split("?")[0]); window.scrollTo(0, 0); }

  buildMasthead();
  window.addEventListener("hashchange", route);
  route();
  document.getElementById("year").textContent = new Date().getFullYear();
})();
