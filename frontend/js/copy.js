/* UI copy catalog (VISUALIZATION.md §4 demo register + §6 copy/).
   Confident, declarative, sponsor-facing. Numbers are injected from
   SRMP_DEMO.kpi so every screen states the same figures. */
window.COPY = (function () {
  const K = window.SRMP_DEMO.kpi;
  const F = window.FMT;
  const lift = "+" + K.indexLift.toFixed(1);

  return {
    productName: "Sponsorship Intelligence",
    caseName: "Lenovo × FIFA",
    demoNotice: "Demonstration environment · illustrative data",

    nav: [
      { id: "overview", label: "Overview", group: "The partnership" },
      { id: "reach", label: "Reach", group: "The story" },
      { id: "attention", label: "Attention" },
      { id: "perception", label: "Perception" },
      { id: "portfolio", label: "Portfolio" },
      { id: "proof", label: "Proof" },
      { id: "return", label: "Return" },
      { id: "about", label: "About the platform", group: "Platform" },
    ],

    overview: {
      kicker: "Lenovo × FIFA partnership",
      title: "The FIFA partnership, measured.",
      insight: `The FIFA partnership delivered ${F.big(K.digitalImpressions)} digital impressions and a ${F.big(K.broadcastAudience)} broadcast audience, lifted Lenovo's Brand Index by ${lift} points, and returned ${F.usd(K.annualValueUsd)} in annual brand-driven earnings — ${F.mult(K.roiMultiple)} the investment.`,
      kpis: {
        impressions: "Digital impressions",
        broadcast: "Broadcast audience",
        lift: "Brand Index lift",
        value: "Annual brand value",
        roi: "Return multiple",
      },
      sections: {
        reach: ["Reach", "Exposure delivered"],
        attention: ["Attention", "Brand salience"],
        perception: ["Perception", "Audience impact"],
        value: ["Proof", "Counterfactual"],
        return: ["Return", "Financial impact"],
      },
      timelineTitle: "Partnership timeline",
    },

    reach: {
      kicker: "Reach",
      title: "How many people saw Lenovo",
      insight: `${F.big(K.totalExposure)} total exposure across digital and broadcast — World Cup weeks alone delivered the majority of all partnership reach.`,
      hero: "Cumulative partnership exposure",
      heroLabel: "Chart 1",
      byProperty: "Weekly exposure by property",
      share: "FIFA share of portfolio exposure",
      adstock: "Attention carryover",
      adstockNote: "Your exposure keeps working: attention decays with a 3-week half-life after each activation, so match weeks pay off long after the final whistle.",
      engagement: "Fan engagement",
      engagementNote: `${F.big(K.engagementsTotal)} engagements across FIFA properties, peaking on match weeks.`,
    },

    attention: {
      kicker: "Attention",
      title: "Did people care?",
      insight: "Brand attention peaked at an all-partnership high in the World Cup build-up and holds above the pre-partnership baseline.",
      hero: "Lenovo Brand Index — weekly",
      surveyDots: "Independent survey research",
      surveyNote: `Tracks independent survey measurement across ${K.surveyQuarters} quarters.`,
      media: "Earned media",
      mediaNote: "Global news coverage of Lenovo, colored by tone.",
      intent: "Commercial intent",
      intentNote: "Search interest for Lenovo products and prices — attention that shops.",
    },

    perception: {
      kicker: "Perception",
      title: "Did it change minds?",
      insight: `Fans who experienced the sponsorship choose Lenovo more at every step: appeal up to +${K.appealLiftRange[1]} pp, purchase intent up to +${K.intentLiftRange[1]} pp.`,
      hero: "The sponsorship funnel — exposed vs unexposed audiences",
      aware: "Experienced the sponsorship",
      unaware: "Did not",
      heat: "Lift by property and wave",
      heatNote: "Appeal and purchase-intent lift, every FIFA property, every survey wave.",
      cards: [
        { stat: "≈ 2×", text: "Fans exposed to the sponsorship are about twice as likely to consider Lenovo." },
        { stat: `+${K.appealLiftRange[1]} pp`, text: "Peak appeal lift among audiences who experienced the sponsorship." },
        { stat: `+${K.intentLiftRange[1]} pp`, text: "Peak purchase-intent lift — perception that converts." },
      ],
    },

    portfolio: {
      kicker: "Portfolio",
      title: "How FIFA compares",
      insight: `FIFA delivers the portfolio's highest value per impression — ${K.fifaVsMedianMultiple.toFixed(1)}× the portfolio median.`,
      hero: "Value created per million impressions",
      scatter: "Exposure vs return",
      scatterNote: "Bubble size = fee tier. FIFA combines scale with the portfolio's best rate of return.",
      mix: "Share of value vs share of spend",
      mixNote: "FIFA earns a larger share of portfolio value than it takes of portfolio spend.",
    },

    proof: {
      kicker: "Proof",
      title: "Would this have happened anyway?",
      insight: "Without the partnership, Lenovo's brand trajectory tracks the competitor market. With it, Lenovo breaks away.",
      hero: "Actual vs. without-sponsorship Lenovo",
      actual: "Lenovo — actual",
      synthetic: "Without sponsorship",
      gapLabel: "Value created by the partnership",
      callout: `${lift} Index points`,
      calloutSub: "created since the announcement",
      market: "Versus the market",
      marketNote: `Lenovo against ${K.donorCount} competitor brands, each measured against its own pre-announcement baseline. Lenovo pulls away.`,
      credential: `Counterfactual built from ${K.donorCount} competitor brands using synthetic-control methodology.`,
    },

    return: {
      kicker: "Return",
      title: "What it's worth",
      insight: `Every US$1 of sponsorship investment returned US$${K.roiMultiple.toFixed(2)} in brand value.`,
      hero: "From Index points to net value",
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
      royaltyNote: (lo, hi) => `An equivalent licensing view values the uplift at ${F.usd(lo)}–${F.usd(hi)} over the horizon.`,
      tornado: "What moves the number",
      formulaNote: (d) => `${d.toFixed(1)} Index points × US$6.25M per point per year`,
    },

    about: {
      kicker: "About the platform",
      title: "How we measure sponsorship value",
      chain: ["Exposure", "Attention", "Perception", "Financial value"],
      chainNote: "Every activation is traced along one causal chain — from the moment fans see the brand to the earnings it creates.",
      sources: [
        ["Independent survey research", "17 quarters of brand tracking"],
        ["Social & digital analytics", "Impression-level exposure, 13 properties"],
        ["Search interest", "Worldwide, weekly, 2022–2026"],
        ["Global news", "1,600+ days of coverage and tone"],
        ["Market data", "Earnings, prices and market factors"],
      ],
      how: [
        "We start with what fans actually saw. Every post, broadcast and activation is measured at the impression level and rolled into a single weekly exposure history for each property in the portfolio.",
        "We then measure what that exposure did to the brand. A weekly Brand Index tracks Lenovo's salience worldwide and is validated against independent survey research. To isolate the sponsorship's contribution, we compare Lenovo against a synthetic version of itself built from competitor brands that did not sponsor — the difference is value the partnership created.",
        "Finally we translate brand movement into money. A market-based calibration maps each Index point to annual brand-driven earnings, and a transparent waterfall carries it through persistence, fees and activation to net value and the return multiple.",
      ],
    },
  };
})();
