# Quanten-Portfoliorisiko auf AWS Braket — Code und Daten

[English](README.md) · **Deutsch**

Code und Messdaten zu einer Medium-Serie, die klassisches Monte Carlo und
Quantum Amplitude Estimation für Portfoliorisiken auf AWS Braket vergleicht.
Gemessen wird durchgehend eine Größe: **Wall-Clock-Zeit bis zu einer
Zielgenauigkeit ε** — nicht Sample-Zahlen, nicht Orakel-Aufrufe.

Die Artikel und ihre Grafiken erscheinen auf Medium. Dieses Repository enthält
alles, was man braucht, um die Zahlen nachzurechnen; die Skripte `python/plot_*.py`
erzeugen jede Grafik aus den Daten hier neu.

## Die Serie

| # | Titel | Was gemessen wird |
|---|---|---|
| 1 | Die Uhr, die niemand gestartet hat | Warum Sample-Zahlen nichts über Geschwindigkeit sagen; sieben Fragen an jeden Benchmark |
| 2 | 268 Millisekunden | Die klassische Baseline: CVaR der S&P-500-Top-100 per einfachem Monte Carlo |
| 2b | 4,7 Millisekunden | Die Baseline schlagen: Julia, Quasi-Monte-Carlo, Importance Sampling, dicke Enden |
| 3 | Der Faktor 188 | Braket-Setup, Geräteverfügbarkeit, Control-Plane-Latenz, Spending Limits |
| 4 | Der Quantencomputer ist der schnellste Teil | Wohin die Zeit einer Quanten-Schleife geht |
| 5 | 412.800 Orakel-Aufrufe | Quantum Amplitude Estimation aus Standard-Gates: Speedup, Konstante, Kosten |
| 6 | 106 CNOTs | Der kleinste QAE-Circuit auf Hardware von IQM, Rigetti und IonQ |

## Kernergebnisse

Portfolio: die 100 größten Unternehmen des S&P 500 (SPDR-Holdings vom
22.09.2026, Indexgewichte), Kovarianz aus fünf Jahren Tagesrenditen. CVaR zum
99-Prozent-Niveau, ein Tag Horizont, ε = 10⁻³. Klassische Messungen auf einem
Apple M3 Max, 14 Kerne, Python 3.14.7, NumPy 2.5.3 auf Accelerate, Julia 1.12.6.

**Klassisch (Artikel 2 und 2b)**

| | Normalverteilt | Student-t (ν = 4,2) |
|---|---:|---:|
| Einfaches Monte Carlo, 14 Kerne, Ende-zu-Ende | **268 ms** | 1.853 ms |
| Bestes Verfahren, 14 Kerne | **4,7 ms** (Importance Sampling) | **109 ms** (Quasi-MC, PCA-Reihenfolge) |

| Verfahren | N | 1 Kern, normal | 14 Kerne, normal | 14 Kerne, t |
|---|---:|---:|---:|---:|
| NumPy, einfaches MC | 3.102.840 | 1.818 ms | 268 ms | 1.853 ms |
| Julia, OpenBLAS (Standard) | 3.102.840 | 2.485 ms | 1.357 ms | – |
| Julia, Accelerate | 3.102.840 | 1.347 ms | 173 ms | – |
| Quasi-MC, Cholesky | 131.072 | 162 ms | 30 ms | 205 ms |
| Quasi-MC, PCA | 65.536 | 82 ms | 17 ms | 109 ms |
| Importance Sampling | 16.419 | 11 ms | 4,7 ms | 1.659 ms |
| IS + Quasi-MC (PCA) | 4.096 | 7,5 ms | 6,0 ms | 289 ms |

N gilt für die Normalverteilung; unter der t-Verteilung braucht einfaches MC
21,6 Millionen Pfade.

**Cloud-Latenz (Artikel 3 und 4)**

- Lokaler Braket-Simulator, 20 Qubits, 1.000 Shots: 17 ms.
- Eine Iteration einer variationellen Schleife auf IQM Garnet: 3,3 s, davon
  unter 2,4 ms Rechnung (0,07 Prozent). Allein das Pollen des SDK kostet rund
  750 ms pro Iteration; ein Parameter beseitigt es.

**Quantum Amplitude Estimation (Artikel 5, rauschfreier Simulator)**

- Das quadratische Speedup ist echt: Der Fehler fällt mit Steigung −1,00,
  gegenüber −0,50 beim Sampling.
- Für eine Tail-Wahrscheinlichkeit von 1 Prozent auf ε = 10⁻³: **412.800
  Orakel-Aufrufe**, nicht 1.000. Der tiefste Circuit hat 597.594
  Zwei-Qubit-Gates.

**Echte Hardware (Artikel 6)** — 3 Qubits, Tail-Wahrscheinlichkeit 6,6 Prozent,
P(Flag = 1) nach k Grover-Schritten:

| | k = 0 | k = 1 | k = 2 |
|---|---:|---:|---:|
| ideal | 6,6 % | 49,2 % | 92,6 % |
| IonQ Forte Enterprise 1 | 9,5 % | 48,0 % | **74,0 %** |
| IQM Garnet | 12,3 % | 40,1 % | 53,9 % |
| IQM Emerald | 11,6 % | 44,2 % | 46,0 % |
| Rigetti Cepheus-1 | 19,3 % | 50,2 % | 49,9 % |

Vollständiges Rauschen konvergiert gegen 50 Prozent. Gesamtkosten 62,03 $; die
IonQ-Tasks standen 12,4 bis 12,8 Stunden in der Warteschlange.

## Methodik

Alle Entscheidungen sind im Code kommentiert.

1. **Exakte Referenz.** Unter Normal- und t-Verteilung ist der Portfolioverlust
   univariat normal bzw. t; VaR und CVaR haben geschlossene Formen. Gemessen
   wird der echte Fehler (RMSE über 20 Wiederholungen).
2. **Keine Abkürzung beim Sampling.** Jeder Pfad ist ein voller
   100-dimensionaler Draw mit Korrelations-Matmul, weil QAEs State Preparation
   dieselbe gemeinsame Verteilung laden muss. Die Abkürzung wird separat als
   `reduced` gemessen.
3. **BLAS-Threads gepinnt** (`MC_PIN_THREADS=1`) und protokolliert.
4. **Exakte Fehlerkonstante.** N(ε) für einfaches Monte Carlo kommt aus der
   asymptotischen Varianz des CVaR-Schätzers
   (`python/mc_baseline.py`, `cvar_error_constant`: C = 1,76 normal, 4,65 t), nicht aus
   einem Fit. Für Quasi-MC und Importance Sampling: Fit, dann Kalibrierlauf mit
   100 Wiederholungen nahe dem gefundenen N, korrigiert entlang der lokalen
   Steigung.
5. **Direktes Timing** beim endgültigen N, 20 Runden, die Python-Verfahren
   verschachtelt; Julia separat, je 20 Wiederholungen.
6. **Prognose vor Hardware-Läufen.** `python/hw_qae.py preview` simuliert die Circuits
   mit den Fehlerraten, die die Hersteller melden, bevor irgendetwas
   eingereicht wird.

**Grenzen.** Das Portfolio ist linear; für ein Buch mit Optionen schrumpfen die
Gewinne durch Importance Sampling und Quasi-MC weiter. Die Auswahl der heute
größten Unternehmen ist ein Survivorship-Bias (für einen Rechenzeit-Benchmark
unerheblich). Eine Maschine, ein Tag; die Last je Schritt steht in
`results/benchmark.log`.

## Aufbau

Der Code ist nach Sprache gruppiert: `python/` (Modelle, Messungen, Grafiken, Medium-Export), `julia/` (Julia-Portierung der Baseline), `shell/` (die komplette Messkette). Eingangsdaten liegen in `data/`, Messergebnisse und Protokolle in `results/`. Alle Befehle aus dem Wurzelverzeichnis des Repositorys starten; die Skripte lesen und schreiben ihre Dateien relativ dazu.

## Nachrechnen

```bash
python3 -m venv .venv && ./.venv/bin/pip install numpy scipy matplotlib amazon-braket-sdk

# einmalig, mit Netzwerk: Modell bauen (speichert nur abgeleitete Größen)
./.venv/bin/pip install yfinance pandas openpyxl
./.venv/bin/python python/fetch_sp100.py

# Artikel 2 und 2b: komplette Messung, beide Verteilungen, Grafiken
./shell/run_benchmarks.sh

# Artikel 3: lokaler Simulator und Control-Plane-Latenz (kostenlos, nur lesende Aufrufe)
./.venv/bin/python python/probe_local.py
AWS_PROFILE=<dein-profil> ./.venv/bin/python python/probe_api_latency.py

# Artikel 5: QAE auf dem lokalen Simulator (kostenlos)
./.venv/bin/python python/qae_tail.py validate
./.venv/bin/python python/qae_tail.py scaling 400
./.venv/bin/python python/qae_tail.py resources
./.venv/bin/python python/qae_tail.py budget

# Artikel 6: Hardware (erst die kostenlosen Schritte; Einreichen kostet Geld)
./.venv/bin/python python/hw_qae.py check
./.venv/bin/python python/hw_qae.py preview
./.venv/bin/python python/hw_qae.py cost
```

`python/hw_qae.py submit` läuft nicht ohne `--submit` und eine Obergrenze `--max-usd`
über den geplanten Kosten, und es überspringt Geräte, die offline sind. Vorher
in der Braket-Konsole pro Gerät ein Spending Limit setzen.

## Dateien

| Datei | Inhalt |
|---|---|
| `python/fetch_sp100.py` | Lädt Holdings und Kurse, schätzt Kovarianz und ν |
| `data/sp100_model.npz`, `.json` | Abgeleitetes Modell (Ticker, Gewichte, μ, Σ, ν) |
| `data/braket_devices_2026-09-24.json` | Fehlerraten und Timing der Geräte, wie über Braket gemeldet |
| `python/mc_baseline.py` | Modell, Schätzer, exakte Referenz und Fehlerkonstante |
| `python/mc_variance_reduction.py`, `python/retime_variance_reduction.py` | Quasi-MC, Importance Sampling, Kalibrierung, verschachteltes Timing |
| `python/throughput_probe.py` | Mehrkern-Skalierung mit persistentem Pool |
| `julia/mc_baseline.jl`, `python/export_model.py` | Julia-Portierung auf identischem Modell |
| `shell/run_benchmarks.sh` | Komplette Messkette mit Protokoll |
| `python/probe_local.py`, `python/probe_api_latency.py` | Artikel 3: lokaler Simulator, Control-Plane-Latenz |
| `python/loop_core.py`, `python/hybrid_entry.py`, `results/article4_*.json` | Artikel 4: Latenz-Schleife, Einstieg für den Hybrid Job, Rohdaten |
| `python/qae_tail.py` | Artikel 5: QAE aus Standard-Gates, Skalierung, Ressourcen, Budget |
| `python/hw_qae.py`, `results/hw_tasks.json`, `results/hw_spend.json` | Artikel 6: Hardware-Läufe, Ergebnisse, Zähler der Spending Limits |
| `python/plot_*.py` | Erzeugen alle Grafiken (DE/EN, hell/dunkel) |
| `python/medium_export.py` | Macht aus einem Artikel eine Medium-taugliche HTML-Fassung mit Tabellen als Bild |
| `results/` | Alle Messergebnisse (`results_*.json`, `throughput*.json`, `julia_*.json`, `article4_*.json`, `hw_*.json`) und `benchmark.log` |
| `archiv/` | Erste Version (synthetisches Modell) und verworfene Läufe, mit Vermerken |
| `source-dossier.md`, `source-dossier.de.md` | Quellen-Dossier (Englisch, Deutsch) |
| `speedup-results.md`, `speedup-results.de.md` | Ergebnisnotizen zur Speedup-Messung (Englisch, Deutsch) |

## Lizenz

Code (`*.py`, `*.jl`, `*.sh`): [MIT](LICENSE).
Dokumentation und Ergebnisdaten: [CC BY 4.0](LICENSE-CONTENT.md).
Nicht enthalten: Rohkurse und ETF-Holdings (`data/raw/`), die `python/fetch_sp100.py`
neu lädt; die AWS-Konto-ID ist in allen Task-ARNs durch `<account-id>`
ersetzt.
