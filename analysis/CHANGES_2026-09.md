# Analysis script update (Sept 2026)
 
Changes made on 24–26 September 2026
All scripts run from `analysis/` and read the raw logs in `../data/` (override with `MGTD_DATA_DIR` / `MGTD_OUT_DIR`).
 
| Script | Output folder | Changes |
|---|---|---|
| `thermal_rectification_plots.py` (plots 1–8, summary table) | `../figures/regenerated/` | Reads the raw logs instead of hardcoded local file paths; gap-sweep values computed from the Module-B/C logs (the contact sum was hardcoded as 1015 mV; the log gives 1007.8 mV); 508 µm point added; smallest gap 7.62 µm (0.3 mil); Plot 2 uses a far-field gray-body model at 340 K (ad hoc near-field factor removed), log–log axes; Plot 8's hand-entered "vacuum prediction" curve replaced by the measured ~36 Torr glass–glass point |
| `thermal_model.py` (plots 12–14) | `../figures/regenerated/` | Calibration points and gap-sweep points read from the raw logs (values identical to the old hardcoded ones); 7.62 µm; "vacuum" relabelled "hard vacuum (< ~10⁻² Torr)"; SG−GG sum difference relabelled a material-contrast signal; summary text corrected ("buried below noise" contradicted its own 1.9 mV vs 0.9 mV numbers) |
| `uncertainty_analysis.py` (plots 9–11) | `../figures/regenerated/` | Data paths only |
| `paper_figures.py` (new) | `../figures/paper/` | TJAS paper Figures 6–11 (Allan deviation, gap sweep, atmospheric null and Seebeck artifact, pressure map, vacuum result, gap bound) as PNG/PDF/SVG, plus `table2_gap_sweep.csv` and `table3_vacuum_plateaus.csv`. Imports `../simulations/` for Simulations 1–2 and the shared plot style. |
 
All four handle the NUL bytes and CRLF endings in the firmware logs.
 
## Values that differ from the February 2026 versions
 
| Quantity | February 2026 | Now (from the raw logs) |
|---|---|---|
| Smallest gap | 8.5 µm | 7.62 µm (0.3 mil Kapton) |
| Air:radiation ratio at the smallest gap | 419× | 468× (k = 0.026 W/m·K, 340 K) |
| Gap-sweep V_bot drop, 7.62 → 508 µm | 32% over 60× | 31.7% over 67× |
| Gap-sweep sum drop | 4.1% | 1.9% across the gaps (4.1% from contact) |
| Through-gap vs sum sensitivity | 16× | 17× |
| Run-to-run CV of the sum | 0.10, 0.15, 0.20% | 0.10, 0.17, 0.24, 0.11% (7.62, 25.4, 254, 508 µm) |
| Atmospheric corrected η (Allan uncertainty, `uncertainty_analysis.py`) | 1.0006 ± 0.0008, p = 0.754 | 1.0007 ± 0.0009, p = 0.48 |
| Atmospheric corrected η (phase-to-phase spread, 95% CI, `paper_figures.py`) | — | sum 1.0007 ± 0.0019; through-gap 0.9883 ± 0.0065 |
| Heated-plate offset, steel–glass vs glass–glass | 4.4 °C (A1 only) | 3.0 °C mean, 2.4–4.4 °C by phase; predicted artifact 0.6–1.3% vs measured 1.17% |
| Vacuum η_corrected | 0.9325 ± 0.0016 | through-gap 0.83–0.99, sum 1.02–1.06 (depends on window and phases; metric-dependent) |
 
The published p = 0.754 is not reproducible: with η = 1.0006 ± 0.0008 the two-sided p would be 0.45.
 
Contact point: `thermal_rectification_plots.py` averages the last 600 rows (V_bot 397.1 mV, sum 1007.8 mV), which includes one corrupted row at the end of the contact log; `paper_figures.py` sorts by time and averages the last 10 minutes (397.2 mV, 1008.3 mV). The difference is 0.1–0.5 mV.
 
## Known model limitation
`thermal_model.py` reproduces its calibration runs only to 14–22% and the gap sweep to ~50% (it assumes a 50 °C heater for the gap sweep; the logs show ~58 °C at the plateau). This was true of the original script as well. Use it for trends, not absolute values.
 
