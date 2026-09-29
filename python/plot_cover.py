"""Cover images for the articles: 1920 x 1080, the palette of the charts.

Medium and LinkedIn show the cover full width and use it as the preview
image, so it carries the article's one number, not decoration. Each cover
is a headline over a single chart; the data are the article's own. The
headline states what the chart shows -- not the article title, which the
platforms print right above the image anyway.

    python python/plot_cover.py            # all covers, both languages
    python python/plot_cover.py 1          # article 1 only
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
}


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
    fig.text(0.07, 0.86, c["kicker"], fontsize=20, color=P["ink2"],
             fontweight="bold")
    fig.text(0.07, 0.72, c["title"], fontsize=c["title_size"],
             color=P["ink"], fontweight="bold")
    fig.text(0.07, 0.645, c["subtitle"], fontsize=c["subtitle_size"],
             color=P["ink2"])

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
    ax.set_xscale("log")
    ax.set_xlim(base, 60)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_yticks([])
    ax.set_xticks([1e-7, 1e-5, 1e-3, 1e-1, 10])
    ax.set_xticklabels(["100 ns", "10 µs", "1 ms", "100 ms", "10 s"],
                       fontsize=18, color=P["ink2"])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(P["grid"])
    ax.tick_params(axis="x", colors=P["ink2"], length=0)
    ax.grid(axis="x", color=P["grid"], lw=1)
    ax.set_axisbelow(True)

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


RENDER = {1: render_sample_times}

if __name__ == "__main__":
    wanted = [int(a) for a in sys.argv[1:]] or sorted(COVERS)
    for article in wanted:
        for lang, c in COVERS[article].items():
            RENDER[article](c, os.path.join("figures", c["out"]))
