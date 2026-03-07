import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "data.csv"
CHARTS_DIR = ROOT / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ── palette ──────────────────────────────────────────────────────────────────
PRIMARY   = "#1B4F8A"   # deep blue
ACCENT    = "#E8A020"   # amber
SOFT_BLUE = "#4A90D9"
LIGHT     = "#D0E4F7"
RED       = "#C0392B"
GREEN     = "#27AE60"
GREY      = "#95A5A6"

plt.rcParams.update({
    "font.family":    "DejaVu Sans",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.alpha":         0.3,
    "grid.linestyle":     "--",
    "figure.dpi":         150,
})

# ── load data ────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_FILE)
df["channel_count"] = df[["m10", "web", "mobile_ios", "mobile_android"]].sum(axis=1)


# ════════════════════════════════════════════════════════════════════════════
# CHART 1 – Merchant count per category (portfolio depth)
# ════════════════════════════════════════════════════════════════════════════
def chart_merchant_count():
    counts = df.groupby("category_name").size().sort_values(ascending=True)

    # assign colour: top-3 = accent, rest = primary
    colors = [ACCENT if i >= len(counts) - 3 else PRIMARY for i in range(len(counts))]

    fig, ax = plt.subplots(figsize=(11, 9))
    bars = ax.barh(counts.index, counts.values, color=colors, height=0.7, zorder=3)

    for bar, val in zip(bars, counts.values):
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", ha="left", fontsize=9, color="#333")

    # empty category annotation
    ax.axvline(0.5, color=RED, lw=1.2, ls=":", alpha=0.6)
    ax.set_xlabel("Number of merchants", fontsize=11)
    ax.set_title("Merchant Portfolio Depth by Category", fontsize=14, fontweight="bold", pad=14)
    ax.set_xlim(0, counts.max() * 1.12)
    ax.tick_params(axis="y", labelsize=9)
    ax.grid(axis="x", zorder=0)
    ax.set_axisbelow(True)

    # legend patches
    from matplotlib.patches import Patch
    legend = [Patch(color=ACCENT, label="Top 3 categories"),
              Patch(color=PRIMARY, label="Other categories")]
    ax.legend(handles=legend, loc="lower right", fontsize=9)

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "01_merchant_count_by_category.png", bbox_inches="tight")
    plt.close(fig)
    print("Chart 1 saved.")


# ════════════════════════════════════════════════════════════════════════════
# CHART 2 – M10 App coverage gap per category
# ════════════════════════════════════════════════════════════════════════════
def chart_m10_gap():
    agg = df.groupby("category_name").agg(
        total=("merchant_id", "count"),
        on_m10=("m10", "sum"),
    ).assign(web_only=lambda d: d["total"] - d["on_m10"])
    agg = agg.sort_values("web_only", ascending=True)

    # only show categories that have a gap OR are top in total
    agg_show = agg.copy()

    fig, ax = plt.subplots(figsize=(11, 9))
    y = np.arange(len(agg_show))

    ax.barh(y, agg_show["on_m10"],  color=PRIMARY,  height=0.6, label="Available on M10 app", zorder=3)
    ax.barh(y, agg_show["web_only"], left=agg_show["on_m10"],
            color=ACCENT, height=0.6, label="Web-only (not on M10 app)", zorder=3)

    for i, (_, row) in enumerate(agg_show.iterrows()):
        if row["web_only"] > 0:
            ax.text(row["total"] + 0.3, i,
                    f'{int(row["web_only"])} missing',
                    va="center", ha="left", fontsize=8.5, color=RED, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(agg_show.index, fontsize=9)
    ax.set_xlabel("Number of merchants", fontsize=11)
    ax.set_title("M10 App Coverage Gap by Category", fontsize=14, fontweight="bold", pad=14)
    ax.legend(loc="lower right", fontsize=9)
    ax.set_xlim(0, agg_show["total"].max() * 1.22)
    ax.set_axisbelow(True)
    ax.grid(axis="x", zorder=0)

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "02_m10_coverage_gap.png", bbox_inches="tight")
    plt.close(fig)
    print("Chart 2 saved.")


# ════════════════════════════════════════════════════════════════════════════
# CHART 3 – Omnichannel readiness rate per category
# ════════════════════════════════════════════════════════════════════════════
def chart_omnichannel_rate():
    agg = df.groupby("category_name").agg(
        total=("merchant_id", "count"),
        omni=("channel_count", lambda x: (x == 4).sum()),
    )
    agg["rate"] = agg["omni"] / agg["total"] * 100
    agg = agg.sort_values("rate", ascending=True)

    colors = [GREEN if r == 100 else (ACCENT if r >= 80 else RED) for r in agg["rate"]]

    fig, ax = plt.subplots(figsize=(11, 9))
    bars = ax.barh(agg.index, agg["rate"], color=colors, height=0.7, zorder=3)

    for bar, val in zip(bars, agg["rate"]):
        ax.text(min(val + 0.5, 101), bar.get_y() + bar.get_height() / 2,
                f"{val:.0f}%", va="center", ha="left", fontsize=9, color="#333")

    ax.axvline(100, color=GREEN, lw=1.5, ls="--", alpha=0.7, label="100% omnichannel")
    ax.axvline(80,  color=ACCENT, lw=1.2, ls=":",  alpha=0.7, label="80% threshold")
    ax.set_xlabel("% of merchants available on all 4 channels", fontsize=11)
    ax.set_title("Omnichannel Readiness Rate by Category\n(All 4 channels: M10, Web, iOS, Android)",
                 fontsize=14, fontweight="bold", pad=14)
    ax.set_xlim(0, 115)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.tick_params(axis="y", labelsize=9)
    ax.legend(fontsize=9, loc="lower right")
    ax.set_axisbelow(True)
    ax.grid(axis="x", zorder=0)

    from matplotlib.patches import Patch
    legend_patches = [
        Patch(color=GREEN, label="100% — fully integrated"),
        Patch(color=ACCENT, label="80–99% — near complete"),
        Patch(color=RED,   label="<80% — integration gap"),
    ]
    ax.legend(handles=legend_patches, fontsize=9, loc="lower right")

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "03_omnichannel_readiness.png", bbox_inches="tight")
    plt.close(fig)
    print("Chart 3 saved.")


# ════════════════════════════════════════════════════════════════════════════
# CHART 4 – Featured (homepage-promoted) merchants by category
# ════════════════════════════════════════════════════════════════════════════
def chart_featured_merchants():
    featured = df[df["row_number"] > 0]
    total_per_cat = df.groupby("category_name").size().rename("total")
    feat_per_cat  = featured.groupby("category_name").size().rename("featured")

    merged = pd.concat([total_per_cat, feat_per_cat], axis=1).fillna(0)
    merged["featured"] = merged["featured"].astype(int)
    merged["non_featured"] = merged["total"] - merged["featured"]
    merged = merged[merged["featured"] > 0].sort_values("featured", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(merged))

    ax.barh(y, merged["featured"],     color=ACCENT,   height=0.6, label="Featured / promoted",   zorder=3)
    ax.barh(y, merged["non_featured"], left=merged["featured"],
            color=LIGHT, height=0.6, label="Standard (not promoted)", zorder=3)

    for i, (_, row) in enumerate(merged.iterrows()):
        ax.text(row["total"] + 0.2, i, f'{row["featured"]} / {int(row["total"])}',
                va="center", ha="left", fontsize=8.5, color="#333")

    ax.set_yticks(y)
    ax.set_yticklabels(merged.index, fontsize=9)
    ax.set_xlabel("Number of merchants", fontsize=11)
    ax.set_title("Homepage-Promoted Merchants by Category\n(Featured = highlighted in main navigation)",
                 fontsize=14, fontweight="bold", pad=14)
    ax.legend(fontsize=9, loc="lower right")
    ax.set_xlim(0, merged["total"].max() * 1.2)
    ax.set_axisbelow(True)
    ax.grid(axis="x", zorder=0)

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "04_featured_merchants.png", bbox_inches="tight")
    plt.close(fig)
    print("Chart 4 saved.")


# ════════════════════════════════════════════════════════════════════════════
# CHART 5 – Platform channel reach (overall absolute comparison)
# ════════════════════════════════════════════════════════════════════════════
def chart_channel_reach():
    total = len(df)
    channels = {
        "Web Platform": df["web"].sum(),
        "iOS App":      df["mobile_ios"].sum(),
        "Android App":  df["mobile_android"].sum(),
        "M10 App":      df["m10"].sum(),
    }
    ch_df = pd.DataFrame({
        "channel": list(channels.keys()),
        "count":   list(channels.values()),
    }).sort_values("count", ascending=True)
    ch_df["pct"] = ch_df["count"] / total * 100
    ch_df["gap"] = total - ch_df["count"]

    colors = [RED if v < total else GREEN for v in ch_df["count"]]

    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.barh(ch_df["channel"], ch_df["count"], color=colors, height=0.5, zorder=3)

    for bar, val, pct in zip(bars, ch_df["count"], ch_df["pct"]):
        ax.text(val + 1, bar.get_y() + bar.get_height() / 2,
                f"{val}  ({pct:.1f}%)", va="center", ha="left", fontsize=10)

    ax.axvline(total, color=GREY, lw=1.5, ls="--", alpha=0.8, label=f"Total merchants ({total})")
    ax.set_xlabel("Merchants available on channel", fontsize=11)
    ax.set_title("Channel Reach Across All Merchants", fontsize=14, fontweight="bold", pad=14)
    ax.set_xlim(0, total * 1.18)
    ax.legend(fontsize=9)
    ax.set_axisbelow(True)
    ax.grid(axis="x", zorder=0)

    from matplotlib.patches import Patch
    legend_patches = [
        Patch(color=GREEN, label="Full coverage (100%)"),
        Patch(color=RED,   label="Partial coverage (gap exists)"),
    ]
    ax.legend(handles=legend_patches, fontsize=9, loc="lower right")

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "05_channel_reach_overall.png", bbox_inches="tight")
    plt.close(fig)
    print("Chart 5 saved.")


# ════════════════════════════════════════════════════════════════════════════
# CHART 6 – Category concentration: thin vs deep
# ════════════════════════════════════════════════════════════════════════════
def chart_category_concentration():
    counts = df.groupby("category_name").size().sort_values(ascending=False).reset_index()
    counts.columns = ["category", "merchants"]
    counts["cumulative_pct"] = counts["merchants"].cumsum() / counts["merchants"].sum() * 100
    counts["tier"] = pd.cut(
        counts["merchants"],
        bins=[0, 3, 10, 30, 200],
        labels=["Thin (1–3)", "Moderate (4–10)", "Developed (11–30)", "Dominant (30+)"],
    )

    tier_colors = {
        "Thin (1–3)":       RED,
        "Moderate (4–10)":  ACCENT,
        "Developed (11–30)": SOFT_BLUE,
        "Dominant (30+)":   PRIMARY,
    }
    bar_colors = [tier_colors[str(t)] for t in counts["tier"]]

    fig, ax1 = plt.subplots(figsize=(13, 6))
    ax2 = ax1.twinx()

    x = np.arange(len(counts))
    bars = ax1.bar(x, counts["merchants"], color=bar_colors, width=0.7, zorder=3)
    ax2.plot(x, counts["cumulative_pct"], color=GREY, lw=2, marker="o",
             markersize=4, label="Cumulative share", zorder=4)
    ax2.axhline(80, color=GREY, ls=":", lw=1.2, alpha=0.7)
    ax2.text(len(counts) - 0.5, 81, "80% threshold", ha="right", fontsize=8, color=GREY)

    ax1.set_xticks(x)
    ax1.set_xticklabels(counts["category"], rotation=45, ha="right", fontsize=8.5)
    ax1.set_ylabel("Merchant count", fontsize=11)
    ax2.set_ylabel("Cumulative % of all merchants", fontsize=11)
    ax1.set_title("Category Concentration — Merchant Distribution Across All Categories",
                  fontsize=14, fontweight="bold", pad=14)
    ax1.set_axisbelow(True)
    ax1.grid(axis="y", zorder=0)

    from matplotlib.patches import Patch
    legend_patches = [Patch(color=c, label=l) for l, c in tier_colors.items()]
    ax1.legend(handles=legend_patches, fontsize=8.5, loc="upper right")

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "06_category_concentration.png", bbox_inches="tight")
    plt.close(fig)
    print("Chart 6 saved.")


# ── run all ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    chart_merchant_count()
    chart_m10_gap()
    chart_omnichannel_rate()
    chart_featured_merchants()
    chart_channel_reach()
    chart_category_concentration()
    print(f"\nAll charts saved to: {CHARTS_DIR}")
