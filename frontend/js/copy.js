/* FIFA-first executive copy catalog. Numbers are injected from SRMP_DEMO.kpi
   so every screen states the same decision figures. */
window.COPY = (function () {
  const K = window.SRMP_DEMO.kpi;
  const F = window.FMT;
  const lift = "+" + K.indexLift.toFixed(1);

  return {
    productName: "FIFA Partnership Intelligence",
    caseName: "Lenovo \u00d7 FIFA",
    demoNotice: "Demonstration environment \u00b7 illustrative data",

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
      kicker: "Lenovo \u00d7 FIFA partnership",
      title: "The Lenovo \u00d7 FIFA investment case.",
      insight: `The evidence points in one direction: FIFA expands Lenovo's global reach, lifts the brand beyond its counterfactual trajectory, and converts that movement into ${F.usd(K.annualValueUsd)} in annual brand-driven earnings \u2014 ${F.mult(K.roiMultiple)} the investment.`,
      kpis: {
        impressions: "FIFA digital impressions",
        broadcast: "FIFA broadcast audience",
        lift: "Brand Index lift",
        value: "Annual brand value",
        roi: "Return multiple",
      },
      sections: {
        financial: ["Financial case", "Value of the partnership"],
        proof: ["Proof", "The counterfactual test"],
        reach: ["FIFA reach", "Global exposure delivered"],
        attention: ["Attention", "Brand salience"],
        perception: ["Perception", "Audience impact"],
      },
      timelineTitle: "FIFA partnership timeline",
      status: ["Decision case", "Base scenario", "Counterfactual + financial bridge"],
    },

    reach: {
      kicker: "FIFA reach",
      title: "How far did FIFA carry Lenovo?",
      insight: `${F.big(K.totalExposure)} FIFA exposure across digital and broadcast, with the tournament calendar concentrating attention at moments of maximum global relevance.`,
      hero: "Cumulative FIFA partnership exposure",
      heroLabel: "Chart 1",
      byProperty: "FIFA activation map",
      share: "Digital and broadcast mix",
      adstock: "Attention carryover",
      adstockNote: "FIFA exposure keeps working: attention decays with a 3-week half-life after each activation, so match weeks carry value beyond the final whistle.",
      engagement: "Fan engagement",
      engagementNote: `${F.big(K.engagementsTotal)} engagements across FIFA activations, peaking on match weeks.`,
    },

    attention: {
      kicker: "Attention",
      title: "Did FIFA make Lenovo more salient?",
      insight: "Brand attention peaks in the FIFA World Cup build-up and remains above the pre-partnership baseline.",
      hero: "Lenovo Brand Index \u2014 weekly",
      surveyDots: "Independent survey research",
      surveyNote: `Tracks independent survey measurement across ${K.surveyQuarters} quarters.`,
      media: "Earned media",
      mediaNote: "Global news coverage of Lenovo, colored by tone.",
      intent: "Commercial intent",
      intentNote: "Search interest for Lenovo products and prices \u2014 attention that shops.",
    },

    perception: {
      kicker: "Perception",
      title: "Did FIFA change minds?",
      insight: `Audiences who experienced the FIFA partnership choose Lenovo more at every step: appeal up to +${K.appealLiftRange[1]} pp, purchase intent up to +${K.intentLiftRange[1]} pp.`,
      hero: "The FIFA sponsorship funnel \u2014 exposed vs unexposed",
      aware: "Experienced the FIFA partnership",
      unaware: "Did not",
      heat: "Lift by FIFA competition and wave",
      heatNote: "Appeal and purchase-intent lift across the FIFA World Cup, FIFA Women's World Cup and FIFA Club World Cup measurement waves.",
      cards: [
        { stat: "\u2248 2\u00d7", text: "Fans exposed to the FIFA partnership are about twice as likely to consider Lenovo." },
        { stat: `+${K.appealLiftRange[1]} pp`, text: "Peak appeal lift among audiences who experienced FIFA activation." },
        { stat: `+${K.intentLiftRange[1]} pp`, text: "Peak purchase-intent lift \u2014 perception that converts." },
      ],
    },

    proof: {
      kicker: "Causal proof",
      title: "Did FIFA cause the lift?",
      insight: "The decisive test is not whether Lenovo improved, but whether it improved beyond what would have happened without the FIFA partnership.",
      hero: "Actual Lenovo vs. the without-FIFA trajectory",
      actual: "Lenovo \u2014 actual",
      synthetic: "Lenovo without FIFA",
      gapLabel: "Increment attributed to the FIFA partnership",
      callout: `${lift} Index points`,
      calloutSub: "above the without-FIFA trajectory",
      market: "Lenovo's breakaway from the market",
      marketNote: `Lenovo against ${K.donorCount} non-sponsor competitor brands, each measured against its own pre-announcement baseline. Lenovo pulls away.`,
      credential: `Counterfactual built from ${K.donorCount} non-sponsor competitor brands using synthetic-control methodology.`,
      verdict: "The observed lift is not explained by the competitor market alone.",
      evidence: [
        ["Observed", "Lenovo Brand Index and independent survey signals"],
        ["Estimated", `Without-FIFA trajectory built from ${K.donorCount} non-sponsor brands`],
        ["Illustrative", "Post-tournament extension is shown with dashed lines"],
      ],
    },

    return: {
      kicker: "Financial case",
      title: "What value does FIFA create?",
      insight: `In the base case, every US$1 invested in the FIFA partnership returns US$${K.roiMultiple.toFixed(2)} in gross brand value.`,
      hero: "From FIFA-attributed lift to financial value",
      steps: {
        annual: "Annual brand earnings",
        persistence: "Persistence",
        gross: "Gross brand value",
        investment: "Fee + activation",
        net: "Net value created",
      },
      scenario: "Scenario",
      scenarios: { conservative: "Conservative", base: "Base", ambitious: "Ambitious" },
      royalty: "Licensing cross-check",
      royaltyNote: (lo, hi) => `An equivalent licensing view values the uplift at ${F.usd(lo)}\u2013${F.usd(hi)} over the horizon.`,
      tornado: "What moves the number",
      formulaNote: (d) => `${d.toFixed(1)} Index points \u00d7 US$6.25M per point per year`,
      decisionLabel: "Decision signal",
      decisionText: "The partnership clears its modelled investment cost under all three scenarios.",
    },

    about: {
      kicker: "Method & evidence",
      title: "How we measure FIFA partnership value",
      chain: ["FIFA exposure", "Attention", "Perception", "Financial value"],
      chainNote: "Every FIFA activation is traced along one evidence chain \u2014 from the moment fans see Lenovo to the earnings-equivalent value it creates.",
      sources: [
        ["Independent survey research", "17 quarters of brand tracking"],
        ["FIFA exposure analytics", "Impression-level digital and broadcast signals"],
        ["Search interest", "Worldwide, weekly, 2022\u20132026"],
        ["Global news", "1,600+ days of coverage and tone"],
        ["Market data", "Earnings, prices and market factors"],
      ],
      how: [
        "We start with what fans actually saw. Every FIFA post, broadcast and activation is measured at the impression level and rolled into a single weekly partnership exposure history.",
        "We then measure what that exposure did to the brand. A weekly Brand Index tracks Lenovo's salience worldwide and is validated against independent survey research. To isolate FIFA's contribution, we compare Lenovo against a synthetic version of itself built from competitor brands that did not sponsor. The difference is the value attributed to the partnership.",
        "Finally, we translate brand movement into money. A market-based calibration maps each Index point to annual brand-driven earnings, and a transparent waterfall carries it through persistence, fees and activation to net value and the return multiple.",
      ],
    },
  };
})();