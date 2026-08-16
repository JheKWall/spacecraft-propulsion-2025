"""The four output pages.

Design notes
------------
Every metric in this dataset is a RANGE, not a point, so the marks are ranges:
a bar from low to high with a dot at each end, collapsing to a single dot where
a source published one number. Drawing a bar to a single value would assert a
precision the sources do not support.

Scales are logarithmic on all four pages because the data spans five orders of
magnitude (202 s to 10,000,000 s on specific impulse). That is itself part of
the finding and it is annotated rather than hidden.

Colour encodes MATURITY, never rank. Three levels map to the first three slots
of the validated categorical palette - the three that clear the all-pairs CVD
and normal-vision floors in both modes. Identity is never carried by colour
alone: every chart is directly labelled and legended.
"""
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from config import CHARTS_DIR, PROCESSED_DIR

# --- palette (validated: node scripts/validate_palette.js, all checks pass) ---
MATURITY_COLOR = {
    "proven": "#2a78d6",       # slot 1, blue
    "prototype": "#eb6834",    # slot 2, orange
    "theoretical": "#1baf7a",  # slot 3, aqua
}
MATURITY_ORDER = ["proven", "prototype", "theoretical"]

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_2,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": INK_2,
    "grid.color": GRID,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _style(ax, xlabel=None, title=None, subtitle=None):
    ax.grid(axis="x", linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, color=INK_2, labelpad=8)
    # Positioned in offset POINTS from the axes corner rather than axes fractions,
    # so the gap between title and subtitle stays constant regardless of figure
    # height. Axes fractions collide on short figures.
    if title:
        ax.annotate(title, xy=(0, 1), xycoords="axes fraction",
                    xytext=(0, 34), textcoords="offset points",
                    fontsize=14, color=INK, fontweight="bold", va="bottom", ha="left")
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1), xycoords="axes fraction",
                    xytext=(0, 13), textcoords="offset points",
                    fontsize=9.5, color=INK_2, va="bottom", ha="left")


def _range_marks(ax, y, low, high, color):
    """A range as a bar with end dots; a single dot when low == high."""
    if pd.isna(low) or pd.isna(high):
        return
    if high > low:
        ax.plot([low, high], [y, y], color=color, linewidth=5, solid_capstyle="round",
                zorder=3)
        ax.plot([low, high], [y, y], "o", color=color, markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    else:
        ax.plot([low], [y], "o", color=color, markersize=9,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)


def _legend(ax, levels, loc="lower right"):
    handles = [Line2D([], [], color=MATURITY_COLOR[m], marker="o", linestyle="-",
                      linewidth=4, markersize=8, label=m.capitalize())
               for m in MATURITY_ORDER if m in levels]
    ax.legend(handles=handles, loc=loc, frameon=True, facecolor=SURFACE,
              edgecolor=GRID, fontsize=9.5, title="Maturity",
              title_fontsize=9.5, labelcolor=INK_2)


def _fmt(v):
    """Two significant figures below 1, whole numbers above 10.

    Deliberately coarse: these are ranges drawn from published sources, and
    printing 0.05236 asserts a precision no source claims.
    """
    if v >= 10:
        return f"{v:,.0f}"
    if v >= 1:
        return f"{v:.1f}"
    return f"{v:.2g}"


# ---------------------------------------------------------------- page 1

def page1_all_systems_isp(df):
    d = df[df["isp_high"].notna()].sort_values("isp_high")
    fig, ax = plt.subplots(figsize=(11, 7.5))

    for i, (_, r) in enumerate(d.iterrows()):
        _range_marks(ax, i, r["isp_low"], r["isp_high"], MATURITY_COLOR[r["maturity"]])
        label = _fmt(r["isp_high"])
        if r["isp_high"] > r["isp_low"]:
            label = f"{_fmt(r['isp_low'])}–{label}"
        ax.text(r["isp_high"] * 1.35, i, label, va="center", fontsize=8.5, color=INK_2)

    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["name"], fontsize=10)
    ax.set_xscale("log")
    ax.set_xlim(100, 4e8)
    ax.set_ylim(-0.8, len(d) - 0.2)

    _style(ax, "Specific impulse (seconds, log scale)",
           "Specific impulse across all 15 systems",
           "The original comparison — and why ranking on it alone misleads. "
           "The top two systems have never been built.")
    _legend(ax, set(d["maturity"]), loc="lower right")

    fig.text(0.01, 0.015,
             "Nuclear figures rest on a more favourable basis than chemical ones: Pewee's "
             "is ideal-vacuum (calculated, infinite nozzle expansion, no losses),\nagainst "
             "delivered performance for the chemical engines. The nuclear advantage is real; "
             "these numbers overstate it. See docs/data-collection.md §7.",
             fontsize=7.5, color=MUTED, va="bottom")

    fig.tight_layout(rect=[0, 0.075, 1, 1])
    fig.savefig(CHARTS_DIR / "01_all_systems_isp.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- page 2

def page2_chemical_tw(df):
    d = df[(df["category"] == "chemical") & (df["tw_low"].notna())]
    d = d.sort_values("tw_high")
    excluded = df[(df["category"] == "chemical") & (df["tw_low"].isna())]["name"].tolist()

    fig, ax = plt.subplots(figsize=(11, 5.6))

    for i, (_, r) in enumerate(d.iterrows()):
        _range_marks(ax, i, r["tw_low"], r["tw_high"], MATURITY_COLOR[r["maturity"]])
        label = _fmt(r["tw_high"])
        if r["tw_high"] > r["tw_low"]:
            label = f"{_fmt(r['tw_low'])}–{label}"
        ax.text(r["tw_high"] * 1.25, i, label, va="center", fontsize=9, color=INK_2)

    ax.axvline(1.0, color="#d03b3b", linewidth=1.5, linestyle="--", zorder=2)
    ax.annotate("T/W = 1", xy=(1.0, 1), xycoords=("data", "axes fraction"),
                xytext=(8, -18), textcoords="offset points",
                color="#d03b3b", fontsize=9.5, fontweight="bold", va="top")
    ax.annotate("left of this line an engine cannot lift its own weight",
                xy=(1.0, 1), xycoords=("data", "axes fraction"),
                xytext=(8, -33), textcoords="offset points",
                color="#d03b3b", fontsize=8.5, va="top")

    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["name"], fontsize=10)
    ax.set_xscale("log")
    ax.set_xlim(0.02, 400)
    ax.set_ylim(-0.7, len(d) - 0.2)

    _style(ax, "Thrust-to-weight ratio (log scale)",
           "Chemical propulsion — the only category that can leave the ground",
           "But not all of it. The MR-103J is an attitude thruster: chemical, "
           "flight-proven, and unable to lift itself.")

    note = ("Excluded: " + ", ".join(excluded) +
            " — thrust and specific impulse are published, but no engine mass is available "
            "from any Tier 1/2 source,\nso thrust-to-weight cannot be computed. "
            "Across the whole dataset, 12 systems have a citable thrust and only 8 a "
            "citable mass.")
    fig.text(0.01, 0.015, note, fontsize=7.5, color=MUTED, va="bottom")

    fig.tight_layout(rect=[0, 0.10, 1, 1])
    fig.savefig(CHARTS_DIR / "02_chemical_tw.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- page 3

def page3_electric_power_thrust(df):
    d = df[(df["category"] == "electric") & df["input_power_low"].notna()
           & df["thrust_low"].notna()].sort_values("input_power_high")

    # Hand-placed labels. The five throttle lines converge in the middle of the
    # plot, so a uniform offset stacks four labels on top of each other. With
    # only five series, placing each one is more reliable than any rule.
    # name -> (which end to anchor, dx, dy, horizontal alignment)
    LABELS = {
        "NEXT-C":   ("high", 10, 2, "left"),
        "NSTAR":    ("high", 10, -12, "left"),
        "SPT-100":  ("high", 8, 9, "left"),
        "PPS-1350": ("low", -10, 6, "right"),
        "BHT-600":  ("low", -10, -6, "right"),
    }

    fig, ax = plt.subplots(figsize=(11, 6.4))
    color = MATURITY_COLOR["proven"]

    for _, r in d.iterrows():
        ax.plot([r["input_power_low"], r["input_power_high"]],
                [r["thrust_low"], r["thrust_high"]],
                color=color, linewidth=3.5, solid_capstyle="round", alpha=0.85, zorder=3)
        ax.plot([r["input_power_low"], r["input_power_high"]],
                [r["thrust_low"], r["thrust_high"]], "o", color=color, markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)

        anchor, dx, dy, ha = LABELS.get(r["name"], ("high", 9, 5, "left"))
        xy = ((r["input_power_high"], r["thrust_high"]) if anchor == "high"
              else (r["input_power_low"], r["thrust_low"]))
        ax.annotate(r["name"], xy, textcoords="offset points", xytext=(dx, dy),
                    fontsize=9.5, color=INK_2, fontweight="bold", ha=ha, zorder=5)

    ax.set_xscale("log")
    ax.set_yscale("log")

    # Explicit ticks. Matplotlib's log minor labels render as 6x10^-2, which is
    # unreadable at a glance for quantities people think of as "0.06 N".
    ax.set_xticks([0.2, 0.3, 0.5, 1, 2, 3, 5, 7])
    ax.set_yticks([0.02, 0.03, 0.05, 0.1, 0.2])
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xlim(0.15, 11)
    ax.set_ylim(0.016, 0.34)

    ax.set_ylabel("Thrust (newtons, log scale)", fontsize=10, color=INK_2, labelpad=8)
    ax.grid(axis="both", linewidth=0.8, alpha=0.9)

    _style(ax, "Input power to the thruster (kW, log scale)",
           "Electric propulsion — bought with power, not fuel",
           "Every thruster here beats every chemical engine on specific impulse. "
           "None can produce more than a quarter of a newton.")

    fig.text(0.01, 0.015,
             "Thrust-to-weight for these thrusters is of order 0.0002–0.002, against ~60 for "
             "the RS-25 — a gap of roughly five orders of magnitude.\nPower is thruster input, "
             "not power drawn from the spacecraft; the two differ by about 10% and the "
             "literature uses both names for both quantities.",
             fontsize=7.5, color=MUTED, va="bottom")

    fig.tight_layout(rect=[0, 0.085, 1, 1])
    fig.savefig(CHARTS_DIR / "03_electric_power_thrust.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- page 4

def page4_nuclear(df):
    d = df[df["category"] == "nuclear"]
    with_thrust = d[d["thrust_low"].notna()].sort_values("isp_high")
    without = d[d["thrust_low"].isna() & d["isp_low"].notna()].sort_values("isp_high")
    no_data = d[d["isp_low"].isna()]["name"].tolist()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6.2),
                                   gridspec_kw={"width_ratios": [1.15, 1]})

    # left: systems with measured hardware figures
    for _, r in with_thrust.iterrows():
        c = MATURITY_COLOR[r["maturity"]]
        ax1.plot([r["isp_low"], r["isp_high"]], [r["thrust_low"], r["thrust_high"]],
                 color=c, linewidth=4, solid_capstyle="round", zorder=3)
        ax1.plot([r["isp_low"], r["isp_high"]], [r["thrust_low"], r["thrust_high"]],
                 "o", color=c, markersize=9, markeredgecolor=SURFACE,
                 markeredgewidth=2, zorder=4)
        ax1.annotate(r["name"], (r["isp_high"], r["thrust_high"]),
                     textcoords="offset points", xytext=(10, 6),
                     fontsize=10, color=INK_2, fontweight="600")

    # Fit the axes to the data with a margin, rather than a round-number range
    # that leaves most of the panel empty.
    isp_lo = with_thrust["isp_low"].min()
    isp_hi = with_thrust["isp_high"].max()
    pad = (isp_hi - isp_lo) * 0.35
    ax1.set_xlim(isp_lo - pad, isp_hi + pad)
    thrust_hi = with_thrust["thrust_high"].max()
    ax1.set_ylim(0, thrust_hi * 1.22)
    ax1.set_ylabel("Thrust (newtons)", fontsize=10, color=INK_2, labelpad=8)
    ax1.grid(axis="both", linewidth=0.8, alpha=0.9)
    ax1.set_axisbelow(True)
    ax1.set_xlabel("Specific impulse (seconds)", fontsize=10, color=INK_2, labelpad=8)
    ax1.set_title("Built and fired", fontsize=12, color=INK, loc="left",
                  pad=10, fontweight="600")

    # right: theoretical concepts - Isp only, and the empty axis is the point
    for i, (_, r) in enumerate(without.iterrows()):
        _range_marks(ax2, i, r["isp_low"], r["isp_high"], MATURITY_COLOR[r["maturity"]])
        label = _fmt(r["isp_high"])
        if r["isp_high"] > r["isp_low"]:
            label = f"{_fmt(r['isp_low'])}–{label}"
        ax2.text(r["isp_high"] * 1.5, i, label, va="center", fontsize=9, color=INK_2)

    ax2.set_yticks(range(len(without)))
    ax2.set_yticklabels(without["name"], fontsize=10)
    ax2.set_xscale("log")
    ax2.set_xlim(without["isp_low"].min() / 3, without["isp_high"].max() * 30)
    ax2.set_ylim(-0.7, max(len(without) - 0.2, 1))
    ax2.grid(axis="x", linewidth=0.8, alpha=0.9)
    ax2.set_axisbelow(True)
    ax2.set_xlabel("Specific impulse (seconds, log scale)", fontsize=10,
                   color=INK_2, labelpad=8)
    ax2.set_title("Never built — no thrust figure exists", fontsize=12, color=INK,
                  loc="left", pad=10, fontweight="600")
    ax2.text(0.5, 0.5, "no thrust axis:\nnothing to plot against",
             transform=ax2.transAxes, fontsize=10, color=MUTED,
             ha="center", va="center", style="italic")

    fig.suptitle("Nuclear propulsion — high performance, almost none of it built",
                 fontsize=14, color=INK, x=0.008, ha="left", y=0.98, fontweight="600")
    fig.text(0.008, 0.915,
             "No nuclear system in this dataset has ever flown. "
             f"{'DRACO, the only one being built to fly, was cancelled in 2025 and published no performance figure at all.' if no_data else ''}",
             fontsize=9.5, color=INK_2)

    # Legend only for levels actually drawn. DRACO is the sole prototype and has
    # no measurements, so advertising an orange "Prototype" series would promise
    # a mark that appears nowhere on the page.
    plotted = set(with_thrust["maturity"]) | set(without["maturity"])
    handles = [Line2D([], [], color=MATURITY_COLOR[m], marker="o", linestyle="-",
                      linewidth=4, markersize=8, label=m.capitalize())
               for m in MATURITY_ORDER if m in plotted]
    ax1.legend(handles=handles, loc="lower right", frameon=True, facecolor=SURFACE,
               edgecolor=GRID, fontsize=9.5, title="Maturity", title_fontsize=9.5,
               labelcolor=INK_2)

    fig.text(0.008, 0.015,
             "Pewee's specific impulse is ideal-vacuum: calculated assuming infinite nozzle "
             "expansion and no losses, from fuel-element exit temperature rather than nozzle\n"
             "chamber temperature. A real Pewee engine would deliver materially less. "
             "NERVA's is a design specification for hardware that was built and fired.",
             fontsize=7.5, color=MUTED, va="bottom")

    fig.tight_layout(rect=[0, 0.075, 1, 0.90])
    fig.savefig(CHARTS_DIR / "04_nuclear_thrust_isp.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


def main():
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(PROCESSED_DIR / "analysis.csv", index_col=False)

    page1_all_systems_isp(df)
    page2_chemical_tw(df)
    page3_electric_power_thrust(df)
    page4_nuclear(df)

    for p in sorted(CHARTS_DIR.glob("*.png")):
        print(f"  wrote {p.name}  ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
