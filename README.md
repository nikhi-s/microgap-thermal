# Micro-Gap Thermal Diode — Experimental Research Repository

**Nikhitha Swaminathan** · Lowery Freshman Center, Allen ISD, Allen, Texas  
USPTO Provisional Patent No. 64/013,320 · Filed March 2026  
**Interactive 3D Device Model:** https://nikhi-s.github.io/microgap-thermal/

---

## Key Result

Far-field radiative thermal rectification measured across a 508 µm vacuum micro-gap between asymmetric emissivity material pairs (steel ε≈0.2, glass ε≈0.9) under ~38 Torr partial vacuum.

| Metric | Value |
|---|---|
| Corrected rectification ratio η | 0.9325 ± 0.0016 |
| Rectification | −6.75% |
| p-value | < 0.001 |
| 95% Confidence Interval | [6.4%, 7.1%] |
| Vacuum pressure | ~38 Torr (~5% atmosphere) |
| Gap distance | 508 µm |
| Material pair | Steel (ε≈0.2) vs. Glass (ε≈0.9) |

Atmospheric control experiment returned η = 1.0006 ± 0.0008 (p = 0.754) — a null result consistent with air conduction masking the emissivity signal at atmospheric pressure. This null validates the measurement system.

A statistically significant atmospheric result (η = 0.9883, p = 0.0005) was **identified and rejected** via first-principles Seebeck coefficient analysis: steel-glass heater pair ran 4.4°C hotter than glass-glass pair, predicting a 1.2% calibration artifact. Measured apparent signal: 1.17%. Match within 0.03%.

---

## Original Discovery — Thermal Current Divider Effect

Gap sweep experiments (8.5, 25.4, 254, 508 µm) revealed that in constant-power heating, heat splits between two parallel sensor paths. When gap resistance increases, blocked heat redistributes to the parallel path rather than disappearing.

- V_bot (through-gap metric): −32% sensitivity across 60× gap increase
- V_top + V_bot sum metric: only −4.1% sensitivity
- **Sensitivity advantage of through-gap metric: 16×**

This effect does not appear in existing near-field thermal radiation literature. It means the conventional sum-based measurement metric used in prior studies is 16× less sensitive to gap physics than the through-gap metric.

---

## Apparatus

Home laboratory. All components assembled from scratch across two complete design phases.

| Component | Specification |
|---|---|
| Carrier plates | Aluminum 6061, 75×75×3 mm |
| Heaters | Kapton film, 12V, 7W each |
| Heat flux sensors | TEG modules SP1848-27145 (V_top, V_bot) |
| Gap spacers | Kapton shim — 8.5, 25.4, 254, 508 µm |
| Sample plates | Swappable: glass (ε≈0.9) or steel (ε≈0.2) |
| Data acquisition | Arduino Mega 2560 + ADS1115 16-bit ADC |
| Noise floor | <3 µV at 8 SPS |
| Vacuum | Mechanical pump, ~38 Torr, improvised chamber |
| Run duration | 9+ hours overnight, ~30,000 data points per run |

**Phase 1** (150×150 mm plates, screw clamping, microsphere spacers) failed — heat spread laterally, never reached steady state, gap variation from tilt. **Phase 2** (75×75 mm, kinematic constraint, Kapton shims) reached 70–92°C with stable plateaus in 10–12 minutes.

See `figures/figure_M1_mechanical_stack.png` for the full annotated apparatus diagram.

---

## Measurement Protocol — ABBA Bidirectional Heating

To cancel slow environmental drift across 9-hour overnight runs:

```
[A1 forward] → adaptive cooldown → [B1 reverse] → adaptive cooldown → [B2 reverse] → adaptive cooldown → [A2 forward]
```

- Cooldown criterion: within 3°C of ambient for 30 seconds
- Allan deviation analysis used to identify optimal averaging window (τ ≈ 3–7s)
- Without both: precision overestimated by 10–20×

See `arduino/Test16_ABBA_Adaptive_Cooldown_Rectification.ino` for the firmware that ran the key experiment.

---

## Repository Structure

```
microgap-thermal/
│
├── README.md                        ← this file
│
├── arduino/                         ← experiment firmware (Arduino Mega 2560)
│   ├── Test16_ABBA_Adaptive_Cooldown_Rectification.ino   ← KEY RESULT
│   ├── Test15_GAP_SWEEP_Adaptive.ino
│   ├── Test14_ABBA_Adaptive_Cooldown.ino
│   ├── GAP_SWEEP_Adaptive__1_.ino
│   ├── sketch_feb16a_ABBA.ino
│   └── HEATER_DIAGNOSTIC.ino
│
├── analysis/                        ← Python analysis scripts
│   ├── thermal_rectification_plots.py
│   ├── thermal_model.py
│   ├── uncertainty_analysis.py
│   └── README.md                    ← describes each script
│
├── figures/                         ← publication-quality result figures
│   ├── fig7_key_result.png          ← KEY RESULT — 5-panel vacuum ABBA
│   ├── fig5_gap_sweep_vbot.png
│   ├── fig6_current_divider.png
│   ├── fig8_allan_deviation.png
│   ├── fig9_rectification_physics.png
│   ├── fig10_vacuum_prediction.png
│   ├── figure_M1_mechanical_stack.png
│   ├── stack_diagram_top_half.png
│   ├── stack_diagram_bottom_half.png
│   ├── drsef_5panel_tight.png
│   └── README.md                    ← describes each figure
│
├── data/                            ← raw experimental data (1 Hz, Arduino Serial Monitor)
│   ├── README.md                    ← describes each file in detail
│   ├── Module-A_contact_G-G_ABBA_16Feb_Control.txt          ← calibration, no gap
│   ├── Module-B_10Mil_G-G_GapSweep_16Feb.txt                ← gap sweep 254 µm
│   ├── Module-B_1Mil_G-G_GapSweep_17Feb.txt                 ← gap sweep 25.4 µm
│   ├── Module-B_20mil_G-G_GapSweep_20Feb.txt                ← gap sweep 508 µm
│   ├── Module-C_1by3Mil_G-G_GapSweep_17Feb.txt              ← gap sweep 8.5 µm
│   ├── Module-C_3-6um_G-G_GapSweep_18Feb_Clumpsy.txt        ← microsphere failure (documented)
│   ├── Module-C_3-6um_G-G_GapSweep_19Feb_Cleaned.txt        ← post-cleaning retake
│   ├── Module-C_3-6um_G-G_GapSweep_19Feb_retake.txt         ← second retake
│   ├── Module-D_20mil_S-G_Rectification_19Feb_failed.txt    ← atmospheric attempt (incomplete)
│   ├── Module-D_20mil_S-G_Rectification_19Feb_retake.txt    ← atmospheric null η=1.0006
│   ├── Module-E_20mil_G-G_Rectification_20Feb_Control.txt   ← vacuum GG control η_apparatus=0.9269
│   ├── Module-E_20mil_S-G_Rectification_23Feb_Vacuum_fixedTime.txt  ← ⭐ KEY RESULT η=0.9325
│   └── Module-E_20mil_S-G_Rectification_24Feb_Vacuum_fixedTime_A2_Rerun.txt  ← A2 rerun attempt
│
├── docs/                            ← research paper and protocol
│   └── GENIUS_ResearchPaper.pdf
│
└── index.html                       ← interactive 3D model of future 2046 device
```

---

## Experimental Comparison With Published Predictions

Otey, Lau & Fan (2010) *Physical Review Letters* predicted rectification ratios of 5–10% for moderate emissivity contrasts at far-field separations. The 6.7% measured here for steel-glass (4.5× emissivity contrast) falls within that prediction.

The Thermal Current Divider effect does not appear in Song et al. (2015), Lim et al. (2015), or other near-field thermal radiation experimental literature reviewed.

---

## Next Steps (Future Work)

1. **Higher emissivity contrast** — gold-coated glass (ε≈0.02) vs. high-ε ceramic (~47× contrast vs. current 4.5×)
2. **Deeper vacuum** — KF-flanged turbomolecular system targeting <1 Torr
3. **Micro-gap regime** — sub-10 µm with AFM-verified substrate flatness and capacitance gap sensing
4. **Nano-gap regime** — 50–500 nm with piezo actuator stack and feedback control
5. **FEM thermal model** — predictive COMSOL/Python model to pre-calculate η before each run

---

## Recognition

- USPTO Provisional Patent No. 64/013,320 (sole inventor, March 2026)
- GENIUS Olympiad 2026 — Finalist, Resource & Energy category
- Toshiba ExploraVision 2026 — National Finalist (1 of 24 teams)
- Sigma Xi Student Research Showcase 2026 — Accepted presenter
- 2026 TXST STEM Conference — Presented alongside university-level researchers

---

## Contact

**Nikhitha Swaminathan**  
ani.nikhitha@gmail.com  
Lowery Freshman Center, Allen ISD, Allen, Texas
