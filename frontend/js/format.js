/* Number & date formatting (VISUALIZATION.md §4.3): compact notation, one
   decimal max on Index points, zero decimals on percentages. Sponsor-facing
   demo → en-US compact. */
window.FMT = (function () {
  function big(v) {
    const a = Math.abs(v);
    if (a >= 1e9) return trim(v / 1e9) + "B";
    if (a >= 1e6) return trim(v / 1e6) + "M";
    if (a >= 1e3) return trim(v / 1e3) + "K";
    return String(Math.round(v));
  }
  function trim(x) {
    const s = x >= 100 ? Math.round(x).toString() : x.toFixed(1);
    return s.endsWith(".0") ? s.slice(0, -2) : s;
  }
  const usd = (v) => (v < 0 ? "−US$" + big(-v) : "US$" + big(v));
  const pts = (v, signed = true) => (signed && v > 0 ? "+" : "") + v.toFixed(1) + " pts";
  const mult = (v) => v.toFixed(1) + "×";
  const pct = (v) => Math.round(v * 100) + "%";
  const pp = (v, signed = true) => (signed && v > 0 ? "+" : "") + Math.round(v * 100) + " pp";
  function monthYear(w) {
    const d = new Date(w + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  }
  const year = (w) => w.slice(0, 4);

  /* animated count-up (respects prefers-reduced-motion) */
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function countUp(el, target, fmt, ms = 1100) {
    if (reduced) { el.textContent = fmt(target); return; }
    const t0 = performance.now();
    function tick(t) {
      const p = Math.min(1, (t - t0) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(target * eased);
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
  return { big, usd, pts, mult, pct, pp, monthYear, year, countUp, reduced };
})();
