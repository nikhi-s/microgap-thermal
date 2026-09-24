"""
sim1_pressure.py -- Sim 1: gap heat transfer vs. pressure.

Goal (spec): show that at 36 Torr, gas conduction across the 508 um gap is
still ~99% of its atmospheric value, so radiation carries only ~11%
(glass-glass) and ~3% (steel-glass) of the gap heat.

How to run:
    python sim1_pressure.py        (never with -O: that strips the asserts)
The script runs the stages in order and stops at the first stage whose
check fails. Every spec "Check" is an assert below, so a unit error fails
loudly.

Outputs:
    figures/sim1_pressure.png (300 DPI), .pdf and .svg
    results/sim1_key_values.csv    key numbers quoted in the paper
    results/sim1_pressure_sweep.csv  the 500-point sweep behind the figure

"""

import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import brentq

import mgtd_common as mc
import mgtd_plotstyle as ps

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
RES_DIR = os.path.join(HERE, "results")
FIG_PATH = os.path.join(FIG_DIR, "sim1_pressure.png")
CSV_PATH = os.path.join(RES_DIR, "sim1_key_values.csv")
SWEEP_CSV_PATH = os.path.join(RES_DIR, "sim1_pressure_sweep.csv")

# The three surface pairs (eps1, eps2)
PAIRS = {
    "glass-glass": (mc.EPS_GLASS, mc.EPS_GLASS),
    "steel-glass": (mc.EPS_STEEL, mc.EPS_GLASS),
    "gold-ceramic": (mc.EPS_GOLD, mc.EPS_CERAMIC),
}

# Dashed vertical reference lines: (pressure in Torr, short label, CSV label)
REF_LINES_TORR = [
    (760.0, "Air", "760 Torr (air runs)"),
    (36.0, "Vacuum", "36 Torr (vacuum runs)"),
    (10.7, "A2", "10.7 Torr (A2 phase)"),
    (7.5e-3, "Scroll floor", "Scroll-pump floor (1e-2 mbar)"),
    (7.5e-6, "Chamber spec", "New chamber spec (1e-5 mbar)"),
]

# Figure: full page width so 8 pt text stays 8 pt (style in mgtd_plotstyle.py)
FIG_SIZE_IN = (ps.FULL_WIDTH_IN, 3.4)

# Stage 1B: the paper used k = 0.026. None = use k_air(T) (~0.0291 at 340 K);
# 0.026 = reproduce the paper. Say which in section 2.7.
K_OVERRIDE = None

# Crossover search range for brentq, Pa
P_SEARCH_MIN = float(mc.torr_to_pa(1e-9))
P_SEARCH_MAX = float(mc.torr_to_pa(760.0))


# ---------------------------------------------------------------------------
# Stage 1E -- sweep, plot and key numbers
# ---------------------------------------------------------------------------
def pressure_sweep_pa():
    """500 log-spaced pressures from 1e-5 to 760 Torr, returned in Pa."""
    return mc.torr_to_pa(np.geomspace(1e-5, 760.0, 500))


def radiation_fraction(p, eps1, eps2):
    """f_rad = G_rad / (G_rad + G_gas) at pressure p (Pa). Works on arrays."""
    r = mc.g_rad(eps1, eps2)
    return r / (r + mc.g_gas(p))


def crossover_pressure_pa(eps1, eps2, target):
    """Pressure (Pa) where f_rad == target (e.g. 0.5 or 0.9).

    brentq on log(p), not on p itself.
    """
    root = brentq(lambda log_p: radiation_fraction(np.exp(log_p), eps1, eps2) - target,
                  np.log(P_SEARCH_MIN), np.log(P_SEARCH_MAX))
    return float(np.exp(root))


def key_values():
    """Return a dict keyed by pair name, each holding:
        f_rad_760, f_rad_36, f_rad_1pa      (fractions, 0-1)
        p50_torr, p90_torr                  (crossover pressures, Torr)
    """
    p760, p36 = mc.torr_to_pa(760.0), mc.torr_to_pa(36.0)
    out = {}
    for name, (e1, e2) in PAIRS.items():
        out[name] = {
            "f_rad_760": float(radiation_fraction(p760, e1, e2)),
            "f_rad_36": float(radiation_fraction(p36, e1, e2)),
            "f_rad_1pa": float(radiation_fraction(1.0, e1, e2)),
            "p50_torr": float(mc.pa_to_torr(crossover_pressure_pa(e1, e2, 0.5))),
            "p90_torr": float(mc.pa_to_torr(crossover_pressure_pa(e1, e2, 0.9))),
        }
    return out


def _write_rows(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_key_values_csv(values, path=CSV_PATH):
    """Write results/sim1_key_values.csv: every reference pressure, 1 Pa,
    and the 50% / 90% crossovers, for each pair."""
    rows = []
    conditions = [(label, float(mc.torr_to_pa(p))) for p, _, label in REF_LINES_TORR]
    conditions.append(("Exactly 1 Pa (1e-2 mbar)", 1.0))
    for name, (e1, e2) in PAIRS.items():
        r = float(mc.g_rad(e1, e2))
        for label, p in conditions:
            g = float(mc.g_gas(p))
            rows.append(dict(pair=name, condition=label, pressure_Pa=p,
                             pressure_Torr=float(mc.pa_to_torr(p)),
                             G_rad_W_m2K=r, G_gas_W_m2K=g, radiation_fraction=r / (r + g)))
        for fraction, key in [(0.5, "p50_torr"), (0.9, "p90_torr")]:
            p = float(mc.torr_to_pa(values[name][key]))
            rows.append(dict(pair=name, condition=f"Radiation fraction {fraction:.0%}",
                             pressure_Pa=p, pressure_Torr=values[name][key],
                             G_rad_W_m2K=r, G_gas_W_m2K=float(mc.g_gas(p)),
                             radiation_fraction=fraction))
    _write_rows(path, rows)


def write_sweep_csv(path=SWEEP_CSV_PATH):
    """Write the 500-point sweep behind the figure."""
    rows = []
    for p in pressure_sweep_pa():
        g = float(mc.g_gas(p))
        row = {"pressure_Torr": float(mc.pa_to_torr(p)), "pressure_Pa": float(p),
               "G_gas_W_m2K": g}
        for name, pair in PAIRS.items():
            r = float(mc.g_rad(*pair))
            row[f"{name}_G_rad_W_m2K"] = r
            row[f"{name}_radiation_fraction"] = r / (r + g)
        rows.append(row)
    _write_rows(path, rows)


def make_figure(path=FIG_PATH):
    """Two-panel figure for the paper (full page width).

    (a) G_gas and the three G_rad lines vs. pressure, log-log axes.
    (b) Radiation share of the gap heat vs. pressure; legend gives the
        36 Torr value for each pair (open circles).
    Both panels: dashed reference lines. Saved as PNG (300 DPI), PDF and SVG.
    """
    ps.apply_style()
    fig, axes = plt.subplots(1, 2, figsize=FIG_SIZE_IN, layout="constrained")

    # Extend the plotted range to the chamber-spec line (below the 1e-5 Torr sweep).
    plot_torr = np.r_[7.5e-6, mc.pa_to_torr(pressure_sweep_pa())]
    gas = mc.g_gas(mc.torr_to_pa(plot_torr))
    p36 = mc.torr_to_pa(36.0)

    axes[0].loglog(plot_torr, gas, color=ps.INK, lw=1.8, label="Gas conduction")
    for name, pair in PAIRS.items():
        color, style = ps.PAIR_COLOR[name], ps.PAIR_STYLE[name]
        r = float(mc.g_rad(*pair))
        axes[0].axhline(r, color=color, ls=style, lw=1.4, label=f"{ps.PAIR_LABEL[name]} radiation")
        f36 = 100 * float(radiation_fraction(p36, *pair))
        axes[1].semilogx(plot_torr, 100 * r / (r + gas), color=color, ls=style, lw=1.6,
                         label=f"{ps.PAIR_LABEL[name]}: {f36:.1f}%")
        # Open circle where the vacuum runs sit
        axes[1].plot(36.0, f36, "o", ms=4, mfc="white", mec=color, mew=1.1, zorder=5)

    for ax in axes:
        ps.draw_ref_lines(ax)
        ax.set_xlim(5e-6, 1300)
        ax.set_xlabel("Absolute pressure (Torr)")
        ax.grid(which="major", alpha=ps.GRID_ALPHA)

    axes[0].set_ylabel("Conductance per area (W m$^{-2}$ K$^{-1}$)")
    axes[1].set_ylabel("Radiation share of gap heat (%)")
    axes[1].set_ylim(0, 102)
    ps.panel_label(axes[0], "(a)")
    ps.panel_label(axes[1], "(b)", right=True)
    axes[0].legend(loc="lower right")
    axes[1].legend(loc="upper right", bbox_to_anchor=(1.0, 0.88), title="Share at 36 Torr",
                   title_fontsize=6.5)

    ps.save_figure(fig, path)


# ---------------------------------------------------------------------------
# Checks -- one function per stage. Do not loosen a tolerance to make a
# check pass; find the bug instead.
# ---------------------------------------------------------------------------
def check_1a():
    """Stage 1A: radiative conductance for the three pairs."""
    g_gg = float(mc.g_rad(*PAIRS["glass-glass"]))
    g_sg = float(mc.g_rad(*PAIRS["steel-glass"]))
    g_au = float(mc.g_rad(*PAIRS["gold-ceramic"]))
    assert abs(g_gg - 7.3) <= 0.1, f"glass-glass G_rad = {g_gg:.3f}; expected 7.3 +/- 0.1"
    assert abs(g_sg - 1.74) <= 0.05, f"steel-glass G_rad = {g_sg:.3f}; expected 1.74 +/- 0.05"
    assert abs(g_au - 0.18) <= 0.01, f"gold-ceramic G_rad = {g_au:.3f}; expected 0.18 +/- 0.01"
    # eps_eff must be symmetric: swapping the plates changes nothing
    assert mc.eps_eff(0.2, 0.9) == mc.eps_eff(0.9, 0.2)
    return {"glass-glass": g_gg, "steel-glass": g_sg, "gold-ceramic": g_au}


def check_1b():
    """Stage 1B: continuum gas conduction with temperature jump."""
    p36 = mc.torr_to_pa(36.0)
    p760 = mc.torr_to_pa(760.0)

    kn36 = float(mc.mean_free_path(p36, mc.T_MEAN) / mc.D_GAP)
    assert 0.0025 <= kn36 <= 0.0035, f"Kn(36 Torr) = {kn36:.4f}; expected ~0.003"

    g760 = float(mc.g_cont(p760, k=K_OVERRIDE))
    if K_OVERRIDE is None:
        assert 55.0 <= g760 <= 59.0, f"G_cont(760) = {g760:.1f}; expected ~57 with k_air(T)"
    else:
        assert 49.0 <= g760 <= 53.0, f"G_cont(760) = {g760:.1f}; expected ~51 with k = 0.026"

    ratio = float(mc.g_cont(p36, k=K_OVERRIDE) / g760)
    assert 0.98 <= ratio <= 1.00, f"G_cont(36)/G_cont(760) = {ratio:.4f}; expected 0.98-1.00"
    return {"Kn_36": kn36, "G_cont_760": g760, "ratio_36_760": ratio}


def check_1c():
    """Stage 1C: free-molecular limit."""
    per_pa = float(mc.h_fm(1.0) / 1.0)
    assert abs(per_pa - 0.90) <= 0.05, f"h_FM/p = {per_pa:.3f}; expected 0.90 +/- 0.05 W/m^2K per Pa"
    # h_FM must be proportional to pressure
    assert abs(mc.h_fm(2.0) / mc.h_fm(1.0) - 2.0) < 1e-12
    return {"h_FM_per_Pa": per_pa}


def check_1d():
    """Stage 1D: series interpolation across all pressures."""
    p36 = mc.torr_to_pa(36.0)
    rel = float(mc.g_gas(p36) / mc.g_cont(p36) - 1.0)
    assert abs(rel) <= 0.01, f"G_gas vs G_cont at 36 Torr differ by {100*rel:.2f}%; must be within 1%"

    g1 = float(mc.g_gas(1.0))
    assert abs(g1 - 0.89) <= 0.02, f"G_gas(1 Pa) = {g1:.3f}; expected ~0.89"

    # Limits: high pressure -> d/k ; low pressure -> h_FM
    g_hi = mc.g_gas(mc.torr_to_pa(760.0))
    assert abs(g_hi / (mc.k_air(mc.T_MEAN) / mc.D_GAP) - 1.0) < 0.01
    p_lo = 1e-4
    assert abs(mc.g_gas(p_lo) / mc.h_fm(p_lo) - 1.0) < 0.01

    # Must accept arrays and be monotonic in pressure
    p = np.logspace(-3, 5, 50)
    g = mc.g_gas(p)
    assert np.shape(g) == p.shape and np.all(np.diff(g) > 0)

    # Extra checks (from supplied file): wider range, bounded, exact limits
    p_wide = np.geomspace(1e-9, 1e9, 500)
    g_wide = mc.g_gas(p_wide)
    assert np.all(np.diff(g_wide) > 0), "G_gas must rise with pressure"
    assert np.all(g_wide < mc.k_air() / mc.D_GAP), "G_gas can never exceed k/d"
    assert mc.g_gas(0) == 0, "no gas, no conduction"
    assert abs(mc.g_gas(1e-9) / mc.h_fm(1e-9) - 1) < 1e-8
    assert abs(mc.g_gas(1e9) / (mc.k_air() / mc.D_GAP) - 1) < 1e-6
    return {"G_gas_1Pa": g1, "G_gas36_over_G_cont36_minus_1": rel}


# Spec table values ("should land near"). Tolerances: 10% on fractions and
# crossover pressures -- tight enough to catch a real error, loose enough
# for the spec's rounding.
EXPECTED_1E = {
    #               f760   f36    f1Pa   p50 (Torr)  p90 (Torr)
    "glass-glass":  (0.11, 0.11, 0.89, 0.07, 7e-3),
    "steel-glass":  (0.03, 0.03, 0.66, 0.015, 1.6e-3),
    "gold-ceramic": (0.003, 0.003, 0.17, 1.5e-3, 1.6e-4),
}


def check_1e(values):
    """Stage 1E: key values against the spec table, then the output files."""
    keys = ("f_rad_760", "f_rad_36", "f_rad_1pa", "p50_torr", "p90_torr")
    for pair, expected in EXPECTED_1E.items():
        for key, exp in zip(keys, expected):
            got = values[pair][key]
            assert abs(got / exp - 1.0) <= 0.10, (
                f"{pair} {key} = {got:.3g}; expected ~{exp:.3g}. "
                "If off by more than 2x, look for a unit error first."
            )
    # Radiation fraction barely changes between 760 and 36 Torr (<~1 point)
    for pair in PAIRS:
        assert abs(values[pair]["f_rad_36"] - values[pair]["f_rad_760"]) < 0.01

    # Extra check (from supplied file): crossovers against the closed-form
    # answer. With G_gas = h/(1 + h d/k) and h = c p, setting f_rad = F gives
    #   G_gas* = G_rad (1 - F)/F  and  p* = G_gas* / (c (1 - G_gas* d / k)).
    c = float(mc.h_fm(1.0))
    k_over_d = float(mc.k_air() / mc.D_GAP)
    for pair, (e1, e2) in PAIRS.items():
        r = float(mc.g_rad(e1, e2))
        for F, key in [(0.5, "p50_torr"), (0.9, "p90_torr")]:
            g_star = r * (1 - F) / F
            p_star = g_star / (c * (1 - g_star / k_over_d))
            p_found = float(mc.torr_to_pa(values[pair][key]))
            assert abs(p_found / p_star - 1) < 1e-8, f"{pair} {key}: brentq disagrees with closed form"

    assert os.path.isfile(CSV_PATH), "results/sim1_key_values.csv was not written"
    assert os.path.isfile(SWEEP_CSV_PATH), "results/sim1_pressure_sweep.csv was not written"
    assert os.path.isfile(FIG_PATH), "figures/sim1_pressure.png was not written"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    if not __debug__:
        raise RuntimeError("Run without -O: the check asserts must stay enabled")
    os.makedirs(FIG_DIR, exist_ok=True)
    os.makedirs(RES_DIR, exist_ok=True)

    stages = [
        ("mgtd_common", mc.check_common),
        ("Stage 1A: radiative conductance", check_1a),
        ("Stage 1B: continuum gas conduction", check_1b),
        ("Stage 1C: free-molecular limit", check_1c),
        ("Stage 1D: one formula for all pressures", check_1d),
    ]
    for name, check in stages:
        try:
            out = check()
        except NotImplementedError as e:
            print(f"STOP at {name}: not written yet ({e})")
            return
        print(f"PASS {name}" + (f"  {out}" if out else ""))

    values = key_values()
    write_key_values_csv(values)
    write_sweep_csv()
    make_figure()
    check_1e(values)
    print("PASS Stage 1E: sweep, plot and key numbers")
    for pair, v in values.items():
        print(f"  {pair:13s} f_rad 760 Torr {100*v['f_rad_760']:.2f}%  36 Torr {100*v['f_rad_36']:.2f}%  "
              f"1 Pa {100*v['f_rad_1pa']:.1f}%  50% at {v['p50_torr']:.3g} Torr  90% at {v['p90_torr']:.3g} Torr")
    print(f"Figure: {FIG_PATH}\nTables: {CSV_PATH}\n        {SWEEP_CSV_PATH}")


if __name__ == "__main__":
    main()
