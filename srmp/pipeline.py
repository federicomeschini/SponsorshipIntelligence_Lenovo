"""Rebuild every derived artifact in dependency order.

    python -m srmp.pipeline                 # derived steps only (index, experiments)
    python -m srmp.pipeline --with-pulls    # refresh public data and client exports first
    python -m srmp.pipeline --tests         # run the test suite at the end
    python -m srmp.pipeline --review        # re-execute the review notebooks (AGENTS.md)

Steps run as separate processes, exactly as each module's command line does,
and the run stops at the first failure.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

PULLS: list[tuple[str, ...]] = [
    ("srmp.ingest.market",),
    ("srmp.ingest.wikipedia",),
    ("srmp.ingest.gdelt",),
    ("srmp.ingest.trends", "--backend", "anonymous"),
    ("srmp.ingest.trends_joint",),
    ("srmp.ingest.trends_joint", "--config", "config/cobrand_placebo_trends.yaml"),
    ("srmp.ingest.blinkfire",),
    ("srmp.ingest.media_values",),
    ("srmp.exposure.aggregate",),
]

DERIVED: list[tuple[str, ...]] = [
    ("srmp.ingest.fifa_calendar",),                               # stages the stored FIFA snapshot
    ("srmp.validation.proxy_gate",),
    ("srmp.index.composite",),
    ("srmp.index.proxy_led",),
    ("srmp.index.multisignal_compare",),
    ("srmp.index.figure",),
    ("srmp.experiments.sponsorship_monetization_v1",),          # adstocked exposure
    ("srmp.experiments.sponsorship_counterfactual_v1",),
    ("srmp.experiments.sponsorship_total_effect_v1",),            # headline estimate
    ("srmp.experiments.cobrand_placebo_v1",),
    ("srmp.experiments.world_cup_impact_v1",),
    ("srmp.experiments.stock_brand_response_v2",),
    ("srmp.experiments.brand_financial_bridge_v1",),
    ("srmp.experiments.market_implied_earnings_bridge_v1",),
    ("srmp.experiments.sponsorship_total_return_v3",),
    ("srmp.experiments.valuation_routes_v1",),
    ("srmp.experiments.brand_value_dominance_v1",),
    ("srmp.experiments.brand_value_dcf_v1",),
]


def run(steps: list[tuple[str, ...]]) -> None:
    for module, *args in steps:
        label = " ".join([module, *args])
        started = time.monotonic()
        print(f"== {label}", flush=True)
        subprocess.run([sys.executable, "-m", module, *args], check=True, stdout=subprocess.DEVNULL)
        print(f"   ok ({time.monotonic() - started:.0f}s)", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--with-pulls", action="store_true", help="refresh data sources before the derived steps")
    parser.add_argument("--tests", action="store_true", help="run pytest after the rebuild")
    parser.add_argument("--review", action="store_true", help="re-execute every review notebook after the rebuild")
    args = parser.parse_args()
    run((PULLS if args.with_pulls else []) + DERIVED)
    if args.review:
        subprocess.run([sys.executable, "-m", "srmp.review"], check=True)
    if args.tests:
        subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], check=True)
    print("PIPELINE_OK")


if __name__ == "__main__":
    main()
