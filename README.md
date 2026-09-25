# Klassische Monte-Carlo-Baseline

Die Referenzzahl, gegen die jede Quanten-Behauptung der Serie antritt.
Gemessen wird **Wall-Clock-Zeit bis zu einer Zielgenauigkeit ε** — nicht
Sample-Zahl.

## Ergebnis

Portfolio: die 100 größten Unternehmen des S&P 500 (SPY-Holdings vom
22.09.2026, Indexgewichte), Kovarianz aus fünf Jahren Tagesrenditen.
CVaR @ 99 %, 1 Tag Horizont, ε = 10⁻³.
Apple M3 Max (14 Kerne), Python 3.14.7, NumPy 2.5.3 (Accelerate), Julia 1.12.6.

### Schlagzeile

| | Normalverteilt | Student-t (ν = 4,2) |
|---|---:|---:|
| Einfaches MC, 14 Kerne, Ende-zu-Ende | **268 ms** | 1.853 ms |
| Bestes Verfahren, 14 Kerne | **4,7 ms** (Importance Sampling) | **109 ms** (Quasi-MC, PCA) |

### Alle Verfahren, ε = 10⁻³

| Verfahren | N | 1 Kern, normal | 14 Kerne, normal | 14 Kerne, t |
|---|---:|---:|---:|---:|
| NumPy, einfaches MC | 3.102.840 | 1.818 ms | 268 ms | 1.853 ms |
| Julia, OpenBLAS (Standard) | 3.102.840 | 2.485 ms | 1.357 ms | – |
| Julia, Accelerate | 3.102.840 | 1.347 ms | 173 ms | – |
| Quasi-MC, Cholesky | 131.072 | 162 ms | 30 ms | 205 ms |
| Quasi-MC, PCA | 65.536 | 82 ms | 17 ms | 109 ms |
| Importance Sampling | 16.419 | 11 ms | 4,7 ms | 1.659 ms |
| IS + Quasi-MC (PCA) | 4.096 | 7,5 ms | 6,0 ms | 289 ms |

N gilt für die Normalverteilung. Unter t: einfaches MC 21,6 Mio., Quasi-MC
0,5–1 Mio., Importance Sampling 8,2 Mio.

### Zeit bis Zielgenauigkeit, einfaches MC, normal

| ε | N benötigt | 1 Kern | 14 Kerne | analytisch reduziert |
|---|---|---|---|---|
| 10⁻² | 31.028 | 18 ms | 2,2 ms | 0,4 ms |
| 10⁻³ | 3.102.839 | **1,82 s** | **268 ms** | 36 ms |
| 10⁻⁴ | 310.283.903 | 180 s | 22 s | 3,6 s |
| 10⁻⁵ | 31.028.390.255 | 5,0 h | 37 min | 6,0 min |
| 10⁻⁶ | 3.102.839.025.470 | 20,8 d | 2,6 d | 10,1 h |

Die Zeile ε = 10⁻³ ist Ende-zu-Ende gemessen (ziehen, einsammeln, schätzen).
Die übrigen Zeilen sind N durch gemessenen Durchsatz, also ohne den
Overhead von 46 ms; ab 10⁻⁴ extrapoliert.

### Mehrkern-Skalierung

| Worker | Pfade/s | Speedup | Effizienz |
|---|---|---|---|
| 1 | 1.733.148 | 1,0× | 100 % |
| 2 | 3.368.709 | 1,9× | 97 % |
| 4 | 6.181.884 | 3,6× | 89 % |
| 8 | 10.438.086 | 6,0× | 75 % |
| 14 | 13.946.163 | 8,0× | **57 %** |

Wahrscheinliche Ursache: die Speicherbandbreite, nicht der Overhead der
Parallelisierung (nicht separat gemessen).

## Methodik

Alle Entscheidungen sind im Code kommentiert.

1. **Exakte Referenz.** Unter Normal- und t-Verteilung ist der Portfolioverlust
   univariat normal bzw. t; VaR und CVaR haben geschlossene Formen. Gemessen
   wird der echte Fehler (RMSE über 20 Wiederholungen).
2. **Keine Abkürzung beim Sampling.** Jeder Pfad ist ein voller
   100-dimensionaler Draw mit Korrelations-Matmul, weil QAEs State Preparation
   dieselbe gemeinsame Verteilung laden muss. Die Abkürzung wird separat als
   `reduced` gemessen: Faktor 50 auf einem Kern, mehr als 14 Kerne (8×).
3. **BLAS-Threads gepinnt** (`MC_PIN_THREADS=1`), im Output protokolliert.
4. **Exakte Fehlerkonstante.** N(ε) für einfaches MC kommt aus der
   asymptotischen Varianz des CVaR-Schätzers
   (`mc_baseline.cvar_error_constant`, C = 1,76 normal, 4,65 t), nicht aus
   einem Fit. Die erste Version hat C am größten gemessenen N kalibriert und
   N damit um 28 % zu niedrig angesetzt. Für Quasi-MC und Importance Sampling
   gibt es keine geschlossene Form: dort Fit plus Kalibrierlauf mit 100
   Wiederholungen nahe dem gefundenen N, korrigiert entlang der lokalen
   Steigung.
5. **Direktes Timing** beim endgültigen N, 20 Runden, die Python-Verfahren
   verschachtelt; Julia separat, je 20 Wiederholungen.

### Grenzen

- Das Portfolio ist linear. Für ein Buch mit Optionen schrumpfen die Gewinne
  durch Importance Sampling und Quasi-MC weiter.
- Survivorship-Bias durch Auswahl der heute größten Titel (für einen
  Rechenzeit-Benchmark unerheblich).
- Eine Maschine, ein Tag. Load Average je Schritt in `benchmark.log`.
- GPU: noch offen.

## Reproduktion

```bash
python3 -m venv .venv && ./.venv/bin/pip install numpy scipy matplotlib

# einmalig mit Netzwerk: Modell bauen (speichert nur abgeleitete Größen)
./.venv/bin/pip install yfinance pandas openpyxl
./.venv/bin/python fetch_sp100.py

# komplette Messung, beide Verteilungen, Grafiken
./run_benchmarks.sh
```

Einzelne Schritte, Verteilung per `MC_DIST=normal|t`, Universum per
`MC_UNIVERSE=sp100|synthetic`:

```bash
MC_PIN_THREADS=1 ./.venv/bin/python mc_baseline.py --reps 20 --max-n 1e7
./.venv/bin/python throughput_probe.py
MC_PIN_THREADS=1 ./.venv/bin/python mc_variance_reduction.py --workers 14
./.venv/bin/python retime_variance_reduction.py 14 20 results_vr_sp100_normal.json
./.venv/bin/python export_model.py && julia -t 14 mc_baseline.jl 3102840 20 256
```

## Dateien

| Datei | Inhalt |
|---|---|
| `fetch_sp100.py` | Holdings + Kurse laden, Kovarianz und ν schätzen |
| `data/sp100_model.npz`, `.json` | Abgeleitetes Modell (Ticker, Gewichte, μ, Σ, ν) |
| `data/raw/` | Rohdaten, lokal, **nicht veröffentlichen** |
| `mc_baseline.py` | Modell, Schätzer, exakte Referenz und Fehlerkonstante |
| `mc_variance_reduction.py` | Quasi-MC, Importance Sampling, Kalibrierung, Timing |
| `retime_variance_reduction.py` | Verschachteltes Nachtiming |
| `throughput_probe.py` | Mehrkern-Skalierung mit persistentem Pool |
| `mc_baseline.jl`, `export_model.py` | Julia-Portierung, identisches Modell |
| `run_benchmarks.sh` | Komplette Messkette mit Protokoll |
| `plot_baseline.py`, `plot_variance_reduction.py` | Erzeugen die Grafiken (DE/EN, hell/dunkel) |
| `qae_tail.py`, `plot_qae.py` | Artikel 5: QAE aus Standard-Gates, Skalierung, Ressourcen, Budget |
| `hw_qae.py`, `plot_hw.py`, `hw_tasks.json`, `hw_spend.json` | Artikel 6: Hardware-Lauf, Prognose, Ergebnisse, Kosten |
| `probe_local.py`, `probe_api_latency.py`, `loop_core.py`, `hybrid_entry.py`, `article4_*.json` | Artikel 3 und 4: lokaler Simulator, API-Latenz, Latenz-Schleife |
| `medium_export.py` | Erzeugt aus einem Artikel die HTML-Fassung und Tabellen als Bild für Medium |
| `results_1core*.json`, `results_vr_sp100_*.json`, `throughput*.json`, `julia_*.json` | Rohdaten |
| `benchmark.log` | Protokoll der Messung, Last je Schritt |
| `archiv/` | Erste Version (synthetisches Modell, M3 Ultra), ohne Grafiken |
| `quellen-dossier.md` | Belegsammlung der Serie |

## Anschluss an die Serie

Diese Kurven sind die klassische Hälfte der zentralen Grafik der Serie. Was
fehlt, ist die Quantenkurve — gemessen auf Braket, mit demselben ε-Kriterium
und derselben Wall-Clock-Definition.

## Artikel

Die Artikel selbst erscheinen auf Medium; dieses Repository enthält Code und
Messdaten dazu. Die Grafiken erzeugen die `plot_*.py`-Skripte aus den Daten.

| # | Titel |
|---|---|
| 1 | Die Uhr, die niemand gestartet hat / The Clock Nobody Started |
| 2 | 268 Millisekunden / 268 Milliseconds |
| 2b | 4,7 Millisekunden / 4.7 Milliseconds |
| 3 | Der Faktor 188 / A Factor of 188 |
| 4 | Der Quantencomputer ist der schnellste Teil / The Quantum Computer Is the Fastest Part |
| 5 | 412.800 Orakel-Aufrufe / 412,800 Oracle Calls |
| 6 | 106 CNOTs |

## Lizenz

Code (`*.py`, `*.jl`, `*.sh`): [MIT](LICENSE).
Dokumentation und Ergebnisdaten: [CC BY 4.0](LICENSE-CONTENT.md).
Nicht enthalten: Rohkurse und ETF-Holdings (`data/raw/`), die `fetch_sp100.py`
neu lädt; die AWS-Konto-ID ist in allen Task-ARNs durch `<account-id>` ersetzt.
