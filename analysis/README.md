# analysis/

Python scripts for data analysis, thermal modelling, and figure generation.
All scripts authored by Nikhitha Swaminathan, February 2026.

**Dependencies:** numpy, matplotlib, scipy
```
pip install numpy matplotlib scipy
```

---

## Scripts

### `thermal_rectification_plots.py` — Main figure generator
Generates the complete figure set for the DRSEF/ISEF project.

**Data inputs (expected in same directory or path-specified):**
- `abba_sio2_contact.txt` — SiO2-SiO2 contact ABBA run
- `abba_steel_glass_508um.txt` — Steel-glass 508 µm ABBA run (key result)
- `abba_glass_glass_508um.txt` — Glass-glass 508 µm ABBA control run
- Gap sweep values hardcoded from Module B/C measurements

**Figures produced:**
- Fig 5: Gap sweep V_bot bar chart
- Fig 6: Thermal Current Divider (sum + stacked split)
- Fig 7: Key result 5-panel vacuum ABBA
- Fig 9: Rectification physics (air masking + signal prediction)

**To run:**
```bash
python thermal_rectification_plots.py
```

---

### `thermal_model.py` — 1D thermal resistance network model
Predicts heat flow distribution across the apparatus stack and explains why thermal rectification is undetectable in air.

**What it models:**
- Full resistance network: cork → support plate → TEG → heater → carrier → gap → carrier → TEG → support plate → cork
- Gap resistance as a function of gap distance (air conduction + radiation)
- Predicted TEG voltages in air vs. vacuum at each gap distance
- Why the sum metric (V_top + V_bot) is insensitive to gap physics
- Predicted rectification signal magnitude as function of gap and pressure

**Figures produced:**
- Fig 10: Air vs. vacuum TEG sum prediction with rectification band
- Air-to-radiation ratio plot
- Resistance network sensitivity analysis

**To run:**
```bash
python thermal_model.py
```

---

### `uncertainty_analysis.py` — Allan deviation + uncertainty propagation
Computes measurement uncertainty and optimal averaging parameters.

**What it computes:**
1. Allan deviation for each ABBA phase (A1, A2, B1, B2) — identifies transition from white noise to drift
2. Optimal averaging time τ from Allan minimum (~3–7s)
3. Uncertainty propagation through η = η_raw / η_apparatus correction
4. 95% confidence intervals on corrected rectification ratio
5. p-value from t-test on A vs. B plateau means

**Data inputs:**
- Plateau voltage arrays extracted from ABBA run CSV files

**Figures produced:**
- Fig 8: Allan deviation plots (Steel-Glass + Glass-Glass control)
- Uncertainty budget table

**Key output:**
```
η_corrected = 0.9325 ± 0.0016
95% CI: [0.9294, 0.9356]  →  rectification [6.4%, 7.1%]
p < 0.001
```

**To run:**
```bash
python uncertainty_analysis.py
```

---

## Data File Format

ABBA run CSV files (from Arduino Serial Monitor output) have the following columns:
```
timestamp_ms, phase, Vtop_mV, Vbot_mV, T_top_C, T_bot_C, T_ambient_C, vacuum_inHg
```

Each row is one 1 Hz sample. Phase labels: `A1_HEAT`, `A1_COOL`, `B1_HEAT`, `B1_COOL`, `B2_HEAT`, `B2_COOL`, `A2_HEAT`, `A2_COOL`.
