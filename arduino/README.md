# arduino/

Arduino firmware for the Micro-Gap Thermal Diode experiments.
All scripts authored by Nikhitha Swaminathan, February 2026.
Hardware: Arduino Mega 2560 + ADS1115 16-bit ADC + MAX31855 thermocouple interfaces.

**Libraries required:**
- Adafruit_ADS1X15
- Adafruit_MAX31855
- DHT sensor library

---

## Firmware Files

### `Test16_ABBA_Adaptive_Cooldown_Rectification.ino` ⭐ KEY EXPERIMENT
**The firmware that produced the 6.7% rectification result.**

Module D — Steel-Glass asymmetric pair, 508 µm gap, vacuum chamber.
Implements the full ABBA bidirectional heating protocol with adaptive cooldown.
- Forward heating (A): top heater ON, bottom OFF — steel plate is hot side
- Reverse heating (B): bottom heater ON, top OFF — glass plate is hot side
- Cooldown criterion: within 3°C of ambient for 30 seconds
- Logging: 1 Hz, timestamps, phase labels, Vtop, Vbot, T_top, T_bot, T_ambient, vacuum_inHg
- Run duration: 9+ hours overnight, ~30,000 data points

### `Test15_GAP_SWEEP_Adaptive.ino`
**Refined gap sweep firmware — Modules B & C.**

Glass-glass control plates at 5 gap distances (contact, 8.5, 25.4, 254, 508 µm).
3 consecutive heat-cool cycles per gap for statistical error bars.
Only forward heating (no ABBA) — symmetric material pair, direction doesn't matter.
Adaptive steady-state detection via dV/dt monitoring instead of fixed timing.

### `Test14_ABBA_Adaptive_Cooldown.ino`
**Atmospheric ABBA runs — the null result.**

Same ABBA protocol as Test16 but at atmospheric pressure (no vacuum chamber).
Used for both the atmospheric null result (η = 1.0006, p = 0.754) and the
false positive investigation (η = 0.9883, p = 0.0005, later rejected via
Seebeck artifact analysis).

### `GAP_SWEEP_Adaptive__1_.ino`
**Early gap sweep version — Thermal Current Divider discovery.**

Earlier iteration of the gap sweep firmware. Measures V_top + V_bot sum and
V_bot individually across gap distances. This is the run that revealed the
Thermal Current Divider effect: sum drops only 4.1% while V_bot drops 32%
across a 60× gap increase.

### `sketch_feb16a_ABBA.ino` (Test 13)
**Early ABBA protocol with full metadata logging.**

First complete ABBA implementation with structured metadata headers:
RUN_ID, GAP_DISTANCE, MATERIAL_PAIR, SPACER_TYPE, RUN_NUMBER, OPERATOR_NOTES.
Used for Phase 1 calibration and early atmospheric runs. Fixed heating/cooling
durations (not yet adaptive). Documents the protocol development history.

### `HEATER_DIAGNOSTIC.ino`
**Hardware validation tool.**

Fires top heater for 2 minutes, then bottom heater for 2 minutes.
Monitors TEG voltage response to confirm both heaters are delivering power.
Expected: Vtop rises to ~200+ mV when top fires; Vbot rises to ~200+ mV when bottom fires.
Run before every experimental session to verify hardware integrity.

---

## Experimental Sequence

The scripts map to the experimental progression:

```
sketch_feb16a_ABBA.ino     →  Test 13: Protocol development + Phase 1 calibration
Test14_ABBA_Adaptive.ino   →  Test 14: Atmospheric ABBA (null result + false positive)
GAP_SWEEP_Adaptive__1_.ino →  Gap sweep: Thermal Current Divider discovery
Test15_GAP_SWEEP.ino       →  Test 15: Refined gap sweep with error bars
Test16_ABBA_Rectif.ino     →  Test 16: Vacuum ABBA → 6.7% rectification ← KEY RESULT
```
