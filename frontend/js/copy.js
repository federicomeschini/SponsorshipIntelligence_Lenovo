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
      market: "Source: market data (Lenovo Group, 0992.HK) · Elaboration: OpenEconomics",
    },

    home: {
      title: "FIFA Partnership Intelligence",
      sub: "Measurement, causal proof and financial valuation for FIFA partner programmes. Select a programme to open its dashboard.",
      gridTitle: "Partner programmes",
      openLabel: "Open dashboard →",
      activeChip: "Live",
      brands: [
        { id: "lenovo", name: "Lenovo", category: "Technology partner", active: true },
        { id: "adidas", name: "adidas", category: "Official partner" },
        { id: "cocacola", name: "Coca‑Cola", category: "Official partner" },
        { id: "visa", name: "Visa", category: "Payment technology partner" },
        { id: "hyundai", name: "Hyundai", category: "Mobility partner" },
        { id: "kia", name: "Kia", category: "Mobility partner" },
        { id: "qatarairways", name: "Qatar Airways", category: "Airline partner" },
        { id: "qatarenergy", name: "QatarEnergy", category: "Energy partner" },
        { id: "aramco", name: "Aramco", category: "Major worldwide partner" },
        { id: "bankofamerica", name: "Bank of America", category: "Tournament sponsor" },
        { id: "mcdonalds", name: "McDonald’s", category: "Tournament sponsor" },
        { id: "verizon", name: "Verizon", category: "Tournament sponsor" },
      ],
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
      byProperty: "Exposure by FIFA property",
      share: "Digital and broadcast mix",
      adstock: "Attention carryover",
      adstockNote: "Weekly exposure converted into an attention stock with a three-week half-life: activation weeks continue to contribute after the event itself.",
      engagement: "Fan engagement",
      engagementNote: `${F.big(K.engagementsTotal)} fan interactions recorded across FIFA contents in which Lenovo is exposed, peaking on match weeks.`,
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
      insight: "The metric under test is the Brand Index — a weekly 0–100 score of how present Lenovo is in worldwide searches, media and surveys. The question is not whether it improved, but whether it moved beyond where it would have been without the partnership; a synthetic control built from non-sponsor competitors provides that baseline.",
      pointMeaning: `≈ ${F.usd(K.usdPerPointYear)}/yr of brand earnings`,
      hero: "Actual Lenovo vs. the without-FIFA trajectory",
      howTo: "How to read it: the solid line is Lenovo as measured; the dashed line is the Lenovo estimated without FIFA. The green area between them is what the partnership added.",
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
      insight: `In the base case the partnership creates ${F.usd(K.grossValueUsd)} of additional brand value — extra brand-driven earnings attributable to FIFA — against ${F.usd(K.investmentUsd)} of partnership cost: ${F.mult(K.roiMultiple)} the investment, ${F.usd(K.netValueUsd)} net.`,
      hero: "From Brand Index lift to additional brand value",
      steps: {
        annual: "Additional brand earnings / yr",
        persistence: "Effect lasts",
        investment: "Partnership cost",
        net: "Net additional brand value",
      },
      bridgeNote: (s) => `How to read it: the ${s.deltaIndex.toFixed(1)}-point Brand Index lift attributed to FIFA converts into ${F.usd(s.annualUsd)} of additional brand-driven earnings per year. The effect persists for about ${s.persistenceYears} years, worth ${F.usd(s.grossUsd)} in total; subtracting the ${F.usd(s.investmentUsd)} partnership cost (fee + activation) leaves ${F.usd(s.netUsd)} of net additional brand value.`,
      scenario: "Scenario",
      scenarios: { conservative: "Conservative", base: "Base", ambitious: "Ambitious" },
      stock: "Lenovo share price — indexed to 100 at January 2022",
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
