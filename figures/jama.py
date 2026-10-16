"Render Figures 1-4 of the JAMA Network Open manuscript from public aggregate CSVs."

import csv
import math
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
from PIL import Image

from config import RESULTS_DIR, ROOT

OUT = ROOT / "figures/output"
OUT.mkdir(parents=True, exist_ok=True)
plt.switch_backend("Agg")

INK, GREY, RULE, MARK = ("#262626", "#797a79", "#d9d9d9", "#374E55")  # JAMA palette (ggsci pal_jama)
# Regime colors from one family: pale slate for early awards, muted ochre for legacy awards, and the ink teal of the
# forest-plot markers for dedicated-pathway awards.
EARLY, LEGACY, POST = ("#00A1D5", "#DF8F44", MARK)
assert any(f.name in ("Arial", "Helvetica") for f in font_manager.fontManager.ttflist), "Arial/Helvetica unavailable"
plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 8,
        "text.color": INK,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.labelsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "axes.unicode_minus": True,
    }
)


def read_csv(relative, required, nrows=None):
    path = RESULTS_DIR / relative
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert set(required) <= set(reader.fieldnames), f"missing columns in {path}: {reader.fieldnames}"
        data = list(reader)
    assert nrows is None or len(data) == nrows, f"expected {nrows} rows in {path}, got {len(data)}"
    return data


def one(data, **keys):
    found = [r for r in data if all(r[k] == v for k, v in keys.items())]
    assert len(found) == 1, f"expected one row for {keys}, got {len(found)}"
    return found[0]


def triple(row):
    value, lo, hi = (float(row[k]) for k in ("estimate", "lo", "hi"))
    assert all(math.isfinite(v) for v in (value, lo, hi)) and lo <= value <= hi, row
    return value, lo, hi


def d1(v):
    return str(Decimal(str(v)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)).replace("-", "−")


def ci_text(value, lo, hi):
    # JAMA style: hyphen between positive limits, "to" when a limit is negative.
    sep = " to " if lo < 0 or hi < 0 else "-"
    return f"{d1(value)} ({d1(lo)}{sep}{d1(hi)})"


def save(fig, name):
    assert fig.get_figwidth() <= 7.5, f"figure too wide: {fig.get_figwidth()}"
    fig.savefig(OUT / f"{name}.pdf")
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=300)
    with Image.open(buffer) as rendered:
        rendered.convert("RGB").save(OUT / f"{name}.tif", compression="tiff_lzw", dpi=(300, 300))
    fig.savefig(OUT / f"{name}.png", dpi=150)
    plt.close(fig)


def forest_table(
    rows,
    columns,
    limits,
    ticks,
    xlabel,
    directions,
    name,
    width=7.5,
    est_x=0.585,
    plot=(0.7, 0.98),
    groups=(),
    est_header="Adjusted DID,\npercentage points (95% CI)",
):
    """rows: (label, indent, cells, estimate or None, marker); columns: [(x, header)] for the cell texts."""
    height = 0.75 + 0.2 * len(rows) + (0.35 if groups else 0)
    fig = plt.figure(figsize=(width, height))
    top = 1 - (0.8 if groups else 0.6) / height
    bottom = 0.5 / height
    ax = fig.add_axes([plot[0], bottom, plot[1] - plot[0], top - bottom])
    n = len(rows)
    ax.set(xlim=limits, ylim=(n - 0.5, -0.5), yticks=[], xticks=ticks, xlabel=xlabel)
    ax.axvline(0, color=INK, lw=0.6, ls=":", zorder=0)
    ax.spines["left"].set_visible(False)
    to_fig = ax.transData + fig.transFigure.inverted()
    for y, (label, indent, cells, est, marker) in enumerate(rows):
        yf = to_fig.transform((limits[0], y))[1]
        fig.text(0.01 + 0.015 * indent, yf, label, va="center", fontsize=8)
        for (x, _), text in zip(columns, cells, strict=False):
            if text:
                fig.text(x, yf, text, va="center", fontsize=8)
        if est is not None:
            value, lo, hi = est
            fig.text(est_x, yf, ci_text(value, lo, hi), va="center", fontsize=8)
            # Square: primary correction; diamond: periods pooled (lighter); circle: uncorrected.
            color = EARLY if marker == "D" else MARK
            ax.plot([lo, hi], [y, y], color=color, lw=0.9, solid_capstyle="butt")
            ax.plot(
                value,
                y,
                marker=marker,
                ms=5.5 if marker == "s" else 5,
                color=color,
                mfc="white" if marker == "o" else color,
                mew=0.9,
                ls="none",
            )
        yb = to_fig.transform((limits[0], y + 0.5))[1]
        fig.add_artist(Line2D([0.01, plot[0] - 0.02], [yb, yb], color=RULE, lw=0.5))
    yh = to_fig.transform((limits[0], -0.5))[1]
    fig.add_artist(Line2D([0.01, plot[0] - 0.02], [yh, yh], color=INK, lw=0.6))
    for x, header in columns + [(est_x, est_header)]:
        fig.text(x, yh + 0.006, header, va="bottom", fontsize=8)
    for x0, x1, header in groups:
        yg = yh + 0.012 + 0.32 / height
        fig.add_artist(Line2D([x0, x1], [yg, yg], color=INK, lw=0.5))
        fig.text((x0 + x1) / 2, yg + 0.006, header, ha="center", va="bottom", fontsize=8)
    zero = to_fig.transform((0, -0.5))[0]
    fig.text(zero - 0.008, yh + 0.006, directions[0], ha="right", va="bottom", fontsize=8)
    fig.text(zero + 0.008, yh + 0.006, directions[1], ha="left", va="bottom", fontsize=8)
    save(fig, name)


# Figure 1: flowchart of awardee selection in the JAMA Network style: tinted boxes, bold counts in a right-aligned
# column, exclusions in side boxes with reasons, and no phase labels (those belong to PRISMA and CONSORT diagrams).
FIG_H = 5.6
fig = plt.figure(figsize=(7.0, FIG_H))
fig.add_axes([0, 0, 1, 1]).axis("off")
BOX_FILL, BOX_EDGE, FLOW = ("#E8EFF3", "#8FA9B8", "#7A7A7A")
LINE_H = 8 * 1.45 / 72 / FIG_H
NUM_W, INDENT = (0.045, 0.03)


def box(x, y, w, h, rows):
    """rows: (count, text, level); counts are bold and right-aligned, text starts after them."""
    fig.add_artist(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="square,pad=0", fc=BOX_FILL, ec=BOX_EDGE, lw=0.7, transform=fig.transFigure
        )
    )
    top = y + h / 2 + (len(rows) - 1) * LINE_H / 2
    for i, (count, text, level) in enumerate(rows):
        nx = x + 0.012 + NUM_W + level * INDENT
        fig.text(nx, top - i * LINE_H, count, ha="right", va="center", fontsize=8, fontweight="bold")
        fig.text(nx + 0.008, top - i * LINE_H, text, ha="left", va="center", fontsize=8)


def line(xs, ys):
    fig.add_artist(Line2D(xs, ys, color=FLOW, lw=0.8))


def arrow(x0, y0, x1, y1):
    fig.add_artist(
        plt.Annotation(
            "",
            (x1, y1),
            xytext=(x0, y0),
            xycoords="figure fraction",
            arrowprops={"arrowstyle": "-|>", "color": FLOW, "lw": 0.8, "mutation_scale": 7, "shrinkA": 0, "shrinkB": 0},
        )
    )


# JAMA layout: one vertical spine at the midpoint of the two group columns; main boxes centered on the spine,
# exclusion boxes just right of it between main boxes, and the two source and group boxes centered on their columns.
SPINE, L, R = (0.5, 0.255, 0.745)
SIDE_W, MAIN_W, EXCL_X, EXCL_W = (0.45, 0.40, 0.535, 0.435)
LX, RX, MX = (L - SIDE_W / 2, R - SIDE_W / 2, SPINE - MAIN_W / 2)
box(
    LX,
    0.86,
    SIDE_W,
    0.11,
    [("1860", "K08 and K23 awardees under earlier parent", 0), ("", "announcements, fiscal years 2014-2019", 0)],
)
box(
    RX,
    0.86,
    SIDE_W,
    0.11,
    [("1527", "K08 and K23 awardees under dedicated-pathway", 0), ("", "announcements, fiscal years 2018-2021", 0)],
)
line([L, L], [0.86, 0.82])
line([R, R], [0.86, 0.82])
line([L, R], [0.82, 0.82])
arrow(SPINE, 0.82, SPINE, 0.775)
box(MX, 0.71, MAIN_W, 0.065, [("3387", "Awardees (earliest qualifying award each)", 0)])
arrow(SPINE, 0.71, SPINE, 0.585)
arrow(SPINE, 0.6475, EXCL_X, 0.6475)
box(EXCL_X, 0.605, EXCL_W, 0.085, [("25", "Excluded", 0), ("25", "Basic-experimental-only projects", 1)])
box(MX, 0.52, MAIN_W, 0.065, [("3362", "Awardees", 0)])
arrow(SPINE, 0.52, SPINE, 0.395)
arrow(SPINE, 0.4575, EXCL_X, 0.4575)
box(
    EXCL_X,
    0.415,
    EXCL_W,
    0.085,
    [("1515", "Excluded from the main analysis", 0), ("1515", "K08 awardees, analyzed separately", 1)],
)
box(MX, 0.33, MAIN_W, 0.065, [("1847", "K23 awardees included", 0)])
line([SPINE, SPINE], [0.33, 0.29])
line([L, R], [0.29, 0.29])
arrow(L, 0.29, L, 0.245)
arrow(R, 0.29, R, 0.245)
box(
    LX,
    0.03,
    SIDE_W,
    0.215,
    [
        ("1010", "Earlier awards", 0),
        ("792", "Early, fiscal years 2014-2017", 1),
        ("218", "Legacy, fiscal years 2018-2019", 1),
        ("375", "With trial plans", 1),
        ("635", "Without trial plans", 1),
    ],
)
box(
    RX,
    0.03,
    SIDE_W,
    0.215,
    [
        ("837", "Pathway awards, fiscal years 2018-2021", 0),
        ("", "Required or Not Allowed announcements", 0),
        ("346", "With trial plans", 1),
        ("491", "Without trial plans", 1),
    ],
)
save(fig, "JNO_Figure1")

# Figure 2: main estimates with instrument-measured cell percentages.
cells = read_csv("supplementary/ktrial_cells.csv", ["mechanism", "period", "intent", "n", "ktrial_direct", "new_trial"])
corrected = read_csv("validation/corrected_did.csv", ["variant", "quantity", "estimate", "lo", "hi", "n", "reps"], 72)
assert all(r["n"] == "1847" and r["reps"] == "2000" for r in corrected)


def pct(period, intent, col):
    return one(cells, mechanism="K23", period=period, intent=intent)[col]


ns = {(p, i): one(cells, mechanism="K23", period=p, intent=i)["n"] for p in ("pre_policy", "post_policy") for i in "10"}
VERSIONS = [
    ("Corrected (primary)", "human_centered", "s"),
    ("Corrected, periods pooled", "human_pooled_periods", "D"),
    ("Uncorrected", "observed", "o"),
]
rows = []
for label, col, quantity in [
    ("K-trial leadership", "ktrial_direct", "K-trial DID"),
    ("New-trial leadership", "new_trial", "new-trial DID"),
    ("Any-trial leadership", "any_trial", "any-trial DID"),
]:
    rows.append((label, 0, [pct(p, i, col) for p in ("pre_policy", "post_policy") for i in "10"], None, None))
    for name, variant, marker in VERSIONS:
        rows.append((name, 1, [], triple(one(corrected, variant=variant, quantity=quantity)), marker))
rows.append(("Which trials awardees led (primary correction)", 0, [], None, None))
for label, quantity in [
    ("Neither trial type", "neither-state DID"),
    ("K trial only", "K-only-state DID"),
    ("New trial only", "new-only-state DID"),
    ("Both trial types", "both-state DID"),
]:
    _name, variant, marker = VERSIONS[0]
    rows.append((label, 1, [], triple(one(corrected, variant=variant, quantity=quantity)), marker))
cols = [
    (0.225, f"Trial plan\n(n = {ns['pre_policy', '1']})"),
    (0.3, f"No plan\n(n = {ns['pre_policy', '0']})"),
    (0.385, f"Trial plan\n(n = {ns['post_policy', '1']})"),
    (0.46, f"No plan\n(n = {ns['post_policy', '0']})"),
]
forest_table(
    rows,
    cols,
    (-20, 35),
    [-20, -10, 0, 10, 20, 30],
    "DID, percentage points",
    ("Gap narrowed", "Gap widened"),
    "JNO_Figure2",
    est_x=0.54,
    plot=(0.76, 0.98),
    groups=[(0.225, 0.36, "Earlier awards,\nuncorrected %"), (0.385, 0.52, "Pathway awards,\nuncorrected %")],
)

# eFigure 1: annual instrument-measured leadership by regime and intent.
year = read_csv(
    "historical/ktrial_by_year.csv",
    ["mechanism", "intent", "fiscal_year", "period", "n", "ktrial_direct", "new_trial"],
    37,
)
STRATA = [("pre_early", EARLY, "o"), ("pre_legacy", LEGACY, "s"), ("post", POST, "^")]
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2), sharey=True)
for ax, (tag, col, words) in zip(
    axes, [("A", "ktrial_direct", "K-trial leadership"), ("B", "new_trial", "New-trial leadership")], strict=True
):
    for intent_value, filled in [("1", True), ("0", False)]:
        for stratum, color, marker in STRATA:
            pts = sorted(
                (
                    r
                    for r in year
                    if r["mechanism"] == "K23"
                    and r["intent"] == intent_value
                    and int(r["n"]) >= 10
                    and (
                        (stratum == "pre_early" and r["period"] == "pre_policy" and int(r["fiscal_year"]) <= 2017)
                        or (stratum == "pre_legacy" and r["period"] == "pre_policy" and int(r["fiscal_year"]) >= 2018)
                        or (stratum == "post" and r["period"] == "post_policy")
                    )
                ),
                key=lambda r: int(r["fiscal_year"]),
            )
            xs = [
                int(r["fiscal_year"])
                + ((-0.1 if stratum == "pre_legacy" else 0.1) if r["fiscal_year"] == "2018" else 0)
                for r in pts
            ]
            ax.plot(
                xs,
                [float(r[col]) for r in pts],
                marker=marker,
                color=color,
                ms=4.5,
                mfc=color if filled else "white",
                mew=1,
                lw=1.3,
                ls="-" if filled else "--",
            )
    ax.set(
        xlim=(2013.6, 2021.4),
        ylim=(0, 90),
        xticks=range(2014, 2022),
        yticks=range(0, 100, 20),
        xlabel="Fiscal year of K award start",
    )
    ax.set_title(f"{tag}  {words}", loc="left", fontsize=8.5)
    ax.yaxis.grid(True, color=RULE, lw=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="x", labelsize=7.5)
axes[0].set_ylabel("Awardees, %")
fig.legend(
    [Line2D([0], [0], marker=m, color=c, lw=1) for _, c, m in STRATA]
    + [Line2D([0], [0], color=INK, lw=1, ls="-"), Line2D([0], [0], color=INK, lw=1, ls="--")],
    ["Early awards", "Legacy awards", "Pathway awards", "Trial plans", "No trial plans"],
    loc="lower center",
    ncol=5,
    fontsize=7.5,
    bbox_to_anchor=(0.5, -0.01),
    columnspacing=1.2,
    handlelength=2.2,
)
fig.subplots_adjust(left=0.08, right=0.99, top=0.9, bottom=0.27, wspace=0.08)
save(fig, "JNO_eFigure1")

# Figure 3: comparison-group and trend checks on the human-corrected scale (same draws as the primary estimates).
checks = read_csv("validation/corrected_checks.csv", ["check", "quantity", "estimate", "lo", "hi", "n"], 15)
rows = []
for check, label in [
    ("Full sample", "All awards (primary)"),
    ("Legacy awards as comparator", "Legacy awards as comparator"),
    ("Fiscal years 2018-2019 in both regimes", "Fiscal years 2018-2019, both announcement types"),
    ("Extrapolated early-cohort trend", "Extrapolated early-cohort trends"),
]:
    n = one(checks, check=check, quantity="K-trial DID")["n"]
    rows.append((f"{label} (n = {n})", 0, [], None, None))
    for quantity, word in [
        ("K-trial DID", "K-trial leadership"),
        ("new-trial DID", "New-trial leadership"),
    ]:
        rows.append((word, 1, [], triple(one(checks, check=check, quantity=quantity)), "s"))
forest_table(
    rows,
    [],
    (-45, 60),
    [-40, -20, 0, 20, 40, 60],
    "DID, percentage points",
    ("Gap narrowed", "Gap widened"),
    "JNO_Figure3",
    est_x=0.4,
    plot=(0.66, 0.98),
)

# Table 1: K23 awardee characteristics by regime and trial intent.
balance = read_csv("composition/balance.csv", ["mechanism", "covariate", "mean_pre_intent", "did", "lo", "hi"])
links = read_csv("sensitivity/grant_link_cells.csv", ["stratum", "intent", "component", "n"])


def stratum_n(stratum, intent):
    return one(links, stratum=stratum, intent=intent, component="id_field")["n"]


header = [
    "Characteristic",
    "Earlier awards, trial plans",
    "Earlier awards, no trial plans",
    "Pathway awards, trial plans",
    "Pathway awards, no trial plans",
    "DID (95% CI)",
]
table = [
    ["Awardees, No.", ns["pre_policy", "1"], ns["pre_policy", "0"], ns["post_policy", "1"], ns["post_policy", "0"], ""],
    [
        "Early awards, fiscal years 2014-2017, No.",
        stratum_n("pre_early", "1"),
        stratum_n("pre_early", "0"),
        "NA",
        "NA",
        "",
    ],
    [
        "Legacy awards, fiscal years 2018-2019, No.",
        stratum_n("pre_legacy", "1"),
        stratum_n("pre_legacy", "0"),
        "NA",
        "NA",
        "",
    ],
]
assert int(stratum_n("pre_early", "1")) + int(stratum_n("pre_legacy", "1")) == int(ns["pre_policy", "1"])
assert int(stratum_n("pre_early", "0")) + int(stratum_n("pre_legacy", "0")) == int(ns["pre_policy", "0"])
for covariate, label, scale in [
    ("preK_PI_nonK", "Prior non-K trial leadership, No. (%)", 100),
    ("prior_nih_pi_award", "Prior NIH award as principal investigator, No. (%)", 100),
    ("prior_research_grant", "Prior NIH research grant, No. (%)", 100),
    ("inst_log_k", "Institution size, geometric mean No. of cohort K awards", 1),
]:
    r = one(balance, mechanism="K23", covariate=covariate)
    fmt = (lambda v: d1(float(v) * 100)) if scale == 100 else (lambda v: f"{math.exp(float(v)):.0f}")
    did_row = {"estimate": float(r["did"]) * scale, "lo": float(r["lo"]) * scale, "hi": float(r["hi"]) * scale}
    est = (did_row["estimate"], did_row["lo"], did_row["hi"])
    ratio = [math.exp(v) for v in est]
    did_text = ci_text(*est) if scale == 100 else f"Ratio, {ratio[0]:.2f} ({ratio[1]:.2f}-{ratio[2]:.2f})"
    cells = []
    for c, key in (
        ("mean_pre_intent", ("pre_policy", "1")),
        ("mean_pre_nointent", ("pre_policy", "0")),
        ("mean_post_intent", ("post_policy", "1")),
        ("mean_post_nointent", ("post_policy", "0")),
    ):
        if scale == 1:
            cells.append(fmt(r[c]))
            continue
        # Three-decimal shares identify counts exactly for denominators below 1000.
        n = int(ns[key])
        k = round(float(r[c]) * n)
        assert n < 1000 and round(k / n, 3) == float(r[c]), f"count not recoverable: {covariate}, {c}"
        cells.append(f"{k} ({d1(100 * k / n)})")
    table.append([label] + cells + [did_text])
md = (
    "| "
    + " | ".join(header)
    + " |\n|"
    + "|".join("-" * w for w in (26, 13, 13, 13, 13, 18))
    + "|\n"
    + "\n".join("| " + " | ".join(map(str, r)) + " |" for r in table)
    + "\n"
)
(OUT / "JNO_Table1.md").write_text(md)
print("JNO Table 1:", len(table), "rows")
