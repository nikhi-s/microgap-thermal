# analysis/

Python scripts that turn the raw logs in `../data/` into every number, table and figure in the papers.

Original scripts (`thermal_rectification_plots.py`, `thermal_model.py`, `uncertainty_analysis.py`) by Nikhitha Swaminathan, February 2026. Updated 24–26 September 2026, and `paper_figures.py` written, with AI assistance (Claude); see `../AI_USE_LOG.md` and `CHANGES_2026-09.md`.

**Dependencies:** numpy, scipy, matplotlib
```
pip install numpy scipy matplotlib
```
Run every script from this folder. Override the data and output folders with `MGTD_DATA_DIR` / `MGTD_OUT_DIR`.

**Conventions used by all scripts**
- Through-gap channel = V_bot in A phases (top heater on), V_top in B phases (bottom heater on)
- A = steel heated (forward), B = glass heated (reverse); η = A / B
- η_corrected = η(steel–glass) / η(glass–glass control at the same pressure)
- Sum metric = V_top + V_bot

---

## Scripts

### `paper_figures.py` — TJAS 2026 paper figures and tables
Reads the raw logs and imports `../simulations/` (Simulation 1 and 2 code and the shared plot style). Writes PNG (300 DPI), PDF and SVG to `../figures/paper/`.

| Output | Paper | Content |
|---|---|---|
| `fig_allan_deviation` | Figure 6 | Allan deviation of each air ABBA plateau; optimal τ 3–7 s |
| `fig3_gap_sweep` | Figure 7 | V_bot and sum vs gap (7.62–508 µm); warm-up curves with plateau windows |
| `fig5_air_null_artifact` | Figure 8 | Atmospheric η_corrected on both metrics; heated-plate temperatures and the Seebeck artifact |
| `fig4_pressure_map` | Figure 9 | Simulation 1: gas vs radiation across the gap vs pressure |
| `fig6_vacuum_result` | Figure 10 | Vacuum phase curves incl. both A2 attempts; glass–glass control; η_corrected by window, metric and pairing |
| `fig7_gap_bound` | Figure 11 | Simulation 2: rectification the gap alone can produce vs ΔT |
| `table2_gap_sweep.csv` | Table 2 | V_bot, V_top, sum, V_bot/sum, runs, run-to-run SD and CV per gap |
| `table3_vacuum_plateaus.csv` | Table 3 | Plateau values for the steel–glass run, the glass–glass control and the A2 rerun |

Numbers it prints: V_bot −31.7% and sum −1.9% (7.62 → 508 µm); atmospheric η_corrected sum 1.0007 ± 0.0019, through-gap 0.9883 ± 0.0065 (95% CI from phase-to-phase spread); heated-plate offset 3.0 °C (2.4–4.4 by phase), predicted artifact 0.6–1.3% vs measured 1.17%; vacuum η_corrected through-gap 0.830–0.994, sum 1.022–1.062.

(The `fig3`–`fig7` file names predate the paper's numbering; the table above maps them.)

### `thermal_rectification_plots.py` — plots 1–8 and summary table
Writes to `../figures/regenerated/`. Gap sweep (sum and V_bot, contact to 508 µm), air-vs-radiation model, atmospheric ABBA time series, TEG mismatch, atmospheric raw and corrected η (sum metric), V_top/V_bot split, repeatability, and the measured total signal in air vs ~36 Torr.

### `thermal_model.py` — plots 12–14, 1D thermal-resistance network
Writes to `../figures/regenerated/`. Resistance network cork → support → TEG → heater → carrier → gap → carrier → TEG → support → cork, calibrated to the atmospheric ABBA runs. Shows that the gap is about 6% of the stack resistance, why the sum metric is flat, and how much the steel–glass and glass–glass sums would differ in *hard* vacuum (gas conduction removed, below ~10⁻² Torr). The model reproduces its calibration runs only to 14–22% and the gap sweep to ~50%; use it for trends, not absolute values. Section 2.7 of the paper also uses Simulation 1.

### `uncertainty_analysis.py` — plots 9–11, Allan deviation and uncertainty
Writes to `../figures/regenerated/`. For the **atmospheric** ABBA runs: Allan deviation of every plateau, optimal averaging time (τ ≈ 3–7 s), naive standard error vs Allan-based uncertainty, plateau stability, and uncertainty propagation through η_corrected with a two-sided z-test.
```
η_corrected (air, sum metric) = 1.0007 ± 0.0009   95% CI [0.9988, 1.0025]   z = 0.70   p = 0.48
```
The earlier published "1.0006 ± 0.0008, p = 0.754" is not reproducible (with that uncertainty the two-sided p would be 0.45). This script does not analyse the vacuum runs; the vacuum numbers come from `paper_figures.py`.

---

## Reproducing the superseded vacuum number
The previously reported η = 0.9325 ± 0.0016 is the through-gap A1/B1 ratio using the 30–50 min window for steel–glass and the 20–40 min window for the glass–glass control (1.1392 / 1.2216). `paper_figures.py` (Figure 10c) shows how it changes with window, metric and phase choice.

---

## Data file format
See `../data/README.md`. ABBA logs have 11 columns:
```
time_ms, phase, phase_time_ms, sample_num, Vtop_mV, Vbot_mV, Tt_C, Tb_C, dT_C, Vheater_V, Tamb_C
```
with phase labels `WAIT_*`, `A1_FWD_HEAT`, `A1_COOLDOWN`, `B1_REV_HEAT`, `B1_COOLDOWN`, `B2_REV_HEAT`, `B2_COOLDOWN`, `A2_FWD_HEAT`, `A2_COOLDOWN`. Gap-sweep logs have 13 columns (adding `run` and `dVdt_mVs`) with phases `WAIT_AMBIENT`, `HEATING`, `PLATEAU`, `COOLDOWN`. Pressure is not logged.
