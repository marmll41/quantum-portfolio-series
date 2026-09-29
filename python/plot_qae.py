"""Figure for article 5: relative error of a tail-probability estimate against
the number of oracle calls. This is deliberately the axis the series refuses
elsewhere -- it shows the mathematics of QAE, not its speed, and the subtitle
says so.

Renders 4 files: {de,en} x {light,dark}.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator

LIGHT = dict(c=["#2a78d6", "#eb6834", "#1baf7a"], surface="#fcfcfb",
             ink="#0b0b0b", ink2="#52514e", grid="#d8d7d2")
DARK = dict(c=["#3987e5", "#d95926", "#199e70"], surface="#1a1a19",
            ink="#ffffff", ink2="#c3c2b7", grid="#3a3a38")

S = {
    "de": dict(
        title="Das quadratische Speedup ist echt — mit großer Konstante",
        sub="Tail-Wahrscheinlichkeit 1 % · MLAE, rauschfrei · x-Achse bewusst "
            "Orakel-Aufrufe, nicht Sekunden",
        x="Orakel-Aufrufe (Anwendungen von A)",
        y="relativer Fehler (RMSE)",
        mlae400="MLAE, 400 Shots je Circuit", mlae100="MLAE, 100 Shots je Circuit",
        med100="… davon Median", mc="Sampling ohne Grover (Monte Carlo)",
        eps="ε = 10⁻³", slope1="Steigung −1", slope05="Steigung −½",
    ),
    "en": dict(
        title="The quadratic speedup is real — with a large constant",
        sub="Tail probability 1% · MLAE, noiseless · x-axis deliberately "
            "oracle calls, not seconds",
        x="Oracle calls (applications of A)",
        y="Relative error (RMSE)",
        mlae400="MLAE, 400 shots per circuit", mlae100="MLAE, 100 shots per circuit",
        med100="… its median", mc="Sampling without Grover (Monte Carlo)",
        eps="ε = 10⁻³", slope1="slope −1", slope05="slope −½",
    ),
}


def render(lang, P, out):
    L = S[lang]
    s400 = json.load(open("results_qae_scaling_s400.json"))
    s100 = json.load(open("results_qae_scaling_s100.json"))
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=200)
    fig.patch.set_facecolor(P["surface"]); ax.set_facecolor(P["surface"])

    def xy(rows, key):
        return [r["oracle_calls"] for r in rows], [r[key] for r in rows]

    x, y = xy(s400["mlae"], "relerr")
    ax.plot(x, y, "-o", color=P["c"][0], lw=2, ms=7, mec=P["surface"], mew=1.5,
            label=L["mlae400"], zorder=4)
    x, y = xy(s100["mlae"], "relerr")
    ax.plot(x, y, "-s", color=P["c"][1], lw=2, ms=6.5, mec=P["surface"],
            mew=1.5, label=L["mlae100"], zorder=4)
    x, y = xy(s100["mlae"], "median")
    ax.plot(x, y, ":", color=P["c"][1], lw=2, label=L["med100"], zorder=3)
    mc = s400["mc"] + s100["mc"]
    mc.sort(key=lambda r: r["oracle_calls"])
    x, y = xy(mc, "relerr")
    ax.plot(x, y, "-^", color=P["c"][2], lw=2, ms=6.5, mec=P["surface"],
            mew=1.5, label=L["mc"], zorder=4)

    ax.axhline(1e-3, color=P["ink2"], lw=1, ls=(0, (2, 2)), zorder=2)
    ax.annotate(L["eps"], xy=(1.3e2, 1.15e-3), color=P["ink2"], fontsize=10)

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(80, 3e6); ax.set_ylim(1e-4, 2)
    ax.set_xlabel(L["x"], color=P["ink2"], fontsize=11.5)
    ax.set_ylabel(L["y"], color=P["ink2"], fontsize=11.5)
    ax.set_title(L["title"], color=P["ink"], fontsize=14.5, fontweight="bold",
                 loc="left", pad=16)
    ax.annotate(L["sub"], xy=(0, 1.012), xycoords="axes fraction",
                color=P["ink2"], fontsize=9.5)
    ax.grid(True, which="major", color=P["grid"], lw=.7, alpha=.9, zorder=0)
    ax.grid(True, which="minor", color=P["grid"], lw=.4, alpha=.5, zorder=0)
    ax.xaxis.set_minor_locator(LogLocator(base=10, subs="auto", numticks=20))
    for sp in ax.spines.values():
        sp.set_color(P["grid"])
    ax.tick_params(colors=P["ink2"], labelsize=10)
    leg = ax.legend(loc="lower left", frameon=True, fontsize=10,
                    facecolor=P["surface"], edgecolor=P["grid"])
    for t in leg.get_texts():
        t.set_color(P["ink"])
    fig.tight_layout()
    fig.savefig(out, facecolor=P["surface"])
    print(f"wrote {out}")


if __name__ == "__main__":
    for lang in ("de", "en"):
        for mode, P in (("light", LIGHT), ("dark", DARK)):
            render(lang, P, f"fig_qae_scaling_{lang}_{mode}.png")
