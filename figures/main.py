"Render Fig 1–4 from public aggregate CSVs."

import csv
import math
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from PIL import Image

from config import RESULTS_DIR, ROOT

OUT = ROOT / "figures/output"
OUT.mkdir(parents=True, exist_ok=True)
plt.switch_backend("Agg")

# Dark grey ink, grey annotation, light rules; regime colours from the Okabe-Ito palette.
INK, GREY, RULE = ("#262626", "#797a79", "#c8c9c8")
EARLY, LEGACY, POST = ("#0072B2", "#E69F00", "#009E73")
BLACK = INK
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
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "savefig.dpi": 300,
        "axes.unicode_minus": True,
    }
)
STRATA = [("pre_early", "Early", EARLY, "o"), ("pre_legacy", "Legacy", LEGACY, "s"), ("post", "Post", POST, "^")]


def read_csv(relative, required, nrows):
    path = RESULTS_DIR / relative
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert set(required) <= set(reader.fieldnames), f"missing columns in {path}: {reader.fieldnames}"
        data = list(reader)
    assert len(data) == nrows, f"expected {nrows} rows in {path}, got {len(data)}"
    return data


def number(row, key):
    value = float(row[key])
    assert math.isfinite(value), f"nonfinite {key}: {row}"
    return value


def one(data, **keys):
    found = [r for r in data if all((r[k] == v for k, v in keys.items()))]
    assert len(found) == 1, f"expected one row for {keys}, got {len(found)}"
    return found[0]


def interval(row, key="estimate"):
    value, lo, hi = (number(row, k) for k in (key, "lo", "hi"))
    assert lo <= value <= hi, f"interval does not contain estimate: {row}"
    return (value, lo, hi)


def text_interval(value, lo, hi):
    return "{} ({}, {})".format(
        *(str(Decimal(str(v)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) for v in (value, lo, hi))
    ).replace("-", "−")


def title(fig, y, letter, words):
    fig.text(0.035, y, letter, fontsize=9, weight="bold", va="top")
    fig.text(0.058, y, words, fontsize=9, va="top")


def forest(fig, bottom, height, rows, limits=(-20, 35), xlabel="Difference (percentage points)"):
    ax = fig.add_axes([0.43, bottom, 0.3, height])
    ax.axvline(0, color=GREY, lw=0.6, zorder=0)
    for y, (label, row, key, color, marker) in enumerate(rows):
        if row is None:
            ax.text(-1.31, y, label, transform=ax.get_yaxis_transform(), va="center", fontsize=8)
            continue
        value, lo, hi = interval(row, key)
        ax.errorbar(
            value,
            y,
            xerr=[[value - lo], [hi - value]],
            fmt=marker,
            color=color,
            mfc="white" if marker == "o" and color == BLACK else color,
            ms=4,
            lw=1.1,
            capsize=2,
        )
        ax.text(-1.31, y, label, transform=ax.get_yaxis_transform(), va="center", fontsize=8)
        ax.text(
            1.05,
            y,
            text_interval(value, lo, hi),
            transform=ax.get_yaxis_transform(),
            va="center",
            fontsize=8,
            color=INK,
        )
    ax.set(xlim=limits, ylim=(len(rows) - 0.45, -0.55), yticks=[], xlabel=xlabel)
    ax.text(1.05, -0.93, "Estimate (95% CI)", transform=ax.get_yaxis_transform(), fontsize=8)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    return ax


def save(fig, name):
    assert fig.get_figwidth() <= 7.5, f"figure too wide: {fig.get_figwidth()}"
    fig.savefig(OUT / f"{name}.pdf")
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=300)
    with Image.open(buffer) as rendered:
        rendered.convert("RGB").save(OUT / f"{name}.tif", compression="tiff_lzw", dpi=(300, 300))
    fig.savefig(OUT / f"{name}.png", dpi=150)
    with Image.open(OUT / f"{name}.tif") as image:
        assert tuple(round(d) for d in image.info["dpi"]) == (300, 300), image.info
        assert image.info["compression"] == "tiff_lzw", image.info
        assert image.mode == "RGB", image.mode
        assert image.width <= 2250, image.size
    plt.close(fig)


year = read_csv(
    "historical/ktrial_by_year.csv",
    ["mechanism", "intent", "fiscal_year", "period", "n", "ktrial_direct", "new_trial"],
    37,
)
did = read_csv("historical/joint_leadership_estimates.csv", ["mechanism", "quantity", "estimate", "lo", "hi", "n"], 6)
shares = read_csv(
    "registry_panel/shares.csv",
    [
        "stratum",
        "n_intent_awardees",
        "a_pi_from_registration",
        "b_link_added_later_or_never",
        "c_responsibility_shift",
        "d_insufficient",
    ],
    3,
)
panel = read_csv("registry_panel/differences.csv", ["quantity", "comparison", "estimate", "lo", "hi"], 34)
report = read_csv(
    "sensitivity/reporting_trial_cells.csv",
    ["stratum", "n_due", "n_within12", "within12_pct"],
    3,
)
report_diff = read_csv("sensitivity/reporting_trial_estimates.csv", ["outcome", "spec", "estimate", "lo", "hi"], 10)
legacy = read_csv("sensitivity/legacy_estimates.csv", ["mechanism", "outcome", "spec", "estimate", "lo", "hi"], 18)
horizon = read_csv(
    "sensitivity/registration_horizon_estimates.csv", ["mechanism", "outcome", "estimate", "lo", "hi"], 8
)
lineage_counts = read_csv("lineage/estimates.csv", ["quantity", "comparison", "hi"], 9)
lineage = read_csv("validation/lineage_corrected.csv", ["quantity", "estimate", "lo", "hi"], 9)
corrected = read_csv("validation/corrected_did.csv", ["variant", "quantity", "estimate", "lo", "hi", "n", "reps"], 64)
assert all(r["n"] == "1847" and r["reps"] == "2000" for r in corrected)
seven = read_csv("follow_up/estimates.csv", ["mechanism", "outcome", "estimate", "lo", "hi", "n"], 6)
cells = read_csv("follow_up/cells.csv", ["mechanism", "post", "intent", "n"], 8)
assert sum(int(r["n"]) for r in year if r["mechanism"] == "K23") == int(
    one(did, mechanism="K23", quantity="K-trial DID")["n"]
)
assert sum(int(r["n"]) for r in cells if r["mechanism"] == "K23") == int(
    one(seven, mechanism="K23", outcome="new_trial_7y")["n"]
)
fig = plt.figure(figsize=(7.5, 10.4))
title(fig, 0.98, "A", "Three accounts and what each predicts")
ax = fig.add_axes([0.04, 0.705, 0.92, 0.25])
ax.axis("off")
ax.set(xlim=(0, 1), ylim=(0, 1))
accounts = [
    (0.40, "Supported-project\ndelivery", "runs the funded trial"),
    (0.59, "Trialist\ndevelopment", "leads new trials"),
    (0.78, "Selection", "draws trial-oriented\nawardees"),
]
for x, name, gloss in accounts:
    ax.text(x, 0.86, name, ha="center", va="bottom", fontsize=8)
    ax.text(x, 0.845, gloss, ha="center", va="top", fontsize=7.5, color=GREY)
ax.text(0.95, 0.86, "Observed", ha="center", va="bottom", fontsize=8)
ax.plot([0.0, 1.0], [0.71, 0.71], color=RULE, lw=0.6)
predictions = [
    ("K-trial leadership", ("rise", None, "rise"), "rose"),
    ("New-trial leadership", ("flat", "rise", "rise"), "no detectable gain"),
    ("Any-trial leadership", (None, "rise", "rise"), "unresolved"),
]
for i, (outcome, marks, observed) in enumerate(predictions):
    y = 0.60 - i * 0.14
    ax.text(0.0, y, outcome, va="center", fontsize=8)
    for (x, _, _), mark in zip(accounts, marks, strict=True):
        if mark is None:
            ax.plot([x - 0.012, x + 0.012], [y, y], color=GREY, lw=0.8)
        else:
            ax.plot(x, y, "o", ms=6, color=INK, mfc=INK if mark == "rise" else "white", mew=0.8)
    ax.text(0.95, y, observed, ha="center", va="center", fontsize=8)
ax.plot([0.0, 1.0], [0.24, 0.24], color=RULE, lw=0.6)
ax.text(0.0, 0.16, "Filled, predicts a rise; open, predicts no change; dash, no prediction.", fontsize=7.5, color=GREY)
ax.text(
    0.0,
    0.07,
    "K trial: the study the award supports. New trial: a distinct study without a K-grant link.",
    fontsize=7.5,
    color=GREY,
)
for left, tag, col, words in [
    (0.1, "B", "ktrial_direct", "K-trial leadership"),
    (0.56, "C", "new_trial", "New-trial leadership"),
]:
    ax = fig.add_axes([left, 0.47, 0.38, 0.2])
    for intent_value, filled in [("1", True), ("0", False)]:
        for stratum, _, color, marker in STRATA:
            rows = [
                r
                for r in year
                if r["mechanism"] == "K23"
                and r["intent"] == intent_value
                and (int(r["n"]) >= 10)
                and (
                    stratum == "pre_early"
                    and r["period"] == "pre_policy"
                    and (int(r["fiscal_year"]) <= 2017)
                    or (stratum == "pre_legacy" and r["period"] == "pre_policy" and (int(r["fiscal_year"]) >= 2018))
                    or (stratum == "post" and r["period"] == "post_policy")
                )
            ]
            rows.sort(key=lambda r: int(r["fiscal_year"]))
            xs = [
                int(r["fiscal_year"])
                + ((-0.1 if stratum == "pre_legacy" else 0.1) if r["fiscal_year"] == "2018" else 0)
                for r in rows
            ]
            ax.plot(
                xs,
                [number(r, col) for r in rows],
                marker=marker,
                color=color,
                ms=4,
                mfc=color if filled else "white",
                lw=1,
                ls="-" if filled else "--",
            )
    for intent_value in ("1", "0"):
        sparse = one(year, mechanism="K23", intent=intent_value, period="post_policy", fiscal_year="2018")
        assert int(sparse["n"]) == (16 if intent_value == "1" else 20), sparse
        ax.annotate(
            "*", (2018.1, number(sparse, col)), xytext=(3, 5), textcoords="offset points", color=POST, fontsize=11
        )
    ax.axhline(0, color=".5", lw=0.6)
    ax.set(
        xlim=(2013.7, 2021.3),
        ylim=(-3, 90),
        xticks=range(2014, 2022),
        yticks=[0, 20, 40, 60, 80],
        xlabel="Fiscal year of K start",
    )
    ax.set_title(words, loc="left", pad=8)
    ax.text(-0.13, 1.045, tag, transform=ax.transAxes, fontsize=9, weight="bold", va="bottom")
    ax.tick_params(axis="x", labelrotation=45)
    if tag == "B":
        ax.set_ylabel("K23 awardees (%)")
fig.legend(
    [Line2D([0], [0], marker=m, color=c, lw=0) for _, _, c, m in STRATA],
    ["Early parent awards", "Legacy parent awards", "Post-policy awards"],
    loc="lower center",
    bbox_to_anchor=(0.5, 0.372),
    ncol=3,
    columnspacing=1.6,
)
fig.text(
    0.5,
    0.363,
    "Filled / solid: trial intent; open / dashed: no trial intent. * FY2018 post: n = 16 / 20, respectively.",
    ha="center",
    fontsize=8,
)
fig.text(
    0.5, 0.346, "Annual rates are descriptive. FY2019 legacy cells with n < 10 are omitted.", ha="center", fontsize=8
)
title(fig, 0.318, "D", "Human-corrected primary estimates and supporting comparisons")
rows = []
for label, quantity in [
    ("K-trial DID", "K-trial DID"),
    ("New-trial DID", "new-trial DID"),
    ("K minus new DID (supporting)", "K-trial minus new-trial DID"),
    ("Any-trial DID (supporting)", "any-trial DID"),
]:
    rows.append((label, one(corrected, variant="human_centered", quantity=quantity), "estimate", BLACK, "D"))
    rows.append(("", one(corrected, variant="observed", quantity=quantity), "estimate", BLACK, "o"))
for label, quantity in [
    ("Joint state: neither", "neither-state DID"),
    ("Joint state: K only", "K-only-state DID"),
    ("Joint state: new only", "new-only-state DID"),
    ("Joint state: both", "both-state DID"),
]:
    rows.append((label, one(corrected, variant="human_centered", quantity=quantity), "estimate", BLACK, "D"))
for spec, label in [
    ("FY2018-2019 legacy pre; all post; five-year outcomes", "Legacy vs all post"),
    ("FY2018-2019 legacy and post; five-year outcomes", "FY2018–19, both regimes"),
]:
    for outcome, short in [("ktrial_direct", "K"), ("primary", "new")]:
        rows.append(
            (f"{label}: {short}", one(legacy, mechanism="K23", spec=spec, outcome=outcome), "estimate", BLACK, "s")
        )
forest(fig, 0.045, 0.215, rows, (-30, 40), "Adjusted DID (percentage points)")
fig.legend(
    [
        Line2D([0], [0], marker=m, color=BLACK, mfc=fill, lw=0)
        for m, fill in [("D", BLACK), ("o", "white"), ("s", BLACK)]
    ],
    ["Human-corrected", "Instrument", "Legacy comparison (instrument)"],
    loc="lower center",
    bbox_to_anchor=(0.5, 0.272),
    ncol=3,
    columnspacing=1.0,
)
save(fig, "Fig1")
categories = [
    ("a_pi_from_registration", "PI and K link at registration"),
    ("b_link_added_later_or_never", "PI at registration, K link later / never"),
    ("c_responsibility_shift", "Responsibility shift"),
    ("d_insufficient", "Public record insufficient"),
]
fig = plt.figure(figsize=(7.5, 9.0))
title(fig, 0.98, "A", "Leadership records among all trial-intent awardees")
ax = fig.add_axes([0.43, 0.715, 0.3, 0.2])
ax.axvline(0, color=".5", lw=0.6)
for j, (key, lab) in enumerate(categories):
    ax.text(-1.31, j, lab, transform=ax.get_yaxis_transform(), va="center", fontsize=8)
    for index, (offset, (stratum, _, color, marker)) in enumerate(zip([-0.19, 0, 0.19], STRATA, strict=False)):
        value = number(one(shares, stratum=stratum), key)
        assert 0 <= value <= 100, f"share out of range: {stratum}, {key}, {value}"
        ax.plot(value, j + offset, marker, color=color, ms=4)
        ax.text(
            1.1 + index * 0.24,
            j,
            f"{value:.1f}",
            transform=ax.get_yaxis_transform(),
            ha="center",
            va="center",
            fontsize=8,
        )
for x, (stratum, lab, color, marker) in zip([1.1, 1.34, 1.58], STRATA, strict=False):
    n = one(shares, stratum=stratum)["n_intent_awardees"]
    ax.text(x, -0.8, f"{lab}\nn = {n}", transform=ax.get_yaxis_transform(), ha="center", va="center", fontsize=8)
    ax.plot(x, -1.35, marker, color=color, ms=4, transform=ax.get_yaxis_transform(), clip_on=False)
ax.set(xlim=(0, 55), ylim=(3.5, -0.5), yticks=[], xlabel="Awardees (%)")
ax.spines["left"].set_visible(False)
title(fig, 0.65, "B", "Initial leadership and K linkage increased")
rows = []
for key, lab in categories + [("klink_added_later", "K link added after registration")]:
    rows.append((lab, None, "", BLACK, ""))
    for i, (ref, _short, color) in enumerate([("pre_early", "early", EARLY), ("pre_legacy", "legacy", LEGACY)]):
        rows.append(
            (
                f"    vs {_short}",
                one(panel, quantity=key, comparison=f"post minus {ref}"),
                "estimate",
                color,
                "o" if i == 0 else "s",
            )
        )
forest(fig, 0.305, 0.30, rows, (-15, 30), "Within-intent difference (percentage points)")
title(fig, 0.255, "C", "Recorded initiation and current-status/primary-completion-date proxy")
rows = []
for key, lab in [
    ("started", "Recorded initiation"),
    ("completed_within_5y", "Completion proxy"),
]:
    rows.append((lab, None, "", BLACK, ""))
    for i, (ref, color) in enumerate([("pre_early", EARLY), ("pre_legacy", LEGACY)]):
        rows.append(
            (
                "    vs early" if i == 0 else "    vs legacy",
                one(panel, quantity=key, comparison=f"post minus {ref}"),
                "estimate",
                color,
                "o" if i == 0 else "s",
            )
        )
forest(fig, 0.085, 0.13, rows, (-15, 30), "Within-intent difference (percentage points)")
fig.text(
    0.035,
    0.023,
    "Proxy: current COMPLETED status and primary-completion date no later than K start + 5 years.",
    fontsize=8,
)
save(fig, "Fig2")
fig = plt.figure(figsize=(7.5, 6.5))
ax = fig.add_axes([0.32, 0.855, 0.61, 0.095])
for y, start, end, color, coverage in [
    (2, 2014, 2017, EARLY, "Not covered*"),
    (1, 2018, 2019, LEGACY, "Likely covered*"),
    (0, 2018, 2021, POST, "Likely covered*"),
]:
    ax.plot([start - 0.5, end + 0.5], [y, y], lw=7, color=color, solid_capstyle="butt")
    ax.text(1.02, y, coverage, transform=ax.get_yaxis_transform(), va="center", fontsize=8)
ax.set_position([0.32, 0.855, 0.43, 0.095])
ax.set(
    xlim=(2013.4, 2021.6),
    ylim=(-0.5, 2.5),
    xticks=range(2014, 2022),
    yticks=[2, 1, 0],
    yticklabels=["Early parent awards", "Legacy parent awards", "Post-policy awards"],
    xlabel="Fiscal year of K start",
)
ax.tick_params(axis="y", length=0, pad=9)
ax.spines["left"].set_visible(False)
fig.text(
    0.035,
    0.985,
    "NIH dissemination-policy coverage: application timing proxy, not a K-start cutoff",
    va="top",
    fontsize=8,
)
title(fig, 0.76, "A", "Trial-level submission within 12 months was similar in legacy and post")
ax = fig.add_axes([0.43, 0.495, 0.3, 0.2])
ax.axvline(0, color=".5", lw=0.6)
for j, (stratum, lab, color, marker) in enumerate(STRATA):
    r = one(report, stratum=stratum)
    value = number(r, "within12_pct")
    ax.plot(value, j, marker, color=color, ms=5)
    ax.text(
        -1.31,
        j,
        f"{lab}: {r['n_within12']}/{r['n_due']} trials",
        transform=ax.get_yaxis_transform(),
        va="center",
        fontsize=8,
    )
    ax.text(
        1.05,
        j,
        f"{Decimal(str(value)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}% submitted",
        transform=ax.get_yaxis_transform(),
        va="center",
        fontsize=8,
    )
ax.set(xlim=(0, 100), ylim=(2.5, -0.5), yticks=[], xlabel="Due K trials with results submitted within 12 months (%)")
ax.spines["left"].set_visible(False)
title(fig, 0.405, "B", "Post–legacy contrasts did not show an additional rise")
rows = []
for outcome, lab in [("within12", "Within 12 months"), ("ever_submitted", "Ever submitted")]:
    for ref, short, color, marker in [("pre_early", "early", EARLY, "o"), ("pre_legacy", "legacy", LEGACY, "s")]:
        rows.append(
            (
                f"{lab}: post minus {short}",
                one(report_diff, outcome=outcome, spec=f"post minus {ref}"),
                "estimate",
                color,
                marker,
            )
        )
forest(fig, 0.13, 0.205, rows, (-25, 40), "Trial-level difference (percentage points)")
fig.text(
    0.035,
    0.038,
    "Due: COMPLETED or TERMINATED with actual enrollment >0, primary completion ≥12 months before retrieval.",
    fontsize=8,
)
fig.text(
    0.035,
    0.015,
    "* Coverage is inferred from award timing. Application dates were not verified for individual awards.",
    fontsize=8,
)
save(fig, "Fig3")
fig = plt.figure(figsize=(7.5, 6.5))
title(fig, 0.97, "A", "Scientifically continuous leadership among all trial-intent awardees")
rows = [
    (f"Developed-from-K trial: post minus {short}", one(lineage, quantity=f"diff_{ref}"), "estimate", color, marker)
    for ref, short, color, marker in [("pre_early", "early", EARLY, "o"), ("pre_legacy", "legacy", LEGACY, "s")]
]
forest(fig, 0.788, 0.11, rows, (-20, 15), "Within-intent difference (percentage points)")
title(fig, 0.678, "B", "Human-corrected scientific continuity among rated new-trial records")
ax = fig.add_axes([0.43, 0.466, 0.3, 0.146])
ax.axvline(0, color=".5", lw=0.6)
for j, (stratum, lab, color, marker) in enumerate(STRATA):
    row = one(lineage_counts, quantity="share of new trials developed from the K work", comparison=stratum)
    share = one(lineage, quantity=f"pairshare_{stratum}")
    value, lo, hi = (number(share, k) for k in ("estimate", "lo", "hi"))
    assert row["hi"].startswith("n="), f"missing lineage trial denominator: {row}"
    ax.errorbar(value, j, xerr=[[value - lo], [hi - value]], fmt=marker, color=color, ms=4, capsize=2, lw=1)
    ax.text(
        -1.31,
        j,
        f"{lab}: {row['hi'][2:]} awardee–trial pairs",
        transform=ax.get_yaxis_transform(),
        va="center",
        fontsize=8,
    )
    ax.text(
        1.05,
        j,
        f"{value:.1f}% ({lo:.1f}, {hi:.1f})",
        transform=ax.get_yaxis_transform(),
        va="center",
        fontsize=8,
    )
ax.set(xlim=(0, 100), ylim=(2.5, -0.5), yticks=[], xlabel="Rated records developed from K work (%)")
ax.spines["left"].set_visible(False)
title(fig, 0.352, "C", "Longer follow-up did not reveal a detectable gain")
rows = [
    (label, one(horizon, mechanism="K23", outcome=outcome), "estimate", BLACK, marker)
    for label, outcome, marker in [
        ("Registered by five-year horizon", "new_5y_registered", "o"),
        ("Registered by seven-year horizon", "new_7y_registered", "o"),
    ]
]
forest(fig, 0.174, 0.11, rows, (-20, 15), "Adjusted DID (percentage points)")
counts = {(r["post"], r["intent"]): r["n"] for r in cells if r["mechanism"] == "K23"}
fig.text(
    0.035,
    0.075,
    f"Same complete-follow-up sample: pre, intent / no intent n = {counts['0', '1']} / {counts['0', '0']}. "
    f"post, {counts['1', '1']} / {counts['1', '0']}. "
    f"Total n = {one(seven, mechanism='K23', outcome='new_trial_7y')['n']}.",
    fontsize=8,
)
fig.text(
    0.035,
    0.025,
    "Open circles: instrument labels at both horizons. Human validation covers five years.",
    fontsize=8,
)
save(fig, "Fig4")
print("Main figures: 4; historical K23 n=1847; seven-year K23 n=1274")
