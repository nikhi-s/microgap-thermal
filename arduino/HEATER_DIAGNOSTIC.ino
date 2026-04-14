/*
 * HEATER DIAGNOSTIC — Quick test to verify both heaters fire
 * Fires top heater for 2 min, monitors TEG, then bottom heater for 2 min.
 * If working: Vtop should rise to ~200+ mV when top fires,
 *             Vbot should rise to ~200+ mV when bottom fires.
 * If broken:  voltage stays near 0 = heater not delivering power.
 */

#include <Wire.h>
#include <SPI.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_MAX31855.h>
#include <DHT.h>

const int TOP_CTRL = 6;
const int BOT_CTRL = 7;

#define CS_T_TOP 10
#define CS_T_BOT 9
#define DHT_PIN  A1
#define DHT_TYPE DHT11

Adafruit_ADS1115 ads;
Adafruit_MAX31855 tcTop(CS_T_TOP);
Adafruit_MAX31855 tcBot(CS_T_BOT);
DHT dht(DHT_PIN, DHT_TYPE);

const float mV_per_count = 0.125f;

enum TestPhase { IDLE_BEFORE, TOP_ON, GAP1, BOT_ON, GAP2, DONE };
TestPhase phase = IDLE_BEFORE;
unsigned long phaseStart = 0;
unsigned long lastSample = 0;

// 2 min each phase
const unsigned long HEAT_TIME = 120000;  // 2 min heating
const unsigned long IDLE_TIME = 10000;   // 10 sec baseline

void setup() {
  Serial.begin(9600);
  while (!Serial);
  delay(2000);

  pinMode(TOP_CTRL, OUTPUT);
  pinMode(BOT_CTRL, OUTPUT);
  digitalWrite(TOP_CTRL, LOW);
  digitalWrite(BOT_CTRL, LOW);

  pinMode(CS_T_TOP, OUTPUT); digitalWrite(CS_T_TOP, HIGH);
  pinMode(CS_T_BOT, OUTPUT); digitalWrite(CS_T_BOT, HIGH);

  Wire.begin();
  Wire.setClock(100000);
  ads.begin(0x48);
  ads.setGain(GAIN_ONE);
  dht.begin();
  delay(2000);

  Serial.println("# ============================================");
  Serial.println("# HEATER DIAGNOSTIC TEST");
  Serial.println("# Phase 1: 10s baseline (both OFF)");
  Serial.println("# Phase 2: TOP heater ON for 2 min");
  Serial.println("# Phase 3: 10s gap (both OFF)");
  Serial.println("# Phase 4: BOT heater ON for 2 min");
  Serial.println("# Phase 5: 10s gap (both OFF)");
  Serial.println("# ============================================");
  Serial.println("# PASS: Vtop rises >100mV during TOP ON");
  Serial.println("#        Vbot rises >100mV during BOT ON");
  Serial.println("# FAIL: voltage stays near 0 = check wiring/power");
  Serial.println("# ============================================");
  Serial.println("time_s,phase,Vtop_mV,Vbot_mV,Sum_mV,Tt_C,Tb_C,Tamb_C");

  phase = IDLE_BEFORE;
  phaseStart = millis();
}

const char* phaseLabel() {
  switch (phase) {
    case IDLE_BEFORE: return "BASELINE";
    case TOP_ON:      return "TOP_HEAT";
    case GAP1:        return "GAP1";
    case BOT_ON:      return "BOT_HEAT";
    case GAP2:        return "GAP2";
    case DONE:        return "DONE";
  }
  return "?";
}

void loop() {
  unsigned long now = millis();
  unsigned long elapsed = now - phaseStart;

  // Phase transitions
  if (phase == IDLE_BEFORE && elapsed >= IDLE_TIME) {
    phase = TOP_ON;
    phaseStart = now;
    digitalWrite(TOP_CTRL, HIGH);
    Serial.println("# >>> TOP HEATER ON — watch Vtop");
  }
  else if (phase == TOP_ON && elapsed >= HEAT_TIME) {
    digitalWrite(TOP_CTRL, LOW);
    phase = GAP1;
    phaseStart = now;
    Serial.println("# >>> TOP HEATER OFF");
  }
  else if (phase == GAP1 && elapsed >= IDLE_TIME) {
    phase = BOT_ON;
    phaseStart = now;
    digitalWrite(BOT_CTRL, HIGH);
    Serial.println("# >>> BOT HEATER ON — watch Vbot");
  }
  else if (phase == BOT_ON && elapsed >= HEAT_TIME) {
    digitalWrite(BOT_CTRL, LOW);
    phase = GAP2;
    phaseStart = now;
    Serial.println("# >>> BOT HEATER OFF");
  }
  else if (phase == GAP2 && elapsed >= IDLE_TIME) {
    phase = DONE;
    phaseStart = now;
    Serial.println("# ============================================");
    Serial.println("# DIAGNOSTIC COMPLETE — check results above");
    Serial.println("# ============================================");
  }

  // Sample at 1 Hz
  if (phase != DONE && now - lastSample >= 1000) {
    lastSample = now;

    int16_t raw01 = ads.readADC_Differential_0_1();
    int16_t raw23 = ads.readADC_Differential_2_3();
    float vTop = raw01 * mV_per_count;
    float vBot = raw23 * mV_per_count;
    double Tt = tcTop.readCelsius();
    double Tb = tcBot.readCelsius();
    float Tamb = dht.readTemperature();
    if (isnan(Tamb)) Tamb = -1;

    Serial.print(now / 1000); Serial.print(",");
    Serial.print(phaseLabel()); Serial.print(",");
    Serial.print(vTop, 2); Serial.print(",");
    Serial.print(vBot, 2); Serial.print(",");
    Serial.print(vTop + vBot, 2); Serial.print(",");
    Serial.print(Tt, 1); Serial.print(",");
    Serial.print(Tb, 1); Serial.print(",");
    Serial.println(Tamb, 1);
  }

  if (phase == DONE) {
    digitalWrite(LED_BUILTIN, (millis() / 500) % 2);
  }
}
