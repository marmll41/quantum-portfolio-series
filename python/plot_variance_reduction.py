"""Figure for "Beating 78 milliseconds" in article 2.

Relative CVaR error against WALL-CLOCK TIME on one core -- the same axes as
fig_baseline, for the same reason: sample count is the wrong x-axis.

Every point is measured (median time and RMSE over 20 replications from
results_variance_reduction.json). No extrapolation, so no dashed segments.
Diamonds are the direct timing runs at N(eps). The hollow square is the
Julia port of plain MC at the same N.

Renders 4 files: {de,en} x {light,dark}.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator

# Categorical slots 1-5 of the validated reference palette (validator: PASS
# both modes; light-mode contrast WARN on slots 3-5 -> marker shapes + legend).
LIGHT = dict(c=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"],
             surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#d8d7d2")
DARK = dict(c=["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"],
            surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", grid="#3a3a38")
MARKERS = ["o", "s", "^", "v", "D"]

METHODS = ["full", "qmc_chol", "qmc_pca", "is", "is_qmc_pca"]

# Inputs: results_vr_<universe>_<dist>.json from mc_variance_reduction.py and,
# if present, julia_accelerate_1.json from mc_baseline.jl (JL_OUT=...).
UNIVERSE = os.environ.get("MC_UNIVERSE", "sp100")
DIST = os.environ.get("MC_DIST", "normal")
RESULTS = os.environ.get("VR_RESULTS", f"results_vr_{UNIVERSE}_{DIST}.json")
JULIA = os.environ.get("JL_RESULT", "julia_accelerate_1.json")

STRINGS = {
    "de": dict(
        title="Gleiche Genauigkeit, andere Methode",
        sub="CVaR @ 99 % · {universe} · {dist} · voller Draw pro Pfad · "
            "1 Kern · {cpu} · alle Punkte gemessen",
        xlabel="Wall-Clock-Zeit, 1 Kern (Sekunden)",
        ylabel="relativer Fehler, CVaR @ 99 %",
        target="Zielgenauigkeit ε = 10⁻³",
        names=["Monte Carlo (NumPy)", "Quasi-MC, Cholesky", "Quasi-MC, PCA",
               "Importance Sampling", "IS + Quasi-MC (PCA)"],
        julia="dieselbe Rechnung in Julia",
        floor="Fixkosten: Sobol-Setup",
    ),
    "en": dict(
        title="Same accuracy, different method",
        sub="CVaR @ 99% · {universe} · {dist} · full draw per path · "
            "1 core · {cpu} · every point measured",
        xlabel="Wall-clock time, 1 core (seconds)",
        ylabel="Relative error, CVaR @ 99%",
        target="Target accuracy ε = 10⁻³",
        names=["Monte Carlo (NumPy)", "Quasi-MC, Cholesky", "Quasi-MC, PCA",
               "Importance sampling", "IS + quasi-MC (PCA)"],
        julia="same computation in Julia",
        floor="fixed cost: Sobol setup",
    ),
}

EPS = 1e-3


def fmt_ms(s, lang):
    if s >= 1:
        txt = f"{s:.2f} s"
    else:
        ms = s * 1e3
        txt = f"{ms:.0f} ms" if ms >= 10 else f"{ms:.1f} ms"
    return txt.replace(".", ",") if lang == "de" else txt


LABELS = {"de": {"sp100": "S&P-500-Top-100", "synthetic": "synthetisch",
                 "normal": "normalverteilt", "t": "Student-t"},
          "en": {"sp100": "S&P 500 top 100", "synthetic": "synthetic",
                 "normal": "normal", "t": "Student-t"}}


def cpu_brand():
    import subprocess
    return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                          capture_output=True, text=True).stdout.strip()


def render(lang, P, res, out, julia, cpu):
    L = LABELS[lang]
    S = {k: v.format(universe=L[UNIVERSE], dist=L[DIST], cpu=cpu)
         if isinstance(v, str) else v for k, v in STRINGS[lang].items()}
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=200)
    fig.patch.set_facecolor(P["surface"])
    ax.set_facecolor(P["surface"])

    for i, me in enumerate(METHODS):
        d = res["methods"][me]
        xs = [c["time_median_s"] for c in d["curve"]]
        ys = [c["relerr_cvar"] for c in d["curve"]]
        col = P["c"][i]
        ax.plot(xs, ys, "-", color=col, lw=2, zorder=3)
        ax.plot(xs, ys, MARKERS[i], ms=6.5, color=col, mec=P["surface"],
                mew=1.5, zorder=4, label=S["names"][i])
        t = d["timing"]["1"]["time_median_s"]
        ax.plot([t], [EPS], marker="D", ms=9, color=col, mec=P["ink"],
                mew=1.2, zorder=6)

    # Two callouts only: plain MC and whichever method is fastest here.
    t1 = {me: res["methods"][me]["timing"]["1"]["time_median_s"]
          for me in METHODS}
    best = min(t1, key=t1.get)
    for me, dy, ha in (("full", -26, "center"), (best, -26, "center")):
        t = res["methods"][me]["timing"]["1"]["time_median_s"]
        ax.annotate(fmt_ms(t, lang), xy=(t, EPS), xytext=(0, dy), textcoords="offset points",
                    ha=ha, color=P["ink"], fontsize=11, fontweight="bold",
                    zorder=7)

    # Julia: one measured point, same N as plain MC (normal case only).
    if julia:
        jt, je = julia["time_median_s"], julia["relerr_cvar"]
        ax.plot([jt], [je], "s", ms=10, mfc="none", mec=P["ink"], mew=1.6,
                zorder=6)
        ax.annotate(S["julia"], xy=(jt, je), xytext=(0, 14),
                    textcoords="offset points", ha="center", va="bottom",
                    color=P["ink2"], fontsize=9.5, zorder=7)

    ax.axhline(EPS, color=P["ink2"], lw=1, ls=":", alpha=.8, zorder=2)
    ax.annotate(S["target"], xy=(4e-5, EPS * 1.25), ha="left",
                color=P["ink2"], fontsize=10)

    # The quasi-MC curves start vertical: at tiny N the Sobol engine's setup
    # dominates. Say so on the chart rather than let it look like noise.
    q = res["methods"]["qmc_pca"]["curve"][0]
    ax.annotate(S["floor"], xy=(q["time_median_s"], q["relerr_cvar"]),
                xytext=(14, 6), textcoords="offset points",
                color=P["ink2"], fontsize=9.5)

    ax.set_xscale("log"); ax.set_yscale("log")
    t_max = max([c["time_median_s"] for me in METHODS
                 for c in res["methods"][me]["curve"]] + list(t1.values()))
    ax.set_xlim(3e-5, max(12, t_max * 2.5)); ax.set_ylim(1e-6, 1.0)
    ax.set_xlabel(S["xlabel"], color=P["ink2"], fontsize=11.5)
    ax.set_ylabel(S["ylabel"], color=P["ink2"], fontsize=11.5)
    ax.set_title(S["title"], color=P["ink"], fontsize=14.5,
                 fontweight="bold", loc="left", pad=16)
    ax.annotate(S["sub"], xy=(0, 1.012), xycoords="axes fraction",
                color=P["ink2"], fontsize=9.5)

    ax.grid(True, which="major", color=P["grid"], lw=.7, alpha=.9, zorder=0)
    ax.grid(True, which="minor", color=P["grid"], lw=.4, alpha=.5, zorder=0)
    ax.xaxis.set_minor_locator(LogLocator(base=10, subs="auto", numticks=20))
    for s in ax.spines.values():
        s.set_color(P["grid"])
    ax.tick_params(colors=P["ink2"], labelsize=10)

    leg = ax.legend(loc="lower left", frameon=True, fontsize=10,
                    facecolor=P["surface"], edgecolor=P["grid"])
    for t in leg.get_texts():
        t.set_color(P["ink"])

    fig.tight_layout()
    fig.savefig(out, facecolor=P["surface"])
    print(f"wrote {out}")


if __name__ == "__main__":
    res = json.load(open(RESULTS))
    julia = None
    if DIST == "normal" and os.path.exists(JULIA):
        julia = json.load(open(JULIA))
    cpu = cpu_brand()
    tag = f"{UNIVERSE}_{DIST}"
    for lang in ("de", "en"):
        for mode, P in (("light", LIGHT), ("dark", DARK)):
            render(lang, P, res, f"fig_methods_{tag}_{lang}_{mode}.png",
                   julia, cpu)
