"""Cover images for the articles: 1920 x 1080, the palette of the charts.

Medium and LinkedIn show the cover full width and use it as the preview
image, so it carries the article's one number, not decoration. Each cover
is a headline over a single chart; the data are the article's own. The
headline states what the chart shows -- not the article title, which the
platforms print right above the image anyway.

    python python/plot_cover.py            # all covers, both languages
    python python/plot_cover.py 1          # article 1 only
    python python/plot_cover.py 2b         # article 2b only
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

P = dict(s1="#2a78d6", s2="#eb6834", s3="#1baf7a",
         surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#d8d7d2")

# Article 1: time for one sample, from the table in the article
# (classical rows from article 2, Garnet rows from article 4, "gates only"
# rows are estimates for ~1,000 two-qubit gates). Measured rows are run time
# divided by samples -- 268 ms / 3,102,840 paths on 14 cores, Garnet task
# time / 100 shots -- hence "average per sample in a full run", not the
# latency of one isolated sample. The queued row has no single value and is
# left out.
SAMPLE_TIMES = [  # (lo, hi) in seconds, quantum?
    ((86e-9, 86e-9), False),
    ((0.6e-6, 0.6e-6), False),
    ((20e-6, 40e-6), True),
    ((11e-3, 11e-3), True),
    ((33e-3, 33e-3), True),
    ((0.97, 0.97), True),
]

# Article 2: time to target accuracy for plain Monte Carlo on 14 cores, from
# the table in the article (N from the exact error constant, time from the
# measured 14-core throughput). Every factor of ten in accuracy is a factor
# of a hundred in paths, hence in time.
TIME_TO_EPS = [  # (eps exponent, seconds)
    (-2, 2.2e-3),
    (-3, 0.268),
    (-4, 22.0),
    (-5, 37 * 60.0),
    (-6, 2.6 * 86400.0),
]

# Article 2b: time to eps = 1e-3 on 14 cores per method, normal and
# Student-t, from the table in the article (results/results_vr_sp100_*.json,
# results/julia_accelerate_14.json). Julia was run for the normal case only.
METHODS = [  # (normal ms, t ms or None)
    (268.0, 1853.0),     # NumPy, plain MC
    (173.0, None),       # Julia, Accelerate
    (17.0, 109.0),       # quasi-MC, PCA order
    (4.7, 1659.0),       # importance sampling
]

COVERS = {
    1: {
        "en": dict(
            out="cover_article01_en.png",
            kicker="QUANTUM PORTFOLIO RISK ON AWS BRAKET  ·  PART 1",
            title="Up to seven orders of magnitude per sample", title_size=48,
            subtitle="Average time per sample in a full run — classical "
                     "Monte Carlo vs. quantum hardware", subtitle_size=26,
            labels=["Classical, 14 cores", "Classical, 1 core",
                    "Superconducting, gates only", "IQM Garnet, per shot",
                    "IQM Garnet, at the client", "Trapped ion, gates only"],
            legend=("classical Monte Carlo", "quantum hardware", 0.255),
            footer="Measured: classical, IQM Garnet. Estimated: gates only.",
            footer_size=18),
        "de": dict(
            out="cover_artikel01_de.png",
            kicker="QUANTEN-PORTFOLIORISIKO AUF AWS BRAKET  ·  TEIL 1",
            title="Bis zu sieben Größenordnungen pro Sample", title_size=48,
            subtitle="Mittlere Zeit pro Sample im vollen Lauf — klassisches "
                     "Monte Carlo gegen Quantenhardware", subtitle_size=24,
            labels=["Klassisch, 14 Kerne", "Klassisch, 1 Kern",
                    "Supraleitend, nur Gates", "IQM Garnet, pro Shot",
                    "IQM Garnet, beim Client", "Ionenfalle, nur Gates"],
            legend=("klassisches Monte Carlo", "Quantenhardware", 0.27),
            footer="Gemessen: klassisch, IQM Garnet. Geschätzt: nur Gates.",
            footer_size=18),
    },
    2: {
        "en": dict(
            out="cover_article02_en.png",
            kicker="QUANTUM PORTFOLIO RISK ON AWS BRAKET  ·  PART 2",
            title="Ten times the accuracy, a hundred times the time",
            title_size=42,
            subtitle="Plain Monte Carlo, CVaR 99% of the S&P 500 top 100, "
                     "14 cores — time to target accuracy ε", subtitle_size=26,
            eps_label="ε = {} ({})", pct=["1%", "0.1%", "0.01%", "0.001%",
                                          "0.0001%"],
            times=["2.2 ms", "268 ms", "22 s", "37 min", "2.6 days"],
            footer="ε relative to the closed-form CVaR. Apple M3 Max, "
                   "NumPy on Accelerate.", footer_size=18),
        "de": dict(
            out="cover_artikel02_de.png",
            kicker="QUANTEN-PORTFOLIORISIKO AUF AWS BRAKET  ·  TEIL 2",
            title="Zehnfache Genauigkeit, hundertfache Zeit", title_size=48,
            subtitle="Einfaches Monte Carlo, CVaR 99 % der S&P-500-Top-100, "
                     "14 Kerne — Zeit bis zur Zielgenauigkeit ε",
            subtitle_size=24,
            eps_label="ε = {} ({})", pct=["1 %", "0,1 %", "0,01 %",
                                          "0,001 %", "0,0001 %"],
            times=["2,2 ms", "268 ms", "22 s", "37 min", "2,6 Tage"],
            footer="ε relativ zum exakten CVaR. Apple M3 Max, NumPy auf "
                   "Accelerate.", footer_size=18),
    },
    "2b": {
        "en": dict(
            out="cover_article02b_en.png",
            kicker="QUANTUM PORTFOLIO RISK ON AWS BRAKET  ·  PART 2B",
            title="The method is worth 57×, the language 1.5×", title_size=46,
            subtitle="CVaR 99% of the S&P 500 top 100, ε = 10⁻³, 14 cores — "
                     "time per method", subtitle_size=26,
            labels=["NumPy, plain Monte Carlo", "Julia, Apple Accelerate",
                    "Quasi-Monte Carlo, PCA", "Importance sampling"],
            legend=("normal returns", "fat tails (Student-t)", 0.235),
            fmt=lambda ms: (f"{ms:,.0f} ms" if ms >= 10 else f"{ms:.1f} ms"),
            na="not run",
            footer="Under fat tails importance sampling falls to 1.1×; "
                   "quasi-MC keeps 17×.", footer_size=18),
        "de": dict(
            out="cover_artikel02b_de.png",
            kicker="QUANTEN-PORTFOLIORISIKO AUF AWS BRAKET  ·  TEIL 2B",
            title="Die Methode bringt 57×, die Sprache 1,5×", title_size=46,
            subtitle="CVaR 99 % der S&P-500-Top-100, ε = 10⁻³, 14 Kerne — "
                     "Zeit je Verfahren", subtitle_size=26,
            labels=["NumPy, einfaches Monte Carlo", "Julia, Apple Accelerate",
                    "Quasi-Monte-Carlo, PCA", "Importance Sampling"],
            legend=("Normalverteilung", "Fat Tails (Student-t)", 0.215),
            fmt=lambda ms: (f"{ms:,.0f} ms".replace(",", ".") if ms >= 10
                            else f"{ms:.1f} ms".replace(".", ",")),
            na="nicht gemessen",
            footer="Bei Fat Tails fällt Importance Sampling auf 1,1×; "
                   "Quasi-MC hält 17×.", footer_size=18),
    },
}


def title_block(fig, c):
    fig.text(0.07, 0.86, c["kicker"], fontsize=20, color=P["ink2"],
             fontweight="bold")
    fig.text(0.07, 0.72, c["title"], fontsize=c["title_size"],
             color=P["ink"], fontweight="bold")
    fig.text(0.07, 0.645, c["subtitle"], fontsize=c["subtitle_size"],
             color=P["ink2"])


def style_log_axis(ax, ticks, labels):
    ax.set_xscale("log")
    ax.set_yticks([])
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=18, color=P["ink2"])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(P["grid"])
    ax.tick_params(axis="x", colors=P["ink2"], length=0)
    ax.grid(axis="x", color=P["grid"], lw=1)
    ax.set_axisbelow(True)


def fmt_time(lo, hi):
    if hi < 1e-6:
        return f"{lo * 1e9:.0f} ns"
    if hi < 1e-5:
        return f"{lo * 1e6:.1f} µs"
    if hi < 1e-3:
        return f"{lo * 1e6:.0f}–{hi * 1e6:.0f} µs"
    if hi < 1:
        return f"{lo * 1e3:.0f} ms"
    return f"{lo:.2f} s"


def render_sample_times(c, out):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor(P["surface"])
    title_block(fig, c)

    ax = fig.add_axes([0.35, 0.13, 0.57, 0.44])
    ax.set_facecolor(P["surface"])
    n = len(SAMPLE_TIMES)
    base = 1e-8                       # left edge of the log axis
    for yi, ((lo, hi), quantum), label in zip(np.arange(n)[::-1],
                                              SAMPLE_TIMES, c["labels"]):
        ax.barh(yi, hi - base, left=base, height=0.62,
                color=P["s2"] if quantum else P["s1"])
        ax.text(hi * 1.6, yi, fmt_time(lo, hi), va="center", fontsize=22,
                color=P["ink"])
        fig.text(0.07, 0.13 + 0.44 * (yi + 0.5) / n, label, va="center",
                 fontsize=22, color=P["ink"])
    style_log_axis(ax, [1e-7, 1e-5, 1e-3, 1e-1, 10],
                   ["100 ns", "10 µs", "1 ms", "100 ms", "10 s"])
    ax.set_xlim(base, 60)
    ax.set_ylim(-0.6, n - 0.4)

    classical, quantum, x2 = c["legend"]
    fig.text(0.07, 0.045, "■", fontsize=20, color=P["s1"])
    fig.text(0.085, 0.045, classical, fontsize=18, color=P["ink2"])
    fig.text(x2, 0.045, "■", fontsize=20, color=P["s2"])
    fig.text(x2 + 0.015, 0.045, quantum, fontsize=18, color=P["ink2"])
    fig.text(0.93, 0.045, c["footer"], ha="right",
             fontsize=c["footer_size"], color=P["ink2"], style="italic")

    os.makedirs("figures", exist_ok=True)
    fig.savefig(out, facecolor=P["surface"])
    plt.close(fig)
    print(f"wrote {out}")


def render_time_to_eps(c, out):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor(P["surface"])
    title_block(fig, c)

    ax = fig.add_axes([0.35, 0.13, 0.57, 0.44])
    ax.set_facecolor(P["surface"])
    n = len(TIME_TO_EPS)
    base = 1e-4
    sup = {-2: "10⁻²", -3: "10⁻³", -4: "10⁻⁴", -5: "10⁻⁵", -6: "10⁻⁶"}
    for yi, (e, sec), pct, txt in zip(np.arange(n)[::-1], TIME_TO_EPS,
                                      c["pct"], c["times"]):
        headline = e == -3            # the target of the series
        ax.barh(yi, sec - base, left=base, height=0.62,
                color=P["s1"] if headline else P["grid"])
        ax.text(sec * 1.6, yi, txt, va="center", fontsize=22,
                color=P["ink"], fontweight="bold" if headline else "normal")
        fig.text(0.07, 0.13 + 0.44 * (yi + 0.5) / n,
                 c["eps_label"].format(sup[e], pct), va="center",
                 fontsize=22, color=P["ink"],
                 fontweight="bold" if headline else "normal")
    style_log_axis(ax, [1e-3, 1, 60, 3600, 86400],
                   ["1 ms", "1 s", "1 min", "1 h", "1 d"])
    ax.set_xlim(base, 3e6)
    ax.set_ylim(-0.6, n - 0.4)

    fig.text(0.93, 0.045, c["footer"], ha="right",
             fontsize=c["footer_size"], color=P["ink2"], style="italic")
    os.makedirs("figures", exist_ok=True)
    fig.savefig(out, facecolor=P["surface"])
    plt.close(fig)
    print(f"wrote {out}")


def render_methods(c, out):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor(P["surface"])
    title_block(fig, c)

    ax = fig.add_axes([0.35, 0.13, 0.57, 0.44])
    ax.set_facecolor(P["surface"])
    n = len(METHODS)
    base = 1.0                               # ms, left edge of the log axis
    for yi, (normal, fat), label in zip(np.arange(n)[::-1], METHODS,
                                        c["labels"]):
        for dy, ms, colour in ((0.19, normal, P["s1"]), (-0.19, fat, P["s2"])):
            if ms is None:
                ax.text(base * 1.3, yi + dy, c["na"], va="center",
                        fontsize=18, color=P["ink2"], style="italic")
                continue
            ax.barh(yi + dy, ms - base, left=base, height=0.34, color=colour)
            ax.text(ms * 1.25, yi + dy, c["fmt"](ms), va="center",
                    fontsize=20, color=P["ink"])
        fig.text(0.07, 0.13 + 0.44 * (yi + 0.5) / n, label, va="center",
                 fontsize=22, color=P["ink"])
    style_log_axis(ax, [1, 10, 100, 1000],
                   ["1 ms", "10 ms", "100 ms", "1 s"])
    ax.set_xlim(base, 6000)
    ax.set_ylim(-0.6, n - 0.4)

    normal, fat, x2 = c["legend"]
    fig.text(0.07, 0.045, "■", fontsize=20, color=P["s1"])
    fig.text(0.085, 0.045, normal, fontsize=18, color=P["ink2"])
    fig.text(x2, 0.045, "■", fontsize=20, color=P["s2"])
    fig.text(x2 + 0.015, 0.045, fat, fontsize=18, color=P["ink2"])
    fig.text(0.93, 0.045, c["footer"], ha="right",
             fontsize=c["footer_size"], color=P["ink2"], style="italic")
    os.makedirs("figures", exist_ok=True)
    fig.savefig(out, facecolor=P["surface"])
    plt.close(fig)
    print(f"wrote {out}")


RENDER = {1: render_sample_times, 2: render_time_to_eps, "2b": render_methods}

if __name__ == "__main__":
    keys = {str(k): k for k in COVERS}
    wanted = [keys[a] for a in sys.argv[1:]] or list(COVERS)
    for article in wanted:
        for lang, c in COVERS[article].items():
            RENDER[article](c, os.path.join("figures", c["out"]))
