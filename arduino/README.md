# arduino/

Arduino firmware for the Micro-Gap Thermal Diode experiments.
All firmware written by Nikhitha Swaminathan, December 2025 – February 2026.
Hardware: Arduino Mega 2560 + ADS1115 16-bit ADC + MAX31855 thermocouple interfaces + DHT11 ambient sensor.

**Libraries required:**
- Adafruit_ADS1X15
- Adafruit_MAX31855
- DHT sensor library

Every firmware version prints a `#` metadata header (RUN_ID, GAP_DISTANCE, MATERIAL_PAIR,
timing parameters, hardware self-test) before the 1 Hz CSV data. The logs in `../data/`
were captured from the serial stream with CoolTerm. Pressure is not logged; gauge
readings are recorded in the lab notebook.

---

## Firmware Files

### `Test16_ABBA_Adaptive_Cooldown_Rectification.ino`
**ABBA rectification protocol, Test 16 (adaptive-cooldown version).**

Full ABBA bidirectional heating for the 508 µm runs:
- Forward heating (A): top heater on — the top plate (steel in the steel–glass stack) is the hot side
- Reverse heating (B): bottom heater on — the bottom plate (glass) is the hot side
- Cooldown: adaptive, both thermocouples within 3 °C of ambient for 30 s
- Logging: 1 Hz; time, phase, V_top, V_bot, T_top, T_bot, ΔT, heater voltage, T_ambient

**Note on the partial-vacuum runs (Feb 22–24).** The thermocouples were damaged when the stack
was moved into the vacuum chamber, so the adaptive cooldown could not be used. Those runs used a
fixed-cooldown build of this firmware (TEST 16B glass–glass control: 40-min heat / 70-min cooldown;
TEST 16C steel–glass: 50 / 90; TEST 16E A2 rerun). That build is not yet in this folder —
**to be added**. Its settings are recorded in the headers of the three Module-E vacuum logs.

The partial-vacuum result is inconclusive (see the main README): the measured asymmetry changes
direction with the metric, and the planned confirmation of A1 did not reproduce it.

### `Test15_GAP_SWEEP_Adaptive.ino`
**Refined gap sweep firmware — Modules B & C.**

Glass–glass plates at 7.62, 25.4, 254 and 508 µm (Kapton shims), 3–5 heat–plateau–cool cycles per gap.
Forward heating only (symmetric pair). Adaptive steady-state detection: the 180 s PLATEAU window starts
when dV/dt falls below 0.05 mV/s. This triggers 7–10 min after heater-on, while V_bot is still rising,
so the gap-sweep values are readings at a fixed stage of warm-up rather than true steady state.
(The firmware header labels the smallest gap "8.5um"; the shim is 0.3 mil = 7.62 µm.)

### `Test14_ABBA_Adaptive_Cooldown.ino`
**Atmospheric ABBA runs.**

Same ABBA protocol as Test 16 at atmospheric pressure, 40-min heat phases with adaptive cooldown.
Used for the atmospheric null (sum-based η_corrected = 1.0007 ± 0.0009, p = 0.48) and the
false-positive investigation (through-gap η_corrected = 0.9883, p = 0.0005, rejected as a Seebeck
calibration artifact from a 2.4–4.4 °C heater-plate offset).

### `GAP_SWEEP_Adaptive (1).ino`
**Early gap sweep version.**

Earlier iteration of the gap sweep firmware. Measures V_top + V_bot and V_bot across gap distances;
the data that first showed the thermal current divider effect (V_bot falls 32% while the sum
changes 1.9% across the 67× gap increase from 7.62 to 508 µm).

### `sketch_feb16a_ABBA.ino` (Test 13)
**Early ABBA protocol with full metadata logging.**

First complete ABBA implementation with structured metadata headers:
RUN_ID, GAP_DISTANCE, MATERIAL_PAIR, SPACER_TYPE, RUN_NUMBER, OPERATOR_NOTES.
Fixed heating and cooling durations (not yet adaptive). Documents the protocol development history.

### `HEATER_DIAGNOSTIC.ino`
**Hardware validation tool.**

Fires the top heater for 2 minutes, then the bottom heater for 2 minutes, and monitors the TEG
response to confirm both heaters deliver power (expected: V_top, then V_bot, rise above ~200 mV).
Run before every experimental session.

---

## Experimental Sequence

```
sketch_feb16a_ABBA.ino        →  Test 13: protocol development + Phase 1 calibration
Test14_ABBA_Adaptive.ino      →  Test 14: atmospheric ABBA (null result + rejected false positive)
GAP_SWEEP_Adaptive (1).ino    →  early gap sweep: thermal current divider effect
Test15_GAP_SWEEP.ino          →  Test 15: refined gap sweep, 7.62–508 µm
Test16_ABBA_Rectif.ino        →  Test 16: 508 µm ABBA; fixed-cooldown build (16B/16C/16E) used for the
                                  partial-vacuum runs — result inconclusive
```
