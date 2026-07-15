/* Token DS — mirror standalone di src/tokens.ts (no ESM). Tenere allineato al CSS. */
window.OE = (function () {
  const bluette = {50:'#EFE5FF',100:'#D9C1FF',200:'#B991FF',300:'#A16AFF',400:'#8742FF',500:'#6E1AFF',600:'#5902EE',700:'#4400B3',800:'#340088',900:'#270065'};
  const lime = {50:'#EFFFDC',100:'#DFFFBB',200:'#D5FFA4',300:'#C9FF8C',400:'#B9FF69',500:'#91FF15',600:'#7FF100',700:'#67C300',800:'#458300',900:'#315C01'};
  const gray = {0:'#FFFFFF',100:'#F1F1F1',200:'#E7E7E7',300:'#D2D2D2',400:'#AFAFAF',500:'#999999',600:'#6E6E6E',700:'#545454',800:'#2C2C2C',900:'#000000'};
  const dataviz = {
    magenta:{600:'#FF00FF'}, blu:{600:'#0000FF'}, yellow:{600:'#F4E900'}, green:{600:'#00E279'}, cyan:{600:'#00FFFF'}
  };
  const chartSeries = [bluette[700], lime[500], dataviz.magenta[600], dataviz.cyan[600], dataviz.yellow[600], dataviz.green[600], dataviz.blu[600]];
  const font = {
    serif:'"Hedvig Letters Serif", Georgia, serif',
    sans:'"Atkinson Hyperlegible Next", -apple-system, "Helvetica Neue", Arial, sans-serif',
    mono:'"Atkinson Hyperlegible Mono", ui-monospace, Menlo, monospace'
  };
  function formatNumber(value, locale, decimals){
    locale = locale || 'it-IT'; decimals = decimals || 0;
    return new Intl.NumberFormat(locale,{minimumFractionDigits:decimals,maximumFractionDigits:decimals,useGrouping:'always'}).format(value);
  }
  return { bluette, lime, gray, dataviz, chartSeries, font, formatNumber, radius:0 };
})();
