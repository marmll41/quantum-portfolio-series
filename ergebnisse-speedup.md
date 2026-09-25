# Speedup-Messung: Julia, Quasi-Monte-Carlo, Importance Sampling

Stand 24.09.2026, endgültige Messung. Frage: Lässt sich die klassische
Baseline schlagen — mit einer schnelleren Sprache oder mit einer besseren
Methode? Und was davon übersteht echte Daten und dicke Enden?

## Protokoll

- S&P-500-Top-100 (SPY-Holdings 22.09.2026, Indexgewichte), Kovarianz aus
  1.254 Handelstagen 09/2021–09/2026; normal und Student-t (ν = 4,18)
- CVaR@99 %, ε = 10⁻³ (relativer RMSE gegen geschlossene Lösung)
- Jeder Pfad voller 100-dimensionaler Draw plus Korrelations-Matmul
- N(ε): einfaches MC exakt aus asymptotischer Varianz; übrige Verfahren
  lokaler Potenzgesetz-Fit (20 Replikationen, N = 2⁴ … 2²²) plus
  Kalibrierlauf mit 100 Replikationen
- Direktes Timing beim endgültigen N, 20 Runden, verschachtelt
- Apple M3 Max, 14 Kerne, ruhige Maschine (Hintergrundprogramme beendet);
  Last je Schritt in `benchmark.log`

## Ergebnis

| Verfahren | 1 Kern, normal | 14 Kerne, normal | 14 Kerne, t |
|---|---:|---:|---:|
| NumPy, einfaches MC | 1.818 ms | 268 ms | 1.853 ms |
| Julia, OpenBLAS | 2.485 ms | 1.357 ms (0,2×) | – |
| Julia, Accelerate | 1.347 ms | 173 ms (1,5×) | – |
| Quasi-MC, Cholesky | 162 ms | 30 ms (9×) | 205 ms (9×) |
| Quasi-MC, PCA | 82 ms | 17 ms (16×) | 109 ms (17×) |
| Importance Sampling | 11 ms | 4,7 ms (57×) | 1.659 ms (1,1×) |
| IS + Quasi-MC | 7,5 ms | 6,0 ms (45×) | 289 ms (6×) |

## Befunde

1. **Sprache: Faktor 1,5, und nur mit derselben BLAS.** Julia mit OpenBLAS
   ist fünfmal langsamer als NumPy mit Accelerate.
2. **Methode: Faktor 9 bis 57** bei identischer Arbeit pro Pfad.
3. **Importance Sampling ist nicht robust.** 57× unter Normalverteilung,
   1,1× unter t: Die Verschiebung der Faktoren erfasst nicht die
   Mischvariable, die bei dicken Enden den Tail treibt.
4. **Quasi-MC ist robust:** 9× und 16–17× in beiden Verteilungen. Lokale
   Steigungen −0,54 bis −0,83 — teilweise klassisch „quadratisch".

## Vergleich mit dem synthetischen Ein-Faktor-Modell (archiv/)

Das synthetische Modell war der günstigste Fall: IS + Quasi-MC erreichte dort
Faktor 63, Quasi-MC mit PCA 18×, mit Cholesky nur 3,3×. Mit echten Daten
steigt Cholesky auf 9×, PCA bleibt bei 16×, und die Robustheitsfrage stellt
erst die t-Verteilung.

## Korrektur gegenüber der ersten Version

N(ε) für einfaches MC wurde zuerst aus einer gemessenen Fehlerkonstante
bestimmt (RMSE am größten N). Bei 20 Replikationen streut der RMSE um ~16 %,
N damit um ~30 %. Ergebnis: N 28 % zu niedrig, die alte Schlagzeile von 78 ms
(M3 Ultra, synthetisch) hätte rund 109 ms lauten müssen. Jetzt: exakte
Konstante, Messung nur noch zur Kontrolle.

## Reproduktion

`./run_benchmarks.sh` (siehe README).
