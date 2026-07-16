/* Demo-data consistency checks (VISUALIZATION.md §7.3).
 * Run: node frontend/tests/check-consistency.mjs
 * Fails (exit 1) if any invariant breaks.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DATA = join(dirname(fileURLToPath(import.meta.url)), "..", "data");
function load(name, key) {
  const w = {};
  new Function("window", readFileSync(join(DATA, name), "utf8"))(w);
  return w[key];
}
const REAL = load("real-data.js", "SRMP_REAL");
const D = load("demo-data.js", "SRMP_DEMO");

let failures = 0;
function check(name, ok, detail = "") {
  if (ok) console.log("  ok  " + name);
  else { failures++; console.error("FAIL  " + name + (detail ? " — " + detail : "")); }
}

// --- shared timeline alignment ------------------------------------------------
check("timeline is weekly W-MON with no gaps",
  D.timeline.every((w, i) => i === 0 || (new Date(w) - new Date(D.timeline[i - 1])) === 7 * 864e5));
check("index aligned to timeline", D.index.week.length === D.timeline.length && D.index.level.length === D.timeline.length);
check("counterfactual aligned to timeline", D.counterfactual.week.length === D.timeline.length);
check("exposure weeks are a suffix of the timeline",
  JSON.stringify(D.exposure.week) === JSON.stringify(D.timeline.filter((w) => w >= D.exposure.week[0])));

// --- simulated series continuous with the real series they extend --------------
const nReal = REAL.brandIndexWeekly.week.length;
check("real index embedded unchanged",
  D.index.level.slice(0, nReal).every((v, i) => v === REAL.brandIndexWeekly.level[i]));
const jump = Math.abs(D.index.level[nReal] - D.index.level[nReal - 1]);
check("simulated index extension is continuous (first step < 3 pts)", jump < 3, "jump=" + jump.toFixed(2));
const synJump = Math.abs(D.counterfactual.synthetic[nReal] - REAL.counterfactualWeekly.synthetic[nReal - 1]);
check("simulated synthetic extension is continuous", synJump < 2, "jump=" + synJump.toFixed(2));
check("actual = synthetic + gap on extension",
  D.counterfactual.week.slice(nReal).every((_, k) => {
    const i = nReal + k;
    return Math.abs(D.counterfactual.actual[i] - (D.counterfactual.synthetic[i] + D.counterfactual.gap[i])) < 1e-6;
  }));
const finalIdx = D.counterfactual.week.indexOf("2026-07-13");
check("tournament arc peaks at +2.5 on the finals week", Math.abs(D.counterfactual.gap[finalIdx] - 2.5) < 1e-9);
const tailGap = D.counterfactual.gap.slice(-8);
check("gap decays to ≈ +0.8 persistent plateau",
  tailGap.every((g) => g > 0.45 && g < 1.15), "tail=" + tailGap.map((g) => g.toFixed(2)).join(","));

// --- V6 waterfall arithmetic closes --------------------------------------------
for (const [k, s] of Object.entries(D.roi.scenarios)) {
  check(`waterfall closes (${k}): gross = annual × persistence`,
    Math.abs(s.grossUsd - s.annualUsd * s.persistenceYears) < 1);
  check(`waterfall closes (${k}): net = gross − investment`,
    Math.abs(s.netUsd - (s.grossUsd - s.investmentUsd)) < 1);
  check(`waterfall closes (${k}): roi = gross / investment`,
    Math.abs(s.roiMultiple - s.grossUsd / s.investmentUsd) < 1e-9);
  check(`annual value (${k}) = delta × usd-per-point calibration`,
    Math.abs(s.annualUsd - s.deltaIndex * D.roi.inputs.usdPerPointYear) < 1);
}
check("usd-per-point = real calibration × demo value scale (FE-008, ×15)",
  Math.abs(D.roi.inputs.usdPerPointYear - REAL.earningsCalibration.usdPerIndexPointPerYear * 15) < 1);
check("base delta equals the real exposure-weighted candidate (+1.033)",
  D.roi.scenarios.base.deltaIndex === REAL.counterfactualMeta.exposureWeightedGap);

// --- the three memorable numbers, consistent everywhere -------------------------
check("kpi.indexLift = base scenario delta", D.kpi.indexLift === D.roi.scenarios.base.deltaIndex);
check("kpi.roiMultiple = base scenario roi", D.kpi.roiMultiple === D.roi.scenarios.base.roiMultiple);
check("kpi.annualValueUsd = base annual", D.kpi.annualValueUsd === D.roi.scenarios.base.annualUsd);
check("kpi.totalExposure = digital + broadcast",
  D.kpi.totalExposure === D.kpi.digitalImpressions + D.kpi.broadcastAudience);
const cumDigital = D.exposure.fifaDigital.reduce((a, v) => a + v, 0);
check("kpi.digitalImpressions = Σ weekly FIFA digital", Math.abs(D.kpi.digitalImpressions - cumDigital) <= 1);
const cumBroadcast = D.exposure.broadcast.reduce((a, v) => a + v, 0);
check("kpi.broadcastAudience = Σ weekly broadcast", D.kpi.broadcastAudience === cumBroadcast);

// --- perception waves (FE-008: illustrative, regular programme) ------------------
const props = ["fwc", "fwwc", "fcwc"], stages = ["awareness", "appeal", "purchase_intent"];
check("wave matrix is complete (every wave × property × stage)",
  D.funnelWaves.every((w) => props.every((p) => stages.every((s) =>
    D.funnel.some((r) => r.wave === w && r.property === p && r.stage === s)))));
check("all waves fall inside the partnership window",
  D.funnelWaves.every((w) => w >= "2024-10" && w <= "2026-07"));
check("funnel lift = aware − unaware on every row",
  D.funnel.every((r) => Math.abs(r.lift - (r.aware - r.unaware)) < 0.005));
const fwcAppeal = D.funnelWaves.map((w) => D.funnel.find((r) => r.wave === w && r.property === "fwc" && r.stage === "appeal").lift);
check("FWC appeal lift increases wave over wave",
  fwcAppeal.every((v, i) => !i || v > fwcAppeal[i - 1]));
for (const s of ["awareness", "appeal", "purchase_intent"]) {
  const r = D.funnel.find((x) => x.wave === D.funnelHeroWave && x.property === "fwc" && x.stage === s);
  const h = D.funnelHero.find((x) => x.stage === s);
  check(`funnel hero ${s} matches the latest FWC wave`, r && h && r.lift === h.lift && r.aware === h.aware);
}
check("funnel hero is monotonic (aware)", D.funnelHero.every((s, i, a) => !i || s.aware <= a[i - 1].aware));
check("funnel hero is monotonic (unaware)", D.funnelHero.every((s, i, a) => !i || s.unaware <= a[i - 1].unaware));
check("funnel hero lift = aware − unaware", D.funnelHero.every((s) => Math.abs(s.lift - (s.aware - s.unaware)) < 0.005));
check("kpi lift ranges match the FWC wave series",
  D.kpi.appealLiftRange[1] === Math.round(fwcAppeal[fwcAppeal.length - 1] * 100));

// --- portfolio -------------------------------------------------------------------
const fifa = D.portfolio.find((p) => p.fifa);
check("FIFA portfolio value = base gross value", fifa.valueUsd === D.roi.scenarios.base.grossUsd);
check("FIFA portfolio impressions = kpi digital impressions",
  Math.abs(fifa.impressions - D.kpi.digitalImpressions) <= 1);
const others = D.portfolio.filter((p) => !p.fifa).map((p) => p.valuePerM).sort((a, b) => a - b);
const med = (others[2] + others[3]) / 2;
check("FIFA ≈ 1.6× portfolio median value/impression",
  fifa.valuePerM / med > 1.4 && fifa.valuePerM / med < 1.8, (fifa.valuePerM / med).toFixed(2));
check("portfolio value/M all positive & FIFA highest",
  D.portfolio.every((p) => p.valuePerM > 0) && D.portfolio.every((p) => p.fifa || p.valuePerM < fifa.valuePerM));

// --- royalty cross-check monotonic ------------------------------------------------
check("royalty schedule monotonic",
  D.roi.royaltyView.schedule.every((p, i, a) => !i || (p.indexPoints > a[i - 1].indexPoints && p.usdPerYear > a[i - 1].usdPerYear)));

console.log(failures ? `\n${failures} check(s) FAILED` : "\nAll consistency checks passed.");
process.exit(failures ? 1 : 0);
