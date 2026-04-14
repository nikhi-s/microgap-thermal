# data/

Raw experimental data logged by Arduino firmware at 1 Hz via Serial Monitor.
All files are plain text with CSV-format data rows beneath comment headers.

13 files covering the complete experimental progression from calibration
through the key vacuum rectification result.

---

## File Format

Each file begins with `#` comment lines containing run metadata:
RUN_ID, GAP_DISTANCE, MATERIAL_PAIR, SPACER_TYPE, NOTES, timing parameters.

Data rows follow with columns:
```
time_ms, phase, phase_time_ms, sample_num, Vtop_mV, Vbot_mV, Tt_C, Tb_C, dT_C, Vheater_V, Tamb_C
```

| Column | Units | Description |
|---|---|---|
| `time_ms` | ms | Milliseconds since Arduino boot |
| `phase` | string | Experiment phase label |
| `phase_time_ms` | ms | Elapsed time within current phase |
| `sample_num` | int | Sequential sample counter |
| `Vtop_mV` | mV | TEG voltage — hot-side sensor |
| `Vbot_mV` | mV | TEG voltage — through-gap sensor (primary metric) |
| `Tt_C` | °C | Thermocouple — top carrier plate |
| `Tb_C` | °C | Thermocouple — bottom carrier plate |
| `dT_C` | °C | Temperature differential (Tt - Tb) |
| `Vheater_V` | V | Heater supply voltage |
| `Tamb_C` | °C | DHT11 ambient temperature |

---

## Experimental Files — By Module

### MODULE A — Calibration (Contact, No Gap)

**`Module-A_contact_G-G_ABBA_16Feb_Control.txt`**
- Glass-glass, direct contact (0 µm gap), atmospheric
- Full ABBA protocol: A1/B1/B2/A2 phases
- 27,820 data rows (~7.7 hours)
- Purpose: Baseline calibration — apparatus behaviour with no gap, no emissivity effect

---

### MODULE B — Gap Sweep (Kapton Shims, 3 runs each)

**`Module-B_10Mil_G-G_GapSweep_16Feb.txt`**
- Glass-glass, 254 µm gap (10 mil Kapton shim), atmospheric
- HEATING / PLATEAU / COOLDOWN phases, 3 repeat runs
- 14,024 data rows
- Purpose: Gap sweep data point at 254 µm

**`Module-B_1Mil_G-G_GapSweep_17Feb.txt`**
- Glass-glass, 25.4 µm gap (1 mil Kapton shim), atmospheric
- 23,156 data rows
- Purpose: Gap sweep data point at 25.4 µm

**`Module-B_20mil_G-G_GapSweep_20Feb.txt`**
- Glass-glass, 508 µm gap (20 mil = 2×10 mil Kapton shims), atmospheric
- 23,285 data rows
- Purpose: Gap sweep data point at 508 µm

---

### MODULE C — Gap Sweep (Microsphere Spacers — Phase 1 attempt)

**`Module-C_1by3Mil_G-G_GapSweep_17Feb.txt`**
- Glass-glass, 8.5 µm gap (1/3 mil microsphere spacers), atmospheric
- 22,905 data rows
- Purpose: Smallest gap tested — gap sweep data point at 8.5 µm

**`Module-C_3-6um_G-G_GapSweep_18Feb_Clumpsy.txt`**
- Glass-glass, 3–6 µm microsphere gap attempt, atmospheric
- 22,754 data rows — **compromised**: microspheres clumped unevenly
- Purpose: Documents Phase 1 microsphere failure mode

**`Module-C_3-6um_G-G_GapSweep_19Feb_Cleaned.txt`**
- Glass-glass, 3–6 µm after cleaning, atmospheric
- 2,014 data rows — partial run
- Purpose: Follow-up attempt after cleaning microsphere surfaces

**`Module-C_3-6um_G-G_GapSweep_19Feb_retake.txt`**
- Glass-glass, 3–6 µm retake, atmospheric
- 3,564 data rows
- Purpose: Second retake — confirms microsphere spacers unreliable at this scale

---

### MODULE D — Atmospheric Rectification Attempt (Steel-Glass, Air)

**`Module-D_20mil_S-G_Rectification_19Feb_failed.txt`**
- Steel-glass, 508 µm, atmospheric, ABBA protocol
- 14,237 data rows — **incomplete run**
- Purpose: Documents the failed atmospheric attempt (confirms air masking)
- Note: η ≈ 1.0 as expected — air conduction masks emissivity signal completely

**`Module-D_20mil_S-G_Rectification_19Feb_retake.txt`**
- Steel-glass, 508 µm, atmospheric, full ABBA protocol
- 31,351 data rows (~8.7 hours) — complete run
- Purpose: Full atmospheric null result. Returns η = 1.0006 ± 0.0008, p = 0.754
- **This is the null result referenced in the paper.**

---

### MODULE E — Vacuum Rectification (Key Result)

**`Module-E_20mil_G-G_Rectification_20Feb_Control.txt`**
- Glass-glass, 508 µm, vacuum (~38 Torr), full ABBA protocol
- 30,556 data rows (~8.5 hours)
- Purpose: Apparatus correction factor η_apparatus = 0.9269
- Used to correct for TEG sensitivity mismatch between top and bottom sensors

**`Module-E_20mil_S-G_Rectification_23Feb_Vacuum_fixedTime.txt`** ⭐ **KEY RESULT**
- Steel-glass, 508 µm, vacuum (~38 Torr), full ABBA protocol
- 33,892 data rows (~9.4 hours)
- Phases: WAIT_INITIAL, A1_FWD_HEAT (steel hot), B1_REV_HEAT (glass hot), B2_REV_HEAT, A2_FWD_HEAT
- **Result: η_raw = 0.9275. Corrected: η = 0.9325 ± 0.0016, −6.7% rectification, p < 0.001**
- A2 phase excluded from primary analysis (vacuum degraded from 28.5→29.5 inHg overnight)
- Primary comparison: A1 (350.7 mV) vs B1 (307.8 mV) — both at 28.5 inHg

**`Module-E_20mil_S-G_Rectification_24Feb_Vacuum_fixedTime_A2_Rerun.txt`**
- Steel-glass, 508 µm, vacuum — A2 phase rerun only
- 3,377 data rows
- Purpose: Attempted rerun of excluded A2 phase from 23Feb run
- Note: Pump cycling during rerun introduced artifacts. Not used in primary result.

---

## Experimental Sequence Summary

```
Module A  →  Contact calibration (no gap)
Module B  →  Kapton shim gap sweep: 25.4, 254, 508 µm
Module C  →  Microsphere gap attempt: 3–8.5 µm (documents spacer failure)
Module D  →  Atmospheric ABBA: null result η = 1.0006 (confirms air masking)
Module E  →  Vacuum ABBA: η = 0.9325, −6.7% rectification ← KEY RESULT
```
