"""
mgtd_common.py -- shared constants and physics for the MGTD simulations.

Sims 1, 2 and 3 all import from this file. No other script should hard-code
its own copy of a constant.

Units: SI everywhere inside the code (m, Pa, K, W). Convert only for
plot labels. Conductances are per unit area (W/m^2K).
The gas bridge (Stage 1D) is an interpolation, not an exact
transition-regime solution.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Constants (spec: "Shared parameters")
# ---------------------------------------------------------------------------
SIGMA = 5.670e-8          # Stefan-Boltzmann constant, W/m^2K^4
K_B = 1.380649e-23        # Boltzmann constant, J/K
R_GAS = 8.314             # Gas constant, J/mol.K
M_AIR = 0.02897           # Molar mass of air, kg/mol
GAMMA = 1.40              # Heat-capacity ratio of air
PR = 0.71                 # Prandtl number of air
D_M = 3.7e-10             # Effective molecular diameter of air, m
ALPHA = 0.9               # Thermal accommodation coefficient (range 0.8-1.0)

EPS_GLASS = 0.90          # Soda-lime glass
EPS_STEEL = 0.20          # Mild steel (range 0.10-0.30; depends on finish)
EPS_GOLD = 0.02           # Gold-coated glass (ISEF Phase 1 pair)
EPS_CERAMIC = 0.95        # Ceramic (ISEF Phase 1 pair)

D_GAP = 508e-6            # Gap for all rectification runs, m
T_MEAN = 340.0            # Mean gap temperature, K (paper section 2.7)
AREA = 1.6e-3             # 40 x 40 mm active window, m^2
P_HEATER = 13.8           # W (12.00 V x 1.151 A -- confirm one heater assembly)

# Pressure conversions
TORR_TO_PA = 133.322      # 1 Torr in Pa
MBAR_TO_PA = 100.0        # 1 mbar in Pa
ATM_TO_PA = 101325.0      # 1 standard atmosphere in Pa
INHG_STD_ATM = 29.92      # Standard atmosphere, inHg
INHG_TO_TORR = 25.4       # 1 inHg = 25.4 Torr


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def _positive(value, name):
    """Return value as a float array; raise if any entry is not finite and > 0."""
    a = np.asarray(value, dtype=float)
    if np.any(~np.isfinite(a)) or np.any(a <= 0):
        raise ValueError(f"{name} must be finite and positive")
    return a


def _accommodation(alpha):
    """Accommodation coefficient must be in (0, 1]."""
    alpha = _positive(alpha, "accommodation coefficient")
    if np.any(alpha > 1):
        raise ValueError("accommodation coefficient must be at most one")
    return alpha


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------
def torr_to_pa(p_torr):
    """Torr -> Pa."""
    return np.asarray(p_torr) * TORR_TO_PA


def pa_to_torr(p_pa):
    """Pa -> Torr."""
    return np.asarray(p_pa) / TORR_TO_PA


def mbar_to_pa(p_mbar):
    """mbar -> Pa."""
    return np.asarray(p_mbar) * MBAR_TO_PA


def gauge_to_abs_torr(gauge_inhg, p_atm_inhg=INHG_STD_ATM):
    """Absolute pressure in Torr from a vacuum-gauge reading.

    A vacuum gauge reads relative to local air pressure:
        p_abs (Torr) = (p_atm - gauge reading) x 25.4, both in inHg.
    """
    return (np.asarray(p_atm_inhg) - np.asarray(gauge_inhg)) * INHG_TO_TORR


# ---------------------------------------------------------------------------
# Gas properties
# ---------------------------------------------------------------------------
def k_air(T=T_MEAN):
    """Thermal conductivity of air, W/m.K:  k = 0.0263 x (T / 300 K)^0.8.

    Expect 0.0291 at 340 K.
    """
    return 0.0263 * (_positive(T, "temperature") / 300.0) ** 0.8


def mean_free_path(p, T=T_MEAN):
    """Mean free path of air, m, at pressure p (Pa) and temperature T (K).

        lambda = k_B T / (sqrt(2) pi d_m^2 p)
    """
    return K_B * _positive(T, "temperature") / (
        np.sqrt(2) * np.pi * D_M**2 * _positive(p, "pressure"))


# ---------------------------------------------------------------------------
# Radiation (Stage 1A)
# ---------------------------------------------------------------------------
def eps_eff(eps1, eps2):
    """Effective emissivity of two parallel gray plates.

        eps_eff = 1 / (1/eps1 + 1/eps2 - 1)
    """
    e1, e2 = _positive(eps1, "emissivity"), _positive(eps2, "emissivity")
    if np.any(e1 > 1) or np.any(e2 > 1):
        raise ValueError("emissivity must be at most one")
    return 1.0 / (1.0 / e1 + 1.0 / e2 - 1.0)


def g_rad(eps1, eps2, T=T_MEAN):
    """Linearized radiative conductance, W/m^2K.

        G_rad = 4 eps_eff sigma T^3
    """
    return 4.0 * eps_eff(eps1, eps2) * SIGMA * _positive(T, "temperature") ** 3


# ---------------------------------------------------------------------------
# Gas conduction (Stages 1B-1D)
# ---------------------------------------------------------------------------
def temp_jump_distance(p, T=T_MEAN, alpha=ALPHA):
    """Temperature-jump distance g at each wall, m (continuum regime).

        g = (2 - alpha)/alpha * 2 gamma/(gamma + 1) * lambda / Pr
    """
    alpha = _accommodation(alpha)
    return (2 - alpha) / alpha * 2 * GAMMA / (GAMMA + 1) * mean_free_path(p, T) / PR


def g_cont(p, T=T_MEAN, d=D_GAP, k=None, alpha=ALPHA):
    """Continuum-regime gas conductance with temperature jump, W/m^2K.

        G_cont = k_air(T) / (d + 2 g)

    k: pass a number (e.g. 0.026, the value the paper used) to override
       k_air(T). Leave as None to use k_air(T).
    """
    k = k_air(T) if k is None else _positive(k, "conductivity")
    return k / (_positive(d, "gap") + 2 * temp_jump_distance(p, T, alpha))


def h_fm(p, T=T_MEAN, alpha=ALPHA):
    """Free-molecular conductance, W/m^2K (proportional to p).

        h_FM = alpha/(2 - alpha) * (gamma + 1)/(gamma - 1)
               * p * sqrt(R / (8 pi M_air T))
    """
    alpha = _accommodation(alpha)
    p = np.asarray(p, dtype=float)
    if np.any(~np.isfinite(p)) or np.any(p < 0):
        raise ValueError("pressure must be finite and nonnegative")
    return (alpha / (2 - alpha) * (GAMMA + 1) / (GAMMA - 1) * p
            * np.sqrt(R_GAS / (8 * np.pi * M_AIR * _positive(T, "temperature"))))


def g_gas(p, T=T_MEAN, d=D_GAP, alpha=ALPHA):
    """Gas conductance at any pressure, W/m^2K: the two limits in series.

        1 / G_gas = d / k_air(T) + 1 / h_FM

    Written as h / (1 + h d / k), which is the same thing algebraically but
    also works at p = 0 (gives 0 instead of dividing by zero).
    Works when p is a numpy array (Stage 1E sweeps 500 pressures).
    """
    h = h_fm(p, T, alpha)
    return h / (1 + h * _positive(d, "gap") / k_air(T))


# ---------------------------------------------------------------------------
# Checks for this file (spec: "Shared functions", "Pressure conversions")
# ---------------------------------------------------------------------------
def check_common():
    # Unit helpers
    assert abs(torr_to_pa(1.0) - 133.322) < 1e-9
    assert abs(pa_to_torr(torr_to_pa(36.0)) - 36.0) < 1e-9
    assert abs(pa_to_torr(MBAR_TO_PA) - 0.750) < 0.001, "1 mbar should be 0.750 Torr"

    # Vacuum gauge: 28.5 inHg -> 36 Torr, 29.5 inHg -> 10.7 Torr
    assert abs(gauge_to_abs_torr(28.5) - 36.0) < 0.2
    assert abs(gauge_to_abs_torr(29.5) - 10.7) < 0.1

    # Air conductivity
    assert abs(k_air(300.0) - 0.0263) < 1e-6
    assert abs(k_air(340.0) - 0.0291) < 0.0001

    # Mean free path at 1 atm, 300 K: 67 nm +/- 5 nm
    lam = float(mean_free_path(ATM_TO_PA, 300.0))
    assert abs(lam - 67e-9) <= 5e-9, f"lambda(1 atm, 300 K) = {lam:.3e} m; expected 67 nm"

    print("mgtd_common checks: all passed")


if __name__ == "__main__":
    check_common()
