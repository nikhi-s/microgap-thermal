# figures/

Figures for the Micro-Gap Thermal Diode project. Every data figure is produced by a script in
`../analysis/` or `../simulations/` from the raw logs in `../data/`; nothing is hand-entered.
Colors in the paper figures: steel-heated / forward = orange, glass-heated / reverse = blue;
through-gap metric = yellow, sum metric = green.

---

## `paper/` — TJAS 2026 paper figures and tables

Produced by `../analysis/paper_figures.py` (PNG 300 DPI, PDF, SVG). Draft captions with the
computed numbers are in `paper/FIGURE_CAPTIONS.md`; final captions are written by the author.

| File | Paper | Content |
|---|---|---|
| `fig_allan_deviation` | Figure 6 | Allan deviation of each atmospheric ABBA plateau (steel–glass and glass–glass); optimal averaging τ ≈ 3–7 s; naive σ/√N for comparison |
| `fig3_gap_sweep` | Figure 7 | (a) V_bot and sum vs gap, 7.62–508 µm, run-to-run error bars: −32% vs −1.9%. (b) Warm-up curves for 7.62 and 508 µm with the firmware plateau windows shaded |
| `fig5_air_null_artifact` | Figure 8 | (a) Atmospheric η_corrected on both metrics with 95% CIs. (b) Heated-plate temperatures, steel–glass vs glass–glass, and the predicted Seebeck artifact vs the measured apparent signal |
| `fig4_pressure_map` | Figure 9 | Simulation 1: gas vs radiative conductance and radiation share of gap heat vs pressure; Feb 2026 runs (15–40 Torr) and the 10⁻² mbar target marked |
| `fig6_vacuum_result` | Figure 10 | (a) Vacuum through-gap phase curves incl. both A2 attempts (rerun: planned confirmation, inconclusive). (b) Glass–glass control forward phase rising inside its averaging window. (c) η_corrected for every window, metric and pairing |
| `fig7_gap_bound` | Figure 11 | Simulation 2: rectification the gap alone can produce vs ΔT at ~36 Torr and 10⁻⁵ mbar, against the measured asymmetry ranges |
| `table2_gap_sweep.csv` | Table 2 | Gap-sweep values per gap |
| `table3_vacuum_plateaus.csv` | Table 3 | Vacuum plateau values, both runs and the A2 rerun |

The `fig3`–`fig7` file names predate the paper's numbering; the table maps them.
Simulation figures `sim1_pressure` and `sim2_rectification` are in `../simulations/figures/`.

---

## `regenerated/` — plots 1–14 (September 2026 rerun of the original scripts)

| Files | Script |
|---|---|
| `plot1`–`plot8`, `summary_table` | `thermal_rectification_plots.py` — gap sweep, air vs radiation, atmospheric ABBA, TEG mismatch, atmospheric η, V_top/V_bot split, repeatability, measured air vs ~36 Torr |
| `plot9`–`plot11` | `uncertainty_analysis.py` — Allan deviation, uncertainty budget, plateau stability |
| `plot12`–`plot14` | `thermal_model.py` — 1D resistance model; "vacuum" here means hard vacuum (< ~10⁻² Torr) |

---

## Apparatus diagrams

- `figure_M1_mechanical_stack.png` — full annotated cross-section of the Phase 2 kinematic stack, top to bottom: cork → Al 6061 support → graphite TIM → TEG (V_top) → graphite TIM → top heater → Al carrier → [steel plate / micro-gap / glass slide] → Al carrier → bottom heater → graphite TIM → TEG (V_bot) → graphite TIM → Al support → cork. Orange dashed border marks the swappable test section.
- `stack_diagram_top_half.png`, `stack_diagram_bottom_half.png` — the same diagram split for presentations.

---

## Superseded February 2026 figures

Kept for the record; do not use in new materials. (Suggested: move them to `archive_2026-02/`.)

| File | What it shows | Why superseded | Replacement |
|---|---|---|---|
| `fig7_key_result.png` | Despite its name, the **atmospheric null** (η = 1.0006, sum metric) | Misnamed; old p-value and uncertainty | `paper/fig5_air_null_artifact` |
| `drsef_5panel_tight.png` | Vacuum ABBA 5-panel reporting η = 0.9325 ± 0.0016 as a confirmed 6.7% rectification | The result depends on window, metric and phase choice; the A2 confirmation rerun is shown but not analysed | `paper/fig6_vacuum_result` |
| `fig5_gap_sweep_vbot.png` | V_bot vs gap | "8.5 µm" (shim is 7.62 µm), "60×" (is 67×) | `paper/fig3_gap_sweep` |
| `fig6_current_divider.png` | Sum and V_top/V_bot split vs gap | Same labels; "4.1%" is from contact (1.9% across the gaps) | `paper/fig3_gap_sweep`, `regenerated/plot6` |
| `fig8_allan_deviation.png` | Allan deviation, air runs | Still valid; restyled | `paper/fig_allan_deviation` |
| `fig9_rectification_physics.png` | Air vs radiation (419×…7×) and predicted signals | 8.5 µm; right panel uses an old linear-pressure model | `paper/fig4_pressure_map` |
| `fig10_vacuum_prediction.png` | "Predicted" vacuum curves | Curves were hand-entered, not computed; contradicted by the measured vacuum run | `paper/fig4_pressure_map` |
