# Archiv: erste Version (synthetisches Modell)

- `results_28core_m3ultra_synthetisch.json` — Mehrkern-Lauf auf dem M3 Ultra (28 Kerne),
  synthetisches Ein-Faktor-Modell, nur Durchsatz (Fehler = NaN).
- `results_vr_synthetisch_m3max.json`, `messlauf_synthetisch_m3max.log`,
  `fig_methods_synthetisch_*` — Varianzreduktion auf dem M3 Max, synthetisches Modell.
- `messlauf_sp100_entwicklung.log`, `messlauf_t_verlaengerung_abgebrochen.log` — Entwicklungsläufe.

Die alte Schlagzeile der ersten Version (78 ms, N = 2.163.552 für ε = 10⁻³, M3 Ultra)
stammt aus deren `results_1core.json`. Diese Datei wurde am 24.09.2026 bei der
Neumessung überschrieben; eine Kopie sollte auf dem M3 Ultra liegen. Die exakte
Fehlerkonstante für das synthetische Modell ergibt N = 3.015.806, also lag die erste
Version um 28 % zu niedrig (78 ms × 3,016/2,164 ≈ 109 ms).

## API-Latenz, Wiederholung 25.09.2026 — nicht verwendbar

`results_api_latency_2026-09-25_run*_netz_instabil.json`: zwei Wiederholungen der
Messung aus Artikel 3, abgebrochen, weil das lokale Netz instabil war (wechselnde
Verbindungen). Handshake nach us-west-1 5.175 bzw. 463 ms, nach Stockholm 147 bzw.
262 ms (23.09.: 71 ms). Die Werte messen das lokale Netz, nicht Braket. Artikel 3
stützt sich weiter auf die Messung vom 23.09.2026 (quellen-dossier.md).
