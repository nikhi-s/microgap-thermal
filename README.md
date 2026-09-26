# Micro-Gap Thermal Diode — Experimental Research Repository

**Nikhitha Swaminathan** · Allen High School, Allen ISD, Allen, Texas
USPTO Provisional Patent No. 64/013,320 · Filed March 2026
**Interactive 3D Device Model:** <https://nikhi-s.github.io/microgap-thermal/>

---

## What this repository contains

Everything behind the Micro-Gap Thermal Diode (MGTD) experiments of February 2026: the Arduino firmware, the raw 1 Hz logs, the analysis scripts that turn those logs into every number and figure in the papers, and the physics simulations added in September 2026. All results below are reproducible by running the scripts in `analysis/` and `simulations/` against `data/`.

---

## Results

### Atmospheric measurements (validated)

**Gap sweep (glass–glass, 7.62 → 508 µm, air).** The through-gap voltage V_bot falls 32% across the 67× gap increase while the sum V_top + V_bot changes only 1.9% (4.1% from contact). In constant-power heating the heat splits between two parallel paths, so the sum metric is about 17× less sensitive to gap physics than the through-gap metric (the *thermal current divider* effect). Gap-sweep plateaus were read 7–10 min after heater-on, while V_bot was still rising; the ratio between gaps is affected by warm-up timing.

**Atmospheric ABBA null (steel–glass vs glass–glass control, 508 µm).** Sum-based corrected ratio η = 1.0007 ± 0.0009 (p = 0.48): no rectification detectable in air, as predicted, since gas conduction across the gap exceeds radiation by about 7× at 508 µm and about 470× at 7.62 µm.

**False positive identified and rejected.** The through-gap metric showed an apparent −1.17% signal (p = 0.0005). The steel–glass stack's heated plate ran 3.0 °C hotter than the glass–glass control's (2.4–4.4 °C by phase). With the TEG's Seebeck temperature coefficient of about 0.25–0.30 %/°C this predicts a 0.6–1.3% calibration artifact, which accounts for the signal. It was rejected.

### Partial-vacuum measurements (inconclusive)

A steel–glass ABBA run and a glass–glass control were made at a gauge reading of 28.5 inHg (roughly 15–40 Torr absolute, given gauge accuracy and local air pressure). Simulation 1 shows that at this pressure gas conduction across the 508 µm gap is essentially unchanged from air (mean free path ≈ 1.6 µm), so radiation carries only ~3% of the steel–glass gap heat.

A directional asymmetry was measured, but its **direction depends on the metric**: the glass-glass-corrected through-gap ratio is 0.83–0.99 while the sum-based ratio is 1.02–1.06, depending on the averaging window and which phases are included. The forward phase A1 (350.7 mV) was not reproduced by either A2 attempt (306.3 mV at deeper vacuum; 385 ± 37 mV in the Feb 24 confirmation rerun with pump cycling, treated as inconclusive). Heater temperatures could not be measured because both thermocouples had failed. Simulation 2 shows the gap itself can produce at most ~1% at this pressure. **No rectification is claimed from the February data.** Earlier versions of this repository and of the DRSEF paper reported η = 0.9325 ± 0.0016 (−6.7%); that value is one analysis choice among those above and is superseded.

### What the next experiment needs

A chamber at or below 10⁻² mbar (steel–glass radiation reaches 50% of gap heat at ~0.015 Torr), working thermocouples on both plates, a glass–glass control at the same pressure and phase timing, heat phases long enough to reach a true plateau, replicated ABBA sets, and a metric fixed before the run. This is the design of the SS304L high-vacuum chamber now being built.

---

## Apparatus

Home laboratory. All components assembled from scratch across two design phases.

| Component | Specification |
|---|---|
| Carrier plates | Aluminum 6061, 75×75×3 mm |
| Heaters | Kapton film, 12 V |
| Heat flux sensors | TEG modules SP1848-27145 (V_top, V_bot) |
| Gap spacers | Kapton shim — 7.62 (0.3 mil), 25.4, 254, 508 µm |
| Sample plates | Swappable: glass (ε≈0.9) or stainless steel (ε≈0.2) |
| Data acquisition | Arduino Mega 2560 + ADS1115 16-bit ADC |
| Vacuum (Feb 2026) | Mechanical pump, improvised chamber, ~15–40 Torr |
| Run duration | 7–9.4 hours overnight, ~27,000–34,000 samples per run |

**Phase 1** (150×150 mm plates, screw clamping, microsphere spacers) failed: heat spread laterally, never reached steady state, gap variation from tilt. **Phase 2** (75×75 mm, kinematic constraint, Kapton shims) reached 70–92 °C with stable plateaus in 10–12 minutes.

See `figures/figure_M1_mechanical_stack.png` for the annotated apparatus diagram.

---

## Measurement Protocol — ABBA Bidirectional Heating

```
[A1 forward] → cooldown → [B1 reverse] → cooldown → [B2 reverse] → cooldown → [A2 forward]
```

- Air runs: 40-min heat phases, adaptive cooldown (within 3 °C of ambient for 30 s)
- Vacuum runs: 40-min (glass–glass) / 50-min (steel–glass) heat phases, fixed cooldowns (thermocouples damaged)
- Through-gap channel: V_bot in A phases, V_top in B phases; η = A / B, corrected by the glass–glass control
- Allan deviation used to characterise noise vs drift (τ ≈ 3–7 s)

See `arduino/Test16_ABBA_Adaptive_Cooldown_Rectification.ino` for the firmware.

---

## Repository Structure

```
microgap-thermal/
│
├── README.md                        ← this file
├── AI_USE_LOG.md                    ← record of AI assistance (ISEF Form 2A / TJAS statement)
├── LICENSE                          ← GPL-3.0
├── index.html, MGTD_3DModel_Wix.html ← interactive 3D concept model of the future device
│
├── arduino/                         ← experiment firmware (Arduino Mega 2560); see arduino/README.md
│   ├── Test16_ABBA_Adaptive_Cooldown_Rectification.ino   ← 508 µm ABBA (fixed-cooldown build used in vacuum: to be added)
│   ├── Test15_GAP_SWEEP_Adaptive.ino                     ← gap sweep 7.62–508 µm
│   ├── Test14_ABBA_Adaptive_Cooldown.ino                 ← atmospheric ABBA
│   ├── GAP_SWEEP_Adaptive (1).ino, sketch_feb16a_ABBA.ino, HEATER_DIAGNOSTIC.ino
│   └── README.md
│
├── analysis/                        ← Python analysis (reads ../data, writes ../figures)
│   ├── paper_figures.py             ← TJAS paper Figures 6–11 and Tables 2–3
│   ├── thermal_rectification_plots.py  ← plots 1–8, summary table
│   ├── uncertainty_analysis.py      ← plots 9–11: Allan deviation, uncertainty (air runs)
│   ├── thermal_model.py             ← plots 12–14: 1D thermal-resistance model
│   ├── CHANGES_2026-09.md           ← what changed in September 2026 and which numbers moved
│   └── README.md
│
├── simulations/                     ← gap physics simulations (TJAS 2026 paper)
│   ├── sim1_pressure.py             ← gas vs radiation across the gap vs pressure
│   ├── sim2_gap_rectification.py    ← gap-only forward/reverse rectification
│   ├── mgtd_common.py, mgtd_plotstyle.py
│   ├── results/  figures/
│   └── README.md
│
├── figures/
│   ├── paper/                       ← TJAS paper figures (PNG/PDF/SVG), Table 2–3 CSVs, FIGURE_CAPTIONS.md
│   ├── regenerated/                 ← plots 1–14 regenerated from the raw logs
│   ├── archive_2026-02/             ← superseded February 2026 figures, kept for the record (see its README)
│   ├── figure_M1_mechanical_stack.png, stack_diagram_top_half.png, stack_diagram_bottom_half.png
│   └── README.md
│
├── data/                            ← raw logs (1 Hz, CoolTerm capture of the Arduino serial stream); see data/README.md
│   ├── Module-A_contact_G-G_ABBA_16Feb_Control.txt                           ← contact calibration (air)
│   ├── Module-C_1by3Mil_…, Module-B_1Mil_…, Module-B_10Mil_…, Module-B_20mil_…  ← gap sweep 7.62 / 25.4 / 254 / 508 µm (air)
│   ├── Module-C_3-6um_… (3 files)                                            ← microsphere attempts (not used)
│   ├── Module-D_20mil_S-G_Rectification_19Feb_retake.txt                     ← atmospheric ABBA, steel–glass
│   ├── Module-D_20mil_S-G_Rectification_19Feb_failed.txt                     ← heaters did not fire (not used)
│   ├── Module-E_20mil_G-G_Rectification_20Feb_Control.txt                    ← atmospheric ABBA, glass–glass control
│   ├── Module-E_20mil_G-G_Rectification_22Feb_control_Vacuum_fixedTime.txt   ← vacuum glass–glass control (TEST 16B)
│   ├── Module-E_20mil_S-G_Rectification_23Feb_Vacuum_fixedTime.txt           ← vacuum steel–glass (TEST 16C)
│   └── Module-E_20mil_S-G_Rectification_24Feb_Vacuum_fixedTime_A2_Rerun.txt  ← A2 confirmation rerun (TEST 16E)
│
└── docs/
    └── GENIUS_ResearchPaper.pdf     ← February 2026 paper; its vacuum result is superseded (see Results above)
```

---

## Reproducing the results

```
pip install numpy scipy matplotlib
cd analysis
python thermal_rectification_plots.py
python thermal_model.py
python uncertainty_analysis.py
python paper_figures.py
cd ../simulations
python sim1_pressure.py
python sim2_gap_rectification.py
```

Every number quoted above is printed by one of these scripts.

---

## Comparison With Published Work

Otey, Lau & Fan (2010) predicted thermal rectification through vacuum between materials whose optical properties change with temperature. Emissivity contrast by itself gives zero rectification (Simulation 2), and at 15–40 Torr the gap is dominated by gas conduction (Simulation 1), so the February measurements cannot be compared with far-field radiative predictions. Simulation 2 predicts a few percent of radiative rectification, with a definite sign, in hard vacuum (below ~10⁻³ Torr) if the steel's emissivity depends on temperature. That is the regime the next experiment targets.

To our knowledge, the consequence of heat splitting between parallel paths for the choice of measurement metric has not been discussed in the near-field thermal radiation literature (Song et al., 2015; Lim et al., 2015).

---

## Next Steps

1. **High-vacuum chamber** — SS304L chamber with commercial feedthroughs, ≤10⁻² mbar; turbomolecular pump in 2027.
2. **Higher emissivity contrast** — gold-coated glass (ε≈0.02) vs high-ε ceramic; needs ~10⁻⁴ Torr for radiation to carry 90% (Simulation 1).
3. **Instrumented heaters** — thermocouples on both plates so the Seebeck artifact can be bounded in every run.
4. **Full-stack thermal model (Simulation 3)** — constant-voltage heating, TEG Seebeck temperature dependence and lateral losses, to explain the metric-dependent February asymmetry.
5. **Near-field gaps** — deferred until the far-field result is settled.

---

## Recognition

- TJAS 2025 Physical Sciences — Abstract selected
- USPTO Provisional Patent No. 64/013,320 (sole inventor, March 2026)
- GENIUS Olympiad 2026 — Finalist, Resource & Energy category
- Toshiba ExploraVision 2026 — National Finalist (1 of 24 teams; team project)
- Sigma Xi Student Research Showcase 2026 — Accepted presenter
- 2026 TXST STEM Conference — Presented alongside university-level researchers

---

## Contact

**Nikhitha Swaminathan**
<ani.nikhitha@gmail.com>
Allen High School, Allen ISD, Allen, Texas
