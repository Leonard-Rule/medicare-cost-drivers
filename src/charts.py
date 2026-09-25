"""README charts from output/*.csv (run src/run_pipeline.py first).
Colors: validated categorical palette, fixed order by service category so a category keeps its color."""
import pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
CATS = ["Inpatient Hospital", "Outpatient Hospital", "Professional", "Long-Term Care", "Retail Pharmacy", "Other"]
COLORS = dict(zip(CATS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
money = FuncFormatter(lambda v, _: f"${v:,.0f}")

def style(ax):
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.tick_params(length=0)

# 1. PMPM by service category, stacked by year
p = pd.read_csv(OUT / "pmpm_by_category.csv").pivot(index="yr", columns="service_category", values="pmpm")[CATS]
fig, ax = plt.subplots(figsize=(9, 5.2))
bottom = pd.Series(0.0, index=p.index)
for c in CATS:
    ax.bar(p.index, p[c], bottom=bottom, width=0.62, color=COLORS[c], label=c,
           edgecolor=SURFACE, linewidth=2)
    bottom += p[c]
for yr, tot in bottom.items():
    ax.text(yr, tot + 25, f"${tot:,.0f}", ha="center", va="bottom", color=INK, fontsize=9)
style(ax); ax.yaxis.set_major_formatter(money); ax.set_ylim(0, bottom.max() * 1.1)
ax.set_title("Allowed PMPM by Peterson-Milbank service category, 2016–2022", loc="left", color=INK, fontsize=12, pad=26)
ax.text(0, 1.02, "CMS synthetic Medicare FFS claims · methods demo, dollar levels are not realistic",
        transform=ax.transAxes, color=INK2, fontsize=9)
ax.legend(ncol=3, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.07), labelcolor=INK2)
fig.tight_layout(); fig.savefig(OUT / "charts" / "pmpm_by_category.png", dpi=160); plt.close(fig)

# 2. What drove the change: PMPM change 2016 -> 2022 by category
d = (p.loc[2022] - p.loc[2016]).reindex(CATS).sort_values()
fig, ax = plt.subplots(figsize=(9, 4))
ax.barh(d.index, d.values, color=[COLORS[c] for c in d.index], height=0.6)
for i, (c, v) in enumerate(d.items()):
    sign = "" if round(v) == 0 else ("+" if v > 0 else "−")
    ax.text(v + (4 if v >= 0 else -4), i, f"{sign}${abs(v):,.0f}",
            va="center", ha="left" if v >= 0 else "right", color=INK, fontsize=9)
ax.axvline(0, color=INK2, linewidth=0.8)
ax.spines[["top", "right", "left", "bottom"]].set_visible(False); ax.tick_params(length=0)
ax.xaxis.set_major_formatter(money); ax.grid(axis="x", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
tot = d.sum()
ax.set_title(f"Change in allowed PMPM, 2016 to 2022 (total {'+' if tot >= 0 else '−'}${abs(tot):,.0f})",
             loc="left", color=INK, fontsize=12)
ax.set_xlim(min(d.min(), 0) - 40, d.max() + 45)
fig.tight_layout(); fig.savefig(OUT / "charts" / "pmpm_change_by_category.png", dpi=160); plt.close(fig)
print("wrote", *sorted(p.name for p in (OUT / "charts").glob("*.png")))
