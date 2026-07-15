/* Semantic chart slots (VISUALIZATION.md §5.1) mapped to OE brand tokens.
   Only this file and ds-kit/tokens.js may hold brand color values in JS.
   Series colors validated (dataviz six checks) against the light surface:
   #5902EE / #C300C3 / #0000FF pass; grays carry benchmarks. */
window.THEME = (function () {
  const B = window.OE;
  return {
    surface: "#FFFFFF",
    surfaceMuted: B.gray[100],
    textPrimary: B.gray[900],
    textSecondary: B.gray[600],
    seriesHeadline: B.bluette[600], // #5902EE — the Brand Index / Lenovo line
    seriesHeadlineDeep: B.bluette[700], // fills, bars, brand anchor
    seriesSecondary: "#C300C3", // magenta-700 — second categorical series
    seriesTertiary: "#0000FF", // blu-600 — third categorical series
    seriesCounterfactual: B.gray[500], // dashed "without sponsorship" line
    seriesBenchmark: B.gray[400], // donor market band / non-FIFA bars
    ribbonConfidence: "rgba(89,2,238,.10)", // bluette-600 @ 10%
    gapFill: "rgba(185,255,105,.45)", // lime-400 — created-value shading
    deltaPositive: B.lime[400], // chips (black text on lime)
    deltaPositiveInk: "#458300", // lime-800 — positive text on white
    markerMilestone: B.bluette[300], // event verticals
    heroAccent: B.lime[400],
    stackDigital: B.bluette[700], // stacked exposure: same-hue sequential
    stackBroadcast: B.bluette[200],
    seqRamp: [B.bluette[50], B.bluette[100], B.bluette[200], B.bluette[300], B.bluette[400], B.bluette[500], B.bluette[600]],
    toneNegative: "#C300C3",
    tonePositive: B.bluette[600],
    grid: B.gray[200],
    font: B.font,
  };
})();
