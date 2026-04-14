# figures/

Publication-quality result figures generated from experimental data.
All figures produced with matplotlib. White backgrounds for print/web use.

---

## Key Result

### `fig7_key_result.png` ⭐ Most Important
**5-panel vacuum ABBA result — the primary finding**
- Panel (A): Full overnight ABBA time series (~8.5 hours). Four phases visible: A1 (steel heated), B1 (glass heated), B2 (glass heated repeat), A2 (steel heated repeat). A2 excluded from analysis due to vacuum degradation from 28.5→29.5 inHg.
- Panel (B): Phase curves — A1 (steel heated) reaches 351 mV plateau vs. B1 (glass heated) at 308 mV. Δ = 43 mV separation.
- Panel (C): A2 rerun comparison — confirms B1/B2 consistency at ~306 mV; A1 at 28.5 inHg confirmed as primary forward measurement.
- Panel (D): Plateau bar chart — A1=350.7, B1=307.8, B2=306.2, A2=306.3 mV
- Panel (E): Corrected η = 0.9325 ± 0.0016 (6.7% rectification, p < 0.001, 95% CI [6.4%, 7.1%])

### `drsef_5panel_tight.png`
Competition poster version of the key result (same data as fig7, tighter layout for DRSEF/ISEF display).

---

## Gap Sweep — Thermal Current Divider Discovery

### `fig5_gap_sweep_vbot.png`
**V_bot (through-gap metric) vs. gap distance**
Bar chart showing V_bot at five gap distances: Contact (397.1 mV), 8.5 µm (363.7), 25.4 µm (357.2), 254 µm (279.5), 508 µm (248.5 mV). Drop of 32% across 60× gap increase annotated. Error bars from 3 repeat runs per gap.

### `fig6_current_divider.png`
**Thermal Current Divider effect — the original discovery**
Two-panel figure:
- Left: TEG sum (V_top + V_bot) across gap distances — only 4.1% drop despite 60× gap increase. Demonstrates sum metric insensitivity.
- Right: Stacked bar showing V_top/V_bot split at each gap. As gap increases, heat redirects from V_bot (through-gap) to V_top (hot-side). Shows the current divider mechanism directly.

---

## Measurement Methodology

### `fig8_allan_deviation.png`
**Allan deviation analysis — optimal averaging time**
Two-panel figure (Steel-Glass left, Glass-Glass control right). Log-log plot of Allan deviation vs. averaging time τ for all four ABBA phases (A1, A2, B1, B2). Star markers indicate Allan minimum at τ ≈ 3–7s. Dashed line shows τ^(-1/2) white noise slope. Demonstrates transition from noise-dominated to drift-dominated regime. Used to set plateau averaging window.

---

## Physics — Air Masking and Vacuum Prediction

### `fig9_rectification_physics.png`
**Air conduction masking analysis**
Two-panel figure:
- Left: Heat transfer coefficient h vs. gap distance (log-log). Air conduction (k/d, purple solid) vs. radiation for GG (ε_eff=0.82, dashed) and SG (ε_eff=0.20, dotted). Ratio annotations: 419×, 140×, 14×, 7× at each gap. Shaded region shows air dominance.
- Right: Expected rectification signal (mV) in air vs. vacuum at each gap. Air signals (0.2–0.6 mV) are all below the ±0.9 mV noise floor. Vacuum signals (8–45 mV) are well above detection threshold. Explains why 508 µm was selected for the vacuum experiment.

### `fig10_vacuum_prediction.png`
**Atmospheric data vs. vacuum model prediction**
TEG sum (V_top + V_bot) vs. gap distance. Circles = measured air data. Squares = predicted vacuum glass-glass. Diamonds = predicted vacuum steel-glass. Pink shaded band = predicted rectification signal gap between GG and SG in vacuum (η ≈ 1.02–1.05 predicted). Shows why vacuum was necessary to expose the rectification signal.

---

## Apparatus Diagrams

### `figure_M1_mechanical_stack.png`
**Full thermal stack — annotated cross-section diagram**
Complete layer-by-layer diagram of the Phase 2 kinematic apparatus from top to bottom: Cork insulation → Al 6061 support plate → Graphite TIM → TEG (V_top) → Graphite TIM → Top heater assembly → Al carrier plate → [ACTIVE MICRO-GAP REGION: Steel plate / Micro-gap cavity / Glass slide] → Al carrier plate → Bottom heater assembly → Graphite TIM → TEG (V_bot) → Graphite TIM → Al 6061 support plate → Cork insulation. Orange dashed border highlights the swappable test section.

### `stack_diagram_top_half.png`
Top half of the mechanical stack only (Cork → active micro-gap region). Useful for presentations where full diagram is too tall.

### `stack_diagram_bottom_half.png`
Bottom half of the mechanical stack (active micro-gap region → Cork). Companion to top half.
