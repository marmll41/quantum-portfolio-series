# Quellen-Dossier — Quantum Portfolio Optimization auf AWS

Stand: 2026-09-22

Belegsammlung für die Artikelserie. Jede Quelle mit Status, Kernzahlen,
zitierfähigen Stellen und Zuordnung zum Artikel.

**Legende Belegstatus**
- **[P]** Peer-reviewed / publiziert
- **[PP]** Preprint (arXiv), nicht peer-reviewed
- **[V]** Vendor-/Marketing-Content — kein Beleg, nur Fundstück
- **[S]** Sekundärquelle (Journalismus)

---

## Die These der Serie

> Der Speedup ist real, aber eine Größenordnung zu schwach, um die Konstanten
> zu schlagen — und der Crossover liegt in einem Genauigkeitsbereich ohne
> finanzielle Bedeutung.

Das Belegmuster über alle Quellen hinweg:

**Wenn rigoros gerechnet wird, ist das Ergebnis katastrophal.
Wenn nicht gerechnet wird, gibt es ein Ergebnis.**

---

## 1. Dalzell et al. — Das Bewertungsraster  [PP]

*Quantum algorithms: A survey of applications and end-to-end complexities*
AWS Center for Quantum Computing · arXiv:2310.03011

**Funktion in der Serie:** Methodische Grundlage. Definiert, was eine
End-to-End-Bewertung eines Quantenalgorithmus leisten muss (u. a. "criterion 4
of the end-to-end practical algorithm", auf das die QIPM-Arbeit prüft).

**Warum wichtig:** Artikel 1 braucht kein selbstgebautes Schema. Die Aussage
lautet nicht "ich finde, man müsste anders messen", sondern "AWS hat definiert,
wie man misst, und die meisten Paper tun es nicht."

→ **Artikel 1**

---

## 2. AWS + Goldman Sachs — QIPM, der kontinuierliche Fall  [P]

*End-to-end resource analysis for quantum interior point methods and
portfolio optimization*
PRX Quantum 4, 040325 (2023) · arXiv:2211.12489 (v2, Mai 2024)

Vollständige Ressourcenanalyse auf Circuit-Level, **inklusive konstanter
Faktoren** — von Problemeingabe bis Ausgabe. Genau die Rechnung, die sonst fehlt.

**Kernzahlen für n = 100 Assets**

| Größe | Wert |
|---|---|
| Logische Qubits | 8.000.000 |
| T-Count | 7 × 10^29 |
| T-Depth | 2 × 10^24 |

**Zitat (tragend):**
> "Even if layers of T-gates are optimistically implemented at the GHz speeds
> of classical processors (in reality they are likely to be 2–4 orders of
> magnitude slower than that) these estimates suggest that the runtime of the
> quantum algorithm would still be millions of years, even for an instance size
> that is already classically tractable on a laptop."

**Zitat (Fazit):**
> "the QIPM, in its current form, does not satisfy criterion 4 of the
> end-to-end practical algorithm"

**Eigene Nachrechnung (im Artikel als solche kennzeichnen):**
2 × 10^24 Layer bei 10^9 Layern/s = 2 × 10^15 s ≈ **63 Mio. Jahre**.
Mit den realistischen 2–4 Größenordnungen Abschlag: 6 bis 600 Mrd. Jahre.
Alter des Universums zum Vergleich: ~13,8 Mrd. Jahre.

8 Mio. *logische* Qubits bedeuten bei realistischem Surface-Code-Overhead
mehrere Milliarden physische Qubits. Aktuelle Geräte: einige hundert.

**Rhetorischer Wert:** AWS' eigenes Team, auf AWS' eigenem Blog. Für eine
AWS-Serie ideal — keine Anklage, ein Zitat.

→ **Artikel 6, 8**

---

## 3. Chakrabarti et al. — Derivatebewertung, der Monte-Carlo-Fall  [P]

*A Threshold for Quantum Advantage in Derivative Pricing*
Quantum 5, 463 (2021) · arXiv:2012.03819
Goldman Sachs + IBM + QuICS/UMD

Benchmark-Instrumente: Autocallables und TARFs. Führt die
Re-Parameterization-Methode ein, um bekannte Blocker zu umgehen.

**Kernzahlen**

| Größe | Wert |
|---|---|
| Logische Qubits | 8.000 |
| T-Depth | 54.000.000 |
| Benötigte logische Taktrate | **50 MHz** |

> **Korrektur 24.09.2026 (Faktencheck gegen Original):** Das Paper nennt
> **10 MHz** („the quantum processor would need to execute T-gates at a rate of
> 10MHz"), nicht 50 MHz, und selbst „current estimates target logical clock
> rates around 10kHz" — die ~40 kHz unten sind eine eigene Herleitung, nicht
> aus dem Paper. Außerdem: Das GHz-Zitat der QIPM-Arbeit stammt aus dem
> AWS-Blog vom 13.11.2023, nicht aus dem PRX-Quantum-Paper; „63 Mio. Jahre"
> ist eigene Rechnung. IBM/Vanguard v1: 19.08.2025.

Die 50 MHz sind die Rate, um die klassische MC-Bewertungszeit von ~1 Sekunde
einzuholen.

**Eigene Einordnung (im Artikel als solche kennzeichnen):**
Surface-Code-Zyklus supraleitend ~1 µs; logische Operation ~d Zyklen bei
d ≈ 25 → ~25 µs pro logischer Operation → logische Taktrate **~40 kHz**.
50 MHz liegen damit rund **drei Größenordnungen** jenseits dessen, was
Surface-Code-Architekturen projizieren.

**Der entscheidende Vergleich zu Quelle 2:**
Derivatebewertung braucht 8.000 logische Qubits, QIPM 8.000.000.
QAE ist um Faktor 1.000 der bessere Algorithmus — die Monte-Carlo-Seite ist
der **stärkste Fall**, den Quantum Finance zu bieten hat. Und selbst dort
scheitert es an der Wall-Clock. Deshalb beginnt die Serie mit Monte Carlo.

→ **Artikel 3, 6, 8**

---

## 4. Babbush et al. — Warum quadratisch grundsätzlich nicht reicht  [P]

*Focus beyond Quadratic Speedups for Error-Corrected Quantum Advantage*
PRX Quantum 2, 010103 (2021) · arXiv:2011.04149
Google Quantum AI (Babbush, McClean, Newman, Gidney, Boixo, Neven)

**Kernaussage:** Quadratische Speedups ermöglichen auf frühen fehlerkorrigierten
Geräten **keinen** Quantenvorteil, solange die Fehlerkorrektur nicht grundlegend
besser wird. Der Konstantenfaktor-Overhead frisst sie auf. Für praktischen
Vorteil braucht es eher **quartische** Speedups.

**Warum tragend:** QAE liefert genau einen quadratischen Speedup. Damit ist die
Aussage nicht "die Hardware ist noch nicht so weit", sondern strukturell.
Und sie kommt aus Googles eigenem Quantum-Team — keine Außenseiterposition.

**Merksatz für den Artikel:** Heutige Hardware ist langsam, weil sie verrauscht
ist. Zukünftige Hardware bleibt langsam, weil Fehlerkorrektur teuer ist.

→ **Artikel 1, 8**

---

## 5. IBM + Vanguard — CVaR-VQA, der NISQ-Fall  [PP]

*Portfolio construction using a sampling-based variational quantum scheme*
arXiv:2508.13557 (v1 Aug 2025, **v2 Nov 2025**)
Agliardi, Alevras, Kumar, Lo Nardo, Compostella, Kumar, Proissl (IBM Quantum),
Mehta (Vanguard, Centre for Analytics & Insights)

Hinweis: Der IBM-Blog vom 29.09.2025 bezieht sich auf v1. Immer v2 zitieren.

**Setup**

| | |
|---|---|
| Problem | Bond-ETF-Konstruktion, vereinfacht auf **109 binäre Variablen** |
| Hardware | IBM Heron `ibm_marrakesh`, `ibm_fez`; 109 Qubits |
| Shots | 8.192 pro Iteration |
| Optimizer | NFT, 327–434 Parameter |
| Circuits | TwoLocal bilinear (T 17 / 1.525 Gates / 216 2Q) · TwoLocal color (T 19 / 1.555 / 246) · BFCD (T 57 / 4.220 / 648) |
| Ergebnis | 0,49 % / 0,55 % / 0,91 % Gap n. Local Search; Simulator 0,39 % |

### Befund A — CPLEX löst dasselbe Problem in Sekunden beweisbar optimal

Abschnitt II, wörtlich:
> "The simplified problem with 109 bonds, on the other hand, can be solved by
> classical solvers like CPLEX or Gurobi to optimality in a few seconds,
> yielding, in the case of CPLEX, 33 solutions with one being the proven optimal."

CPLEX: bewiesenes Optimum in Sekunden. Quantenlauf: 0,49 % darüber.
**Dieser Satz steht im Paper und fehlt im IBM-Blog.**

### Befund B — Die "klassische Baseline" ist kein klassischer Solver

Vergleichspunkt in Fig. 5/6 ist die *"Initial"*-Verteilung = Iteration 1,
**untrainierter** Circuit. "Rein klassisch" heißt also: Local Search von
quasi-zufälligen Startpunkten. Kein Simulated Annealing, kein Tabu Search,
kein Laufzeitvergleich gegen CPLEX.

Übersetzt: *trainiertes Quanten-Seeding schlägt zufälliges Seeding.*
Eine Aussage über Startpunkte, nicht über klassische Optimierung.

### Befund C — Keine einzige Hardware-Laufzeit im gesamten Paper

Einzige Zeitangaben: Tabelle I, **MPS-Simulatorzeiten auf einem Apple M1 Pro
Laptop** (5 s / 3 min / 16 min für 1k Shots). Keine QPU-Laufzeit, kein
Time-to-Solution.

Das Speed-Argument ist explizit hypothetisch:
> "For instance, if hardware requires 2x the number of iterations but is then
> 10x faster than simulators time-wise, then still quantum hardware will be
> 5x faster in the overall time taken to run the scheme."

Erfundene Zahlen — und der Vergleichspunkt ist der **Simulator**, also die
klassische Simulation eines Quantencomputers. Nicht der geschäftlich
relevante Vergleich.

### Befund D — Die Abstract-Behauptung wird vom eigenen Hardware-Lauf widerlegt

Abstract: *"hard-to-simulate quantum circuits may lead to better convergence
than simpler circuits."* Stammt aus der **31-Qubit-Simulation**.

Auf 109-Qubit-Hardware schnitt BFCD — der schwer simulierbare Ansatz —
**am schlechtesten** ab (0,91 % vs. 0,49 %). Das Paper sagt das und erklärt es:
langsamere Konvergenz, Local Search versagt bei unkonvergierten Samples.

### Befund E — Die tragende Prämisse ist unveröffentlicht

Motivation: professionelle Solver lieferten bei 1.000–10.000 Instrumenten in
5–10 Minuten keine guten Lösungen. Fußnote 1:
> "Empirical estimate based on internal work."

Kein Benchmark, keine Solver-Version, keine Konfiguration, nicht reproduzierbar.

### Befund F — Die Conclusions sind ehrlich

> "In order for quantum methods to provide an advantage over classical, though,
> it is essential to scale the problem size to a much larger regime, where
> classical solvers struggle."

> "we believe that little can be inferred about the runtime at large scale,
> from experiments of small to mid problem size, given the heuristic nature
> of the methods."

Die Autoren überziehen nicht. **Die Lücke liegt zwischen Paper und Rezeption,
nicht zwischen Paper und Wahrheit.** Ton entsprechend: nicht die Forscher
kritisieren, die Lesart korrigieren.

### Eigene Größenordnung (nicht aus dem Paper)

NFT braucht 3 Circuit-Auswertungen pro Parameter. Bei 327 Parametern:
~981 Circuits/Epoche x 8.192 Shots = **~8 Mio. Shots pro Epoche**.

In Braket-Preisen (IBM rechnet anders ab; nur zur Einordnung der
Ressourcenintensität): Rigetti Cepheus ~3.400 $ · IQM Garnet ~11.600 $ ·
IonQ Forte ~640.000 $ — **pro Epoche**, für ein Problem, das CPLEX in
Sekunden beweisbar optimal löst.

**Offen:** Iterationszahlen stehen nur in Fig. 4–6, nicht im Fließtext.
Für exakte Angaben in die PDF-Grafiken schauen.

→ **Artikel 5, 6, 7 — und der reichweitenstärkste Artikel der Serie**

---

## 6. superpositions.studio — QAE vs Monte Carlo  [V]

`superpositions.studio/comparisons/qae-vs-monte-carlo`

**Kein Autor, kein Datum, keine Literaturangaben.** Marketing-Content einer
kommerziellen Quantum-Plattform. **Als Faktenquelle unbrauchbar** — als
Fundstück ausgezeichnet, weil er den Denkfehler der Serie live enthält.

### Der Crossover bei eps ~ 10^-2 ist ein Artefakt

Eigener Wortlaut: *"the two error curves are **normalized** to cross around
eps ~ 10^-2."*

1/eps^2 und 1/eps mit Konstanten = 1 kreuzen sich bei eps = 1. Damit sie sich
bei 10^-2 kreuzen, wählt man einen Vorfaktor von 100. Eine
**Diagramm-Entscheidung, kein Messergebnis.**

Gefährlich, weil 1 % Genauigkeit ein real genutzter Bereich ist. Eigene
Wall-Clock-Herleitung ergibt den Crossover bei eps < 10^-6 bis 10^-8 —
vier bis sechs Größenordnungen daneben.

> **Korrektur 24.09.2026:** Die Spanne 10⁻⁶–10⁻⁸ setzte fünf bis acht
> Größenordnungen Stückzeit-Verhältnis voraus. Mit eigenen Messungen (klassisch
> 86 ns/Sample auf 14 Kernen, Garnet 11 ms/Shot Service-Zeit, IQM-Gates 20–40 ns) sind es zwei bis
> acht: Crossover 10⁻⁵–10⁻⁶ für gemessene Cloud-Werte, 10⁻⁶–10⁻⁸ für
> Ionenfallen, im günstigsten Fall (supraleitend, reine Hardware, ~1.000 Gates)
> bis 10⁻³. Siehe Artikel 1, Abschnitt „Die Behauptung, die keine ist“.

Die Seite räumt es selbst ein: IQAE schlage MC *"only asymptotically and only
in query count, not runtime."* Der Caveat steht im Text, nicht in der Grafik.

### Ihre eigenen Zahlen widerlegen die Überschrift

| | |
|---|---|
| Problemgröße | **2 Assets** (AAPL, MSFT), 11 Qubits |
| Einzelner AE-Lauf | 202 ms |
| Vollständiger Lauf, 8 Kerne | **20,6 s** |
| Hardware | **rauschfreier Simulator** |

Ein 2-Asset-VaR per klassischem MC: Millisekunden. Ohne Rauschen, ohne Queue,
ohne Cloud-Round-Trip.

### Die zwei Qubit-Zählweisen

~700 Qubits (ihre Schätzung für 100+ Assets) vs. 8.000.000 logische Qubits
(AWS/Goldman für n=100). Kein Widerspruch — **algorithmische** Qubits ohne
Fehlerkorrektur gegen den vollständigen **fehlerkorrigierten** Bedarf.
Der Faktor dazwischen ist das Problem, über das die Debatte hinweggeht.

Eigener Abschnitt wert: *"Warum jede Qubit-Zahl, die du liest, eine von zwei
völlig verschiedenen Zahlen ist."*

### Fairness

Sie schreiben offen, dass nichts auf echter Hardware läuft, und nennen für
industriellen Vorteil fehlerkorrigierte Hardware in den 2030ern mit
*"thousands of logical qubits and roughly 10^7–10^9 logical gate operations"*.
Sachlich vertretbar.

Ton: nicht "die lügen", sondern **"die Caveats stehen im Text, die Grafik sagt
etwas anderes, und niemand liest die Caveats."**

→ **Artikel 1 (Fallbeispiel), 3**

---

## 7. Tech Monitor / Greg Noone  [S]

*Quantum Untangled: AWS and Goldman* · techmonitor.substack.com · 16.11.2023

Sekundärberichterstattung zu Quelle 2. Nicht als Beleg zitieren — Primärquelle
verwenden. Nützlich als Beispiel dafür, wie das Ergebnis rezipiert wurde.

---

## AWS Braket — Plattformfakten (Live-Abfrage 2026-09-22)

Preise und Geräte vor Veröffentlichung jedes Artikels neu prüfen. Wichtig:
**Die AWS-Dokumentation ist an mehreren Stellen veraltet.** Die folgende
Tabelle stammt aus `aws braket search-devices`, nicht aus der Doku.

### Regionen und tatsächlicher Gerätestatus

| Region | Gerät | Qubits | Status |
|---|---|---|---|
| **us-west-1** (N. Kalifornien) | Rigetti **Cepheus-1-108Q** | 108 | online |
| | Rigetti Ankaa-3 | 84 | **retired** — Doku listet es noch |
| | SV1, DM1 | — | online |
| **us-east-1** (N. Virginia) | IonQ Forte Enterprise 1 | 36 | online |
| | IonQ Forte-1 | 36 | **offline** |
| | QuEra Aquila (analog) | 256 | online |
| | SV1, DM1 | — | online |
| **eu-north-1** (Stockholm) | IQM Garnet | 20 | online |
| | IQM Emerald | 54 | online |
| | AQT IBEX-Q1 (**Ionenfalle**) | — | online |
| | *keine Simulatoren* | — | — |
| **eu-west-2** (London) | nur SV1, DM1 | — | Oxford Lucy retired |

- **TN1 ist überall retired.**
- Braket gibt es **nicht in eu-central-1** (Frankfurt). Stockholm ist die
  einzige EU-Region mit QPUs; London ist Drittland und hat nur Simulatoren.
- Das SDK kann Tasks an QPUs in **jeder** Region schicken, unabhängig von der
  Arbeitsregion — es öffnet automatisch eine Session zur Geräteregion.
- **Korrektur gegenüber früherer Fassung:** Rigetti steht in us-west-1,
  nicht us-west-2.

### Preise

| Device | Per-Task | Per-Shot | Reservierung/h |
|---|---|---|---|
| Rigetti Cepheus-1 | $0.30 | **$0.000425** | $4.100 |
| IQM Garnet | $0.30 | $0.00145 | $3.000 |
| IQM Emerald | $0.30 | $0.00160 | $4.000 |
| QuEra Aquila | $0.30 | $0.01000 | $2.500 |
| AQT IBEX-Q1 | $0.30 | $0.02350 | $4.800 |
| IonQ Forte | $0.30 | $0.08000 | $7.000 |

SV1-Simulator: $0.075/Minute. **Kein D-Wave** auf Braket.

20.000 Shots, reine Shot-Gebühren ohne Task-Gebühr: Cepheus **8,50 $** ·
Garnet 29 $ · AQT 470 $ · IonQ 1.600 $. Als vollständiger Lauf mit 20 Tasks à
1.000 Shots: 14,50 $ · 35 $ · 476 $ · 1.606 $.

### Kostenbremse: native Spending Limits

```
aws braket create-spending-limit \
    --device-arn <arn> --spending-limit <USD> \
    --time-period startAt=<epoch>,endAt=<epoch>
```

Pro Gerät, Betrag als `\d+(\.\d{1,2})?`, Zeitraum optional. Dazu
`update-`, `delete-` und `search-spending-limits`.

**Zwei Fallstricke für Artikel 3:**
1. Doku wörtlich: *„Simulators do not support spending limits."* Ausgerechnet
   SV1, nach Minuten abgerechnet, ist nicht absicherbar.
2. Ein Limit mit Enddatum schützt nach Ablauf nicht mehr — aber: **lässt man
   `--time-period` weg, setzt AWS `endAt` auf 2125-12-30**, also faktisch
   unbefristet. Keinen Zeitraum setzen, außer man will ein Periodenbudget.
3. Die Antwort von `search-spending-limits` liefert `totalSpend` und
   `queuedSpend` — Monitoring ohne Cost Explorer.

**Gesetzt am 2026-09-23 im AWS-Konto der Serie** (unbefristet, Verbrauch 0):
Cepheus-1-108Q/us-west-1 100 $ · Garnet 100 $ · Emerald 50 $ · Ibex-Q1 50 $
(alle eu-north-1). Gesamtrisiko **300 $**.

### Program Sets

Seit 2025: bis 100 Circuits pro Task, bis 24x schneller. AWS räumt selbst ein,
dass einzeln eingereichte Circuits einem Experiment **Stunden** hinzufügen
können → Beleg für die Latenz-These in Artikel 4.

### Eigene Messung: lokaler Simulator (kostenlos)

Braket `LocalSimulator`, GHZ-Circuit, Apple M3 Ultra. Kein AWS, keine Kosten.
Das ist der **Boden des Latenz-Stacks** — alles, was die Cloud hinzufügt,
misst sich hiergegen.

| Qubits | Shots | Median | µs/Shot |
|---|---|---|---|
| 5 | 1.000 | 4,3 ms | 4,3 |
| 10 | 1.000 | 6,5 ms | 6,5 |
| 15 | 1.000 | 12,9 ms | 12,9 |
| 20 | 1.000 | **23,7 ms** | 23,7 |

> **Aktualisiert 25.09.2026:** Artikel 3 nutzt die Wiederholung auf dem M3 Max
> (`results_local_sim.json`): 3,7 / 5,6 / 9,2 / **16,8 ms**. Die Werte oben stammen vom
> M3 Ultra (23.09.).

### Eigene Messung: Braket-Control-Plane-Latenz (2026-09-23)

Von einem Rechner in Deutschland, `GetDevice` (kostenloser API-Aufruf, kein
Task eingereicht). Handshake = frisches DNS+TCP+TLS, also der physikalische
Boden. API = warmer Aufruf auf bestehender Verbindung.

| Region | Handshake | API Median | API p90 | API max |
|---|---|---|---|---|
| eu-north-1 Stockholm | 71 ms | **140 ms** | 243 ms | 434 ms |
| us-east-1 N. Virginia | 226 ms | 271 ms | 358 ms | 384 ms |
| us-west-1 N. Kalifornien | 419 ms | **920 ms** | 1.698 ms | 4.217 ms |
| us-west-2 Oregon | 422 ms | **269 ms** | 301 ms | 602 ms |

**Der zentrale Befund:** us-west-1 und us-west-2 haben praktisch identischen
Handshake (419 vs. 422 ms) — gleiche Entfernung. Aber die API-Antwort
unterscheidet sich um **Faktor 3,4**. Das ist keine Distanz, das ist die
Region selbst. us-west-1 ist AWS' älteste und kleinste Westküsten-Region.

Und genau dort steht Cepheus-1-108Q — das Gerät mit 108 Qubits und dem
günstigsten Shot-Preis. **Man zahlt in Latenz, was man an Shots spart.**

Hochgerechnet auf eine variationelle Schleife mit 200 seriellen Iterationen,
nur Round-Trip, ohne Queue und ohne Gate-Zeit:

| Region | 200 Iterationen |
|---|---|
| Stockholm | 28 s |
| us-west-2 | 54 s |
| us-west-1 | **184 s** |

Eine echte Schleife braucht pro Iteration mehrere Aufrufe (submit, poll,
retrieve), der Faktor ist also noch höher.

**Einschränkung:** Eine Messreihe, ein Standort, ein Zeitpunkt. us-west-1
wurde dreimal gemessen (Median 785 / 1.001 / 920 ms) — der Befund ist stabil,
die Verallgemeinerung auf andere Standorte nicht belegt.

**Konsequenz:** Braket Hybrid Jobs führen die klassische Schleife innerhalb
von AWS neben dem Gerät aus. Genau dafür existieren sie. Der Vergleich
„Schleife vom Laptop" gegen „Schleife als Hybrid Job" ist die Kernmessung von
Artikel 4.

### Eigene Messung: Laptop vs. Hybrid Job (2026-09-23) — Kernmessung Artikel 4

Identische serielle Schleife, 25 Iterationen, 4-Qubit-Circuit, 100 Shots,
SV1 in us-west-1. Simulator statt QPU, damit die Warteschlange als Störgröße
wegfällt. Einziger Unterschied: wo der klassische Treiber läuft.

| Variante | Median | min | p90 | max |
|---|---|---|---|---|
| lokaler Simulator (M3 Ultra) | **2,4 ms** | 2 | 3 | 13 |
| SV1 us-west-1, vom Laptop | **3.074 ms** | 1.962 | 3.588 | 3.957 |
| SV1 us-west-1, Hybrid Job (colocated) | **1.677 ms** | 1.556 | 2.081 | 2.611 |

**Der Befund ist nicht „Hybrid Jobs lösen das Problem".**

- Colocation spart **1.397 ms pro Iteration**, Faktor 1,83.
- Es bleiben **1.677 ms Overhead** — das **713-Fache** der eigentlichen
  Rechnung, obwohl der Treiber direkt neben dem Gerät sitzt.
- Die Latenz ist also **nicht primär Netzwerk.** Rund 45 % waren Distanz,
  55 % sind das Braket-Task-Modell selbst: Task-Anlage, Scheduling,
  S3-Schreibvorgang, Ergebnisabruf.

Hochgerechnet auf 200 Iterationen:

| | Zeit |
|---|---|
| Laptop | 615 s |
| Hybrid Job | 336 s |
| reine Rechnung | **0,5 s** |

**Im colocated Lauf sind 0,14 % der Zeit echte Rechnung.** Damit ist die
Serienthese belegt: Die variationelle Schleife ist latenz-limitiert, nicht
rechen-limitiert.

**Untergrenze, nicht Obergrenze:** Gemessen auf einem Simulator ohne
Warteschlange. Eine echte QPU addiert Queue-Zeit obendrauf.

Nebenbefund: Container-Start des Hybrid Jobs **120 s**, einmalig pro Job.
Lohnt sich also erst ab längeren Schleifen.

**Kosten der gesamten Messung: ~0,20 $** (51 SV1-Tasks à mindestens 3 s
Abrechnung, plus 164 s ml.m5.large). Die QPU-Spending-Limits stehen
unverändert bei 0 — SV1 ist ein Simulator und von ihnen nicht erfasst.

### Eigene Messung: echte QPU, IQM Garnet (2026-09-23)

Identische Schleife, 25 Iterationen, 4-Qubit-Circuit, 100 Shots, eu-north-1.
Ausführungsfenster offen, **Queue leer** — also Bestfall ohne Wartezeit.

| Variante | Client-Median | Service-Median |
|---|---|---|
| lokaler Simulator (M3 Ultra) | **2,4 ms** | — |
| SV1 Kalifornien, vom Laptop | 3.074 ms | — |
| SV1 Kalifornien, Hybrid Job | 1.677 ms | — |
| **IQM Garnet Stockholm, echte QPU** | **3.292 ms** | **1.389 ms** |

**Der Hauptbefund: Die Quantenhardware ist nicht der Engpass.** Eine echte QPU
in Stockholm liegt nur 7 % über einem Simulator in Kalifornien (3.292 vs.
3.074 ms). Die von Braket selbst protokollierte Service-Zeit für Garnet
(1.389 ms) ist sogar *kleiner* als die Client-Zeit des colocated Simulators.
Das Gerät ist schnell; die Maschinerie drumherum ist langsam.

#### Das Poll-Artefakt, isoliert

Das SDK pollt per Default **jede Sekunde** (`DEFAULT_RESULTS_POLL_INTERVAL = 1`).
Damit steckt in jeder Client-Messung bis zu 1 s reine Abfragegranularität.
Gegenprobe mit `poll_interval_seconds=0.1`, n=8:

| Poll-Intervall | Client-Median | Service-Median |
|---|---|---|
| 1 s (Default) | 3.292 ms | 1.389 ms |
| 0,1 s | **2.290 ms** | 1.139 ms |

**1.002 ms Differenz — praktisch exakt das Poll-Raster.** Kein Schätzwert.

#### Schichtzerlegung Garnet (bei schnellem Polling)

| Schicht | Zeit | vermeidbar? |
|---|---|---|
| Poll-Granularität (Default) | ~1.000 ms | **ja**, ein Parameter |
| Netzwerk + S3-Abruf + SDK | ~1.151 ms | teilweise (Colocation) |
| Braket-Service + Gerät | ~1.139 ms | nein |
| eigentliche Rechnung | < 2,4 ms | — |

Bei 200 Iterationen in Default-Konfiguration: **11 Minuten Wall-Clock, davon
eine halbe Sekunde Rechnung.**

**Handlungsempfehlung, die aus der Messung folgt:** `poll_interval_seconds`
senken. Ein Parameter spart bei 200 Iterationen rund 200 Sekunden — gratis.

**Kosten:** Garnet 25 Iterationen 11,13 $ + 8 Iterationen Poll-Test 3,56 $ +
Simulatorläufe ~0,20 $ = **~14,89 $**. Das Spending Limit zählt korrekt mit
(11,125 nach dem ersten Lauf) — Bremse nicht nur gesetzt, sondern verifiziert.

### Setup-Hürden (alle in Artikel 3 eingearbeitet)

1. Profilregion eu-central-1 wird vom SDK stillschweigend übernommen →
   Fehler ist ein nackter DNS-Fehler auf `braket.eu-central-1.amazonaws.com`,
   nicht „Region nicht unterstützt".
2. `AWSServiceRoleForAmazonBraket` fehlt anfangs → erster Task scheitert mit
   AccessDenied.
3. Kein S3-Bucket für Task-Ergebnisse vorhanden.
4. Hybrid Jobs brauchen zusätzlich eine Execution Role. Das SDK findet sie
   automatisch **nur unter Pfad `/service-role/`** — sonst `role_arn`
   explizit übergeben.
5. **Fremdanbieter-QPUs verlangen eine Nutzungsvereinbarung.** Ohne Annahme
   in der Konsole scheitert der erste Task mit
   `AccessDeniedException: User agreement has not been accepted`.
   Betrifft IQM, Rigetti, AQT, IonQ, QuEra — **nicht** SV1/DM1, weil die
   AWS' eigene Simulatoren sind. Die Vereinbarung ist ein Vertrag mit den
   Hardwareanbietern und gehört in einem Unternehmen vor die Rechtsabteilung,
   nicht in ein Setup-Skript.

### Umgebung

Ausgangszustand am 2026-09-22: **null Tasks gelaufen, keine Spending Limits**
im AWS-Konto der Serie.

Regionsaufteilung für die Serie: **us-west-1** als Arbeitspferd (Cepheus mit
108 Qubits ≈ Problemgröße des Vanguard-Experiments, günstigster Shot-Preis,
Simulatoren vor Ort). **eu-north-1** für Artikel 5, weil dort mit AQT IBEX-Q1
die einzige erreichbare Ionenfalle in der EU steht.

## Noch zu beschaffen

- [ ] Iterationszahlen aus Fig. 4–6 der Vanguard-Arbeit (PDF-Grafiken)
- [ ] *Quantum Portfolio Optimization: An Extensive Benchmark* (arXiv:2509.17876)
      — durcharbeiten, bislang nur Suchtreffer
- [ ] *Quantum optimization benchmark library — the intractable decathlon*
      (arXiv:2504.03832) — Referenz [15] der Vanguard-Arbeit, Benchmark-Standard
- [ ] Eigene Messreihe: Latenz-Stack auf Braket (Artikel 4)
- [ ] Eigene Messreihe: klassische MC-Baseline (Artikel 2)
