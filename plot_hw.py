"""Figure for article 6: P(flag = 1) after k Grover steps on real hardware.

Ideal curve, the 50% level that full noise converges to, measured points with
binomial 1-sigma bars, and the noise-model preview made before submission
(dashed). Renders {de,en} x {light,dark}.
"""
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LIGHT = dict(c=["#2a78d6", "#eb6834", "#1baf7a", "#eda100"], surface="#fcfcfb",
             ink="#0b0b0b", ink2="#52514e", grid="#d8d7d2")
DARK = dict(c=["#3987e5", "#d95926", "#199e70", "#c98500"], surface="#1a1a19",
            ink="#ffffff", ink2="#c3c2b7", grid="#3a3a38")
MARK = ["o", "s", "^", "D"]
DEVICES = ["IQM Garnet", "IQM Emerald", "Rigetti Cepheus-1", "IonQ Forte Enterprise 1"]

S = {
    "de": dict(title="Nach zwei Drehungen dreht nur noch ein Gerät",
               sub="Kleinste QAE-Version (3 Qubits, a = 6,6 %) · 1.000 Shots je "
                   "Punkt (IonQ 200) · gestrichelt = Prognose vor dem Einreichen",
               x="Grover-Schritte k", y="gemessen: P(Flag = 1)",
               ideal="ideal (rauschfrei)", noise="vollständiges Rauschen (50 %)"),
    "en": dict(title="After two turns, only one machine still turns",
               sub="Smallest QAE version (3 qubits, a = 6.6%) · 1,000 shots per "
                   "point (IonQ 200) · dashed = prediction before submission",
               x="Grover steps k", y="Measured: P(flag = 1)",
               ideal="ideal (noiseless)", noise="full noise (50%)"),
}


def render(lang, P, out):
    L = S[lang]
    tasks = json.load(open("hw_tasks.json"))
    prev = json.load(open("results_hw_preview.json"))
    a = json.load(open("results_hw_check.json"))["a"]
    th = math.asin(math.sqrt(a))
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=200)
    fig.patch.set_facecolor(P["surface"]); ax.set_facecolor(P["surface"])

    kk = [i / 20 for i in range(0, 47)]
    ax.plot(kk, [math.sin((2 * k + 1) * th) ** 2 for k in kk], color=P["ink2"],
            lw=1.6, zorder=2)
    ax.plot([0, 1, 2], [math.sin((2 * k + 1) * th) ** 2 for k in (0, 1, 2)],
            "o", color=P["ink2"], ms=6, zorder=3, label=L["ideal"])
    ax.axhline(0.5, color=P["ink2"], lw=1, ls=":", zorder=1, label=L["noise"])

    dx = {-1: 0}
    for i, dev in enumerate(DEVICES):
        pts = sorted([t for t in tasks if t["device"] == dev and "p_flag" in t],
                     key=lambda t: t["k"])
        if not pts:
            continue
        off = (i - 1.5) * 0.06
        ks = [t["k"] + off for t in pts]
        ps = [t["p_flag"] for t in pts]
        es = [math.sqrt(p * (1 - p) / t["shots"]) for p, t in zip(ps, pts)]
        col = P["c"][i]
        ax.errorbar(ks, ps, yerr=es, fmt=MARK[i] + "-", color=col, lw=2, ms=8,
                    mec=P["surface"], mew=1.5, capsize=3, zorder=5, label=dev)
        pv = prev.get(dev)
        if pv:
            ax.plot([k + off for k in (0, 1, 2)], pv["p_flag"], ls=(0, (4, 3)),
                    color=col, lw=1.4, alpha=.8, zorder=4)

    ax.set_xlim(-0.25, 2.35); ax.set_ylim(0, 1)
    ax.set_xticks([0, 1, 2])
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel(L["x"], color=P["ink2"], fontsize=11.5)
    ax.set_ylabel(L["y"], color=P["ink2"], fontsize=11.5)
    ax.set_title(L["title"], color=P["ink"], fontsize=14.5, fontweight="bold",
                 loc="left", pad=16)
    ax.annotate(L["sub"], xy=(0, 1.012), xycoords="axes fraction",
                color=P["ink2"], fontsize=9.5)
    ax.grid(True, color=P["grid"], lw=.7, alpha=.9, zorder=0)
    for sp in ax.spines.values():
        sp.set_color(P["grid"])
    ax.tick_params(colors=P["ink2"], labelsize=10)
    leg = ax.legend(loc="upper left", frameon=True, fontsize=10,
                    facecolor=P["surface"], edgecolor=P["grid"])
    for t in leg.get_texts():
        t.set_color(P["ink"])
    fig.tight_layout()
    fig.savefig(out, facecolor=P["surface"])
    print(f"wrote {out}")


if __name__ == "__main__":
    for lang in ("de", "en"):
        for mode, P in (("light", LIGHT), ("dark", DARK)):
            render(lang, P, f"fig_hw_{lang}_{mode}.png")
