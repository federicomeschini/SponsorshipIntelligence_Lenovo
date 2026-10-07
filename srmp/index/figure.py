"""Brand Index figure: weekly brand share of attention with its 95% band (ADR-0040)."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ANNOUNCEMENT = pd.Timestamp("2024-10-21")   # first full week after the partnership announcement


def make_figure(weekly_path: str, output_path: str) -> None:
    weekly = pd.read_csv(weekly_path, parse_dates=["week"])

    fig, ax = plt.subplots(figsize=(13, 6))
    band = 1.96 * weekly["index_se"]
    ax.fill_between(weekly["week"], weekly["index_level"] - band, weekly["index_level"] + band,
                    color="#c7d5ea", alpha=0.55, linewidth=0, label="95% band (state uncertainty)")
    ax.plot(weekly["week"], weekly["index_level"], color="#2458a6", linewidth=1.8,
            label="Lenovo Brand Index")
    ax.axhline(100.0, color="#999999", linewidth=0.8, linestyle=":")
    ax.axvline(ANNOUNCEMENT, color="#1c2b3a", linewidth=0.8, linestyle="--", label="FIFA partnership announced")

    ax.set_title("Lenovo Brand Index - brand share of attention against rivals",
                 fontsize=16, fontweight="bold", loc="left", color="#1c2b3a", pad=30)
    ax.text(0.0, 1.03, "Weekly factor model of Google share of search, informed by quarterly GWI engagement and "
                       "consideration; 100 = pre-announcement average.",
            transform=ax.transAxes, fontsize=10, color="#5a6a7a")
    ax.set_ylabel("Index (100 = pre-announcement average)")
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
    parser.add_argument("--output", default="reports/figures/brand_index.png")
    args = parser.parse_args()
    make_figure(args.weekly, args.output)
