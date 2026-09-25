# Analysis script update (Sept 2026)

The three scripts keep their names, plots and output filenames. Run them from
`analysis/`; they read `../data/` and write to `../figures/regenerated/`
(override with `MGTD_DATA_DIR` / `MGTD_OUT_DIR`).

| Script | Changes |
|---|---|
| `thermal_rectification_plots.py` (plots 1–8, summary table) | Reads raw logs instead of `/home/claude/abba_*.txt`; gap-sweep values computed from the Module-B/C logs (contact was hardcoded 1015 mV, now 1007.8 mV from the log); 508 µm point added; smallest gap 7.62 µm (0.3 mil); Plot 2 uses a far-field gray-body model at 340 K (ad hoc near-field factor removed), log–log axes; Plot 8's hand-entered "vacuum prediction" curve replaced by the measured ~36 Torr glass–glass point |
| `thermal_model.py` (plots 12–14) | Calibration points (`abba`) and gap-sweep points read from the raw logs (values identical to the old hardcoded ones); 7.62 µm; "vacuum" relabelled "hard vacuum (< ~10⁻² Torr)"; SG−GG sum difference relabelled a material-contrast signal; summary text corrected ("buried below noise" contradicted its own 1.9 mV vs 0.9 mV numbers) |
| `uncertainty_analysis.py` (plots 9–11) | Data paths only |

All three handle the NUL bytes and CRLF endings in the firmware logs.

## Values that differ from the paper / README
- Air:radiation ratio at the smallest gap: 468× (was 419×).
- Gap-sweep sum drop 7.62→508 µm: 1.9% (4.1% from contact); V_bot drop 31.7%.
- Run-to-run CV of the sum: 0.10%, 0.17%, 0.24%, 0.11% (7.62, 25.4, 254, 508 µm).
- Atmospheric corrected η (uncertainty_analysis.py): 1.0007 ± 0.0009, p = 0.48 (paper: 1.0006 ± 0.0008, p = 0.754).

## Known model limitation
`thermal_model.py` reproduces its calibration runs only to 14–22% and the gap sweep to
~50% (it assumes a 50 °C heater for the gap sweep; the logs show ~58 °C at the plateau).
This was true of the original script as well. Use it for trends, not absolute values.
