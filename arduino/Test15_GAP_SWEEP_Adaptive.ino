/*
 * ============================================================================
 * GAP SWEEP — Modules B & C
 * Adaptive Heating + Adaptive Cooldown, 3 Runs Per Gap
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
 * Measures total heat transfer (Vtop + Vbot) at different gap distances
 * to detect near-field radiative enhancement. Runs 3 consecutive
 * heat-cool cycles per gap for statistical error bars.
 *
 * Only forward heating (top heater) is used — no ABBA needed because
 * both sides are the same material (glass-glass). ABBA is only needed
 * for Module D (asymmetric materials) where direction matters.
 *
 * ============================================================================
 * ADAPTIVE HEATING — HOW STEADY STATE IS DETECTED
 * ============================================================================
 *
 *   Instead of heating for a fixed time, we monitor the TEG voltage
 *   rate-of-change (dV/dt) and detect when the system reaches thermal
 *   equilibrium (steady state).
 *
 *   Algorithm:
 *     1. Heat for at least HEAT_MIN_MS (5 min) before checking.
 *        This gives the thermal wave time to propagate through the stack.
 *
 *     2. Every second, compute a rolling average of |dV/dt| over the
 *        last SS_WINDOW_S samples (30 sec). This smooths out noise.
 *
 *     3. When |dV/dt| < SS_THRESHOLD_MV_S (0.05 mV/s) for
 *        SS_HOLD_MS (60 sec), the system is at steady state.
 *
 *     4. Once steady state is confirmed, collect PLATEAU_MS (180 sec
 *        = 3 min) of plateau data for averaging.
 *
 *     5. Safety timeout: HEAT_MAX_MS (25 min). If steady state is not
 *        reached, advance anyway with a warning.
 *
 *   Heating decision flowchart:
 *
 *       [Heater ON]
 *            |
 *            v
 *       elapsed < HEAT_MIN_MS (5 min)? ---YES---> keep heating
 *            |
 *            NO
 *            |
 *            v
 *       |dV/dt| < SS_THRESHOLD? ---NO---> keep heating
 *            |                              |
 *            YES                            v
 *            |                     elapsed > HEAT_MAX_MS?
 *            v                              |
 *       Hold for SS_HOLD_MS           YES: start plateau + warn
 *            |
 *            v
 *       Still below threshold? ---NO---> reset, keep heating
 *            |
 *            YES
 *            |
 *            v
 *       [STEADY STATE CONFIRMED]
 *            |
 *            v
 *       Collect PLATEAU_MS (3 min) of plateau data
 *            |
 *            v
 *       [Heater OFF, begin cooldown]
 *
 * ============================================================================
 * ADAPTIVE COOLDOWN — same as TEST 14
 * ============================================================================
 *
 *   Both TCs must be within COOL_THRESHOLD_C (3 deg C) of ambient
 *   for COOL_STABLE_MS (30 sec) continuously.
 *
 *   *** REMOVE CORK SHEETS DURING COOLDOWN TO SPEED UP ***
 *   *** PUT CORK BACK ON BEFORE NEXT HEATING PHASE     ***
 *
 *   Without cork removal: ~70 min cooldown
 *   With cork removal + fan: ~15-20 min cooldown
 *
 * ============================================================================
 * USER CONFIG — CHANGE BEFORE EACH GAP
 * ============================================================================ */

const char* RUN_ID          = "GAP_SWEEP_006";
const char* GAP_DISTANCE    = "508um";       // UPDATE for each gap!
const char* MATERIAL_PAIR   = "SiO2-SiO2";
const char* SPACER_TYPE     = "2 x 10 mil shim";    // UPDATE for each gap!
const int   RUNS_PER_GAP    = 5;              // 5 runs for statistics

/* ============================================================================
 * ADAPTIVE HEATING THRESHOLDS
 * ============================================================================
 *
 * HEAT_MIN_MS (5 min):
 *   Minimum heating before checking for steady state. Gives the
 *   thermal wave time to propagate from heater through the stack.
 *   From TEST 14 data, TEG voltages are still climbing steeply
 *   at 5 min, so this prevents premature triggering.
 *
 * HEAT_MAX_MS (25 min):
 *   Safety timeout. From TEST 14, steady state was always reached
 *   by 10-12 min. 25 min is generous — if not reached, something
 *   is wrong (but we still collect whatever data we have).
 *
 * SS_THRESHOLD_MV_S (0.05 mV/s):
 *   Rate-of-change threshold for steady state. When the top TEG
 *   voltage changes by less than 0.05 mV/s over the rolling window,
 *   the system is essentially flat. From TEST 14 data:
 *     - At 5 min: dV/dt ~ 2.0 mV/s (still rising fast)
 *     - At 8 min: dV/dt ~ 0.5 mV/s (slowing)
 *     - At 10 min: dV/dt ~ 0.1 mV/s (nearly flat)
 *     - At 12 min: dV/dt ~ 0.03 mV/s (steady state)
 *
 * SS_WINDOW_S (30 sec):
 *   Rolling window for dV/dt calculation. 30 samples at 1 Hz gives
 *   a smooth derivative that isn't triggered by single-sample noise.
 *
 * SS_HOLD_MS (60 sec):
 *   After dV/dt first drops below threshold, it must stay there
 *   for 60 sec continuously. Prevents false triggers from
 *   momentary flat spots during the rise.
 *
 * PLATEAU_MS (180 sec = 3 min):
 *   After steady state is confirmed, collect this much extra data.
 *   These 3 minutes of plateau data are what gets averaged in
 *   post-processing to produce the final voltage for this run.
 */

const unsigned long HEAT_MIN_MS       = 300000UL;   // 5 min
const unsigned long HEAT_MAX_MS       = 1500000UL;  // 25 min
const float         SS_THRESHOLD_MV_S = 0.05f;      // mV per second
const int           SS_WINDOW_S       = 30;          // rolling window
const unsigned long SS_HOLD_MS        = 60000;       // 60 sec hold
const unsigned long PLATEAU_MS        = 180000;      // 3 min plateau

/* ============================================================================
 * ADAPTIVE COOLDOWN THRESHOLDS (same as TEST 14)
 * ============================================================================ */

const unsigned long CORK_WAIT_MS        = 30000UL;    // 30 sec to put cork back
const unsigned long COOL_MIN_MS        = 120000UL;   // 2 min minimum
const unsigned long COOL_MAX_MS        = 5400000UL;  // 90 min timeout
const float         COOL_THRESHOLD_C   = 3.0;
const unsigned long COOL_STABLE_MS     = 30000;
const unsigned long SAMPLE_INTERVAL_MS = 1000;

/* ============================================================================
 * PIN CONFIGURATION (same as TEST 14)
 * ============================================================================ */

const int TOP_CTRL = 6;
const int BOT_CTRL = 7;
const bool ACTIVE_HIGH = true;

#define CS_T_TOP 10
#define CS_T_BOT 9
#define DHT_PIN  A1
#define DHT_TYPE DHT11

/* ============================================================================
 * LIBRARIES & SENSOR OBJECTS
 * ============================================================================ */

#include <Wire.h>
#include <SPI.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_MAX31855.h>
#include <DHT.h>

DHT dht(DHT_PIN, DHT_TYPE);
Adafruit_ADS1115 ads;
Adafruit_MAX31855 tcTop(CS_T_TOP);
Adafruit_MAX31855 tcBot(CS_T_BOT);
const float mV_per_count = 0.125f;

/* ============================================================================
 * STATE MACHINE
 * ============================================================================
 *
 * For each of the 3 runs:
 *   WAIT_AMBIENT → HEATING → PLATEAU → COOLDOWN
 *
 * HEATING:  heater on, monitoring dV/dt for steady state
 * PLATEAU:  heater still on, collecting stable data for averaging
 * COOLDOWN: heater off, waiting for plates to return to ambient
 */

enum Phase {
  PHASE_WAIT_AMBIENT,   // Wait for room temperature (cork OFF)
  PHASE_WAIT_FOR_CORK,  // 30 sec pause: LED blinks fast, put cork back on!
  PHASE_HEATING,        // Heater on, watching for steady state
  PHASE_PLATEAU,        // Steady state reached, collecting data
  PHASE_COOLDOWN,       // Heater off, cooling to ambient (remove cork!)
  PHASE_COMPLETE        // All runs done
};

const char* phaseNames[] = {
  "WAIT_AMBIENT", "WAIT_CORK", "HEATING", "PLATEAU", "COOLDOWN", "COMPLETE"
};

/* ============================================================================
 * STATE VARIABLES
 * ============================================================================ */

Phase currentPhase       = PHASE_WAIT_AMBIENT;
int   currentRun         = 1;          // Which run (1, 2, or 3)
unsigned long phaseStartTime = 0;
unsigned long lastSampleTime = 0;
unsigned long sampleCount    = 0;
unsigned long readFailCount  = 0;

// Adaptive cooldown tracking
unsigned long coolStableStart    = 0;
bool          coolStableTracking = false;

// Adaptive heating tracking
float vtopHistory[60];     // Circular buffer for dV/dt (up to 60 sec)
int   historyIndex = 0;
int   historyCount = 0;
bool  ssDetected   = false;          // Steady state detected flag
unsigned long ssDetectedTime = 0;    // When dV/dt first dropped below threshold
bool  ssConfirmed  = false;          // Held below threshold for SS_HOLD_MS
unsigned long plateauStartTime = 0;  // When plateau collection began

/* ============================================================================
 * HEATER CONTROL
 * ============================================================================ */

void setTop(bool on) { digitalWrite(TOP_CTRL, (on ^ !ACTIVE_HIGH) ? HIGH : LOW); }
void setBot(bool on) { digitalWrite(BOT_CTRL, (on ^ !ACTIVE_HIGH) ? HIGH : LOW); }

/* ============================================================================
 * HELPER FUNCTIONS
 * ============================================================================ */

float readHeaterVoltage() { return -1.0f; }

float readAmbientTemp() {
  float t = dht.readTemperature();
  if (isnan(t)) return -999.0f;
  return t;
}

bool platesAtAmbient(double tt, double tb, float tamb) {
  if (isnan(tt) || isnan(tb) || tamb < -900) return false;
  return (tt - tamb) < COOL_THRESHOLD_C && (tb - tamb) < COOL_THRESHOLD_C;
}

/*
 * computeDvDt()
 *
 * Computes the rate of change of Vtop over the last SS_WINDOW_S seconds
 * using a simple linear regression (first minus last, divided by time).
 *
 * Returns the absolute value of dV/dt in mV/s.
 * Returns 999.0 if not enough samples in the buffer yet.
 */
float computeDvDt() {
  if (historyCount < SS_WINDOW_S) return 999.0f;

  // Get the oldest and newest values in the window
  int oldestIdx = (historyIndex - SS_WINDOW_S + 60) % 60;
  float oldest = vtopHistory[oldestIdx];
  float newest = vtopHistory[(historyIndex - 1 + 60) % 60];

  float dvdt = (newest - oldest) / (float)SS_WINDOW_S;
  return abs(dvdt);
}

/* ============================================================================
 * PHASE TRANSITIONS
 * ============================================================================ */

void startPhase(Phase newPhase) {
  currentPhase = newPhase;
  phaseStartTime = millis();
  coolStableTracking = false;
  coolStableStart = 0;
  ssDetected = false;
  ssConfirmed = false;
  historyCount = 0;
  historyIndex = 0;

  Serial.print("# PHASE_CHANGE: ");
  Serial.print(phaseNames[newPhase]);
  Serial.print(" (run "); Serial.print(currentRun);
  Serial.print("/"); Serial.print(RUNS_PER_GAP);
  Serial.print(") at t="); Serial.print(millis());
  Serial.println(" ms");

  // Set heater state
  switch (newPhase) {
    case PHASE_WAIT_FOR_CORK:
      setTop(false); setBot(false);
      Serial.println("# ****************************************************");
      Serial.println("# ***   PUT CORK SHEETS BACK ON THE STACK NOW!     ***");
      Serial.println("# ***   LED blinking fast — heating in 30 sec      ***");
      Serial.println("# ****************************************************");
      break;
    case PHASE_HEATING:
    case PHASE_PLATEAU:
      setTop(true); setBot(false);   // Forward heating only
      break;
    default:
      setTop(false); setBot(false);  // Heaters off
      break;
  }
}

void advanceToNextRun() {
  currentRun++;
  if (currentRun > RUNS_PER_GAP) {
    startPhase(PHASE_COMPLETE);
  } else {
    Serial.println("#");
    Serial.print("# *** CORK REMINDER: Put cork sheets back on! ***");
    Serial.println();
    Serial.print("# *** Starting run "); Serial.print(currentRun);
    Serial.print("/"); Serial.print(RUNS_PER_GAP);
    Serial.println(" after cooldown ***");
    Serial.println("#");
    startPhase(PHASE_WAIT_AMBIENT);
  }
}

/* ============================================================================
 * STARTUP DIAGNOSTICS (same as TEST 14)
 * ============================================================================ */

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

/* ============================================================================
 * SETUP
 * ============================================================================ */

void setup() {
  Serial.begin(9600);
  while (!Serial); delay(2000);

  Serial.println("# ============================================");
  Serial.println("# GAP SWEEP — Modules B & C");
  Serial.println("# Adaptive Heating + Adaptive Cooldown");
  Serial.println("# ============================================");
  Serial.print("# RUN_ID: ");          Serial.println(RUN_ID);
  Serial.print("# GAP_DISTANCE: ");    Serial.println(GAP_DISTANCE);
  Serial.print("# MATERIAL_PAIR: ");   Serial.println(MATERIAL_PAIR);
  Serial.print("# SPACER_TYPE: ");     Serial.println(SPACER_TYPE);
  Serial.print("# RUNS_PER_GAP: ");    Serial.println(RUNS_PER_GAP);
  Serial.println("# HEAT_MODE: ADAPTIVE (detect steady state via dV/dt)");
  Serial.print("# HEAT_MIN_MS: ");     Serial.println(HEAT_MIN_MS);
  Serial.print("# HEAT_MAX_MS: ");     Serial.println(HEAT_MAX_MS);
  Serial.print("# SS_THRESHOLD: ");    Serial.print(SS_THRESHOLD_MV_S, 3);
  Serial.println(" mV/s");
  Serial.print("# SS_WINDOW: ");       Serial.print(SS_WINDOW_S);
  Serial.println(" sec");
  Serial.print("# SS_HOLD: ");         Serial.print(SS_HOLD_MS / 1000);
  Serial.println(" sec");
  Serial.print("# PLATEAU_TIME: ");    Serial.print(PLATEAU_MS / 1000);
  Serial.println(" sec");
  Serial.println("# COOL_MODE: ADAPTIVE (wait for ambient)");
  Serial.print("# COOL_THRESHOLD_C: ");Serial.println(COOL_THRESHOLD_C, 1);
  Serial.println("#");

  // Pin config
  pinMode(TOP_CTRL, OUTPUT); pinMode(BOT_CTRL, OUTPUT);
  setTop(false); setBot(false);
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.println("# [OK] Heater pins configured, both OFF");

  // SPI CS pins
  pinMode(CS_T_TOP, OUTPUT); digitalWrite(CS_T_TOP, HIGH);
  pinMode(CS_T_BOT, OUTPUT); digitalWrite(CS_T_BOT, HIGH);

  // I2C
  Wire.begin(); Wire.setClock(100000);
  i2cScan();

  // ADS1115
  bool adsOk = false;
  for (int attempt = 1; attempt <= 5; attempt++) {
    Serial.print("# ADS1115 init attempt "); Serial.print(attempt); Serial.print("/5: ");
    Wire.begin(); delay(100);
    if (ads.begin(0x48)) { Serial.println("SUCCESS"); adsOk = true; break; }
    Serial.println("FAIL"); delay(500);
  }
  if (!adsOk) {
    Serial.println("# FATAL: ADS1115 not found");
    while (1) { digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); delay(250); }
  }
  ads.setGain(GAIN_ONE);
  Serial.println("# [OK] ADS1115 GAIN_ONE");

  // DHT11
  dht.begin(); delay(2000);
  float testAmb = dht.readTemperature();
  if (isnan(testAmb)) Serial.println("# WARNING: DHT11 read failed");
  else { Serial.print("# [OK] DHT11: "); Serial.print(testAmb, 1); Serial.println(" C"); }

  // Sensor verify
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

  Serial.println("#");
  Serial.println("# ============================================");
  Serial.println("# DIAGNOSTICS COMPLETE");
  Serial.println("# Starting run 1/3...");
  Serial.println("# ============================================");

  // CSV header
  Serial.println("time_ms,phase,run,phase_time_ms,sample_num,Vtop_mV,Vbot_mV,Tt_C,Tb_C,dT_C,Vheater_V,Tamb_C,dVdt_mVs");

  phaseStartTime = millis();
}

/* ============================================================================
 * MAIN LOOP
 * ============================================================================ */

void loop() {
  unsigned long now = millis();

  // Most recent readings (persist between loop iterations)
  static double lastTt = 0, lastTb = 0;
  static float lastTamb = 0;
  static float lastVtop = 0;
  static float lastDvdt = 999.0;

  // ------------------------------------------------------------------
  // SENSOR SAMPLING (1 Hz)
  // ------------------------------------------------------------------
  if (now - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = now;
    sampleCount++;

    int16_t raw01 = ads.readADC_Differential_0_1();
    int16_t raw23 = ads.readADC_Differential_2_3();

    if (raw01 == 32767 || raw01 == -32768 || raw23 == 32767 || raw23 == -32768) {
      readFailCount++;
      if (readFailCount <= 10 || readFailCount % 100 == 0) {
        Serial.print("# WARN: ADS saturated #"); Serial.println(readFailCount);
      }
    }

    lastVtop = raw01 * mV_per_count;
    float vBot = raw23 * mV_per_count;
    lastTt = tcTop.readCelsius();
    lastTb = tcBot.readCelsius();
    double dT = lastTt - lastTb;
    lastTamb = readAmbientTemp();

    // Update dV/dt history buffer (during heating/plateau phases)
    if (currentPhase == PHASE_HEATING || currentPhase == PHASE_PLATEAU) {
      vtopHistory[historyIndex % 60] = lastVtop;
      historyIndex = (historyIndex + 1) % 60;
      if (historyCount < 60) historyCount++;
      lastDvdt = computeDvDt();
    } else {
      lastDvdt = -1.0;
    }

    // CSV output (added run number and dV/dt columns)
    Serial.print(now);                        Serial.print(",");
    Serial.print(phaseNames[currentPhase]);   Serial.print(",");
    Serial.print(currentRun);                 Serial.print(",");
    Serial.print(now - phaseStartTime);       Serial.print(",");
    Serial.print(sampleCount);                Serial.print(",");
    Serial.print(lastVtop, 4);                Serial.print(",");
    Serial.print(vBot, 4);                    Serial.print(",");
    Serial.print(lastTt, 2);                  Serial.print(",");
    Serial.print(lastTb, 2);                  Serial.print(",");
    Serial.print(dT, 2);                      Serial.print(",");
    Serial.print(-1.00, 2);                   Serial.print(",");
    Serial.print(lastTamb, 1);                Serial.print(",");
    Serial.println(lastDvdt, 4);
  }

  // ------------------------------------------------------------------
  // PHASE TRANSITIONS
  // ------------------------------------------------------------------

  // ---- COMPLETE ----
  if (currentPhase == PHASE_COMPLETE) {
    static bool completePrinted = false;
    if (!completePrinted) {
      setTop(false); setBot(false);
      Serial.println("# ============================================");
      Serial.println("# GAP SWEEP COMPLETE");
      Serial.print("# Gap: ");           Serial.println(GAP_DISTANCE);
      Serial.print("# Runs completed: "); Serial.println(RUNS_PER_GAP);
      Serial.print("# Total samples: "); Serial.println(sampleCount);
      Serial.print("# Total duration: "); Serial.print(millis() / 60000.0, 1);
      Serial.println(" min");
      Serial.println("#");
      Serial.println("# Next: change shim/spacer, update GAP_DISTANCE");
      Serial.println("#        and SPACER_TYPE, re-upload, and run again.");
      Serial.println("# ============================================");
      completePrinted = true;
    }
    digitalWrite(LED_BUILTIN, (millis() / 1000) % 2);
    return;
  }

  unsigned long phaseElapsed = now - phaseStartTime;

  // ---- WAIT_AMBIENT: adaptive (same as TEST 14) ----
  if (currentPhase == PHASE_WAIT_AMBIENT) {
    if (phaseElapsed >= COOL_MIN_MS) {
      bool atAmbient = platesAtAmbient(lastTt, lastTb, lastTamb);
      if (atAmbient) {
        if (!coolStableTracking) {
          coolStableTracking = true;
          coolStableStart = now;
          Serial.print("# AMBIENT_THRESHOLD_REACHED: Tt="); Serial.print(lastTt, 1);
          Serial.print("C Tb="); Serial.print(lastTb, 1);
          Serial.print("C Tamb="); Serial.print(lastTamb, 1);
          Serial.println("C");
        }
        if (now - coolStableStart >= COOL_STABLE_MS) {
          Serial.print("# AMBIENT_STABLE: run "); Serial.print(currentRun);
          Serial.print(" ready. Wait took ");
          Serial.print(phaseElapsed / 60000.0, 1); Serial.println(" min");
          startPhase(PHASE_WAIT_FOR_CORK);
        }
      } else {
        if (coolStableTracking) {
          Serial.println("# AMBIENT_UNSTABLE: resetting stability timer");
        }
        coolStableTracking = false;
      }
    }
    // Safety timeout
    if (phaseElapsed >= COOL_MAX_MS) {
      Serial.println("# AMBIENT_TIMEOUT: advancing anyway");
      startPhase(PHASE_WAIT_FOR_CORK);
    }
    // Progress every 5 min
    static unsigned long lastWaitReport = 0;
    if (phaseElapsed > 0 && (phaseElapsed / 300000) > (lastWaitReport / 300000)) {
      lastWaitReport = phaseElapsed;
      Serial.print("# WAIT_STATUS: "); Serial.print(phaseElapsed / 60000.0, 1);
      Serial.print(" min, Tt="); Serial.print(lastTt, 1);
      Serial.print("C Tb="); Serial.print(lastTb, 1);
      Serial.print("C Tamb="); Serial.print(lastTamb, 1);
      Serial.println("C ** Remove cork to speed up! **");
    }
  }

  // ---- WAIT_FOR_CORK: 30 sec pause with LED blinking ----
  if (currentPhase == PHASE_WAIT_FOR_CORK) {
    // Blink LED fast (4 Hz) so you can see it across the room
    digitalWrite(LED_BUILTIN, (millis() / 125) % 2);

    // Print countdown every 5 seconds
    unsigned long remaining = 0;
    if (phaseElapsed < CORK_WAIT_MS) remaining = (CORK_WAIT_MS - phaseElapsed) / 1000;
    static unsigned long lastCorkMsg = 999999;
    if (remaining != lastCorkMsg && remaining % 5 == 0) {
      lastCorkMsg = remaining;
      Serial.print("# >>> PUT CORK BACK ON! Heating starts in ");
      Serial.print(remaining);
      Serial.println(" sec <<<");
    }

    // After 30 sec, start heating
    if (phaseElapsed >= CORK_WAIT_MS) {
      lastCorkMsg = 999999;
      digitalWrite(LED_BUILTIN, LOW);
      Serial.println("# CORK_WAIT_DONE: starting heater now");
      startPhase(PHASE_HEATING);
    }
  }

  // ---- HEATING: adaptive steady-state detection ----
  if (currentPhase == PHASE_HEATING) {

    // After minimum heating time, check dV/dt
    if (phaseElapsed >= HEAT_MIN_MS) {
      float dvdt = lastDvdt;

      if (dvdt < SS_THRESHOLD_MV_S) {
        // dV/dt below threshold
        if (!ssDetected) {
          ssDetected = true;
          ssDetectedTime = now;
          Serial.print("# SS_DETECTED: dV/dt="); Serial.print(dvdt, 4);
          Serial.print(" mV/s < "); Serial.print(SS_THRESHOLD_MV_S, 3);
          Serial.print(" at "); Serial.print(phaseElapsed / 60000.0, 1);
          Serial.println(" min — holding...");
        }

        // Check if held for required duration
        if (now - ssDetectedTime >= SS_HOLD_MS && !ssConfirmed) {
          ssConfirmed = true;
          Serial.print("# SS_CONFIRMED: steady state held for ");
          Serial.print(SS_HOLD_MS / 1000); Serial.print("s. dV/dt=");
          Serial.print(dvdt, 4); Serial.println(" mV/s");
          Serial.print("# PLATEAU_START: collecting ");
          Serial.print(PLATEAU_MS / 1000); Serial.println(" sec of plateau data");
          // Transition to plateau phase (heater stays on)
          plateauStartTime = now;
          startPhase(PHASE_PLATEAU);
          setTop(true); setBot(false);  // Keep heater on!
        }
      } else {
        // dV/dt rose above threshold — reset
        if (ssDetected && !ssConfirmed) {
          Serial.print("# SS_RESET: dV/dt="); Serial.print(dvdt, 4);
          Serial.println(" mV/s — back above threshold");
        }
        ssDetected = false;
      }
    }

    // Safety timeout
    if (phaseElapsed >= HEAT_MAX_MS) {
      Serial.print("# HEAT_TIMEOUT: max "); Serial.print(HEAT_MAX_MS / 60000);
      Serial.println(" min reached — forcing plateau");
      plateauStartTime = now;
      startPhase(PHASE_PLATEAU);
      setTop(true); setBot(false);  // Keep heater on
    }

    // Progress every 2 min during heating
    static unsigned long lastHeatReport = 0;
    if (phaseElapsed > 0 && (phaseElapsed / 120000) > (lastHeatReport / 120000)) {
      lastHeatReport = phaseElapsed;
      Serial.print("# HEAT_STATUS: "); Serial.print(phaseElapsed / 60000.0, 1);
      Serial.print(" min, Vtop="); Serial.print(lastVtop, 1);
      Serial.print("mV dV/dt="); Serial.print(lastDvdt, 4);
      Serial.println(" mV/s");
    }
  }

  // ---- PLATEAU: collect steady-state data, then cool ----
  if (currentPhase == PHASE_PLATEAU) {
    if (now - plateauStartTime >= PLATEAU_MS) {
      Serial.print("# PLATEAU_COMPLETE: "); Serial.print(PLATEAU_MS / 1000);
      Serial.print("s of data collected. Vtop="); Serial.print(lastVtop, 1);
      Serial.print("mV Tt="); Serial.print(lastTt, 1);
      Serial.print("C Tb="); Serial.print(lastTb, 1);
      Serial.println("C");
      Serial.println("#");
      Serial.println("# *** CORK REMINDER: Remove cork sheets for faster cooling! ***");
      Serial.println("#");
      startPhase(PHASE_COOLDOWN);
    }
  }

  // ---- COOLDOWN: adaptive (same logic as TEST 14 and WAIT_AMBIENT) ----
  if (currentPhase == PHASE_COOLDOWN) {
    if (phaseElapsed >= COOL_MIN_MS) {
      bool atAmbient = platesAtAmbient(lastTt, lastTb, lastTamb);
      if (atAmbient) {
        if (!coolStableTracking) {
          coolStableTracking = true;
          coolStableStart = now;
          Serial.print("# COOL_THRESHOLD_REACHED: Tt="); Serial.print(lastTt, 1);
          Serial.print("C Tb="); Serial.print(lastTb, 1);
          Serial.print("C Tamb="); Serial.print(lastTamb, 1);
          Serial.println("C");
        }
        if (now - coolStableStart >= COOL_STABLE_MS) {
          Serial.print("# COOL_STABLE: run "); Serial.print(currentRun);
          Serial.print(" cooldown took ");
          Serial.print(phaseElapsed / 60000.0, 1); Serial.println(" min");
          advanceToNextRun();
        }
      } else {
        if (coolStableTracking) {
          Serial.println("# COOL_UNSTABLE: resetting");
        }
        coolStableTracking = false;
      }
    }
    // Safety timeout
    if (phaseElapsed >= COOL_MAX_MS) {
      Serial.print("# COOL_TIMEOUT: "); Serial.print(COOL_MAX_MS / 60000);
      Serial.println(" min — advancing");
      advanceToNextRun();
    }
    // Progress every 5 min
    static unsigned long lastCoolReport = 0;
    if (phaseElapsed > 0 && (phaseElapsed / 300000) > (lastCoolReport / 300000)) {
      lastCoolReport = phaseElapsed;
      Serial.print("# COOL_STATUS: "); Serial.print(phaseElapsed / 60000.0, 1);
      Serial.print(" min, Tt="); Serial.print(lastTt, 1);
      Serial.print("C Tb="); Serial.print(lastTb, 1);
      Serial.print("C Tamb="); Serial.print(lastTamb, 1);
      Serial.println("C ** Remove cork to speed up! **");
    }
  }
}
