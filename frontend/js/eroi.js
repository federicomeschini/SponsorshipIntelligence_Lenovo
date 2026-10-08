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
      sub: "Brand Index: Lenovo's weekly share of attention against rival brands, informed by the GWI and Nielsen surveys (100 = pre-announcement average). The twin is a weighted mix of rival brands that reproduces Lenovo before the deal; the shaded distance afterwards is the gap.",
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
    src(pD, "Sources: Google Trends · GWI Core · Nielsen · Elaboration: OpenEconomics");

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
    src(pF, "Sources: Blinkfire Analytics · Google Trends · Elaboration: OpenEconomics");

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
    src(pI, "Elaboration: OpenEconomics · pre-registered evaluation");

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
    src(pA, `Source: Lenovo ${D.baseYear} results and balance sheet · Elaboration: OpenEconomics`);

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
    src(pC, "Source: market data (0992.HK, Hang Seng, Nasdaq-100 in HKD) · Elaboration: OpenEconomics");

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
    src(pA, "Elaboration: OpenEconomics");

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
    src(pD, "Source: Lenovo annual results · Elaboration: OpenEconomics");

    pager(root, "evaluation", "method");
  }

  /* ============================================================ METHOD === */
  const MT = E.method;
  const pairGrid = (root) => { const g = grid(root); g.classList.add("grid--pair"); return g; };
  const K = X.kpi;
  const STATUS_CLS = { Observed: "tag--obs", Constructed: "tag--con", Estimated: "tag--est", Assumed: "tag--ass" };
  const status = (s) => `<span class="tag ${STATUS_CLS[s] || ""}">${s}</span>`;

  /* a formula block: the equation, what it says in words, and what each symbol is */
  function formula(p, eq, say, symbols) {
    const f = el("div", "formula");
    f.append(el("div", "formula-eq", eq));
    if (say) f.append(el("p", "formula-say", say));
    if (symbols && symbols.length) {
      const dl = el("dl", "symbols");
      symbols.forEach(([s, d]) => { dl.append(el("dt", null, s), el("dd", null, d)); });
      f.append(dl);
    }
    p.append(f);
  }
  function inputs(p, rows) {
    table(p, [{ t: "Input" }, { t: "Source" }, { t: "Status" }], rows.map(([a, b, c]) => [a, b, status(c)]));
  }
  const TOPICS = [
    { id: "exposure", step: "01", name: "FIFA exposure", q: "How is FIFA exposure measured?",
      d: "Blinkfire impressions on FIFA social media, accumulated week by week with carryover.",
      key: () => F.big(K.eventImpressions) + " impressions", view: "exposure", render: topicExposure },
    { id: "television", step: "01", parent: "exposure", hidden: true, name: "Television exposure", q: "Why is there no television exposure?",
      d: "", key: () => "", view: "exposure", render: topicTelevision },
    { id: "brand-index", step: "01", name: "Brand Index", q: "How is the Lenovo brand measured?",
      d: "A dynamic factor model of Lenovo's share of attention against rivals, anchored to the GWI and Nielsen surveys.",
      key: () => "100 → " + X.brandIndex.postMean.toFixed(1), view: "exposure", render: topicBrandIndex },
    { id: "twin", step: "01", name: "No-sponsorship twin", q: "What would Lenovo look like without FIFA?",
      d: `A synthetic Lenovo from ${X.design.donors.length} rival brands, chosen on pre-announcement data only.`,
      key: () => F.pts(X.total.lift) + " whole gap", view: "exposure", render: topicTwin },
    { id: "fifa-specific", step: "01", name: "FIFA-specific effect", q: "How much of the gap is FIFA?",
      d: "A regression of the gap on accumulated FIFA exposure, with controls and a trend.",
      key: () => F.pts(FS.primary_index_points), view: "exposure", render: topicFifaSpecific },
    { id: "factor", step: "02", name: "Brand contribution factor", q: "How much of Lenovo's profit does the brand drive?",
      d: "The brand's share of what moves Lenovo's own share price, by dominance analysis.",
      key: () => F.pct(FAC.share, 1), view: "evaluation", render: topicFactor },
    { id: "income-split", step: "02", name: "Income split (ISO 10668)", q: "How is the brand valued?",
      d: "The factor applied to Lenovo's economic profit, forecast and discounted.",
      key: () => F.usd(B.brandValue), view: "evaluation", render: topicIncomeSplit },
    { id: "cost-of-capital", step: "02", name: "Cost of capital", q: "What discount rate is used?",
      d: "CAPM cost of equity and after-tax cost of debt at market weights.",
      key: () => F.pct(D.wacc.wacc, 1) + " WACC", view: "evaluation", render: topicWacc },
    { id: "monetization", step: "03", name: "FIFA-added brand value", q: "How is the FIFA effect turned into money?",
      d: "The FIFA-specific uplift in brand share applied to the brand value, with scenarios.",
      key: () => F.usd(M.scenarios.base.value), view: "monetization", render: topicMonetization },
    { id: "sources", step: "", name: "Data sources", q: "What data is the study built on?",
      d: "Every source, and which figures are observed, constructed, estimated or assumed.",
      key: () => "7 sources", view: null, render: topicSources },
  ];
  const VISIBLE = TOPICS.filter((t) => !t.hidden);
  const GROUPS = [
    { step: "01", label: "Step 01 · Exposure", title: "From exposure to a FIFA-specific effect" },
    { step: "02", label: "Step 02 · Evaluation", title: "From the share price to a brand value" },
    { step: "03", label: "Step 03 · Monetization", title: "From brand share to money" },
    { step: "", label: "Foundations", title: "The data behind the study" }
  ];

  function viewMethod(root, sub) {
    const topic = TOPICS.find((t) => t.id === sub);
    if (topic) return methodTopic(root, topic);
    head(root, {
      kicker: "Method & evidence",
      title: "How the study is built",
      lead: "Three steps, each producing one number the next consumes. Open any topic below for the formulas, inputs and diagnostics behind it.",
    });
    flow(root, [
      { k: "Step 01 · Exposure", v: F.pts(FS.primary_index_points) + " FIFA-specific", d: `Brand Index (share of attention against rivals, with the GWI and Nielsen surveys) against a synthetic no-sponsorship Lenovo from ${X.design.donors.length} rival brands; the part of the gap explained by FIFA exposure isolated.` },
      { k: "Step 02 · Evaluation", v: F.usd(B.brandValue) + " brand value", cls: "flow-cell--mid", d: `ISO 10668 income split: the brand contribution factor (${F.pct(FAC.share, 1)}, from the share price) × Lenovo's discounted economic profit (${F.usd(D.epPv)}).` },
      { k: "Step 03 · Monetization", v: F.usd(M.scenarios.base.value) + " added by FIFA", cls: "flow-cell--out", d: "FIFA-specific uplift × brand value, with the 95% band and the whole-gap ceiling as scenarios." },
    ], { tall: true });

    GROUPS.forEach((g) => {
      const sec = el("section", "topic-group reveal");
      sec.append(el("div", "topic-group-k", g.label), el("h3", "topic-group-t", g.title));
      const cards = el("div", "topic-cards");
      VISIBLE.filter((t) => t.step === g.step).forEach((t) => {
        const a = el("a", "topic-card");
        a.href = "#/method/" + t.id;
        a.innerHTML = `<div class="topic-card-n">${t.name}</div><div class="topic-card-q">${t.q}</div>
          <p class="topic-card-d">${t.d}</p><div class="topic-card-f"><span class="topic-card-v">${t.key()}</span><span class="topic-card-go">Read →</span></div>`;
        cards.append(a);
      });
      sec.append(cards);
      root.append(sec);
    });

    const g2 = pairGrid(root);
    const p3 = panel(col(g2, 12), { label: "Scope", title: "What the figures cover" });
    const ul = el("ul", "caveats");
    [
      "Exposure: FIFA social media impressions measured by Blinkfire.",
      "Brand Index: Lenovo's weekly share of attention against rival brands, informed by the GWI and Nielsen surveys (100 = before the announcement).",
      "FIFA-specific effect: the part of Lenovo's gap to its no-sponsorship twin explained by accumulated FIFA exposure.",
      `Brand value: ISO 10668 income split on Lenovo's ${D.baseYear} accounts, discounted at market rates of ${F.day(E.meta.dataThrough)}.`,
      "Return on investment: computed from the programme cost entered by the viewer.",
      "World Cup: the pre-registered evaluation window closes on 18 October 2026.",
    ].forEach((t) => ul.append(el("li", null, t)));
    p3.append(ul);
    pager(root, "monetization", null);
  }

  function methodTopic(root, t) {
    const crumbs = el("nav", "crumbs reveal");
    crumbs.setAttribute("aria-label", "Breadcrumb");
    const parent = t.parent && TOPICS.find((x) => x.id === t.parent);
    crumbs.innerHTML = `<a href="#/method">Method &amp; evidence</a><span>/</span>${t.step ? `<span>Step ${t.step}</span><span>/</span>` : ""}`
      + (parent ? `<a href="#/method/${parent.id}">${parent.name}</a><span>/</span>` : "") + `<b>${t.name}</b>`;
    root.append(crumbs);
    t.render(root);

    if (t.view) {
      const see = el("div", "topic-see reveal");
      see.append(el("span", null, "See these results on the dashboard"));
      const b = el("button", "bar-btn", `Step ${VIEWS[t.view].n} · ${VIEWS[t.view].label} →`);
      b.type = "button"; b.addEventListener("click", () => go(t.view));
      see.append(b);
      root.append(see);
    }
    const p = el("div", "pager reveal");
    const mk = (cls, k, tt, href) => { const a = el("a", cls, `<div class="k">${k}</div><div class="t">${tt}</div>`); a.href = href; p.append(a); };
    if (parent) {
      mk("prev", "← Back", parent.name, "#/method/" + parent.id);
    } else {
      const i = VISIBLE.indexOf(t), prev = VISIBLE[i - 1], next = VISIBLE[i + 1];
      mk("prev", prev ? "← Previous topic" : "← Back", prev ? prev.name : "Method & evidence", prev ? "#/method/" + prev.id : "#/method");
      if (next) mk("next", "Next topic →", next.name, "#/method/" + next.id);
    }
    root.append(p);
  }

  /* --- Step 01 topics ------------------------------------------------------ */
  function topicExposure(root) {
    head(root, { kicker: "Method · Step 01", title: "How is FIFA exposure measured?",
      lead: "Exposure is the volume of FIFA social media content in which Lenovo is visible, as measured by Blinkfire Analytics. Because brand memory builds up and fades gradually, weekly impressions are accumulated with a carryover before they enter the analysis." });
    kpiRow(root, [
      { v: F.big(K.eventImpressions), k: "Impressions", n: `FIFA social media, ${F.day(X.event.weeks[0])} to ${F.day(X.event.coverageEnd)}` },
      { v: F.big(K.eventViews), k: "Video views", n: "Same accounts and window" },
      { v: String(X.event.weeks.length), k: "Weeks measured", n: "Weekly series from the partnership start" },
      { v: F.pct(MT.adstock, 0), k: "Weekly carryover", n: "Share of last week's accumulated exposure still active" },
    ]);
    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "Method", title: "From weekly impressions to accumulated exposure" });
    formula(p1, `A<sub>t</sub> = x<sub>t</sub> + δ · A<sub>t−1</sub>`,
      "Accumulated exposure this week is this week's impressions plus most of last week's accumulated exposure. A week of heavy coverage keeps counting, with declining weight, for several weeks after.",
      [["A<sub>t</sub>", "accumulated exposure (adstock) in week t"], ["x<sub>t</sub>", "Blinkfire impressions in week t"],
       ["δ", `weekly carryover, ${MT.adstock.toFixed(2)}: half of a week's effect remains after about ${Math.round(Math.log(0.5) / Math.log(MT.adstock))} weeks`]]);
    formula(p1, `z<sub>t</sub> = standardise( ln(1 + A<sub>t</sub>) )`,
      "The logarithm gives diminishing returns: the first billion impressions matter more than the tenth. Standardising expresses exposure in standard deviations, so its effect reads as Brand Index points per standard deviation.",
      [["z<sub>t</sub>", "the exposure measure used in the FIFA-specific regression"]]);
    const p2 = panel(col(g, 5), { label: "Inputs", title: "What goes in" });
    inputs(p2, [
      ["Weekly impressions and video views", "Blinkfire Analytics", "Observed"],
      ["Social media accounts covered", "FIFA World Cup, FIFA corporate, Club World Cup and others", "Observed"],
      ["Weekly carryover δ", "Fixed scenario, shared with the monetization model", "Assumed"],
    ]);
    const p3 = panel(col(g, 12), { label: "Result", title: "Accumulated FIFA exposure, week by week", sub: "Adstock of FIFA social media impressions (millions)." });
    const cv = chartIn(p3, 260);
    const SP = X.sponsorships;
    lineChart(cv, { weeks: SP.weeks, series: [{ label: "FIFA exposure", data: SP.fifa, color: T.brand, fill: true, fillColor: "rgba(89,2,238,.10)" }],
      yTitle: "Accumulated impressions (millions)", tip: (v) => v.toFixed(0) + "M", milestones: marksFor(SP.weeks, KEY_MARKS) });
    note(p3, "Exposure builds through the Club World Cup in 2025 and peaks with the 2026 World Cup.");
    src(p3, "Source: Blinkfire Analytics · Elaboration: OpenEconomics");

    const call = el("a", "topic-callout reveal");
    call.href = "#/method/television";
    call.innerHTML = `<div><div class="topic-callout-k">In depth</div><div class="topic-callout-t">Why is there no television exposure?</div>
      <p>Exposure is measured on social media. We tested adding television, observed and simulated through the World Cup: the FIFA-specific effect stays within its band.</p></div>
      <span class="bar-btn">Read →</span>`;
    root.append(call);
  }

  function topicTelevision(root) {
    const TV = MT.tv, S = TV.series;
    head(root, { kicker: "Method · Step 01 · FIFA exposure", title: "Why is there no television exposure?",
      lead: "The exposure measure counts FIFA social media impressions. No television measure covers the whole partnership, so television is not part of the primary estimate. We tested adding it: the FIFA-specific effect stays within its band, because television rises and falls in the same weeks as social media." });
    kpiRow(root, [
      { v: `${F.month(TV.coverage[0])} – ${F.month(TV.coverage[1])}`, k: "Television data available", n: "Not the announcement months, not the 2026 World Cup" },
      { v: TV.corrWeekly.toFixed(2), k: "Television vs social media", n: "Week-by-week correlation: both peak in match weeks" },
      { v: `${TV.tvPartRange[1].toFixed(2)} to ${TV.tvPartRange[0].toFixed(2)}`, k: "Television's own contribution", n: `Brand Index points, World Cup simulated; not significant in any scenario (p ${TV.tvPRange[0].toFixed(2)}–${TV.tvPRange[1].toFixed(2)})` },
      { v: F.pts(TV.primary), k: "FIFA-specific effect", n: `Unchanged within its 95% band (${F.pts(TV.band[0])} to ${F.pts(TV.band[1])})` },
    ]);

    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "The data", title: "Television exposure, observed and simulated",
      sub: "Weekly exposure in relative units (2025 Club World Cup total = 1). Television: observed to March 2026, then simulated from the World Cup match calendar." });
    const cv = chartIn(p1, 300);
    make(cv, {
      type: "bar",
      data: { labels: S.weeks, datasets: [
        { type: "bar", label: "Television, observed", data: S.observed, backgroundColor: T.brandDeep, borderWidth: 0, barPercentage: 1, categoryPercentage: 0.9, order: 3 },
        { type: "line", label: "Television, simulated (high)", data: S.simHigh, borderColor: T.brand, borderDash: [5, 4], borderWidth: 2, pointRadius: 0, tension: 0.25, spanGaps: false, order: 1 },
        { type: "line", label: "Television, simulated (low)", data: S.simLow, borderColor: T.brandLight, borderDash: [2, 3], borderWidth: 2, pointRadius: 0, tension: 0.25, spanGaps: false, order: 1 },
        { type: "line", label: "Social media (Blinkfire)", data: S.social, borderColor: T.limeInk, borderWidth: 1.8, pointRadius: 0, tension: 0.25, order: 2 },
      ] },
      options: {
        maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        scales: { x: { grid: { display: false }, ticks: weekTicks(S.weeks) },
                  y: { grid: { color: T.grid }, border: { display: false }, title: { display: true, text: "Weekly exposure (Club World Cup = 1)", color: T.muted, font: { family: T.mono, size: 10 } } } },
        plugins: { milestones: { items: marksFor(S.weeks, ["fcwc_opening_2025", "wc_opening_2026"]) },
                   tooltip: { callbacks: { title: (i) => F.month(S.weeks[i[0].dataIndex]), label: (c) => c.raw == null ? null : `${c.dataset.label}  ${c.raw.toFixed(2)}` } } },
      },
    });
    legend(p1, [{ color: T.brandDeep, label: "Television, observed", square: true }, { color: T.brand, label: "Television, simulated (high)", dash: true },
                { color: T.brandLight, label: "Television, simulated (low)", dash: true }, { color: T.limeInk, label: "Social media (Blinkfire)" }]);
    note(p1, "Television and social media rise and fall in the same tournament weeks. The television series is an estimate of on-screen brand exposure across broadcast and digital media; only its weekly pattern is used.");
    src(p1, "Sources: client media-value export, Blinkfire Analytics, FIFA match calendars · Elaboration: OpenEconomics");

    const right = col(g, 5);
    const p2 = panel(right, { label: "Test 1", title: "With the television data we have", sub: `Weeks to ${F.month(TV.observed.to)}, Brand Index points.` });
    table(p2, [{ t: "Exposure measure" }, { t: "FIFA-specific effect", num: true }], [
      ["Social media only", F.pts(TV.observed.socialOnly)],
      ["Social media + television", `${F.pts(TV.observed.withTv)}`],
      ["of which television", F.pts(TV.observed.tvPart)],
    ], { primary: 0 });
    note(p2, `Television takes over part of what social media already explains, and the total falls by ${(TV.observed.socialOnly - TV.observed.withTv).toFixed(1)} points.`);
    const p3 = panel(right, { label: "Test 2", title: "Simulating television through the World Cup",
      sub: `Value per match by stage from the ${TV.calibrationMatches}-match Club World Cup (knockout ${TV.perMatch.knockout.toFixed(1)}×, semi-final and final ${TV.perMatch.late.toFixed(1)}× a group match), applied to the ${TV.worldCupMatches} World Cup matches.` });
    const sgn = (v) => (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(2);
    table(p3, [{ t: "World Cup audience scenario" }, { t: "Size", num: true }, { t: "Social", num: true }, { t: "TV", num: true }],
      TV.scenarios.map((x) => [x.label, x.scale.toFixed(1) + "×", sgn(x.socialPart), sgn(x.tvPart)]));
    note(p3, `Full sample to July 2026, Brand Index points. Television's part is slightly negative and not significant in every scenario. Because the two series move together, social media's part shifts when television is added; the total (${F.pts(TV.range[0])} to ${F.pts(TV.range[1])}) stays inside the band of the ${F.pts(TV.primary)} estimate.`);

    const p4 = panel(col(pairGrid(root), 12), { label: "Conclusion", title: "What the test shows" });
    const ul = el("ul", "caveats");
    [
      "<b>Television and social media move together.</b> Both peak in the same match weeks, so social media already tracks when FIFA exposure happens, which is what the FIFA-specific effect is estimated from.",
      `<b>Adding television keeps the result within its band.</b> On the weeks with television data, the FIFA effect is ${F.pts(TV.observed.withTv)} with television against ${F.pts(TV.observed.socialOnly)} without. Through the World Cup, with television simulated, it is ${F.pts(TV.range[0])} to ${F.pts(TV.range[1])} against ${F.pts(TV.primary)}, inside the 95% band (${F.pts(TV.band[0])} to ${F.pts(TV.band[1])}).`,
      `<b>The split between the two is not stable.</b> Because they peak together, the model divides the effect between them differently depending on the weeks: television's part is ${F.pts(TV.observed.tvPart)} on the observed weeks and ${F.pts(TV.tvPartRange[1])} to ${F.pts(TV.tvPartRange[0])} with the World Cup simulated, while the total barely moves.`,
      `<b>Why television is not in the headline.</b> Its data cover ${F.month(TV.coverage[0])} to ${F.month(TV.coverage[1])} only, so the World Cup weeks would have to be simulated. The whole gap to the no-sponsorship twin (${F.pts(FS.attribution_band_upper_index_points)}, the ceiling) does not depend on exposure data, so any television effect is already inside it. The check will be re-run when World Cup television data arrive.`,
    ].forEach((x) => ul.append(el("li", null, x)));
    p4.append(ul);
  }

  function topicBrandIndex(root) {
    const BI = MT.brandIndex;
    head(root, { kicker: "Method · Step 01", title: "How is the Lenovo brand measured?",
      lead: "The Brand Index tracks Lenovo's share of attention against its rivals rather than raw search volume, so a market-wide wave in PC demand does not register as brand strength. A dynamic factor model combines the weekly signal with two consumer surveys, GWI and Nielsen, into one weekly index." });
    kpiRow(root, [
      { v: "100", k: "Pre-announcement level", n: `Average ${F.day(BI.base[0])} to ${F.day(BI.base[1])}` },
      { v: X.brandIndex.postMean.toFixed(1), k: "Average since the announcement", n: "Brand share of attention, % of the base" },
      { v: BI.phi.toFixed(2), k: "Weekly persistence", n: "How much of the brand factor carries to the next week" },
      { v: String(BI.weeks), k: "Weeks", n: `${F.day(BI.sample[0])} to ${F.day(BI.sample[1])}` },
    ]);
    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "Method", title: "A factor model of share of attention" });
    formula(p1, `s<sub>t</sub> = ln L<sub>t</sub> − ln Σ<sub>j</sub> R<sub>j,t</sub>`,
      "The weekly signal is Lenovo's search interest relative to the sum of its rivals', in logs. It rises only when Lenovo gains attention relative to the market.",
      [["L<sub>t</sub>", "Google search interest for Lenovo in week t"], ["R<sub>j,t</sub>", "search interest for rival brand j, from the same jointly scaled panel"]]);
    formula(p1, `y<sub>i,t</sub> = λ<sub>i</sub> f<sub>t</sub> + ε<sub>i,t</sub>  ,   f<sub>t</sub> = φ f<sub>t−1</sub> + η<sub>t</sub>`,
      "Each measurement is a noisy reading of one underlying brand factor, which moves smoothly from week to week. The surveys enter as averages of the weekly factor over their quarter (GWI engagement and consideration every quarter; Nielsen awareness in each FIFA research wave): the surveys anchor the brand's level, search gives the weekly detail.",
      [["y<sub>i,t</sub>", "standardised measurement i (weekly share of search; GWI engagement and consideration; Nielsen awareness)"], ["f<sub>t</sub>", "the brand factor"],
       ["λ<sub>i</sub>", "loading: how strongly measurement i reflects the factor"], ["φ", `weekly persistence, estimated at ${BI.phi.toFixed(3)}`]]);
    formula(p1, `BI<sub>t</sub> = 100 · exp( κ · (f<sub>t</sub> − f̄<sub>base</sub>) )`,
      "The factor is put on a readable scale: 100 is the pre-announcement average, and 110 means Lenovo's share of attention is about 10% above it.",
      [["κ", `log points of share of search per standard deviation of the factor (${BI.logPerSd.toFixed(4)})`], ["f̄<sub>base</sub>", "average factor before the announcement"]]);
    const p2 = panel(col(g, 5), { label: "Inputs", title: "What goes in" });
    inputs(p2, [
      ["Weekly search interest, Lenovo and rivals", "Google Trends, jointly scaled panels", "Observed"],
      ["Quarterly engagement and consideration", `GWI Core, ${BI.surveyQuarters} quarters`, "Observed"],
      ["Lenovo awareness by wave", `Nielsen, FIFA consumer research, ${BI.nielsenWaves} waves`, "Observed"],
      ["Share of attention", "Lenovo ÷ rivals, in logs", "Constructed"],
      ["Brand factor and loadings", "Maximum likelihood, Kalman smoother", "Estimated"],
    ]);
    const g2 = pairGrid(root);
    const p3 = panel(col(g2, 6), { label: "Diagnostics", title: "How each measurement loads on the brand factor" });
    table(p3, [{ t: "Measurement" }, { t: "Frequency" }, { t: "Loading", num: true }, { t: "Explained", num: true }, { t: "Obs.", num: true }],
      BI.loadings.map((l) => [l.signal, l.frequency, l.loading.toFixed(2), F.pct(l.explained, 0), String(l.n)]));
    note(p3, "Every measurement loads positively on the brand factor. Search carries the weekly detail; the surveys tie it to how consumers rate the brand.");
    const p4 = panel(col(g2, 6), { label: "Diagnostics", title: "Validity screen: which weekly signals enter", sub: "Correlation of each signal's quarterly average with the GWI series." });
    table(p4, [{ t: "Signal" }, { t: "Engagement", num: true }, { t: "Δ", num: true }, { t: "Consideration", num: true }, { t: "Δ", num: true }, { t: "Status" }],
      BI.screen.map((x) => [x.signal, x.engagement.toFixed(2), x.engagementChange.toFixed(2), x.consideration.toFixed(2), x.considerationChange.toFixed(2),
        x.admitted ? '<span class="tag tag--yes">Admitted</span>' : '<span class="tag tag--no">Not used</span>']));
    note(p4, "A weekly signal is admitted only if its quarterly average moves with both GWI series, in levels and in quarter-on-quarter changes (Δ).");
    const p5 = panel(col(g2, 12), { label: "Result", title: "The Brand Index, week by week", sub: "100 = pre-announcement average." });
    const cv = chartIn(p5, 260);
    lineChart(cv, { weeks: X.brandIndex.weeks, series: [{ label: "Brand Index", data: X.brandIndex.level, color: T.brandDeep }],
      yTitle: "Brand Index (100 = pre-announcement)", tip: (v) => v.toFixed(1), milestones: marksFor(X.brandIndex.weeks, KEY_MARKS) });
    table(p5, [{ t: "Variant" }, { t: "Correlation with the headline", num: true }, { t: "Average since the announcement", num: true }],
      [["Headline", "1.000", X.brandIndex.postMean.toFixed(1)], ...BI.sensitivities.map((s) => [s.label, s.corr.toFixed(3), s.postMean.toFixed(1)])], { primary: 0 });
    src(p5, "Sources: Google Trends, GWI Core, Nielsen · Elaboration: OpenEconomics");
  }

  function topicTwin(root) {
    const DS = X.design;
    head(root, { kicker: "Method · Step 01", title: "What would Lenovo look like without FIFA?",
      lead: `A synthetic Lenovo is built as a weighted mix of ${DS.donors.length} rival brands that had no part in the FIFA deal. The weights are set so the mix tracks Lenovo's Brand Index before the announcement; afterwards it shows where Lenovo would have been without the partnership.` });
    kpiRow(root, [
      { v: F.pts(X.total.lift), k: "Whole gap to the twin", n: `Average over ${X.total.weeks} weeks since the announcement` },
      { v: DS.preRmspe.toFixed(1) + " pts", k: "Pre-announcement fit", n: "Root-mean-square distance before the deal" },
      { v: "p = " + DS.placeboP.toFixed(3), k: "Significance against rivals", n: `Lenovo ranked against ${DS.placebos} rival placebos` },
      { v: F.pct(DS.sharePositive, 0), k: "Specifications positive", n: `${DS.specs} alternative designs` },
    ]);
    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "Method", title: "Synthetic difference-in-differences" });
    formula(p1, `Ŷ<sub>t</sub><sup>N</sup> = α + Σ<sub>j</sub> w<sub>j</sub> Y<sub>j,t</sub>`,
      "The twin is a weighted average of rival brands' Brand Index plus a constant level shift. The weights make the twin move like Lenovo before the announcement.",
      [["Ŷ<sub>t</sub><sup>N</sup>", "Lenovo's Brand Index without the sponsorship"], ["Y<sub>j,t</sub>", "Brand Index of rival j, built the same way as Lenovo's"],
       ["w<sub>j</sub>", "rival weights (non-negative, summing to 1)"], ["α", "level difference between Lenovo and the mix"]]);
    formula(p1, `gap<sub>t</sub> = Y<sub>t</sub> − Ŷ<sub>t</sub><sup>N</sup>`,
      "The gap is how far the real Lenovo sits above its twin. Averaged over the weeks since the announcement, it is the whole effect of the sponsorship period on the brand, before FIFA is isolated.",
      [["Y<sub>t</sub>", "Lenovo's actual Brand Index"]]);
    formula(p1, `p = share of units with a post/pre deviation ratio ≥ Lenovo's`,
      "Significance: the same design is run pretending each rival was the sponsor. The p-value is the share of units whose deviation after the announcement, relative to their fit before it, is at least as large as Lenovo's.", []);
    const p2 = panel(col(g, 5), { label: "Inputs", title: "What goes in" });
    inputs(p2, [
      ["Lenovo Brand Index", "Brand Index model", "Constructed"],
      [`${DS.donors.length} rival brands`, DS.donors.join(", "), "Observed"],
      ["Rival weights and level shift", "Fitted on pre-announcement weeks only", "Estimated"],
    ]);
    const g2 = pairGrid(root);
    const p3 = panel(col(g2, 6), { label: "Design choice", title: "Chosen on how well it predicts before the deal", sub: `Out-of-sample error over ${MT.designFolds} rolling pre-announcement folds; post-announcement data never seen.` });
    table(p3, [{ t: "Method" }, { t: "Rivals" }, { t: "Forecast error (pts)", num: true }],
      MT.designs.map((d) => [d.method, d.pool, d.oosRmspe.toFixed(2)]), { primary: MT.designs.findIndex((d) => d.selected) });
    const p4 = panel(col(g2, 6), { label: "Robustness", title: "The gap under alternative choices" });
    readout(p4, [
      ["Leaving out one rival at a time", `${F.pts(DS.looRange[0])} to ${F.pts(DS.looRange[1])}`],
      [`Across ${DS.specs} specifications`, `${F.pts(MT.specRange[0])} to ${F.pts(MT.specRange[1])}`],
      ["Specifications with a positive gap", F.pct(DS.sharePositive, 0)],
      ["Without the spring 2026 surge", F.pts(DS.exSurge.lift)],
    ]);
    const p5 = panel(col(g2, 12), { label: "Result", title: "Lenovo against its no-sponsorship twin" });
    const cv = chartIn(p5, 280);
    lineChart(cv, { weeks: X.core.weeks, series: [
      { label: "Lenovo", data: X.core.actual, color: T.brandDeep },
      { label: "No-sponsorship twin", data: X.core.synthetic, color: T.counterfactual, dash: [5, 4] }],
      yTitle: "Brand Index (100 = pre-announcement)", tip: (v) => v.toFixed(1), milestones: marksFor(X.core.weeks, KEY_MARKS) });
    legend(p5, [{ color: T.brandDeep, label: "Lenovo — actual Brand Index" }, { color: T.counterfactual, label: "No-sponsorship twin", dash: true }]);
    src(p5, "Sources: Google Trends, GWI Core, Nielsen · Elaboration: OpenEconomics");
  }

  function topicFifaSpecific(root) {
    const d = FS.decomposition_index_points, tt = X.timingTests[FS.primary_specification].fifa_log_adstock;
    head(root, { kicker: "Method · Step 01", title: "How much of the gap is FIFA?",
      lead: "The gap to the twin is regressed on accumulated FIFA exposure, with controls and a time trend. The part of the gap that moves with FIFA exposure is the FIFA-specific effect: the primary estimate carried into the valuation." });
    kpiRow(root, [
      { v: F.pts(FS.primary_index_points), k: "FIFA-specific effect", n: `${F.pctv(FS.primary_uplift_pct)} brand share of attention` },
      { v: `${FS.statistical_band_95_index_points[0].toFixed(1)}–${F.pts(FS.statistical_band_95_index_points[1])}`, k: "95% band", n: "Statistical uncertainty of the coefficient" },
      { v: F.pts(FS.attribution_band_upper_index_points), k: "Ceiling", n: "Whole gap credited to FIFA, same weeks" },
      { v: tt.points_per_sd.toFixed(2), k: "Points per s.d. of exposure", n: `p = ${tt.p.toFixed(3)}` },
    ]);
    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "Method", title: "Exposure-timing regression" });
    formula(p1, `gap<sub>t</sub> = a + c · t + β · z<sub>t</sub> + Γ′ controls<sub>t</sub> + u<sub>t</sub>`,
      "If FIFA drives the gap, weeks with more accumulated FIFA exposure should show a wider gap. β measures how much the gap widens per standard deviation of FIFA exposure; the trend absorbs slow drift unrelated to exposure timing.",
      [["gap<sub>t</sub>", "Lenovo minus its twin, Brand Index points"], ["z<sub>t</sub>", "standardised log of accumulated FIFA exposure"],
       ["β", `${tt.points_per_sd.toFixed(2)} points per s.d. (Newey–West s.e. ${tt.hac_se.toFixed(2)})`], ["t", "linear time trend"]]);
    formula(p1, `Effect<sub>FIFA</sub> = β · mean<sub>post</sub>( z<sub>t</sub> − z<sub>ref</sub> )`,
      `The coefficient times average exposure over the ${FS.weeks} measured weeks, relative to a no-exposure reference, gives the FIFA-specific effect in Brand Index points.`, []);
    formula(p1, `Uplift = Effect<sub>FIFA</sub> ÷ BI<sup>N</sup>`,
      `Divided by the twin's level (${FS.counterfactual_index_level.toFixed(1)}), the effect becomes a percentage uplift in brand share of attention: ${F.pctv(FS.primary_uplift_pct)}.`, []);
    const right = col(g, 5);
    const p2 = panel(right, { label: "Inputs", title: "What goes in" });
    inputs(p2, [
      ["Gap to the twin", "No-sponsorship twin", "Estimated"],
      ["Accumulated FIFA exposure", "Blinkfire, with carryover", "Constructed"],
      ["Controls", "Other activity and Lenovo's own events", "Constructed"],
      ["Coefficients and bands", "OLS with Newey–West errors", "Estimated"],
    ]);
    const p3 = panel(right, { label: "Result", title: "Splitting the gap" });
    const cv = chartIn(p3, 260);
    waterfall(cv, { steps: [
      { label: "Whole gap", value: d.total_gap, total: true, color: T.counterfactual },
      { label: "Not attributed to FIFA", value: d.fifa - d.total_gap, color: T.peer },
      { label: "FIFA-specific", value: d.fifa, total: true, color: T.brandDeep }], fmt: (v) => v.toFixed(2) });
    src(p3, "Sources: Blinkfire Analytics, Google Trends · Elaboration: OpenEconomics");
  }

  /* --- Step 02 topics ------------------------------------------------------ */
  function topicFactor(root) {
    const own = V.dominance.filter((x) => x.group !== "market");
    const market = V.dominance.find((x) => x.group === "market");
    const NAME = { category_demand: "PC category demand", lenovo_events: "Lenovo events", brand: "Brand (Brand Index)" };
    head(root, { kicker: "Method · Step 02", title: "How much of Lenovo's profit does the brand drive?",
      lead: "ISO 10668 asks for the brand's role in generating earnings. Here it is read from the share price: of the movement in Lenovo's weekly returns that its own drivers explain, the share attributable to the brand is the brand contribution factor." });
    kpiRow(root, [
      { v: F.pct(FAC.share, 1), k: "Brand contribution factor", n: "Brand share of Lenovo-specific drivers" },
      { v: String(V.dominance.length), k: "Driver groups", n: "Market, PC category demand, Lenovo events, brand" },
      { v: String(V.weeksN), k: "Weeks", n: "Weekly returns, 0992.HK" },
      { v: F.pct(market.share, 0), k: "Explained by market factors", n: "Set aside: they move every stock" },
    ]);
    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "Method", title: "General dominance analysis" });
    formula(p1, `r<sub>t</sub> = Σ<sub>g</sub> X<sub>g,t</sub> b<sub>g</sub> + e<sub>t</sub>`,
      "Lenovo's weekly share-price return is explained by groups of drivers: market factors (Hang Seng, Nasdaq-100), PC category demand, Lenovo's own events, and the brand (Brand Index innovations).",
      [["r<sub>t</sub>", "Lenovo weekly log return"], ["X<sub>g,t</sub>", "drivers in group g"]]);
    formula(p1, `D<sub>g</sub> = average over subsets S of [ R²(S ∪ g) − R²(S) ]`,
      "Each group's contribution is its average gain in explanatory power across every combination of the other groups (Shapley–Owen). The contributions add up to the model's R².", [["D<sub>g</sub>", "dominance weight of group g"]]);
    formula(p1, `θ = D<sub>brand</sub> ÷ ( D<sub>brand</sub> + D<sub>category</sub> + D<sub>events</sub> )`,
      "Market factors are set aside. The brand's share of what Lenovo's own drivers explain is the factor θ applied to economic profit.", [["θ", `brand contribution factor, ${F.pct(FAC.share, 1)}`]]);
    const right = col(g, 5);
    const p2 = panel(right, { label: "Inputs", title: "What goes in" });
    inputs(p2, [
      ["Lenovo daily closes", "0992.HK", "Observed"],
      ["Market factors", "Hang Seng, Nasdaq-100 in HKD", "Observed"],
      ["Brand Index innovations", "Brand Index model", "Constructed"],
      ["Dominance weights", "Shapley–Owen decomposition", "Estimated"],
    ]);
    const p3 = panel(right, { label: "Result", title: "Lenovo's own drivers", sub: "Share of what Lenovo-specific drivers explain." });
    const cv = chartIn(p3, 180);
    barsH(cv, { labels: own.map((x) => NAME[x.group] || x.group), values: own.map((x) => x.shareOfLenovoSpecific),
      colors: own.map((x) => (x.group === "brand" ? T.brand : T.peer)), xFmt: (v) => F.pct(v, 0) });
    src(p3, "Source: market data · Elaboration: OpenEconomics");
  }

  function topicIncomeSplit(root) {
    head(root, { kicker: "Method · Step 02", title: "How is the brand valued?",
      lead: "The ISO 10668 income approach values the brand as the present value of the earnings it generates. Lenovo's economic profit, what its operations earn above the cost of the capital they use, is forecast and discounted; the brand's share of it is the brand contribution factor." });
    kpiRow(root, [
      { v: F.usd(B.brandValue), k: "Brand value", n: "Present value of branded earnings" },
      { v: F.usd(D.epPv), k: "Economic profit, discounted", n: "Lenovo as a whole" },
      { v: F.pct(D.terminalShare, 0), k: "Value beyond year 5", n: `Long-run growth ${F.pct(D.growthTerminal, 0)}` },
      { v: F.usd(B.valuePerPoint), k: "Per Brand Index point", n: "Brand value ÷ twin level" },
    ]);
    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "Method", title: "Economic profit, split and discounted" });
    formula(p1, `EP<sub>t</sub> = NOPAT<sub>t</sub> − WACC · IC<sub>t−1</sub>`,
      "Economic profit is after-tax operating profit minus a charge for the capital employed at the start of the year.",
      [["NOPAT<sub>t</sub>", "revenue × operating margin × (1 − tax rate)"], ["IC<sub>t−1</sub>", "opening invested capital: equity + debt − cash"], ["WACC", `cost of capital, ${F.pct(D.wacc.wacc, 2)}`]]);
    formula(p1, `BE<sub>t</sub> = θ · EP<sub>t</sub>`,
      "Branded earnings are the brand's share of economic profit.", [["θ", `brand contribution factor, ${F.pct(FAC.share, 1)}`]]);
    formula(p1, `BV = Σ<sub>t=1…5</sub> BE<sub>t</sub> ⁄ (1+WACC)<sup>t</sup>  +  [ BE<sub>5</sub>(1+g) ⁄ (WACC − g) ] ⁄ (1+WACC)<sup>5</sup>`,
      "Five forecast years are discounted; the years after are captured by a growing perpetuity.",
      [["g", `long-run growth, ${F.pct(D.growthTerminal, 0)}`], ["BV", `brand value, ${F.usd(B.brandValue)}`]]);
    const p2 = panel(col(g, 5), { label: "Inputs", title: "What goes in" });
    inputs(p2, [
      [`Revenue ${D.baseYear}: ${F.usd(D.revenue)}`, "Lenovo annual results", "Observed"],
      [`Operating margin ${F.pct(D.operatingMargin, 1)}, tax ${F.pct(D.taxRate, 1)}`, "Lenovo annual results", "Observed"],
      [`Invested capital ${F.usd(D.investedCapital)}`, "Balance sheet", "Observed"],
      [`Growth ${F.pct(D.growthStart, 1)} fading to ${F.pct(D.growthTerminal, 0)}`, "Three-year trend, then long-run rate", "Assumed"],
      ["Brand contribution factor", "Share-price analysis", "Estimated"],
    ]);
    const p3 = panel(col(g, 12), { label: "Result", title: "The forecast" });
    table(p3, [{ t: "Year" }, { t: "Revenue", num: true }, { t: "NOPAT", num: true }, { t: "Capital charge", num: true }, { t: "Economic profit", num: true }, { t: "Branded earnings", num: true }],
      D.forecast.map((f) => [String(f.year), F.usd(f.revenue), F.usd(f.nopat), "−" + F.usd(f.charge), F.usd(f.ep), F.usd(f.branded)]));
    readout(p3, [["Discounted, years 1–5", F.usd(D.explicitPv)], ["Discounted, beyond year 5", F.usd(D.terminalPv)], ["Brand value", F.usd(B.brandValue)]]);
    src(p3, "Source: Lenovo annual results · Elaboration: OpenEconomics");
  }

  function topicWacc(root) {
    const W = D.wacc;
    head(root, { kicker: "Method · Step 02", title: "What discount rate is used?",
      lead: "Branded earnings are discounted at Lenovo's weighted average cost of capital: the return its shareholders and lenders require, weighted by their share of the company's market value." });
    kpiRow(root, [
      { v: F.pct(W.wacc, 2), k: "WACC", n: "Discount rate" },
      { v: F.pct(W.costOfEquity, 2), k: "Cost of equity", n: "CAPM" },
      { v: F.pct(W.costOfDebt, 2), k: "Cost of debt, after tax", n: "Risk-free rate plus spread, less tax" },
      { v: F.pct(W.weightDebt, 1), k: "Debt weight", n: "Market values" },
    ]);
    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "Method", title: "CAPM and market-value weights" });
    formula(p1, `K<sub>e</sub> = r<sub>f</sub> + β · ERP`,
      "Shareholders require the risk-free rate plus a premium for equity risk, scaled by how much Lenovo's shares move with world equities.",
      [["r<sub>f</sub>", `US 10-year Treasury yield, ${F.pct(W.riskFree, 2)}`], ["β", `Lenovo's beta against world equities (104 weeks, Blume-adjusted), ${W.beta.toFixed(2)}`], ["ERP", `equity risk premium, ${F.pct(W.erp, 1)}`]]);
    formula(p1, `WACC = (1 − w<sub>d</sub>) · K<sub>e</sub> + w<sub>d</sub> · K<sub>d</sub> · (1 − τ)`,
      "The cost of equity and the after-tax cost of debt are averaged with the market-value weights of equity and debt.",
      [["w<sub>d</sub>", `debt weight, ${F.pct(W.weightDebt, 1)}`], ["K<sub>d</sub>", "pre-tax cost of debt: US 10-year yield plus a credit spread"],
       ["K<sub>d</sub>(1 − τ)", `after-tax cost of debt, ${F.pct(W.costOfDebt, 2)}`]]);
    const right = col(g, 5);
    const p2 = panel(right, { label: "Inputs", title: "What goes in" });
    inputs(p2, [
      ["Risk-free rate", "US Treasury, 10-year", "Observed"],
      ["Equity beta", "0992.HK vs world equities, weekly", "Estimated"],
      ["Equity risk premium", "Planning assumption", "Assumed"],
      ["Debt spread", "Planning assumption", "Assumed"],
      ["Equity and debt values", "Market capitalisation; balance sheet", "Observed"],
    ]);
    const h = D.heat;
    const p3 = panel(right, { label: "Result", title: "Brand value by factor and WACC" });
    table(p3, [{ t: "Factor" }, ...h.waccs.map((w) => ({ t: "WACC " + F.pct(w, 1), num: true }))],
      h.roles.map((ro) => [F.pct(ro, 0), ...h.waccs.map((w) => F.usd((h.values.find((v) => v.role === ro && v.wacc === w) || {}).value))]));
  }

  /* --- Step 03 ------------------------------------------------------------- */
  function topicMonetization(root) {
    const S3 = M.scenarios;
    head(root, { kicker: "Method · Step 03", title: "How is the FIFA effect turned into money?",
      lead: "The brand value moves in proportion to Lenovo's brand share of attention. The FIFA-specific uplift in brand share, applied to the brand value, gives the brand value FIFA added; entering the programme cost gives the return on it." });
    kpiRow(root, [
      { v: F.usd(S3.base.value), k: "FIFA-added brand value", n: "Base case" },
      { v: F.pctv(S3.base.upliftPct, 2), k: "Uplift in brand share", n: `${S3.base.indexPoints.toFixed(2)} Brand Index points` },
      { v: F.usd(B.brandValue), k: "Brand value", n: "Income split" },
      { v: F.usd(S3.base.value), k: "Break-even programme cost", n: "Cost at which the return is 1×" },
    ]);
    const g = pairGrid(root);
    const p1 = panel(col(g, 7), { label: "Method", title: "Uplift × brand value" });
    formula(p1, `ΔBV<sub>FIFA</sub> = ε · ( Effect<sub>FIFA</sub> ÷ BI<sup>N</sup> ) · BV`,
      "FIFA's share of the brand value is the percentage uplift in brand share times the brand value. With ε = 1, a 1% higher brand share means a 1% higher brand value.",
      [["ε", "elasticity of brand value to brand share, 1"], ["Effect<sub>FIFA</sub> ÷ BI<sup>N</sup>", `FIFA-specific uplift, ${F.pctv(S3.base.upliftPct, 2)}`], ["BV", `brand value, ${F.usd(B.brandValue)}`]]);
    formula(p1, `Return = ΔBV<sub>FIFA</sub> ÷ programme cost`,
      "The multiple on the programme cost (rights fee plus activation), entered on the Monetization page.", []);
    const p2 = panel(col(g, 5), { label: "Scenarios", title: "Three readings of the uplift" });
    table(p2, [{ t: "Case" }, { t: "Uplift", num: true }, { t: "FIFA-added value", num: true }],
      ["conservative", "base", "ambitious"].map((k) => [`<b>${LAB[k]}</b>`, F.pctv(S3[k].upliftPct, 2), F.usd(S3[k].value)]), { primary: 1 });
    note(p2, "Conservative: low end of the 95% band. Base: primary estimate. Ambitious: the whole gap credited to FIFA.");
    const p3 = panel(col(g, 12), { label: "Result", title: "The same value as yearly branded earnings" });
    const fl = M.fifaBrandedEarnings;
    table(p3, [{ t: "Base case" }, ...fl.map((f) => ({ t: "Year " + f.year, num: true }))],
      [["FIFA's branded earnings", ...fl.map((f) => F.usd(f.value))], ["Discounted", ...fl.map((f) => F.usd(f.pv))]]);
    src(p3, "Source: Lenovo annual results · Elaboration: OpenEconomics");
  }

  /* --- Foundations ---------------------------------------------------------- */
  function topicSources(root) {
    head(root, { kicker: "Method · Foundations", title: "What data is the study built on?",
      lead: "The study combines search, survey, social media, market and financial data. Each figure is labelled by how it is obtained: observed directly, constructed from observed data, estimated by a model, or assumed." });
    const g = pairGrid(root);
    const p1 = panel(col(g, 6), { label: "Data sources", title: "What the study is built on" });
    table(p1, [{ t: "Source" }, { t: "Contribution" }], [
      ["<b>Google Trends</b>", "Weekly search interest for Lenovo and rival brands in jointly scaled panels"],
      ["<b>GWI Core</b>", "Quarterly engagement and consideration of Lenovo (2022–2026Q1)"],
      ["<b>Nielsen</b>", `FIFA consumer research: Lenovo awareness in ${MT.brandIndex.nielsenWaves} national-sample waves (June 2024 – April 2026)`],
      ["<b>Blinkfire Analytics</b>", "Weekly impressions and video views on FIFA social media"],
      ["<b>Market data</b>", "0992.HK, Hang Seng, Nasdaq-100, world equities, USD/HKD, US Treasury"],
      ["<b>Lenovo annual results</b>", `${D.baseYear} revenue, operating profit, tax, equity, debt and cash`],
      ["<b>Lenovo</b>", "Results and event calendar"],
      ["<b>FIFA</b>", "Match calendar; partnership announcements"],
    ]);
    const p2 = panel(col(g, 6), { label: "Status of the figures", title: "Observed, constructed, estimated, assumed" });
    table(p2, [{ t: "Status" }, { t: "Applies to" }], [
      [status("Observed"), "Search volumes, GWI and Nielsen survey waves, impressions, share prices, financial statements"],
      [status("Constructed"), "Brand Index, share of attention, accumulated exposure"],
      [status("Estimated"), "No-sponsorship twin, FIFA-specific effect, brand contribution factor, brand value"],
      [status("Assumed"), "Equity risk premium, debt spread, growth path, weekly carryover, elasticity of 1"],
    ]);
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

  function render(path) {
    const [id, sub] = path.split("/");
    const view = VIEWS[id] ? id : "summary";
    const pos = ORDER.indexOf(view);
    document.querySelectorAll(".chev").forEach((b) => {
      const i = ORDER.indexOf(b.dataset.step);
      b.classList.toggle("is-active", b.dataset.step === view);
      b.classList.toggle("is-done", pos > -1 && i > -1 && i < pos);
    });
    document.getElementById("method-link").classList.toggle("is-active", view === "method");
    const topic = view === "method" && TOPICS.find((x) => x.id === sub);
    document.title = (topic ? topic.name + " · " : "") + (VIEWS[view].n ? "Step " + VIEWS[view].n + " · " : "") + VIEWS[view].label + " — " + E.meta.caseLabel + " · OpenEconomics";
    killAll();
    const root = document.getElementById("view");
    root.innerHTML = "";
    VIEWS[view].render(root, sub);
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
