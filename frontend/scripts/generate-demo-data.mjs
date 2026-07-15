/* Seeded demo-data generator (VISUALIZATION.md §2.3).
 *
 * Reads frontend/data/real-data.js (pipeline extract) and writes
 * frontend/data/demo-data.js: the simulated fills plus every derived KPI,
 * computed once here so numbers are consistent on every screen (§7.2).
 * Deterministic — same seed, same output. Regenerating is an explicit step:
 *   node frontend/scripts/generate-demo-data.mjs
 */

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DATA = join(HERE, "..", "data");
const SEED = 20260715; // committed seed — do not change casually

// ---- load the real extract ------------------------------------------------
const realSrc = readFileSync(join(DATA, "real-data.js"), "utf8");
const windowShim = {};
new Function("window", realSrc)(windowShim);
const REAL = windowShim.SRMP_REAL;

// ---- seeded PRNG (mulberry32) ----------------------------------------------
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(SEED);
const noise = (sd) => (rand() + rand() + rand() - 1.5) * 2 * sd; // ~normal-ish

// ---- shared weekly timeline (W-MON), extends real grid to 2026-12-28 -------
const weekMs = 7 * 24 * 3600 * 1000;
const iso = (d) => new Date(d).toISOString().slice(0, 10);
const realWeeks = REAL.brandIndexWeekly.week;
const lastReal = new Date(realWeeks[realWeeks.length - 1] + "T00:00:00Z");
const TIMELINE_END = "2026-12-28";
const extWeeks = [];
for (let t = lastReal.getTime() + weekMs; iso(t) <= TIMELINE_END; t += weekMs)
  extWeeks.push(iso(t));
const timeline = realWeeks.concat(extWeeks);
const simulatedFrom = extWeeks[0]; // 2026-07-13

// =============================================================================
// 1. Brand Index tournament arc (§2.3): continue the real series through the
//    finals peak (+2.5 pts vs counterfactual) decaying to a +0.8 persistent
//    plateau. The counterfactual continues the real synthetic donor path.
// =============================================================================
const cf = REAL.counterfactualWeekly;
const lastSyn = cf.synthetic[cf.synthetic.length - 1]; // 88.68
const synTarget = 88.9; // gentle mean reversion, matches 2026 synthetic range
const FINAL_WEEK = "2026-07-13"; // week containing the 2026-07-19 final
const PLATEAU = 0.8; // persistent lift, ≈ real post-period mean gap (0.82)
const PEAK = 2.5;

const extSynthetic = [];
const extGap = [];
let syn = lastSyn;
extWeeks.forEach((w, i) => {
  syn = syn + (synTarget - syn) * 0.15 + noise(0.28);
  extSynthetic.push(syn);
  let gap;
  if (w <= FINAL_WEEK) gap = PEAK * 0.72; // ramp into finals week
  else {
    const k = i - extWeeks.indexOf(FINAL_WEEK); // weeks after the final
    gap = k === 0 ? PEAK : PLATEAU + (PEAK - PLATEAU) * Math.exp(-k / 5);
  }
  extGap.push(gap + noise(0.09));
});
// exact peak on the finals week
extGap[extWeeks.indexOf(FINAL_WEEK)] = PEAK;
const extActual = extSynthetic.map((s, i) => s + extGap[i]);

const round = (v, nd = 3) => Math.round(v * 10 ** nd) / 10 ** nd;
const index = {
  week: timeline,
  level: REAL.brandIndexWeekly.level.concat(extActual.map((v) => round(v))),
  se: REAL.brandIndexWeekly.se.concat(
    extWeeks.map((_, i) => round(1.5946 + 0.03 * Math.min(i, 20)))
  ),
  simulatedFrom,
};
const extSynRounded = extSynthetic.map((v) => round(v));
const counterfactual = {
  week: timeline,
  actual: index.level,
  synthetic: cf.synthetic.map((v) => round(v)).concat(extSynRounded),
  // extension gap derived from the rounded pair so actual = synthetic + gap exactly
  gap: cf.gap.map((v) => round(v)).concat(extSynRounded.map((s, i) => round(index.level[realWeeks.length + i] - s))),
  announcementWeek: REAL.counterfactualMeta.announcementWeek,
  simulatedFrom,
};

// =============================================================================
// 2. Exposure: fill missing tournament digital weeks from the pipeline's own
//    simulated WC base scenario, then simulate broadcast (peaks 6–8× digital
//    on match weeks, adstock-shaped decay) and engagement.
// =============================================================================
const fifaFamily = REAL.exposureMeta.fifaFamily;
const bfWeeks = new Set();
Object.values(REAL.exposureWeekly).forEach((p) => p.week.forEach((w) => bfWeeks.add(w)));
const lastBfWeek = [...bfWeeks].sort().pop(); // 2026-06-08

// weekly digital per property over the partnership window (2024-09-30 →)
const partnershipWeeks = timeline.filter((w) => w >= "2024-09-30");
const digital = {};
for (const [pid, p] of Object.entries(REAL.exposureWeekly)) {
  const map = new Map(p.week.map((w, i) => [w, p.impressions[i]]));
  digital[pid] = partnershipWeeks.map((w) => map.get(w) ?? 0);
}
// tournament fill on the flagship WC property (fwc)
const wcSim = REAL.worldCupSimulatedExposure;
wcSim.week.forEach((w, i) => {
  if (w > lastBfWeek) {
    const k = partnershipWeeks.indexOf(w);
    if (k >= 0) digital.fwc[k] += wcSim.impressions[i];
  }
});
// gentle post-tournament digital tail on FIFA properties (echo content, decays)
partnershipWeeks.forEach((w, k) => {
  if (w > "2026-07-13" ) {
    const wks = Math.round((new Date(w) - new Date("2026-07-13")) / weekMs);
    digital.fwc[k] += Math.max(0, 38e6 * Math.exp(-wks / 4) * (1 + noise(0.15)));
    digital.fifa[k] += Math.max(0, 14e6 * Math.exp(-wks / 5) * (1 + noise(0.15)));
  }
});

// broadcast audience (simulated): matches calendar; 6–8× digital on WC weeks
const wcMatchWeeks = new Map(REAL.worldCupCalendarWeekly.map((r) => [r.week, r.matches]));
// FCWC 2025 window (opening 2025-06-15 → final 2025-07-13)
const fcwcWeeks = new Set(["2025-06-09", "2025-06-16", "2025-06-23", "2025-06-30", "2025-07-07"]);
const fifaDigitalWeekly = partnershipWeeks.map((_, k) =>
  fifaFamily.reduce((s, pid) => s + (digital[pid] ? digital[pid][k] : 0), 0)
);
const broadcast = partnershipWeeks.map((w, k) => {
  let base = 0;
  const wm = [...wcMatchWeeks.keys()].find((mw) => Math.abs(new Date(mw) - new Date(w)) < weekMs);
  if (wm) base = fifaDigitalWeekly[k] * (6 + 2 * rand()); // 6–8× digital (WC)
  else if (fcwcWeeks.has(w)) base = 90e6 * (1 + 0.6 * rand()); // FCWC broadcast
  else if (w >= "2024-10-14") base = 6e6 * (1 + noise(0.3)); // magazine/friendlies
  return Math.max(0, Math.round(base)); // audience contacts, no carry (no double count)
});

// engagement (simulated): FIFA-family weekly engagement rate 0.5–4%, higher on
// match weeks; engagements = views-weighted share of impressions
const engagementRate = partnershipWeeks.map((w, k) => {
  const isMatch = wcMatchWeeks.has(w) || fcwcWeeks.has(w);
  const r0 = 0.012 + (isMatch ? 0.016 : 0) + Math.abs(noise(0.004));
  return round(Math.min(0.04, Math.max(0.005, r0)), 4);
});
const engagements = partnershipWeeks.map((w, k) =>
  Math.round(fifaDigitalWeekly[k] * engagementRate[k])
);

const exposure = {
  week: partnershipWeeks,
  digital, // per property
  fifaDigital: fifaDigitalWeekly.map((v) => Math.round(v)),
  broadcast,
  engagements,
  engagementRate,
  adstockHalfLifeWeeks: 3, // "attention carryover" framing, §V1
  digitalSimulatedFrom: lastBfWeek < "2026-06-15" ? "2026-06-15" : lastBfWeek,
};

// =============================================================================
// 3. Post-tournament survey wave (simulated): extends the real 2024–2026 lift
//    trajectory upward on the same scale.
// =============================================================================
const funnel = REAL.funnelLift.slice();
[
  { wave: "2026-09", property: "fwc", stage: "appeal", aware: 0.671, unaware: 0.179, lift: 0.492 },
  { wave: "2026-09", property: "fwc", stage: "awareness", aware: 1.0, unaware: 0.512, lift: 0.488 },
  { wave: "2026-09", property: "fwc", stage: "purchase_intent", aware: 0.566, unaware: 0.158, lift: 0.408 },
  { wave: "2026-09", property: "fwwc", stage: "appeal", aware: 0.652, unaware: 0.163, lift: 0.489 },
  { wave: "2026-09", property: "fwwc", stage: "awareness", aware: 1.0, unaware: 0.387, lift: 0.613 },
  { wave: "2026-09", property: "fwwc", stage: "purchase_intent", aware: 0.561, unaware: 0.151, lift: 0.410 },
].forEach((r) => funnel.push({ ...r, simulated: true }));

// Funnel hero (V3): five ordered stages, aware vs unaware, latest FWC wave.
// awareness/appeal/purchase_intent are real (wave 2026-02, fwc); engagement and
// consideration are simulated fills chosen to keep both columns monotonic.
const fw = funnel.filter((r) => r.wave === "2026-02" && r.property === "fwc");
const stageRow = (s) => fw.find((r) => r.stage === s);
const funnelHero = [
  { stage: "awareness", ...pick(stageRow("awareness")) },
  { stage: "engagement", aware: 0.82, unaware: 0.36, lift: 0.46, simulated: true },
  { stage: "appeal", ...pick(stageRow("appeal")) },
  { stage: "consideration", aware: 0.6, unaware: 0.208, lift: 0.392, simulated: true },
  { stage: "purchase_intent", ...pick(stageRow("purchase_intent")) },
];
function pick(r) {
  return { aware: r.aware, unaware: r.unaware, lift: r.lift };
}

// =============================================================================
// 4. ROI block (V6). Base delta = the real exposure-weighted candidate.
// =============================================================================
const USD_PER_POINT_YEAR = REAL.earningsCalibration.usdPerIndexPointPerYear; // 6.253e6
const roiInputs = {
  deltaIndex: REAL.counterfactualMeta.exposureWeightedGap, // +1.033
  usdPerPointYear: USD_PER_POINT_YEAR,
  persistenceYears: 2,
  feeUsd: 2.9e6, // simulated — annualized partnership fee (illustrative)
  activationUsd: 0.9e6, // simulated — activation & content production
};
function waterfall({ deltaIndex, persistenceYears, feeUsd, activationUsd }) {
  const annual = deltaIndex * USD_PER_POINT_YEAR;
  const gross = annual * persistenceYears;
  const investment = feeUsd + activationUsd;
  return {
    deltaIndex,
    annualUsd: annual,
    persistenceYears,
    grossUsd: gross,
    investmentUsd: investment,
    netUsd: gross - investment,
    roiMultiple: gross / investment,
  };
}
const scenarios = {
  conservative: waterfall({ ...roiInputs, deltaIndex: 0.82, persistenceYears: 1.5 }),
  base: waterfall(roiInputs),
  ambitious: waterfall({ ...roiInputs, deltaIndex: 1.5, persistenceYears: 3 }),
};
// royalty cross-check (simulated 4-point monotonic Index→USD/yr curve)
const royaltySchedule = [
  { indexPoints: 0.5, usdPerYear: 3.4e6 },
  { indexPoints: 1.0, usdPerYear: 6.2e6 },
  { indexPoints: 1.5, usdPerYear: 8.6e6 },
  { indexPoints: 2.0, usdPerYear: 10.6e6 },
];
function royaltyAt(pts) {
  const s = royaltySchedule;
  for (let i = 1; i < s.length; i++) {
    if (pts <= s[i].indexPoints) {
      const a = s[i - 1], b = s[i];
      const f = (pts - a.indexPoints) / (b.indexPoints - a.indexPoints);
      return a.usdPerYear + f * (b.usdPerYear - a.usdPerYear);
    }
  }
  return s[s.length - 1].usdPerYear;
}
const royaltyView = {
  schedule: royaltySchedule,
  lowUsd: royaltyAt(0.82) * 1.5,
  highUsd: royaltyAt(1.5) * 3,
  baseUsd: royaltyAt(roiInputs.deltaIndex) * roiInputs.persistenceYears,
};
// sensitivity tornado (± effect on base net value, USD)
const b = scenarios.base;
const tornado = [
  { label: "Index lift (+/−0.25 pts)", lo: waterfall({ ...roiInputs, deltaIndex: roiInputs.deltaIndex - 0.25 }).netUsd - b.netUsd, hi: waterfall({ ...roiInputs, deltaIndex: roiInputs.deltaIndex + 0.25 }).netUsd - b.netUsd },
  { label: "Persistence (1.5 vs 3 yrs)", lo: waterfall({ ...roiInputs, persistenceYears: 1.5 }).netUsd - b.netUsd, hi: waterfall({ ...roiInputs, persistenceYears: 3 }).netUsd - b.netUsd },
  { label: "Earnings per point (±20%)", lo: -0.2 * b.grossUsd, hi: 0.2 * b.grossUsd },
  { label: "Investment (±15%)", lo: 0.15 * b.investmentUsd, hi: -0.15 * b.investmentUsd },
];

// =============================================================================
// 5. Portfolio (V4): value per million impressions, FIFA ≈ 1.6× median.
// =============================================================================
const totals = {};
for (const [pid, p] of Object.entries(REAL.exposureWeekly))
  totals[pid] = p.impressions.reduce((a, v) => a + v, 0);
// same series the KPI sums, so the donut/portfolio agree with the KPI strip
const fifaImpressionsTotal = Math.round(fifaDigitalWeekly.reduce((a, v) => a + v, 0));

const fifaGrossValue = scenarios.base.grossUsd; // consistent with V6
const fifaVpm = fifaGrossValue / (fifaImpressionsTotal / 1e6); // USD per M impressions
const median = fifaVpm / 1.6; // FIFA = 1.6× portfolio median (§2.3)
const rel = { f1: 1.18, motogp: 0.74, ducati: 1.0, carolina_hurricanes: 0.62, montreal_canadiens: 0.88, ny_yankees: 1.32 };
const portfolio = [
  {
    id: "fifa_partnership", label: "FIFA partnership", fifa: true,
    impressions: fifaImpressionsTotal, valuePerM: fifaVpm,
    valueUsd: fifaGrossValue, feeTier: 3, signature: "Highest value per impression in the portfolio",
  },
  ...Object.entries(rel).map(([pid, m]) => {
    const vpm = median * m * (1 + noise(0.03));
    return {
      id: pid,
      label: { f1: "Formula 1", motogp: "MotoGP", ducati: "Ducati", carolina_hurricanes: "Carolina Hurricanes", montreal_canadiens: "Montreal Canadiens", ny_yankees: "New York Yankees" }[pid],
      fifa: false, impressions: totals[pid], valuePerM: vpm,
      valueUsd: (totals[pid] / 1e6) * vpm,
      feeTier: pid === "f1" || pid === "motogp" ? 2 : 1,
    };
  }),
];
const portMedian = median;

// =============================================================================
// 6. Earned media + commercial intent: extend to the demo timeline end.
// =============================================================================
const em = REAL.earnedMediaWeekly;
const emLast = em.week[em.week.length - 1];
const emExt = { week: [], volume: [], tone: [] };
timeline.filter((w) => w > emLast).forEach((w) => {
  const wks = Math.round((new Date(w) - new Date(FINAL_WEEK)) / weekMs);
  const finalsBoost = w <= "2026-07-20" ? 2.6 : Math.exp(-Math.max(0, wks) / 6) + 0.9;
  emExt.week.push(w);
  emExt.volume.push(Math.max(400, Math.round(2400 * finalsBoost * (1 + noise(0.12)))));
  emExt.tone.push(round(1.1 * Math.min(1.6, finalsBoost) * 0.9 + noise(0.25), 2));
});
const earnedMedia = {
  week: em.week.concat(emExt.week),
  volume: em.volume.concat(emExt.volume),
  tone: em.tone.concat(emExt.tone),
  simulatedFrom: emExt.week[0] || null,
};
const ciReal = REAL.commercialIntentWeekly;
const ciLast = ciReal.week[ciReal.week.length - 1];
const ciExt = { week: [], interest: [] };
let ciV = ciReal.interest[ciReal.interest.length - 1];
timeline.filter((w) => w > ciLast).forEach((w) => {
  const boost = w <= FINAL_WEEK ? 1.12 : 1.0;
  ciV = Math.max(4, ciV * (0.985 * boost) + noise(0.5));
  ciExt.week.push(w);
  ciExt.interest.push(round(ciV, 2));
});
const commercialIntent = {
  week: ciReal.week.concat(ciExt.week),
  interest: ciReal.interest.concat(ciExt.interest),
  simulatedFrom: ciExt.week[0] || null,
};

// =============================================================================
// 7. Derived KPIs — single source of truth for every number on screen (§7.2).
// =============================================================================
const digitalTotalClean = fifaDigitalWeekly.reduce((a, v) => a + v, 0);
const broadcastTotal = broadcast.reduce((a, v) => a + v, 0);
const preAnnouncementBaseline = 88.9; // real index level at announcement week
const kpi = {
  digitalImpressions: Math.round(digitalTotalClean),
  broadcastAudience: broadcastTotal,
  totalExposure: Math.round(digitalTotalClean) + broadcastTotal,
  indexLift: roiInputs.deltaIndex, // +1.033 → displayed +1.0
  annualValueUsd: scenarios.base.annualUsd, // ≈ US$6.46M
  grossValueUsd: scenarios.base.grossUsd,
  netValueUsd: scenarios.base.netUsd,
  roiMultiple: scenarios.base.roiMultiple, // ≈ 3.4×
  peakLift: PEAK,
  persistentLift: PLATEAU,
  appealLiftRange: [33, 48], // pp, real range
  intentLiftRange: [28, 41],
  fifaVsMedianMultiple: fifaVpm / portMedian, // 1.6
  totalMatches: REAL.worldCupMeta.totalMatches,
  surveyQuarters: 17,
  donorCount: 11,
  engagementsTotal: engagements.reduce((a, v) => a + v, 0),
};

// =============================================================================
// events (real + tournament milestones)
// =============================================================================
const events = [
  ...REAL.events,
  { id: "wc_opening_2026", type: "tournament_start", name: "FIFA World Cup 2026 opening match", date: REAL.worldCupMeta.firstMatch, property: "fwc" },
  { id: "wc_final_2026", type: "tournament_final", name: "FIFA World Cup 2026 final", date: REAL.worldCupMeta.finalMatch, property: "fwc" },
];

// ---- write ------------------------------------------------------------------
const DEMO = {
  seed: SEED,
  timeline,
  simulatedFrom,
  index,
  counterfactual,
  surveyQuarterly: REAL.surveyQuarterly,
  donorPanel: REAL.donorPanel,
  exposure,
  exposureByProperty: REAL.exposureWeekly,
  funnel,
  funnelHero,
  portfolio,
  portfolioMedianVpm: portMedian,
  earnedMedia,
  commercialIntent,
  worldCupCalendarWeekly: REAL.worldCupCalendarWeekly,
  events,
  roi: { inputs: roiInputs, scenarios, royaltyView, tornado },
  kpi,
};
writeFileSync(
  join(DATA, "demo-data.js"),
  "/* Generated by frontend/scripts/generate-demo-data.mjs (seed " + SEED + ") — do not edit by hand. */\n" +
    "window.SRMP_DEMO = " + JSON.stringify(DEMO) + ";\n"
);
console.log("timeline:", timeline.length, "weeks,", timeline[0], "->", timeline[timeline.length - 1]);
console.log("kpi:", JSON.stringify(kpi, null, 1));
