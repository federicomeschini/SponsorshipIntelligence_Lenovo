/* Preset Chart.js on-brand: font Atkinson Mono sugli assi, niente gridline pesanti,
   niente ombre, colori da OE.chartSeries. Chiamare applyOEChartDefaults() dopo aver caricato Chart.js. */
function applyOEChartDefaults(){
  if (typeof Chart === 'undefined' || !window.OE) return;
  Chart.defaults.font.family = OE.font.mono;
  Chart.defaults.font.size = 13;
  Chart.defaults.color = OE.gray[700];
  Chart.defaults.borderColor = OE.gray[200];
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.elements.bar.borderRadius = 0;
  Chart.defaults.elements.point.radius = 3;
}
/* Helper: assegna i colori serie nell'ordine OE. */
function oeSeriesColor(i){ return OE.chartSeries[i % OE.chartSeries.length]; }
