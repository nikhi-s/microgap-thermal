/*
 * ============================================================================
 * TEST 16 — ABBA Protocol with Adaptive Cooldown
 * Micro-Gap Thermal Rectifier: Direction-Dependent Heat Flow
 * ============================================================================
 *
 * HARDWARE: Arduino Mega 2560 (Elegoo)
 * AUTHOR:   Nikhitha Swaminathan
 * DATE:     February 2026
 * PROJECT:  DRSEF / ISEF — Physical Sciences
 *
 * ============================================================================
 * PURPOSE
 * ============================================================================
 * This script implements the ABBA bidirectional heating protocol for
 * characterizing direction-dependent heat transfer across a micro-gap
 * thermal stack. It logs thermoelectric generator (TEG) voltages,
 * thermocouple temperatures, and ambient temperature at 1 Hz.
 *
 * The ABBA protocol cancels temporal drift by repeating forward (A) and
 * reverse (B) heating in the pattern A-B-B-A. Any linear environmental
 * drift averages out when computing: eta = (A1 + A2) / (B1 + B2).
 *
 * ============================================================================
 * MODULE D — RECTIFICATION EXPERIMENT
 * ============================================================================
 *
 * This version is configured for the thermal rectification measurement
 * using asymmetric materials across a 20 mil (508 um) air gap:
 *
 *   - Top surface:    Stainless steel (low emissivity, e ~ 0.1-0.3)
 *   - Bottom surface: Glass / SiO2    (high emissivity, e ~ 0.9)
 *   - Gap medium:     Air (20 mil, set by 2x 10mil kapton shims at corners)
 *
 * The k-mismatch between steel (~15 W/mK) and glass (~1 W/mK) combined
 * with radiation's T^4 nonlinearity creates a direction-dependent heat
 * transfer asymmetry:
 *
 *   Forward (A): Heat through steel -> gap -> glass
 *     Steel (high k) has small dT, glass (low k) has large dT.
 *     Gap sees moderate temperature difference.
 *
 *   Reverse (B): Heat through glass -> gap -> steel
 *     Glass (low k) has large dT, steel (high k) has small dT.
 *     Different temperature distribution at the gap.
 *
 * Expected signal: 1-5 mV difference between A and B phases.
 * The ABBA protocol is essential to resolve this small asymmetry
 * against environmental drift.
 *
 * ============================================================================
 * WHAT IS ABBA AND WHY?
 * ============================================================================
 *
 *   A = Forward heating  (top heater ON, bottom OFF)
 *   B = Reverse heating  (bottom heater ON, top OFF)
 *
 *   Sequence:  A1 -> cool -> B1 -> cool -> B2 -> cool -> A2 -> cool -> DONE
 *
 *   If room temperature drifts linearly during the experiment (say the
 *   room warms by 1 deg C over several hours), A1 sees a cooler room and
 *   A2 sees a warmer room. Averaging (A1+A2)/2 cancels this drift.
 *   Same for (B1+B2)/2. This is standard practice in precision thermal
 *   metrology.
 *
 *   The rectification ratio is then:
 *       eta = q_forward / q_reverse = mean(A1,A2) / mean(B1,B2)
 *
 *   If eta > 1: heat flows preferentially in the forward direction.
 *   If eta = 1: symmetric (no rectification).
 *   If eta < 1: heat flows preferentially in the reverse direction.
 *
 * ============================================================================
 * ADAPTIVE COOLDOWN — WHY NOT FIXED TIMERS?
 * ============================================================================
 *
 *   Problem with fixed cooldown:
 *   In earlier tests (TEST 12, TEST 13), fixed 30-minute cooldowns were
 *   insufficient. After heating to ~106 deg C, the stack was still at
 *   70-80 deg C after 30 minutes. When the next heating phase started
 *   into an already-hot stack, the TEG could not produce a meaningful
 *   differential signal.
 *
 *   Adaptive solution:
 *   Instead of guessing cooldown time, we MEASURE the actual plate
 *   temperatures and only advance to the next heating phase when BOTH
 *   thermocouples have returned to within COOL_THRESHOLD_C (default
 *   3 deg C) of the ambient temperature (measured by DHT11). This
 *   ensures every heating phase starts from the same thermal baseline.
 *
 *   Stability requirement:
 *   To avoid triggering on a momentary TC reading (noise spike), the
 *   plates must remain within the threshold for COOL_STABLE_MS (30 sec)
 *   continuously. If either TC exceeds the threshold during this window,
 *   the stability timer resets.
 *
 *   Safety timeout:
 *   If the plates haven't cooled within COOL_MAX_MS (90 min), the system
 *   advances anyway and logs a warning. This prevents the experiment from
 *   hanging indefinitely if, for example, a TC fails or ambient is
 *   drifting.
 *
 *   Minimum cooldown:
 *   COOL_MIN_MS (2 min) prevents the system from immediately advancing
 *   due to residual heat still being near ambient at the very start of
 *   cooldown. This gives the thermal wave time to propagate.
 *
 *   Cooldown decision flowchart:
 *
 *       [Heating phase ends]
 *              |
 *              v
 *       [COOLDOWN starts, heaters OFF]
 *              |
 *              v
 *       elapsed < COOL_MIN_MS ? ---YES---> keep waiting
 *              |
 *              NO
 *              |
 *              v
 *       Both TCs within COOL_THRESHOLD_C of ambient? ---NO---> keep waiting
 *              |                                                  |
 *              YES                                                v
 *              |                                        elapsed > COOL_MAX_MS?
 *              v                                                  |
 *       Start stability timer                              YES: advance + warn
 *              |
 *              v
 *       Still within threshold for COOL_STABLE_MS? ---NO---> reset timer
 *              |
 *              YES
 *              |
 *              v
 *       [Advance to next heating phase]
 *
 * ============================================================================
 * SENSOR LAYOUT (Physical Stack, Top to Bottom)
 * ============================================================================
 *
 *   MODULE D RECTIFICATION STACK:
 *   The stack is ASYMMETRIC about the air gap. The top side has a
 *   stainless steel plate (low emissivity) and the bottom side has a
 *   glass slide (high emissivity). The 20 mil air gap is maintained by
 *   two 10 mil kapton shims stacked at each corner.
 *
 *   Heat flows from the active heater through its side of the stack,
 *   across the air gap via conduction + radiation, then through the
 *   opposite side. The TEGs sit on the OUTER side of each heater,
 *   measuring the temperature drop from the heater to the insulated
 *   6mm base plate. TCs are mounted on the inner face of the 3mm
 *   plates, as close to the gap as possible.
 *
 *       +---------------------------------------------+
 *       |     Cork sheet (thermal insulation)          |  top (outermost)
 *       +---------------------------------------------+
 *       |     Aluminum plate (75 x 75 x 6 mm)         |  heat-sink / base
 *       +---------------------------------------------+
 *       |     TEG TOP (SP1848-27145)                   |  <-- ADS1115 ch0-ch1
 *       +---------------------------------------------+
 *       |     TOP PI HEATER                            |  <-- pin 6 via MOSFET
 *       +---------------------------------------------+
 *       |     Aluminum plate (75 x 75 x 3 mm)         |  TC_TOP on gap side
 *       |       TC_TOP mounted here -->                |  <-- MAX31855 CS=pin 10
 *       +---------------------------------------------+
 *       |     Stainless steel plate  (low e ~ 0.1-0.3)|  TOP gap surface
 *       |     ~~~~~~~~ 20 mil AIR GAP ~~~~~~~~~~~~     |  2x10mil kapton shims
 *       |     Glass slide / SiO2     (high e ~ 0.9)   |  BOTTOM gap surface
 *       +---------------------------------------------+
 *       |       TC_BOT mounted here -->                |  <-- MAX31855 CS=pin 9
 *       |     Aluminum plate (75 x 75 x 3 mm)         |  TC_BOT on gap side
 *       +---------------------------------------------+
 *       |     BOT PI HEATER                            |  <-- pin 7 via MOSFET
 *       +---------------------------------------------+
 *       |     TEG BOTTOM (SP1848-27145)                |  <-- ADS1115 ch2-ch3
 *       +---------------------------------------------+
 *       |     Aluminum plate (75 x 75 x 6 mm)         |  heat-sink / base
 *       +---------------------------------------------+
 *       |     Cork sheet (thermal insulation)          |  bottom (outermost)
 *       +---------------------------------------------+
 *
 *   Heat flow path (forward / A phase, top heater ON):
 *     Top heater -> 3mm Al plate -> steel -> AIR GAP -> glass -> 3mm Al plate
 *     (TEG TOP measures delta-T from heater to outer 6mm plate)
 *
 *   Heat flow path (reverse / B phase, bottom heater ON):
 *     Bot heater -> 3mm Al plate -> glass -> AIR GAP -> steel -> 3mm Al plate
 *     (TEG BOT measures delta-T from heater to outer 6mm plate)
 *
 *   TEG modules (SP1848-27145):
 *   - Peltier-type thermoelectric generators
 *   - Output voltage proportional to delta-T across their faces
 *   - ~1V at delta-T = 20 deg C, up to ~4.8V at delta-T = 100 deg C
 *   - Positioned between heater and outer 6mm plate on each side
 *   - Used as heat-flux PROXY (not absolute measurement)
 *
 *   ADS1115 (16-bit ADC, I2C address 0x48):
 *   - GAIN_ONE: +/- 4.096V range, 0.125 mV per count
 *   - Channel 0-1: Top TEG (differential)
 *   - Channel 2-3: Bottom TEG (differential)
 *   - NOTE: GAIN_ONE saturates at 4.096V. If TEG output exceeds this
 *     (delta-T > ~85 deg C), switch to GAIN_TWOTHIRDS (+/- 6.144V).
 *     In practice, observed TEG max is ~845 mV — well within range.
 *
 *   MAX31855 (thermocouple amplifiers, SPI):
 *   - CS_T_TOP = pin 10 (top 3mm plate thermocouple, gap side)
 *   - CS_T_BOT = pin 9  (bottom 3mm plate thermocouple, gap side)
 *   - Type-K thermocouples, mounted on inner face of 3mm plates
 *   - Measures temperature at the gap interface (not at the heater)
 *
 *   DHT11 (ambient temperature, digital on pin A1):
 *   - +/- 2 deg C accuracy (sufficient for drift tracking)
 *   - Determines when plates have cooled to room temperature
 *   - Logged every sample for drift correction in post-processing
 *
 * ============================================================================
 * PIN ASSIGNMENTS (Mega 2560)
 * ============================================================================
 *
 *   Pin 6  (digital)  --> TOP heater MOSFET gate
 *   Pin 7  (digital)  --> BOT heater MOSFET gate
 *   Pin 10 (digital)  --> MAX31855 CS for TOP thermocouple (SPI)
 *   Pin 9  (digital)  --> MAX31855 CS for BOT thermocouple (SPI)
 *   Pin 50 (MISO)     --> MAX31855 data out (SPI, shared)
 *   Pin 52 (SCK)      --> MAX31855 clock (SPI, shared)
 *   Pin 20 (SDA)      --> ADS1115 data (I2C)
 *   Pin 21 (SCL)      --> ADS1115 clock (I2C)
 *   Pin A0 (analog)   --> Heater voltage divider (optional)
 *   Pin A1 (digital)  --> DHT11 data
 *
 * ============================================================================
 * CSV OUTPUT FORMAT
 * ============================================================================
 *
 *   Lines starting with '#' are metadata, diagnostics, or phase events.
 *   All other lines are CSV data with these columns:
 *
 *   Column        | Unit  | Description
 *   --------------|-------|------------------------------------------
 *   time_ms       | ms    | Milliseconds since Arduino boot
 *   phase         | text  | Current ABBA phase name
 *   phase_time_ms | ms    | Milliseconds since current phase started
 *   sample_num    | count | Running sample counter (1, 2, 3...)
 *   Vtop_mV       | mV    | Top TEG voltage (ADS1115 ch0-ch1)
 *   Vbot_mV       | mV    | Bottom TEG voltage (ADS1115 ch2-ch3)
 *   Tt_C          | C     | Top plate thermocouple temperature
 *   Tb_C          | C     | Bottom plate thermocouple temperature
 *   dT_C          | C     | Temperature difference (Tt - Tb)
 *   Vheater_V     | V     | Heater supply voltage (-1 if disabled)
 *   Tamb_C        | C     | Ambient temperature from DHT11
 *
 * ============================================================================
 * EXPECTED TIMELINE (per ABBA cycle)
 * ============================================================================
 *
 *   Phase          | Duration (est.)
 *   ---------------|----------------
 *   WAIT_AMBIENT   | 0-5 min (if stack is cold)
 *   A1_FWD_HEAT    | 40 min
 *   A1_COOLDOWN    | ~50-60 min (from ~83 C to ambient)
 *   B1_REV_HEAT    | 40 min
 *   B1_COOLDOWN    | ~50-60 min
 *   B2_REV_HEAT    | 40 min
 *   B2_COOLDOWN    | ~50-60 min
 *   A2_FWD_HEAT    | 40 min
 *   A2_COOLDOWN    | ~50-60 min
 *   TOTAL          | ~6-7 hours
 *
 *   Ensure CoolTerm capture is running and laptop sleep is disabled!
 *
 * ============================================================================
 * POST-PROCESSING GUIDE
 * ============================================================================
 *
 *   1. Import CSV (skip '#' lines) into Python/Excel.
 *   2. Split data by 'phase' column.
 *   3. For each heating phase, identify steady state:
 *      - Compute dV/dt over rolling 30-second windows.
 *      - Steady state when |dV/dt| < 0.02 mV/s.
 *      - NOTE: This stack takes ~20 min to reach steady state
 *        (longer than the SiO2-SiO2 gap sweep runs).
 *   4. Average TEG voltages during steady-state plateau (last ~20 min).
 *   5. Compute rectification ratio:
 *        eta = mean(A1_ss, A2_ss) / mean(B1_ss, B2_ss)
 *   6. Statistical significance: paired t-test on A vs B values.
 *   7. Allan deviation: compute on steady-state segments to quantify
 *      noise floor vs drift.
 *
 *   Python example:
 *     import pandas as pd
 *     df = pd.read_csv('file.txt', comment='#')
 *     a1 = df[df.phase == 'A1_FWD_HEAT']
 *
 * ============================================================================
 * REVISION HISTORY
 * ============================================================================
 *   TEST 12: Basic forward/reverse with fixed timers
 *   TEST 13: Full ABBA + metadata + DHT11 + diagnostics (fixed cooldown)
 *   TEST 14: Adaptive cooldown — waits for ambient before advancing
 *   TEST 16: Module D rectification — Steel-SiO2 asymmetric stack,
 *            20 mil air gap, 40 min heating (this version)
 *
 * ============================================================================
 * LIBRARIES REQUIRED (install via Arduino IDE Library Manager)
 * ============================================================================
 *   - Adafruit ADS1X15        (for ADS1115 ADC)
 *   - Adafruit MAX31855       (for thermocouple amplifiers)
 *   - DHT sensor library       (by Adafruit, for DHT11)
 *   - Adafruit Unified Sensor  (dependency of DHT library)
 *
 * ============================================================================
 */

#include <Wire.h>
#include <SPI.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_MAX31855.h>
#include <DHT.h>

/* ============================================================================
 * USER CONFIG — CHANGE THESE BEFORE EACH RUN
 * ============================================================================
 * These values are printed in the CSV header so every data file is
 * self-documenting. Update them for each experimental condition.
 *
 * RUN_ID:        Unique identifier (e.g., "CAL_002", "GAP_3um_001")
 * GAP_DISTANCE:  Gap between surfaces ("contact", "508um", etc.)
 * MATERIAL_PAIR: Surfaces facing the gap ("Steel-SiO2", "SiO2-SiO2", etc.)
 * SPACER_TYPE:   What defines the gap ("kapton_shim_2x10mil", "none", etc.)
 * RUN_NUMBER:    Increment for repeat runs at the same condition
 * OPERATOR_NOTES: Free-text for anything noteworthy about this run
 */

//const char* RUN_ID          = "RECT_001";
//const char* GAP_DISTANCE    = "508um";                // 20 mil = 2x10mil kapton shims
//const char* MATERIAL_PAIR   = "Steel-SiO2";           // Steel on top, glass on bottom
//const char* SPACER_TYPE     = "kapton_shim_2x10mil";  // 2 stacked 10mil kapton shims at corners
//const int   RUN_NUMBER      = 1;
//const char* OPERATOR_NOTES  = "Module D rectification: steel top, glass bottom, 20mil air gap, 40min heat";
const char* RUN_ID          = "CTRL_001";
const char* GAP_DISTANCE    = "508um";
const char* MATERIAL_PAIR   = "SiO2-SiO2";
const char* SPACER_TYPE     = "kapton_shim_2x10mil";
const int   RUN_NUMBER      = 1;
const char* OPERATOR_NOTES  = "Control: symmetric glass-glass, 20mil air gap, same conditions as RECT_001";

/* ============================================================================
 * TIMING & ADAPTIVE COOLDOWN THRESHOLDS
 * ============================================================================
 *
 * HEAT_DURATION_MS (40 min):
 *   Fixed heating time per phase. From the test run on 19 Feb, this
 *   asymmetric steel-glass stack takes ~20 min to approach steady state
 *   (dV/dt oscillating near 0.05 mV/s at 21 min). 40 min provides
 *   ~20 min of steady-state plateau data for robust averaging.
 *
 * COOL_THRESHOLD_C (3.0 deg C):
 *   How close both plate TCs must be to the DHT11 ambient reading before
 *   the system considers the stack "cooled." The TEGs produce negligible
 *   voltage at this small gradient, ensuring a near-zero baseline.
 *
 * COOL_STABLE_MS (30 sec):
 *   After both TCs enter the threshold zone, they must STAY there for
 *   this duration continuously. Prevents noise spikes from triggering
 *   a premature phase advance. 30 seconds = ~30 samples at 1 Hz.
 *
 * COOL_MIN_MS (2 min):
 *   Minimum wait before checking cooldown. Prevents immediate advance
 *   if TCs happen to read near ambient before the thermal wave from
 *   the heater has propagated through the aluminum plates.
 *
 * COOL_MAX_MS (90 min):
 *   Safety timeout. If the stack hasn't cooled in 90 min, something
 *   is wrong. The system logs a warning and advances rather than
 *   hanging forever. Cooldown from ~83 deg C expected to take 50-70 min.
 *
 * SAMPLE_INTERVAL_MS (1000 ms = 1 Hz):
 *   Data sampling rate. Matches the research plan. Thermal processes
 *   evolve over minutes, so 1 Hz captures all relevant dynamics.
 */

const unsigned long HEAT_DURATION_MS   = 2400000UL;  // 40 minutes
const unsigned long COOL_MIN_MS        = 120000UL;   // 2 min minimum cooldown
const unsigned long COOL_MAX_MS        = 5400000UL;  // 90 min safety timeout
const float         COOL_THRESHOLD_C   = 3.0;        // deg C above ambient
const unsigned long COOL_STABLE_MS     = 30000;       // 30 sec stability window
const unsigned long SAMPLE_INTERVAL_MS = 1000;        // 1 Hz

/* ============================================================================
 * PIN CONFIGURATION
 * ============================================================================
 * ACTIVE_HIGH = true means: Arduino pin HIGH -> MOSFET ON -> heater ON.
 * This matches standard N-channel MOSFET modules (IRLZ44N, IRF520)
 * where HIGH on the gate turns on the low-side switch.
 *
 * Each MOSFET module has:
 *   - Signal input: connected to Arduino digital pin (via gate resistor)
 *   - 10k pull-down: on the gate to prevent floating during boot
 *   - Screw terminals: one to heater, other to 12V supply GND
 *   - 12V supply (+) connects directly to heater (not through MOSFET)
 */

const int TOP_CTRL = 6;        // Digital pin -> top MOSFET gate
const int BOT_CTRL = 7;        // Digital pin -> bottom MOSFET gate
const bool ACTIVE_HIGH = true;  // HIGH = heater ON

#define CS_T_TOP 10  // SPI chip select: top plate MAX31855
#define CS_T_BOT 9   // SPI chip select: bottom plate MAX31855

#define DHT_PIN  A1       // DHT11 data pin (module has built-in pull-up)
#define DHT_TYPE DHT11

DHT dht(DHT_PIN, DHT_TYPE);

/*
 * Heater voltage monitoring (OPTIONAL)
 *
 * A resistive divider (10k + 2.2k) scales the 12V heater rail to ~1.8V
 * for the Arduino's 0-5V analog input. Lets you verify the PSU stays
 * stable during the run.
 *
 * If not wired, set USE_HEATER_V = false. The Vheater column outputs -1.
 *
 * Divider math:
 *   Vread = Vheater * R2/(R1+R2) = Vheater * 2.2k/12.2k = 0.1803
 *   Vheater = Vread / 0.1803
 */

const bool  USE_HEATER_V    = false;
const int   HEATER_V_PIN    = A0;
const float V_DIVIDER_RATIO = 0.1803f;

/* ============================================================================
 * SENSOR OBJECTS
 * ============================================================================ */

Adafruit_ADS1115 ads;               // 16-bit ADC, I2C address 0x48
Adafruit_MAX31855 tcTop(CS_T_TOP);  // Top plate thermocouple amplifier
Adafruit_MAX31855 tcBot(CS_T_BOT);  // Bottom plate thermocouple amplifier

/*
 * ADS1115 gain setting determines voltage range and resolution:
 *
 *   GAIN_SIXTEEN: +/- 256 mV  (0.0078 mV/count) — too small for TEGs
 *   GAIN_EIGHT:   +/- 512 mV  (0.0156 mV/count) — saturated in TEST 12
 *   GAIN_ONE:     +/- 4096 mV (0.1250 mV/count) — covers full TEG range
 *
 * SP1848-27145 TEG output at various delta-T:
 *   20 deg C  -> ~1.0 V
 *   40 deg C  -> ~1.8 V
 *   100 deg C -> ~4.8 V  (would saturate GAIN_ONE at 4.096V)
 *
 * GAIN_ONE covers all practical conditions in this experiment.
 * Observed max TEG output: ~845 mV — well within 4096 mV limit.
 * If higher delta-T is needed, switch to GAIN_TWOTHIRDS (+/- 6.144V).
 */
const float mV_per_count = 0.125f;  // GAIN_ONE: 0.125 mV per ADC count

/* ============================================================================
 * HEATER CONTROL FUNCTIONS
 * ============================================================================
 * Translate logical ON/OFF to correct pin state based on ACTIVE_HIGH.
 * The XOR logic handles both active-high and active-low MOSFET drivers:
 *   ACTIVE_HIGH + on=true  -> pin HIGH (heater on)
 *   ACTIVE_HIGH + on=false -> pin LOW  (heater off)
 */

void setTop(bool on) { digitalWrite(TOP_CTRL, (on ^ !ACTIVE_HIGH) ? HIGH : LOW); }
void setBot(bool on) { digitalWrite(BOT_CTRL, (on ^ !ACTIVE_HIGH) ? HIGH : LOW); }

/* ============================================================================
 * ABBA STATE MACHINE
 * ============================================================================
 * The experiment progresses through these phases sequentially:
 *
 *   WAIT_AMBIENT  -> ensures stack starts at room temperature
 *   A1_FWD_HEAT   -> top heater ON for 40 min (forward: heat steel side)
 *   A1_COOLDOWN   -> heaters OFF, wait for plates to reach ambient
 *   B1_REV_HEAT   -> bottom heater ON for 40 min (reverse: heat glass side)
 *   B1_COOLDOWN   -> heaters OFF, wait for plates to reach ambient
 *   B2_REV_HEAT   -> bottom heater ON for 40 min (reverse repeat)
 *   B2_COOLDOWN   -> heaters OFF, wait for plates to reach ambient
 *   A2_FWD_HEAT   -> top heater ON for 40 min (forward repeat)
 *   A2_COOLDOWN   -> final cooldown
 *   COMPLETE       -> done, LED blinks
 *
 * Heating phases: fixed duration (HEAT_DURATION_MS = 40 min)
 * Cooling phases: adaptive (wait for ambient temperature)
 */

enum ABBAPhase {
  PHASE_WAIT_AMBIENT,  // Pre-start: wait for room temperature
  PHASE_A1_HEAT,       // Forward heating #1 (top heater -> steel side)
  PHASE_A1_COOL,       // Cooldown to ambient
  PHASE_B1_HEAT,       // Reverse heating #1 (bottom heater -> glass side)
  PHASE_B1_COOL,       // Cooldown to ambient
  PHASE_B2_HEAT,       // Reverse heating #2 (bottom heater -> glass side)
  PHASE_B2_COOL,       // Cooldown to ambient
  PHASE_A2_HEAT,       // Forward heating #2 (top heater -> steel side)
  PHASE_A2_COOL,       // Final cooldown
  PHASE_COMPLETE       // Experiment finished
};

// Human-readable names for CSV phase column and serial log
const char* phaseNames[] = {
  "WAIT_AMBIENT",
  "A1_FWD_HEAT", "A1_COOLDOWN",
  "B1_REV_HEAT", "B1_COOLDOWN",
  "B2_REV_HEAT", "B2_COOLDOWN",
  "A2_FWD_HEAT", "A2_COOLDOWN",
  "COMPLETE"
};

/* ============================================================================
 * STATE VARIABLES
 * ============================================================================ */

ABBAPhase currentPhase       = PHASE_WAIT_AMBIENT;
unsigned long phaseStartTime = 0;       // When current phase began
unsigned long lastSampleTime = 0;       // When last data sample was taken
unsigned long sampleCount    = 0;       // Total samples across all phases
unsigned long readFailCount  = 0;       // ADC saturation counter

/*
 * Adaptive cooldown tracking:
 *
 * coolStableStart:    When both TCs first entered threshold zone
 * coolStableTracking: True while counting toward COOL_STABLE_MS
 *
 * Sequence:
 *   1. Both TCs enter threshold -> start timer
 *   2. Still within threshold after COOL_STABLE_MS? -> advance
 *   3. Either TC exits threshold? -> reset timer, keep waiting
 */
unsigned long coolStableStart    = 0;
bool          coolStableTracking = false;

/* ============================================================================
 * HELPER FUNCTIONS
 * ============================================================================ */

/*
 * readHeaterVoltage()
 * Reads 12V heater supply through voltage divider on A0.
 * Returns reconstructed voltage, or -1.0 if divider not wired.
 */
float readHeaterVoltage() {
  if (!USE_HEATER_V) return -1.0f;
  int raw = analogRead(HEATER_V_PIN);
  return (raw * 5.0f / 1023.0f) / V_DIVIDER_RATIO;
}

/*
 * readAmbientTemp()
 * Reads room temperature from DHT11.
 * Returns -999.0 on failure (sensor timing error or disconnected).
 */
float readAmbientTemp() {
  float t = dht.readTemperature();
  if (isnan(t)) return -999.0f;
  return t;
}

/* Phase category helpers for transition logic */
bool isHeatingPhase() {
  return (currentPhase == PHASE_A1_HEAT || currentPhase == PHASE_B1_HEAT ||
          currentPhase == PHASE_B2_HEAT || currentPhase == PHASE_A2_HEAT);
}

bool isCoolingPhase() {
  return (currentPhase == PHASE_A1_COOL || currentPhase == PHASE_B1_COOL ||
          currentPhase == PHASE_B2_COOL || currentPhase == PHASE_A2_COOL ||
          currentPhase == PHASE_WAIT_AMBIENT);
}

/*
 * applyHeaterState()
 * Sets correct heater ON/OFF for current phase.
 * Called at each phase transition.
 *
 * Forward (A): top heater ON  -> heat through steel, across gap to glass
 * Reverse (B): bot heater ON  -> heat through glass, across gap to steel
 */
void applyHeaterState() {
  switch (currentPhase) {
    case PHASE_A1_HEAT: case PHASE_A2_HEAT:
      setTop(true);  setBot(false);   // Forward: heat from top (steel side)
      break;
    case PHASE_B1_HEAT: case PHASE_B2_HEAT:
      setTop(false); setBot(true);    // Reverse: heat from bottom (glass side)
      break;
    default:
      setTop(false); setBot(false);   // Cooling / waiting / complete
      break;
  }
}

/*
 * advancePhase()
 * Moves to next phase, resets timers, logs transition, sets heaters.
 */
void advancePhase() {
  if (currentPhase < PHASE_COMPLETE) {
    currentPhase = (ABBAPhase)((int)currentPhase + 1);
    phaseStartTime = millis();
    coolStableTracking = false;
    coolStableStart = 0;

    Serial.print("# PHASE_CHANGE: ");
    Serial.print(phaseNames[currentPhase]);
    Serial.print(" at t="); Serial.print(millis());
    Serial.println(" ms");

    applyHeaterState();
  }
}

/*
 * platesAtAmbient()
 *
 * Core adaptive cooldown logic.
 * Returns true only if BOTH TCs are within COOL_THRESHOLD_C of ambient.
 *
 * Why both? If only one plate cooled, the stack has an asymmetric
 * temperature profile. Starting the next heating phase from this state
 * would bias the rectification ratio measurement.
 *
 * Returns false on any invalid reading to prevent advancing on bad data.
 */
bool platesAtAmbient(double tt, double tb, float tamb) {
  if (isnan(tt) || isnan(tb) || tamb < -900) return false;

  bool topCool = (tt - tamb) < COOL_THRESHOLD_C;
  bool botCool = (tb - tamb) < COOL_THRESHOLD_C;

  return topCool && botCool;
}

/* ============================================================================
 * STARTUP DIAGNOSTICS
 * ============================================================================
 * Run once at boot to verify hardware before a multi-hour experiment.
 */

/*
 * i2cScan()
 * Scans all 127 I2C addresses. ADS1115 should appear at 0x48.
 */
void i2cScan() {
  Serial.println("# I2C_SCAN_START");
  int found = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("#   FOUND 0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
      found++;
    }
  }
  Serial.print("#   Devices: "); Serial.println(found);
  Serial.println("# I2C_SCAN_END");
}

/*
 * checkHeaterMOSFETs()
 * Verifies MOSFET gate signal path:
 *   - OFF state = LOW (for ACTIVE_HIGH)
 *   - ON state = HIGH
 *   - Returns to OFF (not stuck)
 *   - No cross-talk between channels
 *
 * NOTE: Tests signal path only, NOT 12V power delivery.
 * A channel that passes here but doesn't heat = power wiring issue.
 */
void checkHeaterMOSFETs() {
  Serial.println("# MOSFET_TEST_START");
  setTop(false); setBot(false); delay(50);
  bool topOff = digitalRead(TOP_CTRL);
  bool botOff = digitalRead(BOT_CTRL);
  Serial.print("#   TOP_OFF="); Serial.print(topOff ? "HIGH" : "LOW");
  Serial.print("  BOT_OFF="); Serial.println(botOff ? "HIGH" : "LOW");

  setTop(true); delay(10);
  Serial.print("#   TOP_ON="); Serial.print(digitalRead(TOP_CTRL) ? "HIGH" : "LOW");
  Serial.println(digitalRead(TOP_CTRL) == HIGH ? " (CORRECT)" : " *** CHECK ***");
  delay(200); setTop(false); delay(50);
  Serial.print("#   TOP_RESTORED="); Serial.println(digitalRead(TOP_CTRL) == topOff ? "OK" : "STUCK!");

  setBot(true); delay(10);
  Serial.print("#   BOT_ON="); Serial.print(digitalRead(BOT_CTRL) ? "HIGH" : "LOW");
  Serial.println(digitalRead(BOT_CTRL) == HIGH ? " (CORRECT)" : " *** CHECK ***");
  delay(200); setBot(false); delay(50);
  Serial.print("#   BOT_RESTORED="); Serial.println(digitalRead(BOT_CTRL) == botOff ? "OK" : "STUCK!");

  setTop(true); delay(50);
  Serial.print("#   XTALK TOP->BOT: "); Serial.println(digitalRead(BOT_CTRL) == botOff ? "OK" : "FAIL!");
  setTop(false); delay(50);

  setBot(true); delay(50);
  Serial.print("#   XTALK BOT->TOP: "); Serial.println(digitalRead(TOP_CTRL) == topOff ? "OK" : "FAIL!");
  setBot(false);
  Serial.println("# MOSFET_TEST_END");
}

/* ============================================================================
 * SETUP — Runs once at power-on or reset
 * ============================================================================
 * Sequence:
 *   1. Open serial port and print metadata header
 *   2. Configure heater pins and run MOSFET diagnostics
 *   3. Initialize SPI (thermocouples) and I2C (ADC)
 *   4. Initialize DHT11 ambient sensor
 *   5. Run 3 verification samples from all sensors
 *   6. Print CSV column header
 *   7. Enter WAIT_AMBIENT phase (heaters off, wait for room temp)
 */
void setup() {
  Serial.begin(9600);
  while (!Serial);
  delay(2000);

  // ---- Self-documenting metadata header ----
  Serial.println("# ============================================");
  Serial.println("# MICRO-GAP THERMAL RECTIFIER - ABBA PROTOCOL");
  Serial.println("# MODULE D: Steel-SiO2 Rectification (TEST 16)");
  Serial.println("# ============================================");
  Serial.print("# RUN_ID: ");            Serial.println(RUN_ID);
  Serial.print("# GAP_DISTANCE: ");      Serial.println(GAP_DISTANCE);
  Serial.print("# MATERIAL_PAIR: ");     Serial.println(MATERIAL_PAIR);
  Serial.print("# SPACER_TYPE: ");       Serial.println(SPACER_TYPE);
  Serial.print("# RUN_NUMBER: ");        Serial.println(RUN_NUMBER);
  Serial.print("# NOTES: ");             Serial.println(OPERATOR_NOTES);
  Serial.print("# HEAT_DURATION_MS: ");  Serial.println(HEAT_DURATION_MS);
  Serial.println("# COOL_MODE: ADAPTIVE (wait for plates to reach ambient)");
  Serial.print("# COOL_THRESHOLD_C: ");  Serial.println(COOL_THRESHOLD_C, 1);
  Serial.print("# COOL_STABLE_MS: ");    Serial.println(COOL_STABLE_MS);
  Serial.print("# COOL_MIN_MS: ");       Serial.println(COOL_MIN_MS);
  Serial.print("# COOL_MAX_MS: ");       Serial.println(COOL_MAX_MS);
  Serial.print("# SAMPLE_RATE_MS: ");    Serial.println(SAMPLE_INTERVAL_MS);
  Serial.print("# ADS_GAIN: GAIN_ONE (+-4096mV, ");
  Serial.print(mV_per_count, 4); Serial.println(" mV/count)");
  Serial.println("# ABBA: WAIT -> A1(steel) -> COOL -> B1(glass) -> COOL -> B2(glass) -> COOL -> A2(steel) -> COOL");
  Serial.println("#");

  // ---- Configure heater control pins ----
  pinMode(TOP_CTRL, OUTPUT);
  pinMode(BOT_CTRL, OUTPUT);
  setTop(false); setBot(false);
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.println("# [OK] Heater pins configured, both OFF");

  // ---- MOSFET diagnostics ----
  checkHeaterMOSFETs();

  // ---- SPI chip selects HIGH before I2C init ----
  pinMode(CS_T_TOP, OUTPUT); digitalWrite(CS_T_TOP, HIGH);
  pinMode(CS_T_BOT, OUTPUT); digitalWrite(CS_T_BOT, HIGH);
  Serial.println("# [OK] SPI CS pins HIGH");

  // ---- I2C bus ----
  Wire.begin();
  Wire.setClock(100000);
  Serial.println("# [OK] Wire.begin() at 100kHz");
  delay(100);

  i2cScan();

  // ---- ADS1115 init with retries ----
  bool adsOk = false;
  for (int attempt = 1; attempt <= 5; attempt++) {
    Serial.print("# ADS1115 init attempt "); Serial.print(attempt); Serial.print("/5: ");
    Wire.begin(); delay(100);
    if (ads.begin(0x48)) {
      Serial.println("SUCCESS");
      adsOk = true;
      break;
    }
    Serial.println("FAIL");
    delay(500);
  }
  if (!adsOk) {
    Serial.println("# FATAL: ADS1115 not found — halting");
    Serial.println("# Check: SDA=pin20, SCL=pin21, VDD, GND, ADDR=GND");
    while (1) { digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); delay(250); }
  }
  ads.setGain(GAIN_ONE);
  Serial.println("# [OK] ADS1115 GAIN_ONE configured");

  // ---- DHT11 init ----
  dht.begin();
  delay(2000);
  float testAmb = dht.readTemperature();
  if (isnan(testAmb)) {
    Serial.println("# WARNING: DHT11 read failed — check wiring");
  } else {
    Serial.print("# [OK] DHT11 ambient: "); Serial.print(testAmb, 1); Serial.println(" C");
  }

  // ---- Verify all sensors ----
  Serial.println("# SENSOR_VERIFY_START");
  for (int i = 0; i < 3; i++) {
    int16_t r01 = ads.readADC_Differential_0_1();
    int16_t r23 = ads.readADC_Differential_2_3();
    double Tt = tcTop.readCelsius();
    double Tb = tcBot.readCelsius();
    float Tamb = readAmbientTemp();
    Serial.print("#   Sample "); Serial.print(i + 1);
    Serial.print(": V01="); Serial.print(r01 * mV_per_count, 2);
    Serial.print("mV V23="); Serial.print(r23 * mV_per_count, 2);
    Serial.print("mV Tt="); Serial.print(Tt, 1);
    Serial.print("C Tb="); Serial.print(Tb, 1);
    Serial.print("C Tamb="); Serial.print(Tamb, 1);
    Serial.println("C");
    delay(500);
  }
  Serial.println("# SENSOR_VERIFY_END");

  // ---- TC fault check ----
  double Tt = tcTop.readCelsius();
  double Tb = tcBot.readCelsius();
  if (isnan(Tt)) { Serial.println("# WARNING: TC_TOP fault"); }
  else { Serial.print("# [OK] TC_TOP: "); Serial.print(Tt, 1); Serial.println(" C"); }
  if (isnan(Tb)) { Serial.println("# WARNING: TC_BOT fault"); }
  else { Serial.print("# [OK] TC_BOT: "); Serial.print(Tb, 1); Serial.println(" C"); }

  // ---- Ready ----
  Serial.println("#");
  Serial.println("# ============================================");
  Serial.println("# DIAGNOSTICS COMPLETE");
  Serial.println("# Waiting for plates to reach ambient...");
  Serial.println("# (Both TCs must be within 3 C of DHT11 for 30 sec)");
  Serial.println("# ============================================");
  Serial.println("time_ms,phase,phase_time_ms,sample_num,Vtop_mV,Vbot_mV,Tt_C,Tb_C,dT_C,Vheater_V,Tamb_C");

  phaseStartTime = millis();
  applyHeaterState();
}

/* ============================================================================
 * MAIN LOOP — Runs continuously after setup()
 * ============================================================================
 *
 * Each loop iteration does two things:
 *
 *   1. SAMPLE (at SAMPLE_INTERVAL_MS = 1 Hz):
 *      Read all sensors, output one CSV data line.
 *
 *   2. CHECK PHASE TRANSITIONS:
 *      - Heating phases: advance after HEAT_DURATION_MS (40 min)
 *      - Cooling phases: advance when plates reach ambient (adaptive)
 *      - Complete: stop, blink LED
 *
 * The static variables lastTt, lastTb, lastTamb persist between
 * iterations so the phase logic can use the most recent readings.
 */
void loop() {
  unsigned long now = millis();

  // ------------------------------------------------------------------
  // SECTION 1: SENSOR SAMPLING
  // ------------------------------------------------------------------
  static double lastTt = 0, lastTb = 0;
  static float lastTamb = 0;

  if (now - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = now;
    sampleCount++;

    // Read TEG voltages (differential, 16-bit)
    int16_t raw01 = ads.readADC_Differential_0_1();
    int16_t raw23 = ads.readADC_Differential_2_3();

    // Saturation check
    if (raw01 == 32767 || raw01 == -32768 || raw23 == 32767 || raw23 == -32768) {
      readFailCount++;
      if (readFailCount <= 10 || readFailCount % 100 == 0) {
        Serial.print("# WARN: ADS saturated #"); Serial.print(readFailCount);
        Serial.print(" raw01="); Serial.print(raw01);
        Serial.print(" raw23="); Serial.println(raw23);
      }
    }

    float vTop = raw01 * mV_per_count;
    float vBot = raw23 * mV_per_count;

    // Read thermocouples and ambient
    lastTt = tcTop.readCelsius();
    lastTb = tcBot.readCelsius();
    double dT = lastTt - lastTb;
    float Vheat = readHeaterVoltage();
    lastTamb = readAmbientTemp();

    // CSV output
    Serial.print(now);                        Serial.print(",");
    Serial.print(phaseNames[currentPhase]);   Serial.print(",");
    Serial.print(now - phaseStartTime);       Serial.print(",");
    Serial.print(sampleCount);                Serial.print(",");
    Serial.print(vTop, 4);                    Serial.print(",");
    Serial.print(vBot, 4);                    Serial.print(",");
    Serial.print(lastTt, 2);                  Serial.print(",");
    Serial.print(lastTb, 2);                  Serial.print(",");
    Serial.print(dT, 2);                      Serial.print(",");
    Serial.print(Vheat, 2);                   Serial.print(",");
    Serial.println(lastTamb, 1);
  }

  // ------------------------------------------------------------------
  // SECTION 2: PHASE TRANSITION LOGIC
  // ------------------------------------------------------------------

  // ---- COMPLETE: experiment finished ----
  if (currentPhase == PHASE_COMPLETE) {
    static bool completePrinted = false;
    if (!completePrinted) {
      setTop(false); setBot(false);
      Serial.println("# ============================================");
      Serial.println("# ABBA PROTOCOL COMPLETE");
      Serial.print("# Total samples: ");     Serial.println(sampleCount);
      Serial.print("# ADS read failures: "); Serial.println(readFailCount);
      Serial.print("# Total duration: ");    Serial.print(millis() / 60000.0, 1); Serial.println(" min");
      Serial.println("# ============================================");
      completePrinted = true;
    }
    digitalWrite(LED_BUILTIN, (millis() / 1000) % 2);
    return;
  }

  unsigned long phaseElapsed = now - phaseStartTime;

  // ---- HEATING PHASES: fixed duration (40 min) ----
  if (isHeatingPhase()) {
    if (phaseElapsed >= HEAT_DURATION_MS) {
      Serial.print("# HEAT_COMPLETE: "); Serial.print(phaseNames[currentPhase]);
      Serial.print(" Tt="); Serial.print(lastTt, 1);
      Serial.print("C Tb="); Serial.print(lastTb, 1);
      Serial.println("C");
      advancePhase();
    }
  }

  // ---- COOLING PHASES: adaptive temperature-based ----
  // See flowchart in header documentation for complete logic.
  if (isCoolingPhase()) {

    // STEP 1: Enforce minimum cooldown
    if (phaseElapsed >= COOL_MIN_MS) {

      // STEP 2: Check if plates are near ambient
      bool atAmbient = platesAtAmbient(lastTt, lastTb, lastTamb);

      if (atAmbient) {
        // STEP 3: Start or continue stability timer
        if (!coolStableTracking) {
          coolStableTracking = true;
          coolStableStart = now;
          Serial.print("# COOL_THRESHOLD_REACHED: Tt="); Serial.print(lastTt, 1);
          Serial.print("C Tb="); Serial.print(lastTb, 1);
          Serial.print("C Tamb="); Serial.print(lastTamb, 1);
          Serial.println("C -- waiting for stability...");
        }

        // STEP 4: Stable long enough? Advance!
        if (now - coolStableStart >= COOL_STABLE_MS) {
          Serial.print("# COOL_STABLE: plates at ambient for ");
          Serial.print(COOL_STABLE_MS / 1000);
          Serial.print("s. Tt="); Serial.print(lastTt, 1);
          Serial.print("C Tb="); Serial.print(lastTb, 1);
          Serial.print("C Tamb="); Serial.print(lastTamb, 1);
          Serial.print("C. Cooldown took ");
          Serial.print(phaseElapsed / 60000.0, 1);
          Serial.println(" min");
          advancePhase();
        }
      } else {
        // Temperature exceeded threshold — reset stability timer
        if (coolStableTracking) {
          Serial.print("# COOL_UNSTABLE: temp exceeded threshold, resetting. Tt=");
          Serial.print(lastTt, 1); Serial.print("C Tb="); Serial.print(lastTb, 1);
          Serial.println("C");
        }
        coolStableTracking = false;
      }
    }

    // STEP 5: Safety timeout
    if (phaseElapsed >= COOL_MAX_MS) {
      Serial.print("# COOL_TIMEOUT: max "); Serial.print(COOL_MAX_MS / 60000);
      Serial.print(" min reached. Tt="); Serial.print(lastTt, 1);
      Serial.print("C Tb="); Serial.print(lastTb, 1);
      Serial.print("C Tamb="); Serial.print(lastTamb, 1);
      Serial.println("C. Advancing anyway.");
      advancePhase();
    }

    // STEP 6: Progress report every 5 minutes
    static unsigned long lastCoolReport = 0;
    if (phaseElapsed > 0 && (phaseElapsed / 300000) > (lastCoolReport / 300000)) {
      lastCoolReport = phaseElapsed;
      Serial.print("# COOL_STATUS: "); Serial.print(phaseElapsed / 60000.0, 1);
      Serial.print(" min, Tt="); Serial.print(lastTt, 1);
      Serial.print("C Tb="); Serial.print(lastTb, 1);
      Serial.print("C Tamb="); Serial.print(lastTamb, 1);
      Serial.print("C gap_top="); Serial.print(lastTt - lastTamb, 1);
      Serial.print("C gap_bot="); Serial.print(lastTb - lastTamb, 1);
      Serial.print("C threshold="); Serial.print(COOL_THRESHOLD_C, 1);
      Serial.println("C");
    }
  }
}
