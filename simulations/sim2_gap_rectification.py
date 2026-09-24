"""
sim2_gap_rectification.py -- Sim 2: gap-only forward/reverse rectification.

Goal (spec): show that
  * emissivity contrast by itself gives exactly zero rectification,
  * temperature-dependent emissivity gives a few percent in hard vacuum,
  * at 36 Torr the gap produces at most about 0.3% on the Stage 2D grid,
and predict the SIGN, to compare with the measured one.

Setup and sign convention (spec):
  T_h = T_mean + dT/2,  T_c = T_mean - dT/2,  T_mean = 340 K
  Forward = steel hot (A phases).  Reverse = glass hot (B phases).
  R = q_fwd / q_rev - 1   (keep the sign)
  Measured: eta_corrected = 0.9325  ->  R = -6.75% (steel-hot transferred less)

How to run:
    python sim2_gap_rectification.py        (never with -O)
Stages run in order and the script stops if a check fails. Needs mgtd_common.py from Sim 1.

If a check is off by more than 2x, look for a unit error first
(um vs m, Torr vs Pa, C vs K).
"""

import os
import csv
import json
from pathlib import Path
from scipy.integrate import quad
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import mgtd_common as mc
import mgtd_plotstyle as ps

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
RES_DIR = os.path.join(HERE, "results")
FIG_PATH = os.path.join(FIG_DIR, "sim2_rectification.png")
CSV_PATH = os.path.join(RES_DIR, "sim2_rectification.csv")
PAPER_TABLE_PATH = os.path.join(RES_DIR, "sim2_paper_table.csv")

# Measured result
ETA_CORRECTED_MEASURED = 0.9325
R_MEASURED = ETA_CORRECTED_MEASURED - 1.0          # -0.0675

# Stage 2C sweep: eps_steel(T) = 0.20 (T/T_mean)^n ; eps_glass(T) = 0.90 + b (T - T_mean)
N_VALUES_2C = [-0.5, 0.0, 0.5, 1.0, 1.5]
B_VALUES_2C = [0.0, -2e-4]                         # per K
DT_VALUES_2C = [5.0, 10.0, 20.0, 40.0]             # K

# Stage 2D grid (results/sim2_rectification.csv)
N_VALUES_2D = [0.5, 1.0, 1.5]
DT_VALUES_2D = [5.0, 10.0, 20.0]                   # K
P_VALUES_2D_TORR = [760.0, 36.0, 7.5e-3, 7.5e-6]

# Paper table: R_total at these pressures, n values and dT values
P_PAPER_TORR = [36.0, 7.5e-6]
DT_PAPER = [10.0, 20.0]

# Figure: R_total vs pressure for n = 1 at these dT values
FIG_N = 1.0
FIG_DT = [10.0, 20.0]
FIG_SIZE_IN = (ps.COLUMN_WIDTH_IN, 2.9)            # one paper column
FIG_BAND_N = (0.5, 1.5)                            # uncertainty band on n, at FIG_DT[-1]


# ---------------------------------------------------------------------------
# Temperatures and properties
# ---------------------------------------------------------------------------
def surface_temperatures(dT, T_mean=mc.T_MEAN):
    """Return (T_h, T_c) = (T_mean + dT/2, T_mean - dT/2), in K."""
    dT, T_mean = float(dT), float(T_mean)
    if not np.isfinite(dT) or not np.isfinite(T_mean) or dT <= 0 or T_mean-dT/2 <= 0:
        raise ValueError("Require positive dT and positive absolute surface temperatures")
    return T_mean+dT/2, T_mean-dT/2


def eps_steel_T(T, n, eps0=mc.EPS_STEEL, T_ref=mc.T_MEAN):
    """Steel emissivity at temperature T:  eps0 x (T / T_ref)^n."""
    T, T_ref = float(T), float(T_ref)
    if not np.isfinite(T) or not np.isfinite(T_ref) or T <= 0 or T_ref <= 0:
        raise ValueError("Temperatures must be finite and positive")
    value = eps0 * (T/T_ref)**n
    if not np.isfinite(value) or not 0 < value <= 1:
        raise ValueError("Steel emissivity model is outside (0, 1]")
    return value


def eps_glass_T(T, b, eps0=mc.EPS_GLASS, T_ref=mc.T_MEAN):
    """Glass emissivity at temperature T:  eps0 + b (T - T_ref)."""
    T, T_ref = float(T), float(T_ref)
    if not np.isfinite(T) or not np.isfinite(T_ref) or T <= 0 or T_ref <= 0:
        raise ValueError("Temperatures must be finite and positive")
    value = eps0 + b*(T-T_ref)
    if not np.isfinite(value) or not 0 < value <= 1:
        raise ValueError("Glass emissivity model is outside (0, 1]")
    return value


# ---------------------------------------------------------------------------
# Stage 2A -- gas conduction between fixed temperatures
# ---------------------------------------------------------------------------
def q_gas_continuum(T_plate1, T_plate2, d=mc.D_GAP):
    """Continuum gas heat flux FROM plate 1 TO plate 2, W/m^2.

        q = (1/d) x integral of k_air(T) dT from T_plate2 to T_plate1

    Use scipy.integrate.quad with mc.k_air. Positive when plate 1 is hotter.
    """
    if not all(np.isfinite(x) and x > 0 for x in (T_plate1, T_plate2, d)):
        raise ValueError("Temperatures and gap must be finite and positive")
    integral, _ = quad(mc.k_air, T_plate2, T_plate1, epsabs=1e-12, epsrel=1e-12)
    return integral/d


# ---------------------------------------------------------------------------
# Stages 2B-2C -- radiation only
# ---------------------------------------------------------------------------
def q_rad_gray(T_h, T_c, eps_hot, eps_cold):
    """Net radiative flux hot -> cold between gray parallel plates, W/m^2.

        q_rad = sigma (T_h^4 - T_c^4) / (1/eps_hot + 1/eps_cold - 1)

    eps_hot is the hot surface's emissivity AT T_h; eps_cold is the cold
    surface's emissivity AT T_c.
    """
    if not all(np.isfinite(x) and x > 0 for x in (T_h, T_c)) or T_h < T_c:
        raise ValueError("Require T_h >= T_c > 0")
    # Factored fourth-power difference avoids subtracting nearly equal powers.
    delta_fourth = (T_h-T_c)*(T_h+T_c)*(T_h*T_h+T_c*T_c)
    return float(mc.SIGMA * delta_fourth * mc.eps_eff(eps_hot, eps_cold))


def rad_fluxes(dT, n, b, T_mean=mc.T_MEAN):
    """Return (q_fwd, q_rev), radiation only, W/m^2.

    Forward: steel at T_h, glass at T_c.  Reverse: glass at T_h, steel at T_c.
    Each emissivity is taken at its own surface temperature.
    """
    T_h, T_c = surface_temperatures(dT, T_mean)
    q_fwd = q_rad_gray(T_h, T_c, eps_steel_T(T_h, n), eps_glass_T(T_c, b))
    q_rev = q_rad_gray(T_h, T_c, eps_glass_T(T_h, b), eps_steel_T(T_c, n))
    return q_fwd, q_rev


def rectification(q_fwd, q_rev):
    """R = q_fwd / q_rev - 1. Keep the sign."""
    if not np.isfinite(q_fwd) or not np.isfinite(q_rev) or q_fwd <= 0 or q_rev <= 0:
        raise ValueError("Directional hot-to-cold flux magnitudes must be finite and positive")
    return q_fwd/q_rev-1


def rad_rectification(dT, n, b=0.0):
    """R_rad for steel-glass, radiation only."""
    return rectification(*rad_fluxes(dT, n, b))


# ---------------------------------------------------------------------------
# Stage 2D -- radiation + gas in parallel
# ---------------------------------------------------------------------------
def total_fluxes(dT, n, b, p):
    """Return (q_fwd, q_rev) with gas added, W/m^2.

        q_total = q_rad + G_gas(p) x dT      (G_gas from mgtd_common, at T_mean)

    p in Pa.
    """
    q_fwd, q_rev = rad_fluxes(dT, n, b)
    gas = float(mc.g_gas(p))*dT
    return q_fwd+gas, q_rev+gas


def total_rectification(dT, n, b, p):
    """R_total for steel-glass at pressure p (Pa)."""
    return rectification(*total_fluxes(dT, n, b, p))


def rectification_rows():
    """One dict per (n, dT, p) in the Stage 2D grid, b = 0. Suggested keys:
        n, dT_K, pressure_Torr, pressure_Pa, R_rad, f_rad, R_total
    (f_rad for steel-glass at that pressure, from Sim 1's definition).
    """
    rows = []
    rad = float(mc.g_rad(mc.EPS_STEEL, mc.EPS_GLASS))
    for n in N_VALUES_2D:
        for dT in DT_VALUES_2D:
            rf, rr = rad_fluxes(dT, n, 0.)
            for p_torr in P_VALUES_2D_TORR:
                p = float(mc.torr_to_pa(p_torr))
                gas = float(mc.g_gas(p))
                tf, tr = total_fluxes(dT, n, 0., p)
                rows.append(dict(n=n, b_per_K=0., dT_K=dT, pressure_Torr=p_torr,
                                 pressure_Pa=p, R_rad=rectification(rf, rr),
                                 f_rad=rad/(rad+gas), f_rad_reverse=rr/tr,
                                 R_total=rectification(tf, tr),
                                 q_rad_fwd_W_m2=rf, q_rad_rev_W_m2=rr,
                                 q_gas_W_m2=gas*dT, q_total_fwd_W_m2=tf, q_total_rev_W_m2=tr))
    return rows


def write_rectification_csv(rows, path=CSV_PATH):
    """Write results/sim2_rectification.csv."""
    if not rows:
        raise ValueError("Cannot export an empty table")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_paper_table(path=PAPER_TABLE_PATH):
    """Paper deliverable: R_total at 36 Torr and 7.5e-6 Torr for
    n = 0.5, 1.0, 1.5 and dT = 10, 20 K (b = 0). Write as CSV, in percent."""
    rows = []
    for n in N_VALUES_2D:
        for dT in DT_PAPER:
            row = dict(n=n, b_per_K=0., dT_K=dT)
            for p in P_PAPER_TORR:
                row[f"R_total_percent_at_{p:g}_Torr"] = 100*total_rectification(dT,n,0.,float(mc.torr_to_pa(p)))
            rows.append(row)
    write_rectification_csv(rows, path)


def make_figure(path=FIG_PATH):
    """R_total (%) vs pressure for steel-glass, one paper column wide.

    Lines: n = FIG_N at each dT in FIG_DT. Shaded band: n from FIG_BAND_N[0]
    to FIG_BAND_N[1] at the largest dT, because steel's n is not known.
    The measured value is drawn as a point at 36 Torr, where it was taken.
    Also writes results/sim2_pressure_sweep.csv (every plotted value).
    Saved as PNG (300 DPI), PDF and SVG.
    """
    ps.apply_style()
    fig, ax = plt.subplots(figsize=FIG_SIZE_IN, layout="constrained")
    pressures = np.geomspace(1e-6, 760., 400)
    p_pa = [float(mc.torr_to_pa(p)) for p in pressures]
    sweep_rows = []

    def curve(n, dT):
        vals = [100*total_rectification(dT, n, 0., p) for p in p_pa]
        sweep_rows.extend(dict(n=n, b_per_K=0., dT_K=dT, pressure_Torr=float(p),
                               R_total_percent=float(v)) for p, v in zip(pressures, vals))
        return np.array(vals)

    dT_band = FIG_DT[-1]
    lo, hi = curve(FIG_BAND_N[0], dT_band), curve(FIG_BAND_N[1], dT_band)
    ax.fill_between(pressures, lo, hi, color=ps.PAIR_COLOR["steel-glass"], alpha=0.14, lw=0,
                    label=f"n = {FIG_BAND_N[0]:g}–{FIG_BAND_N[1]:g}, ΔT = {dT_band:g} K")
    shades = {FIG_DT[-1]: ("#D55E00", "-"), FIG_DT[0]: ("#8C3A00", "--")}
    for dT in sorted(FIG_DT, reverse=True):
        color, style = shades.get(dT, ("#D55E00", ":"))
        ax.semilogx(pressures, curve(FIG_N, dT), color=color, ls=style, lw=1.5,
                    label=f"n = {FIG_N:g}, ΔT = {dT:g} K")

    ax.axhline(0, color=ps.MUTED, lw=0.6, zorder=1)
    ax.plot(36.0, 100*R_MEASURED, "s", ms=5, color=ps.INK, zorder=6,
            label=f"Measured at 36 Torr ({100*R_MEASURED:.2f}%)".replace("-", "−"))
    ps.draw_ref_lines(ax, [r for r in ps.REF_LINES_TORR if r[1] in ("Vacuum runs", "Scroll floor", "Chamber spec")])

    ax.set_xscale("log")
    ax.set(xlabel="Absolute pressure (Torr)", ylabel="Rectification, R (%)",
           xlim=(1e-6, 760), ylim=(-8, 10))
    ax.grid(axis="y", alpha=ps.GRID_ALPHA)
    ax.legend(loc="lower left")
    ps.save_figure(fig, path)
    write_rectification_csv(sweep_rows, os.path.join(RES_DIR, "sim2_pressure_sweep.csv"))


# ---------------------------------------------------------------------------
# Checks -- one function per stage. Do not loosen a tolerance to make a
# check pass; find the bug instead.
# ---------------------------------------------------------------------------
def check_setup():
    T_h, T_c = surface_temperatures(20.0)
    assert abs(T_h - 350.0) < 1e-12 and abs(T_c - 330.0) < 1e-12, "T_h, T_c for dT = 20 K should be 350, 330 K"
    assert eps_steel_T(mc.T_MEAN, 1.0) == mc.EPS_STEEL
    assert eps_glass_T(mc.T_MEAN, -2e-4) == mc.EPS_GLASS
    assert abs(eps_steel_T(2 * mc.T_MEAN, 1.0) - 2 * mc.EPS_STEEL) < 1e-12
    assert abs(eps_glass_T(mc.T_MEAN + 100, -2e-4) - (mc.EPS_GLASS - 0.02)) < 1e-12
    assert abs(R_MEASURED - (-0.0675)) < 1e-12


def check_2a():
    """Stage 2A: gas conduction never rectifies between fixed temperatures."""
    out = {}
    for dT in (5.0, 20.0, 60.0):
        T_h, T_c = surface_temperatures(dT)
        q_fwd = q_gas_continuum(T_h, T_c)          # plate 1 hot
        q_rev = -q_gas_continuum(T_c, T_h)         # plate 2 hot, flux 2 -> 1
        assert q_fwd > 0, "gas heat must flow from hot to cold"
        assert abs(q_fwd / q_rev - 1.0) < 1e-12, (
            f"dT = {dT} K: q_fwd = {q_fwd:.15g}, q_rev = {q_rev:.15g}; must match to 1e-12")
        # Sanity: close to k(T_mean) dT / d (k_air bends only slightly over dT)
        linear = float(mc.k_air(mc.T_MEAN)) * dT / mc.D_GAP
        assert abs(q_fwd / linear - 1.0) < 1e-3, f"dT = {dT} K: integral {q_fwd:.4g} vs k dT/d {linear:.4g}"
        out[f"q_gas_dT{dT:g}"] = q_fwd
    return out


def check_2b():
    """Stage 2B: constant emissivities give zero rectification."""
    worst = 0.0
    for dT in range(1, 61):
        q_fwd, q_rev = rad_fluxes(float(dT), n=0.0, b=0.0)
        assert q_fwd > 0 and q_rev > 0
        R = rectification(q_fwd, q_rev)
        worst = max(worst, abs(R))
        assert abs(R) < 1e-12, f"dT = {dT} K: |R| = {abs(R):.3g}; must be < 1e-12 with constant emissivity"
    # The flux itself should match G_rad x dT closely for small dT
    q_fwd, _ = rad_fluxes(1.0, n=0.0, b=0.0)
    g = float(mc.g_rad(mc.EPS_STEEL, mc.EPS_GLASS))
    assert abs(q_fwd / g - 1.0) < 1e-4, f"q_rad(dT = 1 K) = {q_fwd:.4f}; expected G_rad x 1 K = {g:.4f}"
    return {"max_abs_R": worst}


def check_2c():
    """Stage 2C: temperature-dependent emissivity, radiation only."""
    table = {}
    for n in N_VALUES_2C:
        for b in B_VALUES_2C:
            for dT in DT_VALUES_2C:
                table[(n, b, dT)] = rad_rectification(dT, n, b)

    # R_rad ~ n dT / T_mean for b = 0 (within 10% of that estimate)
    for n in N_VALUES_2C:
        for dT in DT_VALUES_2C:
            R = table[(n, 0.0, dT)]
            est = n * dT / mc.T_MEAN
            if n == 0.0:
                assert abs(R) < 1e-12, f"n = 0, b = 0 must give zero, got {R:.3g}"
            else:
                assert abs(R / est - 1.0) <= 0.10, (
                    f"n = {n}, dT = {dT} K: R_rad = {100*R:.3f}%; expected ~{100*est:.3f}%")
                assert np.sign(R) == np.sign(n), "sign of R_rad must follow the sign of n"

    # Spec example: n = 1, dT = 20 K gives about +6%
    R = table[(1.0, 0.0, 20.0)]
    assert 0.055 <= R <= 0.065, f"n = 1, dT = 20 K: R_rad = {100*R:.2f}%; expected about +6%"

    # R grows with dT for n > 0
    for n in (0.5, 1.0, 1.5):
        vals = [table[(n, 0.0, dT)] for dT in DT_VALUES_2C]
        assert all(np.diff(vals) > 0)
    write_rectification_csv([
        dict(n=n, b_per_K=b, dT_K=dT, R_rad=value,
             q_rad_fwd_W_m2=rad_fluxes(dT,n,b)[0],
             q_rad_rev_W_m2=rad_fluxes(dT,n,b)[1])
        for (n,b,dT),value in table.items()
    ], os.path.join(RES_DIR,"sim2_radiation_only.csv"))
    return {"R_rad_n1_dT20": R}


def check_2d(rows):
    """Stage 2D: radiation + gas at each pressure."""
    p36 = float(mc.torr_to_pa(36.0))
    p_hv = float(mc.torr_to_pa(7.5e-6))

    R36 = total_rectification(20.0, 1.0, 0.0, p36)
    Rhv = total_rectification(20.0, 1.0, 0.0, p_hv)
    assert 0.0012 <= R36 <= 0.0025, f"n = 1, dT = 20 K, 36 Torr: R_total = {100*R36:.3f}%; expected about +0.2%"
    assert 0.055 <= Rhv <= 0.065, f"n = 1, dT = 20 K, 7.5e-6 Torr: R_total = {100*Rhv:.2f}%; expected about +6%"

    # R_total ~ R_rad x f_rad (within 10%)
    r = float(mc.g_rad(mc.EPS_STEEL, mc.EPS_GLASS))
    f36 = r / (r + float(mc.g_gas(p36)))
    approx = rad_rectification(20.0, 1.0) * f36
    assert abs(R36 / approx - 1.0) <= 0.10, f"R_total {100*R36:.3f}% vs R_rad x f_rad {100*approx:.3f}%"

    # At 36 Torr the gap alone produces at most about 0.3% anywhere on the grid
    worst36 = max(abs(total_rectification(dT, n, 0.0, p36))
                  for n in N_VALUES_2D for dT in DT_VALUES_2D)
    assert worst36 <= 0.003, f"max |R_total| at 36 Torr = {100*worst36:.3f}%; spec says at most ~0.3%"

    # Grid is complete: 3 n x 3 dT x 4 pressures
    assert len(rows) == len(N_VALUES_2D) * len(DT_VALUES_2D) * len(P_VALUES_2D_TORR)
    # Every CSV row agrees with the functions (catches Torr/Pa mix-ups in the table)
    for row in rows:
        p_pa = float(mc.torr_to_pa(row["pressure_Torr"]))
        assert abs(row["pressure_Pa"] / p_pa - 1.0) < 1e-12, f"row {row}: pressure_Pa is not pressure_Torr in Pa"
        expect = total_rectification(row["dT_K"], row["n"], 0.0, p_pa)
        assert abs(row["R_total"] - expect) <= 1e-12 + 1e-9 * abs(expect), f"row {row}: R_total mismatch"
        # The dilution identity is exact with the reverse-direction fraction.
        assert abs(row["R_total"]-row["R_rad"]*row["f_rad_reverse"]) < 1e-12
        if row["pressure_Torr"] == 36.0:
            assert abs(row["R_total"]) <= 0.003, f"row {row}: above 0.3% at 36 Torr"

    for path in (CSV_PATH, PAPER_TABLE_PATH, FIG_PATH):
        assert os.path.isfile(path), f"{os.path.relpath(path, HERE)} was not written"
    return {"R_total_36Torr": R36, "R_total_7.5e-6Torr": Rhv, "max_abs_R_36Torr": worst36}


def check_limits():
    """Independent gas integral and limiting/symmetry checks."""
    for dT in (1.,20.,60.):
        hot,cold = surface_temperatures(dT)
        analytic = float(mc.k_air(300))/(300**.8*1.8*mc.D_GAP)*(hot**1.8-cold**1.8)
        assert abs(q_gas_continuum(hot,cold)/analytic-1) < 1e-12
        for p in (0.,1.,float(mc.torr_to_pa(36)),float(mc.torr_to_pa(760))):
            assert abs(total_rectification(dT,0.,0.,p)) < 1e-12
        assert abs(total_rectification(dT,1.,0.,0.)-rad_rectification(dT,1.)) < 1e-12
    # Negative n predicts negative rectification; do not erase its sign.
    assert total_rectification(20.,-.5,0.,float(mc.torr_to_pa(36))) < 0
    for n in N_VALUES_2D:
        values = [total_rectification(20.,n,0.,float(mc.torr_to_pa(p)))
                  for p in sorted(P_VALUES_2D_TORR)]
        assert np.all(np.diff(values) < 0)
    return {"gas_integral_analytic_check": "passed", "symmetry_and_pressure_limits": "passed"}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    if not __debug__:
        raise RuntimeError("Run without -O: the check asserts must stay enabled")
    os.makedirs(FIG_DIR, exist_ok=True)
    os.makedirs(RES_DIR, exist_ok=True)

    stages = [
        ("Setup: temperatures and emissivity models", check_setup),
        ("Stage 2A: gas never rectifies", check_2a),
        ("Stage 2B: constant emissivity gives zero", check_2b),
        ("Stage 2C: temperature-dependent emissivity", check_2c),
        ("Independent limits and symmetry", check_limits),
    ]
    diagnostics = {"status": "all assertions passed", "R_measured": R_MEASURED}
    for name, check in stages:
        try:
            out = check()
        except NotImplementedError as e:
            print(f"STOP at {name}: not written yet ({e})")
            return
        print(f"PASS {name}" + (f"  {out}" if out else ""))
        diagnostics[name] = out

    try:
        rows = rectification_rows()
        write_rectification_csv(rows)
        write_paper_table()
        make_figure()
        out = check_2d(rows)
    except NotImplementedError as e:
        print(f"STOP at Stage 2D: not written yet ({e})")
        return
    print(f"PASS Stage 2D: radiation + gas  {out}")
    diagnostics["Stage 2D"] = out
    with open(os.path.join(RES_DIR,"sim2_checks.json"),"w") as f:
        json.dump(diagnostics,f,indent=2)
        f.write("\n")

    # Report the sign as found -- whatever it is.
    R = total_rectification(20.0, 1.0, 0.0, float(mc.torr_to_pa(7.5e-6)))
    same = np.sign(R) == np.sign(R_MEASURED)
    print(f"Sign check (n = 1, dT = 20 K, hard vacuum): model R = {100*R:+.2f}%, "
          f"measured R = {100*R_MEASURED:+.2f}% -> {'same' if same else 'OPPOSITE'} sign")


if __name__ == "__main__":
    main()
