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
  const B = V.brand;
  const S = () => M.scenarios[scenarioKey];

  /* ============================================================ VIEW 1 === */
  function viewExposure(root) {
    const K = X.kpi, D = X.design, d = FS.decomposition_index_points;

    head(root, {
      kicker: "Step 01 · Exposure",
      title: "How much more did Lenovo stand out because of FIFA?",
      lead: `FIFA properties delivered ${F.big(K.eventImpressions)} measured digital impressions for Lenovo. Exposure alone proves nothing: the whole PC market moved in these two years. So the brand is measured as its <em>share</em> of attention against rival brands, compared with a synthetic Lenovo built from ${D.donors.length} rivals that had no part in the FIFA deal, and the gap is then split between FIFA, Lenovo's other sponsorships and what remains unexplained.`,
    });

    flow(root, [
      { k: "The event", v: F.big(K.eventImpressions) + " impressions", d: "FIFA-family digital and social exposure (Blinkfire); broadcast not measured" },
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
    note(pB, `Exposure is concentrated in tournament windows; the World Cup alone delivered ${F.big(X.byProperty[0].impressions)} impressions. Blinkfire covers digital and social only, through ${F.day(X.event.coverageEnd)}; broadcast audiences are not measured.`);
    src(pB, "Source: Blinkfire Analytics (client exports) · Elaboration: OpenEconomics");
    const pC = panel(col(g2, 5), { label: "Composition", title: "Which properties delivered it", sub: "Digital impressions by FIFA property over the partnership window." });
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
      ["Placebo test", `p = ${D.placeboP.toFixed(3)} (lowest possible ${D.minP.toFixed(3)})`],
      ["Leaving out one rival", `${F.pts(D.looRange[0])} to ${F.pts(D.looRange[1])}`],
      ["Specifications positive", `${Math.round(D.sharePositive * 100)}% of ${D.specs}`],
      ["Without the spring 2026 surge", `${F.pts(D.exSurge.lift)} · p = ${D.exSurge.p.toFixed(3)}`],
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

    const pG = panel(col(g4, 5), { label: "Splitting the gap", title: "What explains the gap", sub: `Average gap over the ${FS.weeks} weeks with exposure data, split by a regression on FIFA exposure, other sponsorships and Lenovo events, with a trend.` });
    const cvG = chartIn(pG, 300);
    waterfall(cvG, {
      steps: [
        { label: "Whole gap", value: d.total_gap, total: true, color: T.counterfactual },
        { label: "Unexplained residual", value: -d.residual, color: T.peer },
        { label: "Other sponsorships & events", value: -(d.other_sponsorships + d.events), color: T.peerLine },
        { label: "FIFA-specific", value: d.fifa, total: true, color: T.brandDeep },
      ],
      fmt: (v) => v.toFixed(2),
    });
    note(pG, `Other sponsorships account for ${F.pts(d.other_sponsorships)} and Lenovo events for ${F.pts(d.events)}. <b>${F.pts(d.residual)}</b> stays unexplained: a slow Lenovo-specific drift, or FIFA effects the exposure measure misses. It is not credited to FIFA in the primary estimate.`);

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

    const pI = panel(col(g5, 7), { label: "Close-up", title: "The World Cup within the sponsorship", sub: "Mean gap to the no-sponsorship twin by period (Brand Index points), and the pre-registered incremental test of the tournament (interim)." });
    const W = X.worldCup;
    table(pI, [{ t: "Period" }, { t: "Weeks", num: true }, { t: "Gap vs twin", num: true }], [
      ["Sponsorship before the tournament", W.beforeTournament.weeks, F.pts(W.beforeTournament.gap)],
      ["Men's World Cup (tournament weeks)", W.tournament.weeks, F.pts(W.tournament.gap)],
      ["After the final", W.afterFinal.weeks, F.pts(W.afterFinal.gap)],
    ]);
    note(pI, `Against the no-sponsorship twin the tournament weeks sit at ${F.pts(W.tournament.gap)} and the weeks after the final at <b>${F.pts(W.afterFinal.gap)}</b>, against ${F.pts(W.beforeTournament.gap)} earlier. The pre-registered test of what the tournament added on top of Lenovo's own trajectory is still interim: ${F.pts(W.incremental.primary_exposure_weighted_gap)} (p = ${W.incrementalP.toFixed(2)}), with ${W.gatesOpen} of ${W.gates} acceptance gates open until the evaluation window closes on 18 October 2026.`);
    src(pI, "Sources: sponsorship_total_effect_v1 · world_cup_impact_v1 (pre-registered, ADR-0019/0029, amended ADR-0040)");

    const g6 = grid(root);
    const pJ = panel(col(g6, 6), { label: "Robustness", title: "Same design, different outcomes", sub: "The engine re-run on Google share of search alone and on the former search-salience index (each in its own units)." });
    table(pJ, [{ t: "Outcome" }, { t: "Effect", num: true }, { t: "Placebo p", num: true }, { t: "Unit" }],
      X.crossChecks.map((c) => [c.label, (c.lift > 0 ? "+" : "") + c.lift.toFixed(2), c.p.toFixed(3), c.unit]), { primary: 0 });
    note(pJ, "All three agree in direction. Significance is clearest on the headline design and weakens on share of search alone once the spring 2026 surge is removed.");
    const pK = panel(col(g6, 6), { label: "Why this split", title: "The FIFA share under other specifications", sub: "The primary specification is fixed (trend, full sample); the alternatives either over-attribute or let a post-period trend absorb FIFA's cumulative build-up." });
    table(pK, [{ t: "Specification" }, { t: "FIFA", num: true }, { t: "Residual", num: true }],
      FS.specifications.map((s) => [s.spec.replace(/_/g, " "), s.fifa.toFixed(2), s.residual.toFixed(2)]),
      { primary: FS.specifications.findIndex((s) => s.spec === FS.primary_specification.replace(":", " / ")) });
    src(pK, "Decomposition: sponsorship_exposure_timing_v1 (ADR-0043) · specification fixed by the owner after it was seen");

    pager(root, "summary", "evaluation");
  }

  /* ============================================================ VIEW 2 === */
  function viewEvaluation(root) {
    const dom = Object.fromEntries(V.dominance.map((g) => [g.group, g]));
    const h0 = V.stockResponse[0], P = V.placebo;

    head(root, {
      kicker: "Step 02 · Evaluation",
      title: "What is the Lenovo brand worth?",
      lead: "Lenovo is listed, so the market prices it every day. The share price is first stripped of what the Hong Kong market and the global technology cycle explain: those moves reflect interest rates and risk appetite, not Lenovo's earning power. Of the movement driven by Lenovo's own factors, the analysis measures how much comes from the brand, against PC category demand and Lenovo's own news, and reads that share as the brand's share of the company's value.",
    });

    flow(root, [
      { k: "Input", v: "Weekly Brand Index moves", d: "Unexpected changes, predicted from prior weeks only" },
      { k: "Brand share of Lenovo-specific drivers", v: F.pct(B.share, 1), d: "Dominance analysis of weekly abnormal returns, market factors set aside", cls: "flow-cell--mid" },
      { k: "Output → Monetization", v: F.usd(B.brandValue) + " brand value", d: `${F.usd(B.valuePerPoint)} per Brand Index point`, cls: "flow-cell--out" },
    ]);

    kpiRow(root, [
      { v: V.ticker, k: "Listed brand under study", n: "The market price is the measuring instrument; only listed brands can be valued this way." },
      { v: F.pct(B.share, 1), k: "Brand share of Lenovo-specific drivers", n: "The brand against PC category demand and Lenovo events, in what moves the share price." },
      { v: F.usd(B.brandValue), k: "Lenovo brand value", n: "Brand share × market capitalisation." },
      { v: F.usd(V.marketCap), k: "Market capitalisation", n: "Mean over the weeks since the announcement (rule-based valuation base)." },
    ]);

    const g0 = grid(root);
    const pW = panel(col(g0, 12), { cls: "panel--tint", label: "The instrument", title: "Why the share price, and what it can and cannot say", sub: "The valuation rests on one reading of market data. It is stated in full, with the points at which it strains." });
    const cols = el("div", "cols2");
    const left = el("div", "assump");
    left.append(el("div", "assump-h", "The reasoning"));
    left.append(el("p", null, "A share price aggregates investors' expectations of future profit. Weekly abnormal returns are decomposed with a general-dominance analysis: each group of Lenovo-specific drivers (PC category demand, Lenovo events, the brand) receives its average contribution to the explained movement over every order in which the groups can be added. Market-wide moves are set aside, because brand value is a slice of what Lenovo's own business is worth."));
    left.append(el("p", null, `The direct route was tried first and is shown below: regressing abnormal returns on unexpected Brand Index moves gives <b>${F.pp(h0.est)}</b> per point with p = ${h0.p.toFixed(2)}; no horizon survives the multiple-testing correction. The market does not reveal a clean per-point price, so the brand's role in price formation is used instead.`));
    cols.append(left);
    const right = el("div", "assump");
    right.append(el("div", "assump-h", "What has to be true — and where it strains"));
    const ul = el("ul");
    [
      ["Variance share is read as value share.", "A brand's share of what moves the price is taken as its share of what the company is worth. That is a judgement, not a measurement."],
      ["The base is thin.", `Lenovo-specific drivers explain a small part of weekly returns, so the brand's share of them is imprecise: 90% bootstrap range ${F.pct(B.share90[0], 0)} to ${F.pct(B.share90[1], 0)}.`],
      ["An unrelated series gets a similar share.", `Put a random series in the brand's place and it takes a median ${F.pct(P.noiseMedian, 0)}; the brand's ${F.pct(P.actual, 1)} is not distinguishable from that (p = ${P.noiseP.toFixed(2)}). The market data alone cannot pin the brand's share down.`],
      ["Unexplained Lenovo news is left out.", `The share is of the measured drivers only; across samples and control sets it ranges from ${F.pct(V.stabilityShareRange[0], 0)} to ${F.pct(V.stabilityShareRange[1], 0)}.`],
    ].forEach(([h, tx]) => ul.append(el("li", null, "<b>" + h + "</b> " + tx)));
    right.append(ul);
    cols.append(right);
    pW.append(cols);
    pW.append(el("div", "verdict-line", `The honest summary: the share-price evidence gives a brand worth <b>${F.usd(B.brandValue)}</b> but cannot by itself pin the brand's share down. The level is credible because independent valuations with different methods land close to it: <b>${F.usd(V.brandFinance)}</b> (Brand Finance 2025, royalty relief) and about <b>${F.usd(V.interbrand2015)}</b> (Interbrand 2015).`));

    const g1 = grid(root);
    const pA = panel(col(g1, 7), { label: "Isolating what the market cannot explain", title: "Observed share price vs the path explained by market factors", sub: "A rolling market model, re-estimated each day on the prior 120 trading days only, prices 0992.HK against the Hang Seng and the previous Nasdaq-100 session in HKD." });
    const cvA = chartIn(pA, 320);
    lineChart(cvA, {
      weeks: V.weeks,
      series: [
        { label: "Explained by market factors", data: V.expectedPath, color: T.counterfactual, width: 2, dash: [6, 4], order: 2 },
        { label: "Observed share price", data: V.actualPath, color: T.brand, width: 2.6, fill: "-1", fillColor: "rgba(89,2,238,.10)", order: 1 },
      ],
      milestones: marksFor(V.weeks, KEY_MARKS),
      yTitle: "Price index · 100 = start of sample",
      tip: (v) => (v == null ? "—" : v.toFixed(1)),
    });
    legend(pA, [{ color: T.brand, label: "Observed share price" }, { color: T.counterfactual, label: "Path explained by market factors", dash: true }]);
    pA.append(el("div", "panel-label spaced", "Residual · cumulative abnormal return"));
    const cvA2 = chartIn(pA, 130);
    lineChart(cvA2, {
      weeks: V.weeks,
      series: [{ label: "Cumulative abnormal return", data: V.carPath, color: T.brandDeep, width: 2, fill: "origin", fillColor: "rgba(68,0,179,.13)" }],
      milestones: marksFor(V.weeks, ["fifa_partner_announcement_2024", "wc_opening_2026"]),
      yFmt: (v) => v.toFixed(0) + "%", tip: (v) => (v == null ? "—" : F.pctv(v)),
    });
    const carAt = V.carPath[V.annIdx], carNow = V.carPath[V.carPath.length - 1];
    note(pA, `At the announcement the share stood ${F.pctv(carAt)} against what market factors implied; it now stands <b>${F.pctv(carNow)}</b>. That residual is what Lenovo's own drivers, the brand among them, have to explain.`);
    src(pA, `Source: market data (0992.HK, Hang Seng, Nasdaq-100 in HKD) · average loadings: Hang Seng ${V.betas.hsi}, Nasdaq-100 ${V.betas.ndx}`);

    const pB = panel(col(g1, 5), { label: "Relative importance", title: "What drives Lenovo's own share-price movement", sub: `Share of the movement explained by Lenovo-specific drivers (general dominance, ${V.weeksN} weeks), market factors set aside.` });
    const cvB = chartIn(pB, 210);
    const NAMES = { category_demand: "PC category demand", lenovo_events: "Lenovo events", brand: "Brand (Brand Index)" };
    const own = V.dominance.filter((g) => g.group !== "market");
    barsH(cvB, {
      labels: own.map((g) => NAMES[g.group] || g.group), values: own.map((g) => g.shareOfLenovoSpecific * 100),
      colors: own.map((g) => (g.group === "brand" ? T.brand : T.peer)), xFmt: (v) => v.toFixed(0) + "%",
    });
    note(pB, `The brand accounts for <b>${F.pct(B.share, 1)}</b> of the movement Lenovo's own drivers explain; its coefficient is positive (t = ${(V.brandCoef.coefficient / V.brandCoef.robust_se).toFixed(2)}), so the share counts as value. Market factors, set aside here, explain ${F.pct(dom.market.share, 0)} of all explained weekly movement.`);
    src(pB, "Elaboration: OpenEconomics · stock_brand_response_v2, brand_value_dominance_v1 (ADR-0044)");

    const g2 = grid(root);
    const pC = panel(col(g2, 7), { label: "How firm is the share?", title: "The brand against a meaningless stand-in", sub: "The same analysis with a random series, and with the real Brand Index series shifted out of step with the share price, in the brand's place." });
    const cvC = chartIn(pC, 230);
    barsH(cvC, {
      labels: ["Brand (actual)", "Random series (median of 500)", "Brand series shifted in time (median)"],
      values: [P.actual * 100, P.noiseMedian * 100, P.shiftMedian * 100],
      colors: [T.brand, T.peer, T.peer], xFmt: (v) => v.toFixed(0) + "%",
    });
    note(pC, `A stand-in with no connection to Lenovo takes a similar share (random series: p = ${P.noiseP.toFixed(2)}; time-shifted: p = ${P.shiftP.toFixed(2)}). Lenovo's own drivers explain so little of weekly returns that the split among them is not identified by the data. The brand value therefore rests on the reading, corroborated by independent valuations, not on statistical proof.`);
    const pD = panel(col(g2, 5), { label: "The direct test", title: "Cumulative abnormal return per unexpected point", sub: "Four horizons frozen in advance and tested as one family (Holm correction)." });
    table(pD, [{ t: "Horizon" }, { t: "Estimate", num: true }, { t: "95% interval", num: true }, { t: "Holm p", num: true }],
      V.stockResponse.map((h) => [h.h + (h.h === 1 ? " week" : " weeks"), F.pp(h.est), `${F.pp(h.lo)} to ${F.pp(h.hi)}`, `<span class="nsig">${h.pHolm.toFixed(2)}</span>`]));
    note(pD, "No horizon is distinguishable from zero, which is why the valuation uses relative importance rather than a per-point coefficient.");

    const g3 = grid(root);
    const pE = panel(col(g3, 7), { label: "Corroboration", title: "Independent valuations of the Lenovo brand", sub: "This study's value next to published brand valuations that use different methods and data." });
    const cvE = chartIn(pE, 220);
    barsH(cvE, {
      labels: ["This study (2026, share-price evidence)", "Brand Finance 2025 (royalty relief)", "Interbrand 2015 (Best Global Brands)"],
      values: [B.brandValue, V.brandFinance, V.interbrand2015], colors: [T.brand, T.peer, T.peer], xFmt: (v) => F.usd(v),
    });
    note(pE, `Three methods, about a decade apart, land between ${F.usd(Math.min(B.brandValue, V.brandFinance, V.interbrand2015))} and ${F.usd(Math.max(B.brandValue, V.brandFinance, V.interbrand2015))}. The study's 90% bootstrap range (${F.usd(B.band90[0])} to ${F.usd(B.band90[1])}) is wide; the convergence is what makes the level credible.`);
    src(pE, "Elaboration: OpenEconomics · Brand Finance China 500 2025 · Interbrand Best Global Brands 2015 (as reported by Lenovo)");
    const pF = panel(col(g3, 5), { cls: "panel--dark", label: "Output of step 02" });
    pF.append(el("div", "figure-v lime", F.usd(B.brandValue)));
    pF.append(el("div", "figure-k", "Lenovo brand value"));
    readout(pF, [
      ["Brand share of Lenovo-specific drivers", F.pct(B.share, 1)],
      ["Market capitalisation", F.usd(V.marketCap)],
      ["Value per Brand Index point", F.usd(B.valuePerPoint)],
      ["Brand Finance 2025, for reference", F.usd(V.brandFinance)],
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
      lead: "The FIFA-specific uplift in brand share is applied to the brand value from step 02. The result is a capitalised value, not a yearly flow: it assumes the uplift holds, which is why the path of the gap is shown below. The programme cost is not in the data, so the break-even cost is stated and any cost can be entered to read the multiple.",
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
    const pA = panel(col(g1, 8), { label: "Value bridge", title: "From the whole gap to the FIFA-specific value", sub: `The whole gap to the no-sponsorship twin, priced at ${F.usd(B.brandValue)} of brand value, less what FIFA exposure does not explain.` });
    const cvA = chartIn(pA, 340);
    const br = M.bridge;
    waterfall(cvA, {
      steps: [
        { label: br[0].label, value: br[0].value, total: true, color: T.counterfactual },
        { label: br[1].label, value: br[1].value, color: T.peer },
        { label: br[2].label, value: br[2].value, color: T.peerLine },
        { label: br[3].label, value: br[3].value, total: true, color: T.brandDeep },
      ],
      fmt: (v) => F.usd(v),
    });
    note(pA, `<b>How to read it.</b> Credited in full, Lenovo's whole gap to its rivals would be worth ${F.usd(br[0].value)}. ${F.usd(-br[1].value)} of it is not explained by any measured exposure and is not credited to FIFA; other sponsorships and events net to ${F.usd(br[2].value)}. What FIFA exposure explains is <b>${F.usd(br[3].value)}</b>.`);
    src(pA, "Elaboration: OpenEconomics · brand_value_dominance_v1, sponsorship_exposure_timing_v1 (ADR-0043)");

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
        : "The rights fee and activation spend are not in the data. Enter them to read the multiple; the sponsorship pays for itself in brand value if they total less than the break-even cost.";
    };
    input.addEventListener("input", showCost);
    showCost();
    pB.append(out);

    kpiRow(root, [
      { v: F.usd(value), k: "FIFA-added brand value", n: `${LAB[scenarioKey]} case.` },
      { v: F.pctv(s.upliftPct, 2), k: "Uplift in brand share", n: `${s.indexPoints.toFixed(2)} Brand Index points over a no-sponsorship level of ${FS.counterfactual_index_level.toFixed(1)}.` },
      { v: F.usd(B.brandValue), k: "Lenovo brand value", n: "From the share-price evidence (step 02)." },
      { v: F.usd(M.scenarios.ambitious.value), k: "Ceiling: whole gap credited to FIFA", n: `${F.pctv(M.scenarios.ambitious.upliftPct, 2)} brand share, residual included.` },
    ]);

    const g2 = grid(root);
    const pP = panel(col(g2, 7), { label: "Is the lift holding?", title: "Gap to the no-sponsorship twin, quarter by quarter", sub: "The capitalised value assumes the uplift persists. This is the observed path of the whole gap (Brand Index points)." });
    const cvP = chartIn(pP, 280);
    barsV(cvP, {
      labels: M.quarterlyGap.map((q) => q.q), values: M.quarterlyGap.map((q) => q.gap),
      colors: M.quarterlyGap.map((q) => (q.q.startsWith("2026Q3") ? T.brandLight : T.brandDeep)), yFmt: (v) => v.toFixed(0),
      yTitle: "Mean gap · Brand Index points",
    });
    const qs = M.quarterlyGap;
    note(pP, `The gap built through 2025 and has not faded: ${qs[qs.length - 2].q} ${F.pts(qs[qs.length - 2].gap)}, ${qs[qs.length - 1].q} so far ${F.pts(qs[qs.length - 1].gap)}. If it decays once activation stops, the capitalised value overstates FIFA's contribution; a brand-tracking wave after the tournament would settle it.`);

    const pQ = panel(col(g2, 5), { label: "Scenario ladder", title: "Uplift in, brand value out", sub: "The three cases are the primary estimate and its bands." });
    table(pQ, [{ t: "Case" }, { t: "Uplift", num: true }, { t: "Index points", num: true }, { t: "FIFA-added value", num: true }],
      ["conservative", "base", "ambitious"].map((k) => [`<b>${LAB[k]}</b>`, F.pctv(M.scenarios[k].upliftPct, 2), M.scenarios[k].indexPoints.toFixed(2), F.usd(M.scenarios[k].value)]),
      { primary: ["conservative", "base", "ambitious"].indexOf(scenarioKey) });
    note(pQ, "Conservative is the low end of the 95% band; ambitious credits the whole gap, residual included, to FIFA.");

    const g3 = grid(root);
    const pC = panel(col(g3, 6), { label: "Sensitivity", title: "What moves the answer", sub: "Base case; each input moved across its range with the others held." });
    const cvC = chartIn(pC, 280);
    const tor = M.tornado;
    make(cvC, {
      type: "bar",
      data: {
        labels: tor.map((t) => t.label),
        datasets: [{ label: "Range", data: tor.map((t) => [Math.min(t.lo, t.hi), Math.max(t.lo, t.hi)]), backgroundColor: T.brandDeep, borderWidth: 0, barPercentage: 0.6 }],
      },
      options: {
        indexAxis: "y", maintainAspectRatio: false,
        scales: {
          x: { grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => F.usd(v), maxTicksLimit: 6 } },
          y: { grid: { display: false }, border: { display: false }, ticks: { font: { family: T.sans, size: 11 }, color: T.ink, callback(v) { const l = this.getLabelForValue(v); return l.length > 34 ? [l.slice(0, l.indexOf("(")).trim(), l.slice(l.indexOf("("))] : l; } } },
        },
        plugins: { tooltip: { callbacks: { label: (c) => F.usd(c.raw[0]) + " to " + F.usd(c.raw[1]) } } },
      },
    });
    note(pC, "The brand's measured share of Lenovo's own price drivers dominates: what the brand is worth is far less certain than how much FIFA lifted it.");

    const pD = panel(col(g3, 6), { label: "Cross-checks", title: "Other routes to a money figure", sub: "Independent valuation routes, each with its own link from brand to money. None is statistically identified; they bracket the answer, they do not confirm it." });
    const ROUTE = {
      market_implied_equity_v3: "Market-implied equity value (total effect)",
      market_implied_annual_earnings: "Market-implied annual earnings (total effect)",
      direct_profit_margin: "Direct profit-margin link (total effect)",
      announcement_event_study: "Announcement event study",
    };
    table(pD, [{ t: "Route" }, { t: "Value", num: true }, { t: "Link identified" }],
      M.routes.filter((x) => ROUTE[x.route]).map((x) => [ROUTE[x.route], x.value == null ? "—" : F.usd(x.value * 1e6), `<span class="tag tag--no">${x.identified ? "yes" : "no"}</span>`]));
    note(pD, `Royalty relief: covering a US$100M programme would need the brand's royalty rate to rise by about ${M.royaltyBreakeven.find((b) => b.costUsdM === 100).bp} basis points. Market-implied earnings: ${F.usd(M.earningsPerPoint.central)} a year per Brand Index point (planning range ${F.usd(M.earningsPerPoint.planning[0])}–${F.usd(M.earningsPerPoint.planning[1])}). Media value is never used as money.`);
    src(pD, "Elaboration: OpenEconomics · valuation_routes_v1, market_implied_earnings_bridge_v1");

    pager(root, "evaluation", "method");
  }

  /* ============================================================ METHOD === */
  function viewMethod(root) {
    head(root, {
      kicker: "Method & evidence",
      title: "How the study is built",
      lead: "Three steps, each producing one number the next consumes. Nothing downstream is stronger than the measurement upstream, so the chain and its weak points are shown rather than summarised.",
    });
    flow(root, [
      { k: "Step 01 · Exposure", v: F.pts(FS.primary_index_points) + " FIFA-specific", d: `Brand Index (share of attention against rivals, with the GWI survey) against a synthetic no-sponsorship Lenovo from ${X.design.donors.length} rival brands; the gap split between FIFA exposure, other sponsorships, events and a residual.` },
      { k: "Step 02 · Evaluation", v: F.usd(B.brandValue) + " brand value", cls: "flow-cell--mid", d: "The brand's share of what Lenovo's own drivers move in its share price (dominance analysis) × market capitalisation; corroborated by Brand Finance and Interbrand." },
      { k: "Step 03 · Monetization", v: F.usd(M.scenarios.base.value) + " added by FIFA", cls: "flow-cell--out", d: "FIFA-specific uplift × brand value, with the 95% band and the whole-gap ceiling as scenarios." },
    ], { tall: true });

    const g = grid(root);
    const p1 = panel(col(g, 6), { label: "Data sources", title: "What the study is built on" });
    table(p1, [{ t: "Source" }, { t: "Contribution" }], [
      ["<b>Google Trends</b>", "Weekly search interest for Lenovo and rival brands in jointly scaled panels; Lenovo product searches as a demand indicator"],
      ["<b>GWI Core</b>", "Quarterly engagement and consideration of Lenovo (2022–2026Q1) in the Brand Index"],
      ["<b>Blinkfire Analytics</b>", "Weekly digital and social impressions by sponsored property"],
      ["<b>Market data</b>", "0992.HK, Hang Seng, Nasdaq-100, USD/HKD daily closes"],
      ["<b>Lenovo</b>", "Results, events, financials"],
      ["<b>FIFA</b>", "Official 2026 match calendar; partnership announcements"],
    ]);
    const p2 = panel(col(g, 6), { label: "Status of the figures", title: "Observed, constructed, estimated, assumed" });
    table(p2, [{ t: "Status" }, { t: "Applies to" }], [
      ["<b>Observed</b>", "Search volumes, survey waves, digital impressions, share prices"],
      ["<b>Constructed</b>", "Brand Index, rival share-of-search series, motorsport exposure before September 2024 (back-cast)"],
      ["<b>Estimated</b>", "Synthetic control, FIFA-specific decomposition, dominance shares, brand value"],
      ["<b>Assumed</b>", "Brand value moves one-for-one with brand share; the uplift persists; exposure carries over at 80% a week"],
    ]);

    const g2 = grid(root);
    const p3 = panel(col(g2, 7), { label: "Limits", title: "What the figures do not establish" });
    const ul = el("ul", "caveats");
    [
      `Significance is borderline: the total effect passes the placebo test (p = ${X.design.placeboP.toFixed(3)}) but not on every check (share of search alone without the spring 2026 surge: p = ${X.crossChecks[1].exSurgeP.toFixed(3)}).`,
      "The FIFA-specific split is a regression decomposition, not an experiment; its specification was fixed after it was seen, so the alternatives are shown in step 01.",
      "Exposure is digital and social only; broadcast audiences are not measured.",
      "The Brand Index is redesigned brand share of attention (October 2026); earlier figures on the former search-salience scale are not comparable.",
      "Brand value rests on share-price relative importance, a proxy for the behavioural evidence ISO 10668 expects. The market data alone cannot pin the brand's share (an unrelated series obtains a similar share); the level is corroborated by Brand Finance and Interbrand, not proven.",
      "The rights fee and activation spend are not in the data, so no return on investment is claimed.",
      "The World Cup evaluation window closes on 18 October 2026; tournament figures are interim.",
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
    { id: "evaluation", n: "02", name: "Evaluation", q: "What is the Lenovo brand worth, read from what moves its share price?",
      chev: "Brand share of Lenovo's own price drivers", metric: () => F.usd(B.brandValue) + " brand value", out: () => F.usd(B.brandValue),
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
