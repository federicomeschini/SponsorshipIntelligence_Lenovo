/* Shared UI builders: panels, KPI cards, insight lines, milestone ribbon.
   All strings routed through COPY (js/copy.js). */
window.UI = (function () {
  const T = window.THEME;
  const D = window.SRMP_DEMO;

  const PROP_NAMES = {
    fifa: "FIFA", fwc: "FIFA World Cup 26", fwwc: "FIFA Women's World Cup",
    fcwc: "FIFA Club World Cup", fifae: "FIFAe", fifaewc: "FIFAe World Cup",
    infantino: "FIFA President", f1: "Formula 1", motogp: "MotoGP", ducati: "Ducati",
    carolina_hurricanes: "Carolina Hurricanes", montreal_canadiens: "Montreal Canadiens",
    ny_yankees: "New York Yankees",
  };
  const STAGE_NAMES = {
    awareness: "Awareness", engagement: "Engagement", appeal: "Appeal",
    consideration: "Consideration", purchase_intent: "Purchase intent",
  };

  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };

  /* screen scaffold: eyebrow chip + title + stated insight (§3 general rules) */
  function screenHead(root, { kicker, title, insight }) {
    const head = el("section", "screen-head reveal");
    head.append(el("span", "oe-tag-chip oe-tag-chip--lime", kicker));
    head.append(el("h1", "screen-title", title));
    if (insight) head.append(el("p", "insight-line", insight));
    root.append(head);
    return head;
  }

  /* chart panel with figure label + PNG export */
  let figN = 0;
  function panel(root, { label, title, height = 300, cls = "" }) {
    figN += 1;
    const p = el("div", "oe-panel reveal " + cls);
    const head = el("div", "oe-panel__head");
    const left = el("div", "", `<div class="oe-panel__label">${label || "Chart " + figN}</div><p class="oe-panel__title">${title}</p>`);
    const exp = el("button", "panel-export", "PNG");
    exp.type = "button";
    exp.title = "Export chart as image";
    head.append(left, exp);
    const box = el("div", "chart-box");
    box.style.height = height + "px";
    const canvas = document.createElement("canvas");
    box.append(canvas);
    p.append(head, box);
    root.append(p);
    return {
      canvas, panel: p,
      bindExport(chart, name) {
        exp.addEventListener("click", () => CH.exportPng(chart, name));
      },
      hideExport() { exp.remove(); },
    };
  }

  /* KPI card — dashboard rule: numbers black on light, .oe-kpi--dark on hero */
  function kpi({ value, fmt, label, note, dark = false, countUp = true }) {
    const card = el("div", "oe-kpi" + (dark ? " oe-kpi--dark" : "") + " reveal");
    const v = el("div", "oe-kpi__value oe-num");
    const l = el("div", "oe-kpi__label", label);
    card.append(v, l);
    if (note) card.append(el("div", "oe-kpi__note", note));
    if (countUp) {
      card.dataset.countup = "1";
      card._start = () => FMT.countUp(v, value, fmt);
      v.textContent = fmt(0);
    } else v.textContent = fmt(value);
    return card;
  }

  /* partnership timeline ribbon: zoomed to the partnership window itself
     (announcement → shortly after the 2026 final), so the milestones that
     matter are spread out instead of lost in a 5-year axis. */
  function milestoneRibbon(root) {
    const wrap = el("div", "ribbon reveal");
    const ev = (id) => D.events.find((e) => e.id === id);
    const DAY = 864e5;

    const ann = ev("fifa_partner_announcement_2024");
    const fcwcDeal = ev("fcwc_partner_announcement_2025");
    const wcFinal = ev("wc_final_2026");

    const t0 = new Date(ann.date).getTime() - 30 * DAY;
    const t1 = new Date(wcFinal.date).getTime() + 45 * DAY;
    const pct = (d) => ((new Date(d).getTime() - t0) / (t1 - t0)) * 100;
    const track = el("div", "ribbon__track");
    const now = Date.now();
    const todayPct = Math.min(100, Math.max(0, pct(now)));

    const elapsed = el("div", "ribbon__elapsed");
    elapsed.style.width = todayPct + "%";
    track.append(elapsed);

    const dot = el("div", "ribbon__dot ribbon__dot--glow");
    dot.style.left = pct(ann.date) + "%";
    dot.append(el("span", "ribbon__label ribbon__label--above ribbon__label--start", `Partnership announced<em>${FMT.monthYear(ann.date)}</em>`));
    track.append(dot);

    const deal = el("div", "ribbon__dot");
    deal.style.left = pct(fcwcDeal.date) + "%";
    deal.append(el("span", "ribbon__label ribbon__label--below", `FCWC partnership deal<em>${FMT.monthYear(fcwcDeal.date)}</em>`));
    track.append(deal);

    [
      { from: ev("fcwc_opening_2025").date, to: ev("fcwc_final_2025").date, label: "Club World Cup 2025", pos: "above" },
      { from: ev("wc_opening_2026").date, to: ev("wc_final_2026").date, label: "World Cup 2026", pos: "above" },
    ].forEach((w) => {
      const span = el("div", "ribbon__win");
      span.style.left = pct(w.from) + "%";
      span.style.width = Math.max(1.2, pct(w.to) - pct(w.from)) + "%";
      span.append(el("span", "ribbon__label ribbon__label--" + w.pos, `${w.label}<em>${FMT.monthYear(w.from)}</em>`));
      track.append(span);
    });

    if (now >= t0 && now <= t1) {
      const today = el("div", "ribbon__today");
      today.style.left = todayPct + "%";
      today.append(el("span", "ribbon__today__label", "Today"));
      track.append(today);
    }

    /* semester ticks (Jan/Jul) instead of year ticks — a 2-year window
       reads better at 6-month resolution than at yearly resolution. */
    const tickDate = new Date(t0);
    tickDate.setDate(1);
    tickDate.setMonth(tickDate.getMonth() < 6 ? 6 : 12);
    if (tickDate.getTime() < t0) tickDate.setMonth(tickDate.getMonth() + 6);
    for (; tickDate.getTime() <= t1; tickDate.setMonth(tickDate.getMonth() + 6)) {
      const tickPct = pct(tickDate);
      if (now >= t0 && now <= t1 && Math.abs(tickPct - todayPct) < 4) continue;
      const tick = el("div", "ribbon__tick");
      tick.style.left = tickPct + "%";
      tick.textContent = tickDate.toLocaleDateString("en-US", { month: "short", year: "numeric" });
      track.append(tick);
    }
    wrap.append(track);
    root.append(wrap);
  }

  /* milestones mapped onto a chart's week labels */
  function milestonesFor(weeks, ids) {
    const SHORT = {
      fifa_partner_announcement_2024: "Announcement",
      fcwc_partner_announcement_2025: "FCWC deal",
      fcwc_opening_2025: "Club WC",
      fcwc_final_2025: "Club WC final",
      wc_opening_2026: "World Cup",
      wc_final_2026: "Final",
    };
    return D.events
      .filter((e) => !ids || ids.includes(e.id))
      .map((e) => {
        const wk = weeks.find((w) => w <= e.date && new Date(e.date) - new Date(w) < 7 * 864e5);
        return wk ? { i: weeks.indexOf(wk), label: SHORT[e.id] || e.name } : null;
      })
      .filter(Boolean);
  }

  /* lime delta chip */
  const deltaChip = (text) => `<span class="delta-chip oe-num">${text}</span>`;

  /* per-chart data attribution (strings centralized in COPY.src) */
  function source(target, text) {
    target.append(el("p", "panel-source", text));
  }

  /* staggered entrance (<900ms, prefers-reduced-motion respected) */
  function animateIn(root) {
    const nodes = root.querySelectorAll(".reveal");
    nodes.forEach((n, i) => {
      if (FMT.reduced) { n.classList.add("is-in"); return; }
      setTimeout(() => n.classList.add("is-in"), Math.min(i * 70, 560));
    });
    root.querySelectorAll("[data-countup]").forEach((c, i) =>
      setTimeout(() => c._start && c._start(), FMT.reduced ? 0 : Math.min(i * 90, 500) + 150)
    );
    /* below-the-fold reveals on scroll */
    if (!FMT.reduced && "IntersectionObserver" in window) {
      const io = new IntersectionObserver((es) =>
        es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } }),
        { threshold: 0.08 });
      nodes.forEach((n) => { if (!n.classList.contains("is-in")) io.observe(n); });
    }
  }

  return { el, screenHead, panel, kpi, milestoneRibbon, milestonesFor, deltaChip, source, animateIn, PROP_NAMES, STAGE_NAMES };
})();
