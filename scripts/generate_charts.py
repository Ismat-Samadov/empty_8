"""
FutureLearn Business Intelligence — Chart Generator
Produces all charts for the executive insight report.
Run: python scripts/generate_charts.py
"""

import csv
import collections
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_PATH   = Path(__file__).parent.parent / "data" / "data.csv"
CHARTS_DIR  = Path(__file__).parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# ── Brand palette ─────────────────────────────────────────────────────────────
PRIMARY   = "#1D3557"   # deep navy
ACCENT    = "#E63946"   # FutureLearn red
HIGHLIGHT = "#457B9D"   # steel blue
NEUTRAL   = "#A8DADC"   # light teal
GOLD      = "#F4A261"   # warm orange

PALETTE_CAT = [PRIMARY, HIGHLIGHT, NEUTRAL, GOLD, ACCENT,
               "#2A9D8F", "#E9C46A", "#264653", "#8ECAE6", "#95D5B2"]

# ── Global style ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "axes.edgecolor":   "#CCCCCC",
    "axes.grid":        True,
    "grid.color":       "#EEEEEE",
    "grid.linewidth":   0.8,
    "font.family":      "DejaVu Sans",
    "font.size":        11,
    "axes.titlesize":   14,
    "axes.titleweight": "bold",
    "axes.labelsize":   11,
    "xtick.labelsize":  10,
    "ytick.labelsize":  10,
    "legend.fontsize":  10,
})

def save(fig, name: str) -> None:
    path = CHARTS_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")

# ── Load data ─────────────────────────────────────────────────────────────────
with open(DATA_PATH, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded {len(rows)} courses.\n")

# Helper: safe int / float
def to_float(v):
    try: return float(v)
    except: return None

def to_int(v):
    try: return int(v)
    except: return None

# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — Course Volume vs Average Enrollment by Category
#           Dual-axis horizontal bar: volume (left) + avg enrollment (right)
# ─────────────────────────────────────────────────────────────────────────────
cat_volume   = collections.Counter(r["category"] for r in rows if r["category"])
cat_enroll   = collections.defaultdict(list)
for r in rows:
    if r["category"] and r["enrolled_count"]:
        cat_enroll[r["category"]].append(int(r["enrolled_count"]))

# Keep categories with >= 5 courses
cats = [c for c, n in cat_volume.most_common() if n >= 5]
volumes  = [cat_volume[c] for c in cats]
avg_enr  = [int(sum(cat_enroll[c]) / len(cat_enroll[c])) if cat_enroll[c] else 0 for c in cats]

# Sort by avg enrollment
order = sorted(range(len(cats)), key=lambda i: avg_enr[i])
cats_s = [cats[i] for i in order]
vol_s  = [volumes[i] for i in order]
enr_s  = [avg_enr[i] for i in order]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
fig.suptitle("Category Overview: Course Volume vs Learner Demand", fontsize=16, fontweight="bold", y=1.01)

y = np.arange(len(cats_s))

# Left: volume
bars1 = ax1.barh(y, vol_s, color=PRIMARY, height=0.6)
ax1.set_yticks(y)
ax1.set_yticklabels(cats_s, fontsize=9)
ax1.set_xlabel("Number of Courses")
ax1.set_title("Courses Offered")
ax1.invert_xaxis()
ax1.yaxis.set_label_position("right")
for bar, v in zip(bars1, vol_s):
    ax1.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
             str(v), va="center", ha="right", fontsize=8, color=PRIMARY)

# Right: avg enrollment
bars2 = ax2.barh(y, enr_s, color=HIGHLIGHT, height=0.6)
ax2.set_yticks(y)
ax2.set_yticklabels([], fontsize=9)
ax2.set_xlabel("Avg Learners per Course")
ax2.set_title("Avg Learner Demand")
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
for bar, v in zip(bars2, enr_s):
    if v > 0:
        ax2.text(bar.get_width() + 100, bar.get_y() + bar.get_height()/2,
                 f"{v:,}", va="center", ha="left", fontsize=8, color=HIGHLIGHT)

fig.tight_layout()
save(fig, "01_category_volume_vs_demand.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 — Free vs Paid: Enrollment Comparison
# ─────────────────────────────────────────────────────────────────────────────
paid_enroll = [int(r["enrolled_count"]) for r in rows
               if r["enrolled_count"] and r["price"] and to_float(r["price"]) and to_float(r["price"]) > 0]
free_enroll = [int(r["enrolled_count"]) for r in rows
               if r["enrolled_count"] and (not r["price"] or to_float(r["price"]) == 0)]

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Free vs Paid Courses: Enrollment & Revenue Opportunity", fontsize=15, fontweight="bold")

# Sub-chart A: avg enrollment
labels = ["Free Courses\n(870 total)", "Paid Courses\n(130 total)"]
avgs   = [int(sum(free_enroll) / len(free_enroll)), int(sum(paid_enroll) / len(paid_enroll))]
colors = [NEUTRAL, ACCENT]
bars   = axes[0].bar(labels, avgs, color=colors, width=0.5, edgecolor="white", linewidth=1.5)
axes[0].set_ylabel("Avg Learners per Course")
axes[0].set_title("Average Enrollment")
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
for bar, v in zip(bars, avgs):
    axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 300,
                 f"{v:,}", ha="center", va="bottom", fontweight="bold", fontsize=12)
axes[0].set_ylim(0, max(avgs) * 1.2)
axes[0].grid(axis="x", visible=False)

# Sub-chart B: enrollment buckets (free vs paid stacked)
buckets = ["< 1K", "1K–5K", "5K–20K", "20K–50K", "> 50K"]
def bucket(n):
    if n < 1000:   return 0
    if n < 5000:   return 1
    if n < 20000:  return 2
    if n < 50000:  return 3
    return 4

free_b = collections.Counter(bucket(n) for n in free_enroll)
paid_b = collections.Counter(bucket(n) for n in paid_enroll)

x = np.arange(len(buckets))
w = 0.35
axes[1].bar(x - w/2, [free_b[i] for i in range(5)], width=w, color=NEUTRAL, label="Free", edgecolor="white")
axes[1].bar(x + w/2, [paid_b[i] for i in range(5)], width=w, color=ACCENT,  label="Paid", edgecolor="white")
axes[1].set_xticks(x)
axes[1].set_xticklabels(buckets)
axes[1].set_ylabel("Number of Courses")
axes[1].set_title("Enrollment Distribution")
axes[1].legend()
axes[1].grid(axis="x", visible=False)

fig.tight_layout()
save(fig, "02_free_vs_paid_enrollment.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 — Price Point Strategy
# ─────────────────────────────────────────────────────────────────────────────
priced_rows = [r for r in rows if r["price"] and to_float(r["price"]) and to_float(r["price"]) > 0]
price_counter = collections.Counter(str(int(to_float(r["price"]))) for r in priced_rows)
price_enroll  = collections.defaultdict(list)
for r in priced_rows:
    if r["enrolled_count"]:
        price_enroll[str(int(to_float(r["price"])))].append(int(r["enrolled_count"]))

price_labels = sorted(price_counter.keys(), key=int)
price_counts = [price_counter[p] for p in price_labels]
price_avg_enr = [int(sum(price_enroll[p])/len(price_enroll[p])) if price_enroll[p] else 0
                 for p in price_labels]
price_labels_disp = [f"£{p}" for p in price_labels]

fig, ax1 = plt.subplots(figsize=(10, 5))
fig.suptitle("Price Point Strategy: Volume & Learner Response", fontsize=15, fontweight="bold")

x = np.arange(len(price_labels_disp))
bars = ax1.bar(x, price_counts, color=PRIMARY, width=0.5, label="# Courses")
ax1.set_xticks(x)
ax1.set_xticklabels(price_labels_disp)
ax1.set_ylabel("Number of Courses", color=PRIMARY)
ax1.set_xlabel("Price Point")
ax1.grid(axis="x", visible=False)
for bar, v in zip(bars, price_counts):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
             str(v), ha="center", va="bottom", fontsize=10, color=PRIMARY, fontweight="bold")

ax2 = ax1.twinx()
ax2.plot(x, price_avg_enr, color=GOLD, marker="o", linewidth=2.5,
         markersize=8, label="Avg Enrollment")
ax2.set_ylabel("Avg Learners per Course", color=GOLD)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
for xi, v in zip(x, price_avg_enr):
    if v > 0:
        ax2.text(xi, v + 500, f"{v:,}", ha="center", fontsize=8, color=GOLD)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
fig.tight_layout()
save(fig, "03_price_point_strategy.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 4 — Duration Sweet Spot (Avg Enrollment by Course Length)
# ─────────────────────────────────────────────────────────────────────────────
dur_enroll = collections.defaultdict(list)
dur_count  = collections.Counter()
for r in rows:
    if r["duration_weeks"]:
        dur_count[int(r["duration_weeks"])] += 1
        if r["enrolled_count"]:
            dur_enroll[int(r["duration_weeks"])].append(int(r["enrolled_count"]))

dur_keys = sorted(dur_enroll.keys())
dur_avgs = [int(sum(dur_enroll[d])/len(dur_enroll[d])) for d in dur_keys]
dur_cnts = [dur_count[d] for d in dur_keys]
dur_labels = [f"{d}w" for d in dur_keys]

fig, ax1 = plt.subplots(figsize=(11, 5))
fig.suptitle("Optimal Course Length: Duration vs Learner Engagement", fontsize=15, fontweight="bold")

x = np.arange(len(dur_labels))
bars = ax1.bar(x, dur_cnts, color=HIGHLIGHT, width=0.5, alpha=0.8, label="# Courses offered")
ax1.set_xticks(x)
ax1.set_xticklabels(dur_labels)
ax1.set_ylabel("Number of Courses", color=HIGHLIGHT)
ax1.grid(axis="x", visible=False)

ax2 = ax1.twinx()
ax2.plot(x, dur_avgs, color=ACCENT, marker="o", linewidth=2.5, markersize=9, label="Avg Enrollment")
ax2.set_ylabel("Avg Learners per Course", color=ACCENT)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
for xi, v in zip(x, dur_avgs):
    ax2.text(xi, v + 200, f"{v:,}", ha="center", fontsize=9, color=ACCENT, fontweight="bold")

lines1, l1 = ax1.get_legend_handles_labels()
lines2, l2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, l1 + l2, loc="upper right")
ax1.set_xlabel("Course Duration")
fig.tight_layout()
save(fig, "04_duration_sweet_spot.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 5 — Top Partners: Total Reach vs Efficiency
# ─────────────────────────────────────────────────────────────────────────────
partner_enroll = collections.defaultdict(list)
partner_count  = collections.Counter()
for r in rows:
    if r["partner"]:
        partner_count[r["partner"]] += 1
        if r["enrolled_count"]:
            partner_enroll[r["partner"]].append(int(r["enrolled_count"]))

# Top 12 by total enrollment
partner_totals = {p: sum(v) for p, v in partner_enroll.items() if len(v) >= 2}
top_partners   = sorted(partner_totals.items(), key=lambda x: -x[1])[:12]
top_names  = [p for p, _ in top_partners]
top_totals = [t for _, t in top_partners]
top_avgs   = [int(sum(partner_enroll[p]) / len(partner_enroll[p])) for p in top_names]
top_n      = [len(partner_enroll[p]) for p in top_names]

# Sort by total
order = sorted(range(len(top_names)), key=lambda i: top_totals[i])
snames  = [top_names[i] for i in order]
stotals = [top_totals[i] for i in order]
savgs   = [top_avgs[i] for i in order]
sn      = [top_n[i] for i in order]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle("Partner Performance: Total Reach vs Per-Course Efficiency", fontsize=15, fontweight="bold")

y = np.arange(len(snames))
short_names = [n[:28] for n in snames]

# Total reach
bars1 = ax1.barh(y, stotals, color=PRIMARY, height=0.6)
ax1.set_yticks(y)
ax1.set_yticklabels(short_names, fontsize=9)
ax1.set_xlabel("Total Learners Enrolled")
ax1.set_title("Total Reach")
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v/1000):,}K"))
for bar, v in zip(bars1, stotals):
    ax1.text(bar.get_width() * 0.98, bar.get_y() + bar.get_height()/2,
             f"{v:,}", va="center", ha="right", fontsize=8, color="white", fontweight="bold")

# Avg per course
bars2 = ax2.barh(y, savgs, color=GOLD, height=0.6)
ax2.set_yticks(y)
ax2.set_yticklabels([], fontsize=9)
ax2.set_xlabel("Avg Learners per Course")
ax2.set_title("Per-Course Efficiency")
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
for bar, v in zip(bars2, savgs):
    ax2.text(bar.get_width() + 200, bar.get_y() + bar.get_height()/2,
             f"{v:,}", va="center", ha="left", fontsize=8, color=GOLD, fontweight="bold")

fig.tight_layout()
save(fig, "05_partner_performance.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 6 — Level Strategy: Volume, Enrollment, and Price
# ─────────────────────────────────────────────────────────────────────────────
level_map = {
    "Introductory level": "Introductory",
    "Intermediate level": "Intermediate",
    "Advanced level":     "Advanced",
}
lv_count   = collections.Counter()
lv_enroll  = collections.defaultdict(list)
lv_price   = collections.defaultdict(list)

for r in rows:
    if r["level"] and r["level"] in level_map:
        lv = level_map[r["level"]]
        lv_count[lv] += 1
        if r["enrolled_count"]:
            lv_enroll[lv].append(int(r["enrolled_count"]))
        if r["price"] and to_float(r["price"]) and to_float(r["price"]) > 0:
            lv_price[lv].append(to_float(r["price"]))

lvls   = ["Introductory", "Intermediate", "Advanced"]
counts = [lv_count[l] for l in lvls]
avgenr = [int(sum(lv_enroll[l])/len(lv_enroll[l])) if lv_enroll[l] else 0 for l in lvls]
avgpri = [round(sum(lv_price[l])/len(lv_price[l]), 1) if lv_price[l] else 0 for l in lvls]

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Difficulty Level Strategy: Supply, Demand & Pricing", fontsize=15, fontweight="bold")

colors_lv = [NEUTRAL, HIGHLIGHT, PRIMARY]

for ax, vals, title, ylabel, fmt in zip(
    axes,
    [counts, avgenr, avgpri],
    ["Courses Offered", "Avg Learner Enrollment", "Avg Price (£)"],
    ["Number of Courses", "Avg Learners", "Price (£)"],
    ["{:,.0f}", "{:,.0f}", "£{:,.0f}"]
):
    bars = ax.bar(lvls, vals, color=colors_lv, width=0.5, edgecolor="white", linewidth=1.5)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.grid(axis="x", visible=False)
    for bar, v in zip(bars, vals):
        label = fmt.format(v)
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*0.02,
                label, ha="center", va="bottom", fontweight="bold", fontsize=11)

fig.tight_layout()
save(fig, "06_level_strategy.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 7 — Quality Leaders: Avg Rating by Category
# ─────────────────────────────────────────────────────────────────────────────
cat_ratings = collections.defaultdict(list)
for r in rows:
    if r["category"] and r["rating"]:
        cat_ratings[r["category"]].append(float(r["rating"]))

# Only categories with >= 3 rated courses
cat_avg_r = {c: sum(v)/len(v) for c, v in cat_ratings.items() if len(v) >= 3}
cat_avg_r_sorted = sorted(cat_avg_r.items(), key=lambda x: x[1])

labels_r = [c for c, _ in cat_avg_r_sorted]
values_r  = [v for _, v in cat_avg_r_sorted]
n_rated   = [len(cat_ratings[c]) for c in labels_r]

fig, ax = plt.subplots(figsize=(11, 6))
fig.suptitle("Learner Satisfaction by Category (Avg Star Rating)", fontsize=15, fontweight="bold")

bar_colors = [ACCENT if v == max(values_r) else HIGHLIGHT for v in values_r]
bars = ax.barh(labels_r, values_r, color=bar_colors, height=0.6)
ax.set_xlim(4.2, 4.9)
ax.set_xlabel("Average Star Rating")
ax.axvline(x=sum(values_r)/len(values_r), color=GOLD, linestyle="--", linewidth=1.5, label=f"Overall avg ({sum(values_r)/len(values_r):.2f})")
ax.legend()
for bar, v, n in zip(bars, values_r, n_rated):
    ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
            f"{v:.2f}  ({n} reviews)", va="center", fontsize=9)

fig.tight_layout()
save(fig, "07_rating_by_category.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 8 — High-Value Segments: Quadrant (Enrollment × Rating)
# ─────────────────────────────────────────────────────────────────────────────
# Aggregate by category: avg_enroll vs avg_rating vs volume
quad_data = []
for cat in cat_avg_r:
    enr = cat_enroll.get(cat, [])
    if not enr: continue
    avg_e = sum(enr)/len(enr)
    avg_r = cat_avg_r[cat]
    vol   = cat_volume[cat]
    quad_data.append((cat, avg_e, avg_r, vol))

fig, ax = plt.subplots(figsize=(11, 7))
fig.suptitle("Strategic Opportunity Map: Satisfaction vs Learner Demand", fontsize=15, fontweight="bold")

xs = [d[1] for d in quad_data]
ys = [d[2] for d in quad_data]
sz = [d[3] * 8 for d in quad_data]   # bubble size ∝ volume
lbls = [d[0] for d in quad_data]

scatter = ax.scatter(xs, ys, s=sz, c=HIGHLIGHT, alpha=0.65, edgecolors=PRIMARY, linewidths=1.2)

# Quadrant lines
med_x = statistics.median(xs)
med_y = statistics.median(ys)
ax.axvline(x=med_x, color="#CCCCCC", linestyle="--", linewidth=1)
ax.axhline(y=med_y, color="#CCCCCC", linestyle="--", linewidth=1)

for cat, xe, yr, vol in quad_data:
    ax.annotate(cat, (xe, yr), fontsize=8.5, ha="center",
                xytext=(0, 9), textcoords="offset points", color=PRIMARY)

ax.set_xlabel("Avg Learners per Course (Demand)")
ax.set_ylabel("Avg Star Rating (Satisfaction)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax.set_title("Bubble size = number of courses offered")

# Quadrant labels
ax.text(max(xs)*0.75, min(ys) + 0.01, "High Demand\nLower Satisfaction", fontsize=8,
        color="#888888", ha="center")
ax.text(max(xs)*0.75, max(ys) - 0.01, "STAR PERFORMERS", fontsize=9,
        color=ACCENT, ha="center", fontweight="bold")
ax.text(min(xs) + 500, min(ys) + 0.01, "Niche / At Risk", fontsize=8, color="#888888")
ax.text(min(xs) + 500, max(ys) - 0.01, "High Satisfaction\nLow Demand", fontsize=8, color="#888888")

fig.tight_layout()
save(fig, "08_opportunity_map.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 9 — Top 15 Courses by Enrollment (Individual Stars)
# ─────────────────────────────────────────────────────────────────────────────
top_courses = sorted(
    [(r["title"], int(r["enrolled_count"]), r["partner"], r.get("category",""))
     for r in rows if r["enrolled_count"]],
    key=lambda x: -x[1]
)[:15]

top_courses_rev = list(reversed(top_courses))
ttitles  = [f"{t[:42]}…" if len(t) > 42 else t for t, *_ in top_courses_rev]
tenrolls = [e for _, e, *_ in top_courses_rev]
tpartner = [p for _, _, p, *_ in top_courses_rev]

fig, ax = plt.subplots(figsize=(13, 8))
fig.suptitle("Top 15 Courses by Total Enrollment", fontsize=15, fontweight="bold")

colors_tc = [ACCENT if e == max(tenrolls) else PRIMARY for e in tenrolls]
bars = ax.barh(range(len(ttitles)), tenrolls, color=colors_tc, height=0.65)
ax.set_yticks(range(len(ttitles)))
ax.set_yticklabels(ttitles, fontsize=9)
ax.set_xlabel("Total Learners Enrolled")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v/1000):.0f}K"))
for bar, v, partner in zip(bars, tenrolls, tpartner):
    ax.text(bar.get_width() + 2000, bar.get_y() + bar.get_height()/2,
            f"{v:,}  |  {partner[:22]}", va="center", fontsize=8, color=PRIMARY)

ax.set_xlim(0, max(tenrolls) * 1.45)
fig.tight_layout()
save(fig, "09_top_courses_enrollment.png")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 10 — Paid Course Rating vs Enrollment (Premium Value Proof)
# ─────────────────────────────────────────────────────────────────────────────
paid_scatter = [
    (float(r["rating"]), int(r["enrolled_count"]), float(r["price"]), r["title"][:30])
    for r in rows
    if r["rating"] and r["enrolled_count"] and r["price"] and to_float(r["price"]) and to_float(r["price"]) > 0
]

if paid_scatter:
    px = [d[0] for d in paid_scatter]
    py = [d[1] for d in paid_scatter]
    pp = [d[2] for d in paid_scatter]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("Premium Course Quality: Rating vs Enrollment (Paid Courses Only)", fontsize=14, fontweight="bold")

    sc = ax.scatter(px, py, c=pp, cmap="YlOrRd", s=80, alpha=0.8, edgecolors="#555", linewidths=0.5)
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Price (£)", fontsize=10)
    ax.set_xlabel("Star Rating")
    ax.set_ylabel("Total Learners Enrolled")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.set_xlim(4.1, 5.05)

    # Trend line
    z = np.polyfit(px, py, 1)
    p_fn = np.poly1d(z)
    xline = np.linspace(min(px), max(px), 100)
    ax.plot(xline, p_fn(xline), color=ACCENT, linestyle="--", linewidth=1.5, label="Trend")
    ax.legend()

    fig.tight_layout()
    save(fig, "10_premium_quality_enrollment.png")

print("\nAll charts generated successfully.")
print(f"Output directory: {CHARTS_DIR}")
