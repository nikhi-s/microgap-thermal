// TEST 13 -- Full ABBA Protocol with Metadata & Diagnostics (Mega 2560)
// Sequence: A1(Forward) -> Cool -> B1(Reverse) -> Cool -> B2(Reverse) -> Cool -> A2(Forward) -> Cool -> Stop
// Sensors: ADS1115 (TEG), MAX31855 (TC), DHT11 (ambient), Voltage divider (heater V)

#include <Wire.h>
#include <SPI.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_MAX31855.h>
#include <DHT.h>

// =================== USER CONFIG (SET BEFORE EACH RUN) ===================
//const char* RUN_ID          = "RUN_001";
//const char* GAP_DISTANCE    = "3um";         // "contact", "3um", "6um", "10um", "30um", "50um"
//const char* MATERIAL_PAIR   = "SiO2-SiO2";  // "SiO2-SiO2", "Au-SiO2", "AlAnod-SS"
//const char* SPACER_TYPE     = "microsphere"; // "microsphere", "kapton_shim", "none"
//const int   RUN_NUMBER      = 1;             // increment for repeat runs
//const char* OPERATOR_NOTES  = "Phase1 ambient air, foam enclosure, 12V heater";
const char* RUN_ID          = "CAL_001";
const char* GAP_DISTANCE    = "contact";      // no gap, slides touching
const char* MATERIAL_PAIR   = "SiO2-SiO2";
const char* SPACER_TYPE     = "none";         // no shim or microspheres
const int   RUN_NUMBER      = 1;
const char* OPERATOR_NOTES  = "Module A calibration, direct contact, no spacer, 12V heater";

// =================== TIMING CONFIG ===================
//const unsigned long HEAT_DURATION_MS   = 1200000UL;  // 20 minutes heating
//const unsigned long COOL_DURATION_MS   = 1200000UL;  // 20 minutes cooling
//const unsigned long HEAT_DURATION_MS   = 1800000UL;  // 30 minutes heating
//const unsigned long COOL_DURATION_MS   = 1800000UL;  // 30 minutes cooling
const unsigned long HEAT_DURATION_MS = 1200000UL;  // 20 minutes heating
const unsigned long COOL_DURATION_MS = 3600000UL;  // 60 minutes cooling
const unsigned long SAMPLE_INTERVAL_MS = 1000;        // 1 Hz (matches research plan)

// =================== PIN CONFIG ===================
const int TOP_CTRL = 6;
const int BOT_CTRL = 7;
const bool ACTIVE_HIGH = true;

#define CS_T_TOP 10
#define CS_T_BOT 9    

// DHT11 ambient temperature sensor
#define DHT_PIN  A1
#define DHT_TYPE DHT11
DHT dht(DHT_PIN, DHT_TYPE);

// Heater voltage sense (10k + 2.2k divider from 12V rail to A0)
// Vread = V_heater * 2.2 / (10 + 2.2) = V_heater * 0.1803
// V_heater = Vread / 0.1803
const int   HEATER_V_PIN     = A0;
const float V_DIVIDER_RATIO  = 0.1803f;  // adjust to your actual resistor values
const bool  USE_HEATER_V     = false;     // false if divider not wired yet
const bool  USE_DHT_AMBIENT  = true;     // false if DHT11 not wired yet

// =================== SENSOR OBJECTS ===================
Adafruit_ADS1115 ads;
Adafruit_MAX31855 tcTop(CS_T_TOP);
Adafruit_MAX31855 tcBot(CS_T_BOT);

// ADS1115 GAIN_ONE: +/-4.096V => 0.125 mV per count
const float mV_per_count = 0.125f;

void setTop(bool on) { digitalWrite(TOP_CTRL, (on ^ !ACTIVE_HIGH) ? HIGH : LOW); }
void setBot(bool on) { digitalWrite(BOT_CTRL, (on ^ !ACTIVE_HIGH) ? HIGH : LOW); }

// =================== ABBA STATE MACHINE ===================
enum ABBAPhase {
  PHASE_A1_HEAT,    // Forward heating (top)
  PHASE_A1_COOL,    // Cooldown after A1
  PHASE_B1_HEAT,    // Reverse heating (bottom)
  PHASE_B1_COOL,    // Cooldown after B1
  PHASE_B2_HEAT,    // Reverse heating repeat
  PHASE_B2_COOL,    // Cooldown after B2
  PHASE_A2_HEAT,    // Forward heating repeat
  PHASE_A2_COOL,    // Cooldown after A2
  PHASE_COMPLETE    // Test done
};

const char* phaseNames[] = {
  "A1_FWD_HEAT", "A1_COOLDOWN",
  "B1_REV_HEAT", "B1_COOLDOWN",
  "B2_REV_HEAT", "B2_COOLDOWN",
  "A2_FWD_HEAT", "A2_COOLDOWN",
  "COMPLETE"
};

ABBAPhase currentPhase = PHASE_A1_HEAT;
unsigned long phaseStartTime = 0;
unsigned long lastSampleTime = 0;
unsigned long sampleCount = 0;
unsigned long readFailCount = 0;

// =================== SENSOR READING FUNCTIONS ===================
float readHeaterVoltage() {
  if (!USE_HEATER_V) return -1.0f;
  int raw = analogRead(HEATER_V_PIN);
  float vPin = raw * (5.0f / 1023.0f);
  return vPin / V_DIVIDER_RATIO;
}

float readAmbientTemp() {
  if (!USE_DHT_AMBIENT) return -999.0f;
  float t = dht.readTemperature();
  if (isnan(t)) return -999.0f;
  return t;
}

// =================== PHASE MANAGEMENT ===================
unsigned long getPhaseDuration() {
  switch (currentPhase) {
    case PHASE_A1_HEAT: case PHASE_B1_HEAT:
    case PHASE_B2_HEAT: case PHASE_A2_HEAT:
      return HEAT_DURATION_MS;
    case PHASE_A1_COOL: case PHASE_B1_COOL:
    case PHASE_B2_COOL: case PHASE_A2_COOL:
      return COOL_DURATION_MS;
    default:
      return 0;
  }
}

void applyHeaterState() {
  switch (currentPhase) {
    case PHASE_A1_HEAT: case PHASE_A2_HEAT:
      setTop(true);  setBot(false);  // Forward
      break;
    case PHASE_B1_HEAT: case PHASE_B2_HEAT:
      setTop(false); setBot(true);   // Reverse
      break;
    default:
      setTop(false); setBot(false);  // Cooling or complete
      break;
  }
}

void advancePhase() {
  if (currentPhase < PHASE_COMPLETE) {
    currentPhase = (ABBAPhase)((int)currentPhase + 1);
    phaseStartTime = millis();

    Serial.print("# PHASE_CHANGE: ");
    Serial.print(phaseNames[currentPhase]);
    Serial.print(" at t=");
    Serial.print(millis());
    Serial.println(" ms");

    applyHeaterState();
  }
}

// =================== DIAGNOSTICS ===================
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
  if (found == 0) {
    Serial.println("#   *** NO I2C DEVICES - check SDA=20, SCL=21, pull-ups ***");
  }
  Serial.println("# I2C_SCAN_END");
}

void checkHeaterMOSFETs() {
  Serial.println("# MOSFET_TEST_START");

  setTop(false); setBot(false); delay(50);
  bool topOff = digitalRead(TOP_CTRL);
  bool botOff = digitalRead(BOT_CTRL);
  Serial.print("#   TOP_OFF="); Serial.print(topOff ? "HIGH" : "LOW");
  Serial.print("  BOT_OFF="); Serial.println(botOff ? "HIGH" : "LOW");

  if (ACTIVE_HIGH && (topOff == HIGH || botOff == HIGH)) {
    Serial.println("#   *** WARNING: Pin HIGH in OFF state with ACTIVE_HIGH! ***");
  }

  // Pulse TOP
  setTop(true); delay(10);
  bool topOn = digitalRead(TOP_CTRL);
  Serial.print("#   TOP_ON="); Serial.print(topOn ? "HIGH" : "LOW");
  Serial.println((ACTIVE_HIGH && topOn) ? " (CORRECT)" : " *** CHECK POLARITY ***");
  delay(200); setTop(false); delay(50);
  Serial.print("#   TOP_RESTORED="); Serial.println(digitalRead(TOP_CTRL) == topOff ? "OK" : "STUCK!");

  // Pulse BOT
  setBot(true); delay(10);
  bool botOn = digitalRead(BOT_CTRL);
  Serial.print("#   BOT_ON="); Serial.print(botOn ? "HIGH" : "LOW");
  Serial.println((ACTIVE_HIGH && botOn) ? " (CORRECT)" : " *** CHECK POLARITY ***");
  delay(200); setBot(false); delay(50);
  Serial.print("#   BOT_RESTORED="); Serial.println(digitalRead(BOT_CTRL) == botOff ? "OK" : "STUCK!");

  // Cross-talk
  setTop(true); delay(50);
  Serial.print("#   XTALK TOP_ON->BOT: "); Serial.println(digitalRead(BOT_CTRL) == botOff ? "OK" : "FAIL!");
  setTop(false); delay(50);
  setBot(true); delay(50);
  Serial.print("#   XTALK BOT_ON->TOP: "); Serial.println(digitalRead(TOP_CTRL) == topOff ? "OK" : "FAIL!");
  setBot(false);

  Serial.println("# MOSFET_TEST_END");
}

void checkWireBus() {
  Serial.println("# I2C_BUS_CHECK_START");
  pinMode(20, INPUT);
  pinMode(21, INPUT);
  int sda = digitalRead(20);
  int scl = digitalRead(21);
  Serial.print("#   SDA="); Serial.print(sda ? "HIGH(ok)" : "LOW(stuck!)");
  Serial.print("  SCL="); Serial.println(scl ? "HIGH(ok)" : "LOW(stuck!)");

  if (!sda || !scl) {
    Serial.println("#   Attempting clock recovery...");
    pinMode(21, OUTPUT);
    for (int i = 0; i < 16; i++) {
      digitalWrite(21, LOW);  delayMicroseconds(5);
      digitalWrite(21, HIGH); delayMicroseconds(5);
    }
    pinMode(21, INPUT);
    delay(10);
    Serial.print("#   After recovery - SDA="); Serial.print(digitalRead(20) ? "HIGH" : "LOW");
    Serial.print("  SCL="); Serial.println(digitalRead(21) ? "HIGH" : "LOW");
  }
  Wire.begin();
  Serial.println("# I2C_BUS_CHECK_END");
}

// =================== SETUP ===================
void setup() {
  Serial.begin(9600);
  while (!Serial) { ; }
  delay(2000);

  // ---- Metadata Header ----
  Serial.println("# ============================================");
  Serial.println("# MICRO-GAP THERMAL RECTIFIER - ABBA PROTOCOL");
  Serial.println("# ============================================");
  Serial.print("# RUN_ID: ");         Serial.println(RUN_ID);
  Serial.print("# GAP_DISTANCE: ");   Serial.println(GAP_DISTANCE);
  Serial.print("# MATERIAL_PAIR: ");  Serial.println(MATERIAL_PAIR);
  Serial.print("# SPACER_TYPE: ");    Serial.println(SPACER_TYPE);
  Serial.print("# RUN_NUMBER: ");     Serial.println(RUN_NUMBER);
  Serial.print("# NOTES: ");          Serial.println(OPERATOR_NOTES);
  Serial.print("# HEAT_DURATION_MS: "); Serial.println(HEAT_DURATION_MS);
  Serial.print("# COOL_DURATION_MS: "); Serial.println(COOL_DURATION_MS);
  Serial.print("# SAMPLE_RATE_MS: ");   Serial.println(SAMPLE_INTERVAL_MS);
  Serial.print("# ADS_GAIN: GAIN_ONE (+-4096mV, ");
  Serial.print(mV_per_count, 4); Serial.println(" mV/count)");
  Serial.println("# ABBA_SEQUENCE: A1_FWD -> COOL -> B1_REV -> COOL -> B2_REV -> COOL -> A2_FWD -> COOL");
  Serial.print("# USE_HEATER_V: ");    Serial.println(USE_HEATER_V ? "YES" : "NO");
  Serial.print("# USE_DHT_AMBIENT: "); Serial.println(USE_DHT_AMBIENT ? "YES" : "NO");
  Serial.println("#");

  // ---- Pin Setup ----
  pinMode(TOP_CTRL, OUTPUT);
  pinMode(BOT_CTRL, OUTPUT);
  setTop(false); setBot(false);
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.println("# [OK] Heater pins configured (TOP=6, BOT=7), both OFF");

  // ---- MOSFET Diagnostics ----
  checkHeaterMOSFETs();

  // ---- SPI CS pins HIGH before I2C ----
  pinMode(CS_T_TOP, OUTPUT); digitalWrite(CS_T_TOP, HIGH);
  pinMode(CS_T_BOT, OUTPUT); digitalWrite(CS_T_BOT, HIGH);
  Serial.println("# [OK] SPI CS pins HIGH (deselected)");

  // ---- I2C Init ----
  Wire.begin();
  Wire.setClock(100000);
  Serial.println("# [OK] Wire.begin() at 100kHz");
  delay(100);

  checkWireBus();
  i2cScan();

  // ---- ADS1115 Init with Retries ----
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
    Wire.beginTransmission(0x48);
    byte err = Wire.endTransmission();
    Serial.print("#   Wire error: "); Serial.println(err);
    delay(500);
  }
  if (!adsOk) {
    Serial.println("# **** FATAL: ADS1115 NOT FOUND ****");
    Serial.println("# Check: SDA=20, SCL=21, VDD, GND, ADDR=GND for 0x48");
    while (1) { digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); delay(250); }
  }
  ads.setGain(GAIN_ONE);
  Serial.println("# [OK] ADS1115 GAIN_ONE configured");

  // ---- DHT11 Init ----
  if (USE_DHT_AMBIENT) {
    dht.begin();
    delay(2000);  // DHT11 needs 1-2s warm-up
    float testAmb = dht.readTemperature();
    if (isnan(testAmb)) {
      Serial.println("# WARNING: DHT11 read failed - check wiring (DATA->A1, VCC->5V, GND)");
    } else {
      Serial.print("# [OK] DHT11 ambient: "); Serial.print(testAmb, 1); Serial.println(" C");
    }
  }

  // ---- Heater Voltage Divider Check ----
  if (USE_HEATER_V) {
    float vTest = readHeaterVoltage();
    Serial.print("# [INFO] Heater voltage reads: "); Serial.print(vTest, 2); Serial.println(" V");
    if (vTest < 0.5) {
      Serial.println("#   (Heater supply appears OFF or divider not connected)");
    } else if (vTest > 14.0) {
      Serial.println("#   *** WARNING: Voltage > 14V - check divider ratio ***");
    }
  }

  // ---- Verify Sensor Readings ----
  Serial.println("# SENSOR_VERIFY_START");
  for (int i = 0; i < 3; i++) {
    int16_t r01 = ads.readADC_Differential_0_1();
    int16_t r23 = ads.readADC_Differential_2_3();
    double Tt = tcTop.readCelsius();
    double Tb = tcBot.readCelsius();
    float Vheat = readHeaterVoltage();
    float Tamb = readAmbientTemp();

    Serial.print("#   Sample "); Serial.print(i + 1);
    Serial.print(": V01="); Serial.print(r01 * mV_per_count, 2);
    Serial.print("mV V23="); Serial.print(r23 * mV_per_count, 2);
    Serial.print("mV Tt="); Serial.print(Tt, 1);
    Serial.print("C Tb="); Serial.print(Tb, 1);
    Serial.print("C Vhtr="); Serial.print(Vheat, 2);
    Serial.print("V Tamb="); Serial.print(Tamb, 1);
    Serial.println("C");
    delay(500);
  }
  Serial.println("# SENSOR_VERIFY_END");

  // ---- TC Fault Check ----
  double Tt = tcTop.readCelsius();
  double Tb = tcBot.readCelsius();
  if (isnan(Tt)) {
    Serial.print("# WARNING: TC_TOP fault - ");
    uint8_t e = tcTop.readError();
    if (e & 0x01) Serial.println("OPEN");
    if (e & 0x02) Serial.println("SHORT_GND");
    if (e & 0x04) Serial.println("SHORT_VCC");
  } else {
    Serial.print("# [OK] TC_TOP: "); Serial.print(Tt, 1); Serial.println(" C");
  }
  if (isnan(Tb)) {
    Serial.print("# WARNING: TC_BOT fault - ");
    uint8_t e = tcBot.readError();
    if (e & 0x01) Serial.println("OPEN");
    if (e & 0x02) Serial.println("SHORT_GND");
    if (e & 0x04) Serial.println("SHORT_VCC");
  } else {
    Serial.print("# [OK] TC_BOT: "); Serial.print(Tb, 1); Serial.println(" C");
  }

  // ---- Calculate and print total run time ----
  unsigned long totalMs = (HEAT_DURATION_MS + COOL_DURATION_MS) * 4;
  Serial.print("# TOTAL_RUN_TIME: "); Serial.print(totalMs / 60000.0, 1); Serial.println(" minutes");
  Serial.print("# EXPECTED_SAMPLES: "); Serial.println(totalMs / SAMPLE_INTERVAL_MS);

  // ---- Start ----
  Serial.println("#");
  Serial.println("# ============================================");
  Serial.println("# DIAGNOSTICS COMPLETE - STARTING ABBA");
  Serial.println("# ============================================");
  Serial.println("time_ms,phase,phase_time_ms,sample_num,Vtop_mV,Vbot_mV,Tt_C,Tb_C,dT_C,Vheater_V,Tamb_C");

  phaseStartTime = millis();
  applyHeaterState();
}

// =================== LOOP ===================
void loop() {
  unsigned long now = millis();

  // ---- Phase Transition Check ----
  if (currentPhase < PHASE_COMPLETE) {
    unsigned long phaseElapsed = now - phaseStartTime;
    if (phaseElapsed >= getPhaseDuration()) {
      advancePhase();
    }
  }

  // ---- Test Complete ----
  if (currentPhase == PHASE_COMPLETE) {
    setTop(false); setBot(false);
    Serial.println("# ============================================");
    Serial.println("# ABBA PROTOCOL COMPLETE");
    Serial.print("# Total samples: ");     Serial.println(sampleCount);
    Serial.print("# ADS read failures: "); Serial.println(readFailCount);
    Serial.print("# Total duration: ");    Serial.print(millis() / 60000.0, 1); Serial.println(" min");
    Serial.print("# Final ambient: ");     Serial.print(readAmbientTemp(), 1); Serial.println(" C");
    Serial.print("# Final heater V: ");    Serial.print(readHeaterVoltage(), 2); Serial.println(" V");
    Serial.println("# ============================================");
    while (1) { digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); delay(1000); }
  }

  // ---- Sample at Configured Rate ----
  if (now - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = now;
    sampleCount++;

    // Read TEG voltages
    int16_t raw01 = ads.readADC_Differential_0_1();
    int16_t raw23 = ads.readADC_Differential_2_3();

    // Saturation / failure check
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

    // Read thermocouples
    double Tt = tcTop.readCelsius();
    double Tb = tcBot.readCelsius();
    double dT = Tt - Tb;

    // Read heater voltage and ambient
    float Vheat = readHeaterVoltage();
    float Tamb  = readAmbientTemp();

    // CSV output
    Serial.print(now);                        Serial.print(",");
    Serial.print(phaseNames[currentPhase]);   Serial.print(",");
    Serial.print(now - phaseStartTime);       Serial.print(",");
    Serial.print(sampleCount);                Serial.print(",");
    Serial.print(vTop, 4);                    Serial.print(",");
    Serial.print(vBot, 4);                    Serial.print(",");
    Serial.print(Tt, 2);                      Serial.print(",");
    Serial.print(Tb, 2);                      Serial.print(",");
    Serial.print(dT, 2);                      Serial.print(",");
    Serial.print(Vheat, 2);                   Serial.print(",");
    Serial.println(Tamb, 1);
  }
}