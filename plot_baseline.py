"""Central figure of the series: relative error vs WALL-CLOCK TIME.

Not error vs sample count. The whole argument of the series is that sample
count is the wrong x-axis, so this chart refuses to draw it.

Markers are measured points. Lines are the 1/sqrt(N) law with its constant
calibrated at the largest measured N; the dashed continuation is
extrapolation and is drawn differently so it cannot be mistaken for data.

Renders 4 files: {de,en} x {light,dark}.
"""
import json
import math
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator

# Categorical slots 1-3 of the validated reference palette.
LIGHT = dict(s1="#2a78d6", s2="#eb6834", s3="#1baf7a",
             surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#d8d7d2")
DARK = dict(s1="#3987e5", s2="#d95926", s3="#199e70",
            surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", grid="#3a3a38")

STRINGS = {
    "de": dict(
        title="Klassisches Monte Carlo: Zeit bis zur Zielgenauigkeit",
        sub="{cpu} · {cores} Kerne · NumPy {numpy} · {universe} · exakte "
            "Referenz aus geschlossener Form · gestrichelt = extrapoliert",
        xlabel="Wall-Clock-Zeit (Sekunden)",
        ylabel="relativer Fehler, CVaR @ 99 %",
        target="Zielgenauigkeit ε = 10⁻³",
        s1="100 Assets, 1 Kern",
        s2="100 Assets, {cores} Kerne",
        s3="analytisch reduziert, 1 Kern",
    ),
    "en": dict(
        title="Classical Monte Carlo: time to target accuracy",
        sub="{cpu} · {cores} cores · NumPy {numpy} · {universe} · exact "
            "closed-form reference · dashed = extrapolated",
        xlabel="Wall-clock time (seconds)",
        ylabel="Relative error, CVaR @ 99%",
        target="Target accuracy ε = 10⁻³",
        s1="100 assets, 1 core",
        s2="100 assets, {cores} cores",
        s3="analytically reduced, 1 core",
    ),
}

TARGET_EPS = 1e-3          # a realistic risk-reporting accuracy
KEY = "cvar"               # CVaR@99% is the estimator QAE papers target
UNIVERSE_LABEL = {"de": {"sp100": "S&P-500-Top-100", "synthetic": "synthetisch"},
                  "en": {"sp100": "S&P 500 top 100", "synthetic": "synthetic"}}
SUFFIX = os.environ.get("MC_DIST", "normal")
SUFFIX = "" if SUFFIX == "normal" else f"_{SUFFIX}"


def load():
    d = json.load(open(f"results_1core{SUFFIX}.json"))
    return d["results"]["full"], d["results"]["reduced"]


def load_throughput():
    """Multi-core throughput at the largest worker count, persistent pool."""
    tp = json.load(open(f"throughput{SUFFIX}.json"))
    best = max(tp["rows"], key=lambda r: r["workers"])
    return best["paths_per_s"], best["workers"], tp


THROUGHPUT_MC, CORES, _TP = load_throughput()


def direct_times():
    """Direct wall-clock of plain MC at N(eps): (1 core, all workers)."""
    dist = os.environ.get("MC_DIST", "normal")
    path = f"results_vr_sp100_{dist}.json"
    if not os.path.exists(path):
        return None
    t = json.load(open(path))["methods"]["full"]["timing"]
    return t["1"]["time_median_s"], t[max(t, key=int)]["time_median_s"]


def law_constant(cells):
    """C in err = C / sqrt(N): the exact asymptotic constant from
    mc_baseline.cvar_error_constant. Both samplers draw the same loss
    distribution, so they share it; the markers show the measurement."""
    return json.load(open(f"results_1core{SUFFIX}.json"))[
        "cvar_error_constant_exact"]


def asymptotic_throughput(cells):
    """Throughput at the largest N -- small-N cells flatter the cache."""
    return max(cells, key=lambda c: c["n"])["paths_per_s"]


def render(lang: str, P: dict, out: str):
    env = json.load(open(f"results_1core{SUFFIX}.json"))["env"]
    fill = dict(cpu=_TP["cpu"], cores=CORES,
                numpy=env["numpy"],
                universe=UNIVERSE_LABEL[lang].get(env.get("universe"),
                                                  "synthetic"))
    S = {k: v.format(**fill) if isinstance(v, str) else v
         for k, v in STRINGS[lang].items()}
    full, reduced = load()
    C_full, C_red = law_constant(full), law_constant(reduced)
    tp_full, tp_red = asymptotic_throughput(full), asymptotic_throughput(reduced)

    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=200)
    fig.patch.set_facecolor(P["surface"])
    ax.set_facecolor(P["surface"])

    specs = [
        (S["s1"], P["s1"], C_full, tp_full,
         [(c["time_median_s"], c[f"relerr_{KEY}"]) for c in full]),
        (S["s2"], P["s2"], C_full, THROUGHPUT_MC,
         [(c["n"] / THROUGHPUT_MC, c[f"relerr_{KEY}"]) for c in full]),
        (S["s3"], P["s3"], C_red, tp_red,
         [(c["time_median_s"], c[f"relerr_{KEY}"]) for c in reduced]),
    ]

    T_LO, T_HI = 1e-4, 3e6
    # Each label sits at its own error level so the three cannot collide.
    LABEL_AT = [2.2e-2, 2.6e-3, 9e-4]
    for (label, color, C, tp, pts), lvl in zip(specs, LABEL_AT):
        t_meas_max = max(p[0] for p in pts)
        for lo, hi, style in ((T_LO, t_meas_max, "-"),
                              (t_meas_max, T_HI, (0, (5, 3)))):
            t = np.logspace(math.log10(lo), math.log10(hi), 200)
            ax.plot(t, C / np.sqrt(t * tp), color=color, lw=2, ls=style,
                    alpha=1.0 if style == "-" else .75, zorder=3)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.plot(xs, ys, "o", ms=8, color=color, zorder=4,
                mec=P["surface"], mew=2, label=label)
        # Direct label on the curve at this series' own error level.
        ax.annotate(label, xy=((C / lvl) ** 2 / tp, lvl), xytext=(10, 8),
                    textcoords="offset points", color=color,
                    fontsize=10.5, fontweight="bold", zorder=5)

    ax.axhline(TARGET_EPS, color=P["ink2"], lw=1, ls=":", alpha=.8, zorder=2)
    ax.annotate(S["target"], xy=(4e5, TARGET_EPS * 1.4), ha="right",
                color=P["ink2"], fontsize=10)

    # Time to the target, per series. dy staggers the callouts. For the
    # multi-core series the throughput line is only the scaling guide; the
    # diamond is the DIRECT end-to-end measurement at N(eps) from
    # results_vr (draw + gather + estimate), which is what the text quotes.
    direct = direct_times()
    for i, ((label, color, C, tp, pts), dy) in enumerate(
            zip(specs, (-21, -37, -21))):
        t_req = (C / TARGET_EPS) ** 2 / tp
        if i < 2 and direct is not None:      # 1 core, all cores
            t_req = direct[i]
        ax.plot([t_req], [TARGET_EPS], marker="D", ms=7, color=color,
                mec=P["surface"], mew=1.5, zorder=6)
        txt = f"{t_req:.2f} s" if t_req >= 1 else f"{t_req*1000:.0f} ms"
        if lang == "de":
            txt = txt.replace(".", ",")
        ax.annotate(txt, xy=(t_req, TARGET_EPS), xytext=(0, dy),
                    textcoords="offset points", ha="center",
                    color=color, fontsize=10, fontweight="bold", zorder=6)

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(T_LO, T_HI); ax.set_ylim(5e-7, 2.4e-1)
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

    leg = ax.legend(loc="upper right", frameon=True, fontsize=10.5,
                    facecolor=P["surface"], edgecolor=P["grid"])
    for t in leg.get_texts():
        t.set_color(P["ink"])

    fig.tight_layout()
    fig.savefig(out, facecolor=P["surface"])
    print(f"wrote {out}")


if __name__ == "__main__":
    for lang in ("de", "en"):
        for mode, P in (("light", LIGHT), ("dark", DARK)):
            render(lang, P, f"fig_baseline{SUFFIX}_{lang}_{mode}.png")

    full, reduced = load()
    C_full, C_red = law_constant(full), law_constant(reduced)
    tp1, tp_red = asymptotic_throughput(full), asymptotic_throughput(reduced)

    def fmt(s):
        if s < 1: return f"{s*1000:,.1f} ms"
        if s < 3600: return f"{s:,.1f} s"
        if s < 86400: return f"{s/3600:,.1f} h"
        return f"{s/86400:,.1f} d"

    print(f"\n{'eps':>8} {'N required':>22} {'1 core':>14} {f'{CORES} cores':>14} "
          f"{'reduced':>14}")
    for eps in (1e-2, 1e-3, 1e-4, 1e-5, 1e-6):
        n, nr = (C_full / eps) ** 2, (C_red / eps) ** 2
        print(f"{eps:>8g} {n:>22,.0f} {fmt(n/tp1):>14} "
              f"{fmt(n/THROUGHPUT_MC):>14} {fmt(nr/tp_red):>14}")
