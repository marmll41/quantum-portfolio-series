"""Central figure of Article 4: where the time in one loop iteration goes.

Top panel   the four measured variants, on a LINEAR scale. Linear on purpose:
            the local simulator at 2.4 ms has to be invisible next to the
            cloud bars, because that is the finding.
Bottom      the Garnet iteration broken into its layers. The layers are
            derived from measurement, not assumed:
              polling   = client(1 s poll) - client(0.1 s poll)
              net+SDK   = client(0.1 s poll) - service
              service   = Braket's own createdAt -> endedAt
            The actual quantum execution sits inside the service segment and
            is far too small to draw, so it is annotated instead of stacked.

Renders {de,en} x {light,dark}.
"""
import json
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt

LIGHT = dict(s1="#2a78d6", s2="#eb6834", s3="#1baf7a", s4="#eda100",
             surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#d8d7d2")
DARK = dict(s1="#3987e5", s2="#d95926", s3="#199e70", s4="#c98500",
            surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", grid="#3a3a38")

S = {
 "de": dict(
   title="Eine Iteration: wo die Zeit hingeht",
   sub="4-Qubit-Circuit, 100 Shots, 25 Iterationen je Variante · Median · "
       "Queue leer · gemessen 2026-09-23",
   xlabel="Median je Iteration (Millisekunden)",
   p2title="Dieselbe Iteration auf IQM Garnet, in Schichten zerlegt",
   bars=["lokaler Simulator\n(M3 Ultra, kostenlos)",
         "SV1 Kalifornien\nals Hybrid Job",
         "SV1 Kalifornien\nvom Laptop",
         "IQM Garnet Stockholm\nechte Quantenhardware"],
   layers=["Braket-Service + Gerät", "Netzwerk + S3 + SDK",
           "Poll-Raster des SDK"],
   avoid="vermeidbar: ein Parameter",
   compute="die Rechnung selbst: 2,4 ms\n(lokal gemessen) — hier",
   note="Die echte QPU ist nur 7 % langsamer als der Simulator."),
 "en": dict(
   title="One iteration: where the time goes",
   sub="4-qubit circuit, 100 shots, 25 iterations per variant · median · "
       "empty queue · measured 2026-09-23",
   xlabel="Median per iteration (milliseconds)",
   p2title="The same iteration on IQM Garnet, broken into layers",
   bars=["local simulator\n(M3 Ultra, free)",
         "SV1 California\nas a Hybrid Job",
         "SV1 California\nfrom a laptop",
         "IQM Garnet Stockholm\nreal quantum hardware"],
   layers=["Braket service + device", "network + S3 + SDK",
           "SDK polling interval"],
   avoid="avoidable: one parameter",
   compute="the computation itself: 2.4 ms\n(measured locally) — here",
   note="The real QPU is only 7% slower than the simulator."),
}


def load():
    lap = json.load(open("article4_laptop.json"))
    hyb = json.load(open("article4_hybrid.json"))
    gar = json.load(open("article4_garnet.json"))
    fast = json.load(open("article4_garnet_fastpoll.json"))
    local = st.median(lap["local_ms"])
    vals = [local, hyb["median_ms"], st.median(lap["laptop_sv1_ms"]),
            st.median(gar["client_ms"])]
    # Layer decomposition, all three terms derived from measurements.
    g_default = st.median(gar["client_ms"])
    g_fast = st.median(fast["client_ms"])
    service = st.median(fast["service_ms"])
    return vals, local, [service, g_fast - service, g_default - g_fast], g_default


def render(lang, P, out):
    T = S[lang]
    vals, local, layers, total = load()

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10.5, 7.4), dpi=200,
        gridspec_kw={"height_ratios": [2.5, 1], "hspace": .55})
    fig.patch.set_facecolor(P["surface"])

    # --- top: the four variants -------------------------------------------
    ax1.set_facecolor(P["surface"])
    y = range(len(vals))
    ax1.barh(list(y), vals, height=.62, color=P["s1"], zorder=3)
    for i, v in enumerate(vals):
        if i == 0:
            continue          # hairline bar: the arrow annotation carries it
        ax1.text(v + 55, i, f"{v:,.0f} ms".replace(",", "."), va="center",
                 color=P["ink"], fontsize=11, fontweight="bold", zorder=4)
    ax1.set_yticks(list(y)); ax1.set_yticklabels(T["bars"], fontsize=10.5)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 3850); ax1.set_ylim(3.8, -0.55)
    ax1.set_xlabel(T["xlabel"], color=P["ink2"], fontsize=11)
    ax1.set_title(T["title"], color=P["ink"], fontsize=15,
                  fontweight="bold", loc="left", pad=40)
    ax1.annotate(T["sub"], xy=(0, 1.045), xycoords="axes fraction",
                 color=P["ink2"], fontsize=9.5)
    # The local bar is a hairline -- point at it, that is the message.
    ax1.annotate(T["compute"], xy=(local, .18), xytext=(430, .50),
                 textcoords="data", va="center", color=P["ink2"], fontsize=10,
                 arrowprops=dict(arrowstyle="->", color=P["ink2"], lw=1.2,
                                 connectionstyle="arc3,rad=-.2"))
    ax1.annotate(T["note"], xy=(3830, 3.62), ha="right", va="center",
                 color=P["ink2"], fontsize=10, style="italic")

    # --- bottom: layer decomposition --------------------------------------
    ax2.set_facecolor(P["surface"])
    cols = [P["s1"], P["s2"], P["s4"]]
    left = 0
    for i, (v, lab) in enumerate(zip(layers, T["layers"])):
        ax2.barh([0], [v], left=left, height=.5, color=cols[i], zorder=3,
                 edgecolor=P["surface"], linewidth=2,
                 hatch="///" if i == 2 else None)
        ax2.text(left + v / 2, 0, f"{v:,.0f} ms".replace(",", "."),
                 ha="center", va="center", color="#ffffff",
                 fontsize=11, fontweight="bold", zorder=4,
                 path_effects=[pe.withStroke(linewidth=2.6,
                                             foreground="#00000088")])
        ax2.text(left + v / 2, .42, lab, ha="center", va="bottom",
                 color=P["ink"], fontsize=10, fontweight="bold")
        left += v
    ax2.annotate(T["avoid"], xy=(left - layers[2] / 2, -.42), ha="center",
                 va="top", color=P["ink2"], fontsize=9.5, style="italic")
    ax2.set_xlim(0, 3850); ax2.set_ylim(-.9, .95)
    ax2.set_yticks([])
    ax2.set_xlabel(T["xlabel"], color=P["ink2"], fontsize=11)
    ax2.set_title(T["p2title"], color=P["ink"], fontsize=12,
                  fontweight="bold", loc="left", pad=22)

    for ax in (ax1, ax2):
        ax.grid(True, axis="x", color=P["grid"], lw=.7, alpha=.9, zorder=0)
        ax.set_axisbelow(True)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(colors=P["ink2"], labelsize=10)
    for lbl in ax1.get_yticklabels():
        lbl.set_color(P["ink"])

    fig.subplots_adjust(left=.20, right=.97, top=.86, bottom=.09)
    fig.savefig(out, facecolor=P["surface"])
    print(f"wrote {out}")


if __name__ == "__main__":
    for lang in ("de", "en"):
        for mode, P in (("light", LIGHT), ("dark", DARK)):
            render(lang, P, f"fig_latency_{lang}_{mode}.png")
    vals, local, layers, total = load()
    print(f"\nSchichten: {[round(x) for x in layers]}  Summe {sum(layers):.0f} ms "
          f"(gemessener Default-Median {total:.0f} ms)")
