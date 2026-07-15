"""Brand Index figure: proxy-led weekly series and GWI calibration waves."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def make_figure(weekly_path: str, composite_path: str, output_path: str) -> None:
    weekly = pd.read_csv(weekly_path, parse_dates=["week"])
    composite = pd.read_csv(composite_path, parse_dates=["fieldwork_midpoint"])
    composite = composite[composite["fieldwork_midpoint"] >= weekly["week"].min()]

    fig, ax = plt.subplots(figsize=(13, 6))
    band = 1.96 * weekly["index_se"]
    ax.fill_between(weekly["week"], weekly["index_level"] - band, weekly["index_level"] + band,
                    color="#c7d5ea", alpha=0.55, linewidth=0, label="95% CI")
    ax.plot(weekly["week"], weekly["index_level"], color="#2458a6", linewidth=1.8,
            label="Weekly proxy-led index")
    ax.scatter(composite["fieldwork_midpoint"], composite["composite_index"],
               color="#1d4d94", zorder=5, s=28, label="GWI calibration composite")
    ax.axhline(100.0, color="#999999", linewidth=0.8, linestyle=":")

    ax.set_title("Lenovo Brand Salience Index - weekly proxy-led series (provisional)",
                 fontsize=16, fontweight="bold", loc="left", color="#1c2b3a", pad=30)
    ax.text(0.0, 1.03, "Lenovo Google Trends drives weekly movement; GWI survey waves (dots) "
                       "calibrate the display scale; band = mapping uncertainty.",
            transform=ax.transAxes, fontsize=10, color="#5a6a7a")
    ax.set_ylabel("Brand Index (mean 100, sd 15)")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly", default="data/curated/index/brand_index_weekly.csv")
    parser.add_argument("--composite", default="data/curated/index/brand_index_composite_quarterly.csv")
    parser.add_argument("--output", default="reports/figures/brand_index.png")
    args = parser.parse_args()
    make_figure(args.weekly, args.composite, args.output)
