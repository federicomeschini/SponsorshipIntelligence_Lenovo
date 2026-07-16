/* Copy catalog for the FIFA Partnership Intelligence platform. Numbers are
   injected from SRMP_DEMO.kpi so every screen states the same figures, and
   per-chart source attributions live in `src` so wording stays uniform. */
window.COPY = (function () {
  const K = window.SRMP_DEMO.kpi;
  const F = window.FMT;
  const lift = "+" + K.indexLift.toFixed(1);
  const OE = "Elaboration: OpenEconomics";

  return {
    productName: "FIFA Partnership Intelligence",
    caseName: "Lenovo × FIFA",
    demoNotice: "Demonstration environment · illustrative data",

    src: {
      exposure: "Sources: Blinkfire Analytics (digital) · Nielsen (broadcast) · " + OE,
      blinkfire: "Source: Blinkfire Analytics · " + OE,
      waves: "Sources: GWI · Nielsen brand-tracking waves · " + OE,
      index: "Sources: Google Trends · GWI survey calibration · Index model: OpenEconomics",
      news: "Source: GDELT global news database · " + OE,
      search: "Source: Google Trends · " + OE,
      counterfactual: "Sources: Google Trends donor panel · GWI · Synthetic-control model: OpenEconomics",
      valuation: "Valuation model: OpenEconomics · Calibration: market earnings data",
    },

    nav: [
      { id: "overview", label: "Executive overview", group: "Decision case" },
      { id: "return", label: "Financial case" },
      { id: "proof", label: "Proof" },
      { id: "reach", label: "FIFA reach", group: "Supporting evidence" },
      { id: "attention", label: "Attention" },
      { id: "perception", label: "Perception" },
      { id: "about", label: "Method & evidence", group: "Method" },
    ],

    overview: {
      kicker: "Lenovo × FIFA partnership",
      title: "The Lenovo × FIFA investment case",
      insight: `FIFA properties delivered ${F.big(K.totalExposure)} exposure contacts, moved the Lenovo Brand Index ${lift} points above its no-partnership trajectory, and generated ${F.usd(K.grossValueUsd)} of brand value over the partnership horizon — ${F.mult(K.roiMultiple)} the investment.`,
      sections: {
        financial: ["Financial case", "Value of the partnership"],
        proof: ["Proof", "The counterfactual test"],
        reach: ["FIFA reach", "Global exposure delivered"],
        attention: ["Attention", "Brand salience"],
        perception: ["Perception", "Audience impact"],
      },
      timelineTitle: "FIFA partnership timeline",
    },

    reach: {
      kicker: "FIFA reach",
      title: "Global exposure delivered by FIFA properties",
      insight: `${F.big(K.totalExposure)} exposure contacts across digital and broadcast channels, concentrated on the tournament windows where global attention peaks.`,
      hero: "Cumulative FIFA partnership exposure",
      heroNote: "Cumulative contacts across the partnership window — impressions and audience contacts, not unique viewers.",
      byProperty: "FIFA activation map",
      share: "Digital and broadcast mix",
      adstock: "Attention carryover",
      adstockNote: "Weekly exposure converted into an attention stock with a three-week half-life: activation weeks continue to contribute after the event itself.",
      engagement: "Fan engagement",
      engagementNote: `${F.big(K.engagementsTotal)} fan interactions recorded across FIFA activations, peaking on match weeks.`,
    },

    attention: {
      kicker: "Attention",
      title: "Brand salience across the partnership",
      insight: "Brand attention rises into each tournament window and holds above the pre-partnership baseline throughout.",
      hero: "Lenovo Brand Index — weekly",
      surveyDots: "Quarterly survey composite",
      surveyNote: `Weekly Brand Index with confidence band; markers show the independent quarterly survey composite across ${K.surveyQuarters} quarters.`,
      media: "Earned media",
      mediaNote: "Weekly news coverage of Lenovo worldwide.",
      intent: "Commercial intent",
      intentNote: "Worldwide search interest in Lenovo products and pricing — a leading indicator of commercial demand.",
    },

    perception: {
      kicker: "Perception",
      title: "Perception shift across the purchase funnel",
      insight: `Audiences exposed to the partnership choose Lenovo more at every funnel stage. In the latest wave, appeal lift reaches +${K.appealLiftRange[1]} pp and purchase-intent lift +${K.intentLiftRange[1]} pp.`,
      hero: "Funnel conversion — exposed vs non-exposed audiences",
      funnelNote: "Share of each audience group reaching each funnel stage. Lift is the exposed-minus-non-exposed difference in percentage points.",
      aware: "Exposed to the partnership",
      unaware: "Not exposed",
      stageHead: "Funnel stage",
      shareHead: "Share of audience at each stage",
      liftHead: "Lift",
      trend: "Lift by measurement wave — FIFA World Cup audience",
      trendNote: "Appeal and purchase-intent lift widen wave over wave as the partnership matures, peaking during the tournament itself.",
      heat: "Lift by FIFA competition and wave",
      heatNote: "Appeal and purchase-intent lift, in percentage points, across the six brand-tracking waves fielded between November 2024 and June 2026.",
      cards: [
        { stat: F.mult(K.exposedChoiceMultiple), text: `Exposed audiences choose Lenovo at ${K.exposedChoiceMultiple}× the rate of the non-exposed control at the appeal stage.` },
        { stat: `+${K.appealLiftRange[1]} pp`, text: `Appeal lift in the latest wave, up from +${K.appealLiftRange[0]} pp in the first wave of the programme.` },
        { stat: `+${K.intentLiftRange[1]} pp`, text: "Purchase-intent lift in the latest wave — the strongest reading of the programme." },
      ],
    },

    proof: {
      kicker: "Causal proof",
      title: "The counterfactual test",
      insight: "The test is whether Lenovo moved beyond where it would have been without the partnership. A synthetic control built from non-sponsor competitors provides that baseline.",
      hero: "Actual Lenovo vs. the without-FIFA trajectory",
      actual: "Lenovo — actual",
      synthetic: "Lenovo without FIFA",
      gapLabel: "Increment attributed to the FIFA partnership",
      calloutSub: "above the without-FIFA trajectory",
      market: "Lenovo versus the non-sponsor market",
      marketNote: `Lenovo against ${K.donorCount} non-sponsor competitor brands, each measured against its own pre-announcement baseline. Lenovo separates from the market after the announcement.`,
      credential: `Counterfactual built from ${K.donorCount} non-sponsor competitor brands using synthetic-control methodology.`,
      verdict: "The observed lift is not explained by market-wide movement among comparable non-sponsor brands.",
      evidence: [
        ["Observed", "Lenovo Brand Index and independent survey signals"],
        ["Estimated", `Without-FIFA trajectory built from ${K.donorCount} non-sponsor brands`],
        ["Illustrative", "Post-tournament extension is shown with dashed lines"],
      ],
    },

    return: {
      kicker: "Financial case",
      title: "The financial value of the partnership",
      insight: `In the base case the partnership generates ${F.usd(K.grossValueUsd)} of gross brand value against ${F.usd(K.investmentUsd)} of fee and activation — ${F.mult(K.roiMultiple)} the investment, ${F.usd(K.netValueUsd)} net.`,
      hero: "From FIFA-attributed lift to financial value",
      steps: {
        annual: "Annual brand earnings",
        persistence: "Persistence",
        investment: "Fee + activation",
        net: "Net value created",
      },
      scenario: "Scenario",
      scenarios: { conservative: "Conservative", base: "Base", ambitious: "Ambitious" },
      supportIntro: ["Stress-test the conclusion", "Two independent checks: does the market price a comparable uplift in the same range, and which assumptions actually move the result."],
      royalty: "Licensing cross-check",
      royaltyIntro: (lo, hi) => `If Lenovo had to license an equivalent brand uplift at market royalty rates, that licence would cost between ${F.usd(lo)} and ${F.usd(hi)} over the partnership horizon.`,
      royaltyVerdict: `The ${F.usd(K.grossValueUsd)} base-case valuation sits inside this independently derived bracket.`,
      royaltyScheduleHead: ["Index lift", "Implied royalty"],
      tornado: "What moves the number",
      tornadoLegend: ["Assumption at low end", "Assumption at high end"],
      tornadoAxis: "Change in net value vs the base case",
      tornadoNote: `Bars show the change in net value — base case ${F.usd(K.netValueUsd)} — when one assumption moves to the low or high end of its range, everything else held fixed. Persistence and the size of the Index lift dominate; investment cost barely moves the result.`,
      formulaNote: (d) => `${d.toFixed(1)} Index points × ${F.usd(K.usdPerPointYear)} per point per year`,
      decisionLabel: "Decision signal",
      decisionText: "The partnership clears its modelled investment cost in all three scenarios.",
    },

    about: {
      kicker: "Method & evidence",
      title: "How we measure FIFA partnership value",
      chain: ["FIFA exposure", "Attention", "Perception", "Financial value"],
      chainNote: "Every FIFA activation is traced along a single evidence chain — from the impressions fans actually saw to the earnings-equivalent value they created.",
      sources: [
        ["GWI · Nielsen", "Brand-tracking survey waves and quarterly composite"],
        ["Blinkfire Analytics", "Impression-level digital exposure by property"],
        ["Nielsen", "Broadcast audience measurement"],
        ["Google Trends", "Worldwide weekly search interest, 2022–2026"],
        ["GDELT", "Global news volume and tone, 1,600+ days of coverage"],
        ["Market data", "Earnings, prices and market factors for calibration"],
      ],
      how: [
        "Exposure is measured at the impression level. Every FIFA post, broadcast window and activation is captured through Blinkfire Analytics and Nielsen audience measurement, then rolled into a single weekly partnership exposure history.",
        "Brand movement is tracked weekly. A composite Brand Index combines worldwide search interest with GWI survey calibration and is validated against the quarterly survey composite. A synthetic control built from eleven non-sponsor competitor brands estimates where Lenovo would be without the partnership; the difference is the lift attributed to FIFA.",
        "Value is stated in currency. A market-based calibration maps each Index point to annual brand-driven earnings, and a transparent waterfall carries the lift through persistence, fee and activation to net value and the return multiple.",
      ],
    },
  };
})();
