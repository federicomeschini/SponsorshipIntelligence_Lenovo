/* Chart builders on Chart.js 4 + the OE chart preset. One library app-wide
   (frontend/DECISIONS.md FE-002). All builders return the Chart instance.
   Shared rules: category week axis with sparse year ticks, recessive grid,
   crosshair tooltip, no dual axes, thin marks. */
window.CH = (function () {
  const T = window.THEME;
  const charts = [];

  Chart.defaults.locale = "en-US";
  Chart.defaults.font.family = T.font.mono;
  Chart.defaults.font.size = 12;
  Chart.defaults.color = T.textSecondary;
  Chart.defaults.borderColor = T.grid;
  Chart.defaults.animation.duration = FMT.reduced ? 0 : 700;
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.boxHeight = 12;
  Chart.defaults.plugins.tooltip.backgroundColor = "#270065";
  Chart.defaults.plugins.tooltip.titleFont = { family: T.font.mono, size: 12 };
  Chart.defaults.plugins.tooltip.bodyFont = { family: T.font.mono, size: 12 };
  Chart.defaults.plugins.tooltip.cornerRadius = 0;
  Chart.defaults.plugins.tooltip.displayColors = false;

  /* --- milestone verticals (events on the shared timeline) --- */
  const milestonePlugin = {
    id: "milestones",
    afterDatasetsDraw(chart, _a, opts) {
      if (!opts || !opts.items || !opts.items.length) return;
      const { ctx, chartArea, scales } = chart;
      const x = scales.x;
      ctx.save();
      ctx.font = "600 10px " + T.font.mono;
      let lastEnd = -Infinity, lane = 0; // stagger labels that would collide
      opts.items.forEach((m) => {
        const px = x.getPixelForValue(m.i);
        if (px < chartArea.left - 2 || px > chartArea.right + 2) return;
        ctx.strokeStyle = T.markerMilestone;
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(px, chartArea.top + 26);
        ctx.lineTo(px, chartArea.bottom);
        ctx.stroke();
        ctx.setLineDash([]);
        const label = m.label.toUpperCase();
        const wpx = ctx.measureText(label).width;
        const right = px > chartArea.right - wpx - 8;
        let x0 = right ? px - wpx - 4 : px + 4;
        lane = x0 <= lastEnd + 6 ? (lane + 1) % 2 : 0;
        lastEnd = x0 + wpx;
        ctx.fillStyle = T.seriesHeadlineDeep;
        ctx.fillText(label, x0, chartArea.top + 9 + lane * 12);
      });
      ctx.restore();
    },
  };
  Chart.register(milestonePlugin);

  function yearTicks(weeks) {
    return {
      autoSkip: false,
      maxRotation: 0,
      callback(v) {
        const w = weeks[v];
        if (!w) return "";
        const d = new Date(w + "T00:00:00");
        // first week of each year (or of each quarter on short spans)
        if (weeks.length > 120) return d.getMonth() === 0 && d.getDate() <= 7 ? d.getFullYear() : "";
        return d.getDate() <= 7 && d.getMonth() % 3 === 0
          ? d.toLocaleDateString("en-US", { month: "short", year: "2-digit" })
          : "";
      },
    };
  }

  function make(canvas, cfg) {
    const c = new Chart(canvas.getContext("2d"), cfg);
    charts.push(c);
    return c;
  }

  /* line with optional confidence ribbon, counterfactual pair, milestones */
  function line(canvas, { weeks, series, ribbon, milestones, yTitle, fill, min, max, dashSim }) {
    const datasets = [];
    if (ribbon) {
      datasets.push(
        { data: ribbon.upper, borderWidth: 0, pointRadius: 0, fill: false, label: "_up", parsing: false },
        { data: ribbon.lower, borderWidth: 0, pointRadius: 0, fill: "-1", backgroundColor: T.ribbonConfidence, label: "_lo", parsing: false }
      );
    }
    series.forEach((s) =>
      datasets.push({
        label: s.label,
        data: s.data,
        borderColor: s.color,
        backgroundColor: s.fillColor || "transparent",
        fill: s.fill || false,
        borderDash: s.dash || [],
        borderWidth: s.width || 2,
        pointRadius: s.points || 0,
        pointBackgroundColor: s.pointColor || s.color,
        pointBorderColor: "#fff",
        pointBorderWidth: s.points ? 1.5 : 0,
        tension: 0.25,
        spanGaps: true,
        showLine: s.showLine !== false,
        segment: s.simFrom != null ? { borderDash: (ctx) => (ctx.p0DataIndex >= s.simFrom ? [5, 4] : undefined) } : undefined,
      })
    );
    return make(canvas, {
      type: "line",
      data: { labels: weeks, datasets },
      options: {
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: yearTicks(weeks) },
          y: { min, max, title: yTitle ? { display: true, text: yTitle } : undefined, grid: { color: T.grid }, border: { display: false } },
        },
        plugins: {
          legend: { display: series.filter((s) => !s.hideLegend).length > 1, labels: { filter: (i) => !i.text.startsWith("_") } },
          tooltip: { filter: (i) => !i.dataset.label.startsWith("_") },
          milestones: { items: milestones || [] },
        },
      },
    });
  }

  /* stacked area (cumulative exposure) */
  function stackedArea(canvas, { weeks, layers, milestones, yFmt }) {
    return make(canvas, {
      type: "line",
      data: {
        labels: weeks,
        datasets: layers.map((l) => ({
          label: l.label, data: l.data, borderColor: l.color, backgroundColor: l.color,
          fill: true, pointRadius: 0, borderWidth: 1, tension: 0.2,
        })),
      },
      options: {
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { stacked: true, grid: { display: false }, ticks: yearTicks(weeks) },
          y: { stacked: true, grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => FMT.big(v) } },
        },
        plugins: {
          legend: { display: true },
          milestones: { items: milestones || [] },
          tooltip: { callbacks: { label: (i) => ` ${i.dataset.label}: ${FMT.big(i.parsed.y)}` } },
        },
      },
    });
  }

  function donut(canvas, { labels, values, colors, centerText }) {
    const centerPlugin = {
      id: "donutCenter",
      afterDraw(chart) {
        if (!centerText) return;
        const { ctx } = chart;
        const meta = chart.getDatasetMeta(0).data[0];
        if (!meta) return;
        ctx.save();
        ctx.textAlign = "center";
        ctx.font = "600 26px " + T.font.sans;
        ctx.fillStyle = T.textPrimary;
        ctx.fillText(centerText[0], meta.x, meta.y - 2);
        ctx.font = "400 11px " + T.font.mono;
        ctx.fillStyle = T.textSecondary;
        ctx.fillText(centerText[1].toUpperCase(), meta.x, meta.y + 18);
        ctx.restore();
      },
    };
    return make(canvas, {
      type: "doughnut",
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderColor: "#fff", borderWidth: 2 }] },
      options: {
        maintainAspectRatio: false, cutout: "68%",
        plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: (i) => ` ${i.label}: ${FMT.big(i.parsed)}` } } },
      },
      plugins: [centerPlugin],
    });
  }

  /* horizontal bars (portfolio return, funnel) */
  function barsH(canvas, { labels, datasets, xFmt, stacked = false, xTitle, annotate }) {
    return make(canvas, {
      type: "bar",
      data: { labels, datasets },
      options: {
        indexAxis: "y",
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: T.grid }, border: { display: false }, stacked, title: xTitle ? { display: true, text: xTitle } : undefined, ticks: { callback: (v) => (xFmt ? xFmt(v) : v) } },
          y: { grid: { display: false }, stacked, ticks: { font: { family: T.font.sans, size: 13 } } },
        },
        plugins: {
          legend: { display: datasets.length > 1 },
          tooltip: { callbacks: { label: (i) => ` ${i.dataset.label || ""} ${xFmt ? xFmt(i.parsed.x) : i.parsed.x}`.trim() } },
        },
      },
      plugins: annotate ? [annotate] : [],
    });
  }

  /* vertical waterfall with floating bars + connectors */
  function waterfall(canvas, { steps, yFmt }) {
    const connector = {
      id: "wfConnect",
      afterDatasetsDraw(chart) {
        const { ctx } = chart;
        const meta = chart.getDatasetMeta(0);
        ctx.save();
        ctx.strokeStyle = T.textSecondary;
        ctx.setLineDash([2, 3]);
        for (let i = 0; i < meta.data.length - 1; i++) {
          const cur = meta.data[i], next = meta.data[i + 1];
          const yEnd = chart.scales.y.getPixelForValue(steps[i].range[1]);
          ctx.beginPath();
          ctx.moveTo(cur.x + cur.width / 2, yEnd);
          ctx.lineTo(next.x - next.width / 2, yEnd);
          ctx.stroke();
        }
        ctx.restore();
        // value labels above bars
        ctx.save();
        ctx.font = "600 12px " + T.font.mono;
        ctx.textAlign = "center";
        meta.data.forEach((bar, i) => {
          const s = steps[i];
          const top = chart.scales.y.getPixelForValue(Math.max(...s.range));
          ctx.fillStyle = T.textPrimary;
          ctx.fillText(s.printed, bar.x, top - 6);
        });
        ctx.restore();
      },
    };
    return make(canvas, {
      type: "bar",
      data: {
        labels: steps.map((s) => s.label),
        datasets: [{
          data: steps.map((s) => s.range),
          backgroundColor: steps.map((s) => s.color),
          borderWidth: 0,
          barPercentage: 0.72,
        }],
      },
      options: {
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: T.font.sans, size: 12 }, maxRotation: 0, autoSkip: false } },
          y: { grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => yFmt(v) } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (i) => " " + steps[i.dataIndex].printed } },
        },
      },
      plugins: [connector],
    });
  }

  function scatter(canvas, { points, xTitle, yTitle, xFmt, yFmt }) {
    return make(canvas, {
      type: "bubble",
      data: {
        datasets: points.map((p) => ({
          label: p.label,
          data: [{ x: p.x, y: p.y, r: p.r }],
          backgroundColor: p.color + "CC",
          borderColor: p.color,
          borderWidth: 1.5,
        })),
      },
      options: {
        maintainAspectRatio: false,
        scales: {
          x: { type: "logarithmic", title: { display: true, text: xTitle }, grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => ([1e7,1e8,1e9,1e10].includes(v) ? FMT.big(v) : "") } },
          y: { title: { display: true, text: yTitle }, grid: { color: T.grid }, border: { display: false }, ticks: { callback: (v) => (yFmt ? yFmt(v) : v) } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (i) => ` ${i.dataset.label}: ${xFmt(i.parsed.x)} · ${yFmt(i.parsed.y)}` } },
        },
      },
    });
  }

  function sparkline(canvas, { data, color, fill }) {
    return make(canvas, {
      type: "line",
      data: { labels: data.map((_, i) => i), datasets: [{ data, borderColor: color, borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: !!fill, backgroundColor: fill || "transparent" }] },
      options: {
        maintainAspectRatio: false, events: [],
        scales: { x: { display: false }, y: { display: false } },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
      },
    });
  }

  /* export-to-image (every chart panel, §3 general rules) */
  function exportPng(chart, name) {
    const src = chart.canvas;
    const out = document.createElement("canvas");
    const pad = 24, foot = 30;
    out.width = src.width + pad * 2;
    out.height = src.height + pad * 2 + foot;
    const ctx = out.getContext("2d");
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.drawImage(src, pad, pad);
    ctx.font = "400 11px " + T.font.mono;
    ctx.fillStyle = T.textSecondary;
    ctx.fillText("Demonstration environment · illustrative data — OpenEconomics", pad, out.height - 12);
    const a = document.createElement("a");
    a.download = name + ".png";
    a.href = out.toDataURL("image/png");
    a.click();
  }

  function destroyAll() {
    charts.splice(0).forEach((c) => c.destroy());
  }

  return { line, stackedArea, donut, barsH, waterfall, scatter, sparkline, exportPng, destroyAll };
})();
