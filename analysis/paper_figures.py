#!/usr/bin/env python3
"""
paper_figures.py -- the data and model figures for the TJAS 2026 paper.

Every number is computed from the raw logs in ../data or from the simulation
modules in ../simulations. Nothing is hardcoded. Figures share the style in
simulations/mgtd_plotstyle.py and are written to ../figures/paper/ as
PNG (300 DPI), PDF and SVG.

  fig3_gap_sweep            V_bot and sum vs gap; the warm-up transient
  fig4_pressure_map         gas vs radiation across the gap vs pressure (Sim 1)
  fig5_air_null_artifact    atmospheric null on both metrics; the Seebeck artifact
  fig6_vacuum_result        vacuum phase curves; eta_corrected by metric/window;
                            the glass-glass control's rising forward phase
  fig7_gap_bound            Sim 2: what the gap itself can produce vs dT

Conventions used throughout:
  through-gap channel = V_bot in A phases (top heater), V_top in B phases
  A = steel heated (forward), B = glass heated (reverse); eta = A / B
  eta_corrected = eta(steel-glass) / eta(glass-glass control)

Run from analysis/:  python paper_figures.py
Override paths with MGTD_DATA_DIR / MGTD_OUT_DIR.

"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "simulations"))
import mgtd_common as mc                  # noqa: E402
import mgtd_plotstyle as ps               # noqa: E402
import sim2_gap_rectification as sim2     # noqa: E402
import matplotlib.pyplot as plt           # noqa: E402
from matplotlib.patches import Patch      # noqa: E402
from matplotlib.lines import Line2D       # noqa: E402

DATA_DIR = os.environ.get("MGTD_DATA_DIR", os.path.join(HERE, "..", "data"))
OUT_DIR = os.environ.get("MGTD_OUT_DIR", os.path.join(HERE, "..", "figures", "paper"))

DATA_FILES = {
    "contact_air": "Module-A_contact_G-G_ABBA_16Feb_Control.txt",
    "sg_air":      "Module-D_20mil_S-G_Rectification_19Feb_retake.txt",
    "gg_air":      "Module-E_20mil_G-G_Rectification_20Feb_Control.txt",
    "gg_vac":      "Module-E_20mil_G-G_Rectification_22Feb_control_Vacuum_fixedTime.txt",
    "sg_vac":      "Module-E_20mil_S-G_Rectification_23Feb_Vacuum_fixedTime.txt",
    "sg_vac_a2":   "Module-E_20mil_S-G_Rectification_24Feb_Vacuum_fixedTime_A2_Rerun.txt",
    "sweep_7.62":  "Module-C_1by3Mil_G-G_GapSweep_17Feb.txt",
    "sweep_25.4":  "Module-B_1Mil_G-G_GapSweep_17Feb.txt",
    "sweep_254":   "Module-B_10Mil_G-G_GapSweep_16Feb.txt",
    "sweep_508":   "Module-B_20mil_G-G_GapSweep_20Feb.txt",
}
SWEEP_GAPS = [7.62, 25.4, 254.0, 508.0]
PH = ["A1_FWD_HEAT", "B1_REV_HEAT", "B2_REV_HEAT", "A2_FWD_HEAT"]
GAPCH = {"A1_FWD_HEAT": "vbot", "A2_FWD_HEAT": "vbot", "B1_REV_HEAT": "vtop", "B2_REV_HEAT": "vtop"}

# Colors: directions and conditions keep the same color in every figure
C_A = "#D55E00"      # steel heated / forward
C_B = "#0072B2"      # glass heated / reverse
C_AIR = "#56B4E9"
C_VAC = "#CC79A7"
C_SUM = "#009E73"
C_GAP = "#E69F00"
INK = ps.INK


# --------------------------------------------------------------------------
# Loaders
# --------------------------------------------------------------------------
def path(key):
    p = os.path.join(DATA_DIR, DATA_FILES[key])
    if not os.path.exists(p):
        raise FileNotFoundError(f"Missing raw log for '{key}': {p}")
    return p


def _lines(fp):
    with open(fp, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.replace("\x00", "").strip().replace("\r", "")
            if line and not line.startswith("#"):
                yield line


def load_abba(fp):
    """phase -> arrays dict (t_min within phase, vtop, vbot, tt, tb)."""
    rows = {}
    for line in _lines(fp):
        p = line.split(",")
        if len(p) != 11 or p[1] == "phase":
            continue
        try:
            rows.setdefault(p[1], []).append((int(p[2]) / 60000, float(p[4]), float(p[5]),
                                              float(p[6]), float(p[7]), int(p[0]) / 3.6e6))
        except ValueError:
            continue
    out = {}
    for ph, r in rows.items():
        a = np.array(sorted(r))
        out[ph] = dict(t=a[:, 0], vtop=a[:, 1], vbot=a[:, 2], tt=a[:, 3], tb=a[:, 4], t_abs=a[:, 5])
    return out


def load_sweep(fp):
    """Gap-sweep log: per-run PLATEAU means [(vtop, vbot)] and the run-1 heating trace."""
    runs, trace = {}, []
    for line in _lines(fp):
        p = line.split(",")
        if len(p) != 13:
            continue
        try:
            run, t_ms, vt, vb = int(p[2]), int(p[0]), float(p[5]), float(p[6])
        except ValueError:
            continue
        if p[1] == "PLATEAU":
            runs.setdefault(run, []).append((vt, vb))
        if run == 1 and p[1] in ("HEATING", "PLATEAU"):
            trace.append((t_ms, vt, vb, p[1] == "PLATEAU"))
    means = [(np.mean([v[0] for v in r]), np.mean([v[1] for v in r])) for r in runs.values()]
    tr = np.array([(t, vt, vb, pl) for t, vt, vb, pl in trace], dtype=float)
    tr[:, 0] = (tr[:, 0] - tr[0, 0]) / 60000
    return means, tr


def win(run, ph, t0, t1, metric="gap"):
    """Mean and SD of the through-gap ('gap') or sum metric over t0..t1 min of a phase."""
    d = run[ph]
    v = d[GAPCH[ph]] if metric == "gap" else d["vtop"] + d["vbot"]
    s = (d["t"] >= t0) & (d["t"] <= t1)
    return float(v[s].mean()), float(v[s].std(ddof=1))


def eta(vals, pairing):
    if pairing == "A1/B1":
        return vals["A1_FWD_HEAT"] / vals["B1_REV_HEAT"]
    return (vals["A1_FWD_HEAT"] + vals["A2_FWD_HEAT"]) / (vals["B1_REV_HEAT"] + vals["B2_REV_HEAT"])


def eta_with_ci(run, metric, t0, t1):
    """ABBA eta = mean(A)/mean(B) with a 1.96-sigma CI from the A1-A2 and B1-B2 spread
    (the larger of spread and within-plateau SE, as in uncertainty_analysis.py)."""
    m = {ph: win(run, ph, t0, t1, metric) for ph in PH}
    A = [m["A1_FWD_HEAT"][0], m["A2_FWD_HEAT"][0]]
    B = [m["B1_REV_HEAT"][0], m["B2_REV_HEAT"][0]]
    n = int((t1 - t0) * 60)
    sA = max(np.std(A, ddof=1) / np.sqrt(2), np.hypot(m["A1_FWD_HEAT"][1], m["A2_FWD_HEAT"][1]) / 2 / np.sqrt(n))
    sB = max(np.std(B, ddof=1) / np.sqrt(2), np.hypot(m["B1_REV_HEAT"][1], m["B2_REV_HEAT"][1]) / 2 / np.sqrt(n))
    e = np.mean(A) / np.mean(B)
    return e, e * np.hypot(sA / np.mean(A), sB / np.mean(B))


def save(fig, name):
    ps.save_figure(fig, os.path.join(OUT_DIR, name + ".png"))
    print(f"  saved {name}.png/.pdf/.svg")


# --------------------------------------------------------------------------
# Figure 3: gap sweep and warm-up transient
# --------------------------------------------------------------------------
def fig3_gap_sweep():
    ct = load_abba(path("contact_air"))
    a1 = ct["A1_FWD_HEAT"]; sel = a1["t"] >= a1["t"].max() - 10
    contact = (a1["vtop"][sel].mean(), a1["vbot"][sel].mean())
    gaps, vbot, vsum, ebot, esum, traces = [], [], [], [], [], {}
    for g in SWEEP_GAPS:
        means, tr = load_sweep(path(f"sweep_{g:g}"))
        vb = [m[1] for m in means]; ss = [m[0] + m[1] for m in means]
        gaps.append(g); vbot.append(np.mean(vb)); vsum.append(np.mean(ss))
        ebot.append(np.std(vb, ddof=1)); esum.append(np.std(ss, ddof=1))
        traces[g] = tr
    drop_b = (1 - vbot[-1] / vbot[0]) * 100
    drop_s = (1 - vsum[-1] / vsum[0]) * 100

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(ps.FULL_WIDTH_IN, 2.9))
    ax.errorbar(gaps, vsum, yerr=esum, fmt="s-", color=C_SUM, ms=4, capsize=2, label="Sum, V$_{top}$ + V$_{bot}$")
    ax.errorbar(gaps, vbot, yerr=ebot, fmt="o-", color=C_GAP, ms=4, capsize=2, label="Through-gap, V$_{bot}$")
    ax.plot([2.5], [contact[0] + contact[1]], "s", color=C_SUM, mfc="white", ms=4)
    ax.plot([2.5], [contact[1]], "o", color=C_GAP, mfc="white", ms=4)
    ax.text(2.5, contact[1] + 25, "contact\n(ABBA)", ha="center", fontsize=6, color=INK)
    ax.set_xscale("log"); ax.set_xlim(1.8, 800); ax.set_ylim(150, 1100)
    ax.set_xticks(gaps); ax.set_xticklabels([f"{g:g}" for g in gaps])
    ax.set_xlabel("Gap (µm)"); ax.set_ylabel("TEG voltage (mV)")
    ax.annotate(f"−{drop_b:.0f}% over {gaps[-1]/gaps[0]:.0f}×", xy=(gaps[-1], vbot[-1]), xytext=(40, 200),
                fontsize=7, color=C_GAP, arrowprops=dict(arrowstyle="->", color=C_GAP, lw=0.7))
    ax.annotate(f"−{drop_s:.1f}%", xy=(gaps[-1], vsum[-1]), xytext=(150, 1030), fontsize=7, color=C_SUM,
                arrowprops=dict(arrowstyle="->", color=C_SUM, lw=0.7))
    ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.62)); ax.grid(alpha=ps.GRID_ALPHA)
    ps.panel_label(ax, "(a)")

    for g, col in [(7.62, C_GAP), (508.0, "#8B4513")]:
        tr = traces[g]
        bx.plot(tr[:, 0], tr[:, 2], color=col, label=f"{g:g} µm, run 1")
        pl = tr[tr[:, 3] == 1]
        bx.axvspan(pl[0, 0], pl[-1, 0], color=col, alpha=0.12)
    gg = load_abba(path("gg_air"))["A1_FWD_HEAT"]
    bx.plot(gg["t"], gg["vbot"], color="0.4", ls="--", lw=1, label="508 µm, 40-min ABBA phase")
    bx.set_xlim(0, 40); bx.set_ylim(0, 420)
    bx.set_xlabel("Time after heater on (min)"); bx.set_ylabel("V$_{bot}$ (mV)")
    bx.text(0.03, 0.86, "shaded: firmware plateau windows\n(read ~7–10 min in, still rising)",
            transform=bx.transAxes, ha="left", va="top", fontsize=6, color=INK)
    bx.legend(loc="lower right"); bx.grid(alpha=ps.GRID_ALPHA)
    ps.panel_label(bx, "(b)")
    fig.tight_layout(); save(fig, "fig3_gap_sweep")
    return dict(vbot=vbot, vsum=vsum, drop_b=drop_b, drop_s=drop_s)


# --------------------------------------------------------------------------
# Figure 4: pressure map (Simulation 1) with the February runs and the target
# --------------------------------------------------------------------------
def fig4_pressure_map():
    p_torr = np.logspace(-6, 3, 400); p_pa = mc.torr_to_pa(p_torr)
    g_gas = mc.g_gas(p_pa)
    pairs = [("glass-glass", mc.EPS_GLASS, mc.EPS_GLASS), ("steel-glass", mc.EPS_STEEL, mc.EPS_GLASS),
             ("gold-ceramic", mc.EPS_GOLD, mc.EPS_CERAMIC)]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(ps.FULL_WIDTH_IN, 2.9))
    ax.loglog(p_torr, g_gas, color=INK, lw=1.4, label="Gas conduction, 508 µm")
    for name, e1, e2 in pairs:
        gr = float(mc.g_rad(e1, e2))
        ax.axhline(gr, color=ps.PAIR_COLOR[name], ls=ps.PAIR_STYLE[name], lw=1.2,
                   label=f"Radiation, {ps.PAIR_LABEL[name]}")
        bx.semilogx(p_torr, 100 * gr / (gr + g_gas), color=ps.PAIR_COLOR[name], ls=ps.PAIR_STYLE[name],
                    lw=1.4, label=ps.PAIR_LABEL[name])
    for a in (ax, bx):
        a.axvspan(15, 40, color=C_VAC, alpha=0.18, lw=0)
        a.axvline(760, color=ps.MUTED, ls=":", lw=0.7)
        a.axvline(7.5e-3, color=ps.MUTED, ls=":", lw=0.7)
        a.set_xlim(1e-6, 1e3); a.set_xlabel("Pressure (Torr)"); a.grid(alpha=ps.GRID_ALPHA, which="both")
    ax.set_ylim(1e-3, 3e2); ax.set_ylabel("Conductance per area (W m$^{-2}$ K$^{-1}$)")
    ax.legend(loc="lower right"); ps.panel_label(ax, "(a)")
    bx.set_ylim(0, 100); bx.set_ylabel("Radiation share of gap heat (%)")
    bx.text(25, 62, "Feb 2026 runs\n15–40 Torr", ha="center", fontsize=6, color=C_VAC)
    bx.text(760, 62, "air", ha="center", fontsize=6, color=INK)
    bx.text(7.5e-3, 62, "10⁻² mbar\ntarget", ha="center", fontsize=6, color=INK)
    bx.legend(loc="center left"); ps.panel_label(bx, "(b)")
    fig.tight_layout(); save(fig, "fig4_pressure_map")
    gr_sg = float(mc.g_rad(mc.EPS_STEEL, mc.EPS_GLASS)); gg36 = float(mc.g_gas(mc.torr_to_pa(36.0)))
    return dict(share_sg_36torr=100 * gr_sg / (gr_sg + gg36))


# --------------------------------------------------------------------------
# Figure 5: atmospheric null on both metrics, and the Seebeck artifact
# --------------------------------------------------------------------------
def fig5_air_null_artifact():
    sg, gg = load_abba(path("sg_air")), load_abba(path("gg_air"))
    res = {}
    for metric in ("sum", "gap"):
        es, ss = eta_with_ci(sg, metric, 30, 40)
        eg, sg_ = eta_with_ci(gg, metric, 30, 40)
        ec = es / eg; sc = ec * np.hypot(ss / es, sg_ / eg)
        res[metric] = (ec, 1.96 * sc)
    # heater-plate temperatures: heated plate TC over the last 10 min, steel-glass vs glass-glass
    def heated_T(run):
        """Heated-plate TC (Tt in A phases, Tb in B phases), last 10 min, per phase."""
        return np.array([run[ph]["tt" if ph.startswith("A") else "tb"][run[ph]["t"] >= 30].mean() for ph in PH])
    Tsg, Tgg = heated_T(sg), heated_T(gg)
    T_sg, T_gg = Tsg.mean(), Tgg.mean()
    dT = T_sg - T_gg                        # mean over the four heated phases
    dT_ph = Tsg - Tgg                       # phase-by-phase offsets (A1, B1, B2, A2)
    coef = (0.25, 0.30)                     # Bi2Te3 Seebeck temperature coefficient, %/°C (literature range)
    art_lo, art_hi = dT_ph.min() * coef[0], dT_ph.max() * coef[1]
    measured_gap = (1 - res["gap"][0]) * 100

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(ps.FULL_WIDTH_IN, 2.9), gridspec_kw=dict(width_ratios=[1.1, 1]))
    labels = ["Sum metric", "Through-gap metric"]; keys = ["sum", "gap"]
    for i, (k, lab) in enumerate(zip(keys, labels)):
        e, ci = res[k]
        ax.errorbar(i, e, yerr=ci, fmt="o", color=C_SUM if k == "sum" else C_GAP, ms=6, capsize=4, lw=1.2)
        ax.text(i, e + ci + 0.0015, f"{e:.4f} ± {ci:.4f}", ha="center", fontsize=6.5, color=INK)
    ax.axhline(1.0, color=ps.MUTED, ls="--", lw=0.8)
    ax.set_xticks([0, 1]); ax.set_xticklabels(labels); ax.set_xlim(-0.6, 2.1); ax.set_ylim(0.978, 1.010)
    ax.set_ylabel("η$_{corrected}$ in air (95% CI)")
    ax.text(1.12, res["gap"][0], f"−{measured_gap:.2f}%\napparent signal\n(Seebeck artifact, b)", ha="left", va="center",
            fontsize=6.5, color=C_GAP)
    ax.text(-0.12, res["sum"][0], "null", ha="right", va="center", fontsize=6.5, color=C_SUM)
    ax.grid(alpha=ps.GRID_ALPHA, axis="y"); ps.panel_label(ax, "(a)")

    bx.bar([0, 1], [T_gg, T_sg], color=[ps.PAIR_COLOR["glass-glass"], ps.PAIR_COLOR["steel-glass"]], width=0.55,
           yerr=[[T_gg - Tgg.min(), T_sg - Tsg.min()], [Tgg.max() - T_gg, Tsg.max() - T_sg]], capsize=3,
           error_kw=dict(lw=0.8))
    for i, T in enumerate([T_gg, T_sg]):
        bx.text(i, 80.8, f"{T:.1f} °C", ha="center", va="bottom", fontsize=6.5, color="white", fontweight="bold")
    bx.set_xticks([0, 1]); bx.set_xticklabels(["Glass–glass\nheater plate", "Steel–glass\nheater plate"])
    bx.set_ylabel("Heated-plate temperature (°C)")
    bx.text(0.97, 0.80, "bars: mean of 4 phases\nwhiskers: phase range", transform=bx.transAxes, ha="right", va="top", fontsize=6)
    bx.annotate("", xy=(1.32, T_sg), xytext=(1.32, T_gg), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8))
    bx.text(1.38, (T_sg + T_gg) / 2, f"+{dT:.1f} °C\n({dT_ph.min():.1f}–{dT_ph.max():.1f}\nby phase)",
            va="center", ha="left", fontsize=6.2)
    bx.text(0.03, 0.96, f"Seebeck shift at {coef[0]}–{coef[1]} %/°C:\npredicted artifact {art_lo:.1f}–{art_hi:.1f}%\n"
            f"measured apparent signal {measured_gap:.2f}%", transform=bx.transAxes, va="top", fontsize=6.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.8"))
    bx.set_ylim(80, 99); bx.set_xlim(-0.6, 2.4); bx.grid(alpha=ps.GRID_ALPHA, axis="y"); ps.panel_label(bx, "(b)", right=True)
    fig.tight_layout(); save(fig, "fig5_air_null_artifact")
    return dict(res=res, T_sg=T_sg, T_gg=T_gg, dT=dT, artifact=(art_lo, art_hi), measured=measured_gap)


# --------------------------------------------------------------------------
# Figure 6: vacuum result
# --------------------------------------------------------------------------
def fig6_vacuum_result():
    sg, gg = load_abba(path("sg_vac")), load_abba(path("gg_vac"))
    rr = load_abba(path("sg_vac_a2"))
    fig = plt.figure(figsize=(ps.FULL_WIDTH_IN, 5.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.15], hspace=0.42, wspace=0.28,
                          left=0.19, right=0.97, top=0.95, bottom=0.2)
    ax = fig.add_subplot(gs[0, 0]); cx = fig.add_subplot(gs[0, 1]); bx = fig.add_subplot(gs[1, :])

    # (a) through-gap phase curves
    for run, ph, lab, col, ls in [(sg, "A1_FWD_HEAT", "A1 steel heated", C_A, "-"),
                                  (sg, "B1_REV_HEAT", "B1 glass heated", C_B, "-"),
                                  (sg, "B2_REV_HEAT", "B2 glass heated", C_B, "--"),
                                  (sg, "A2_FWD_HEAT", "A2 (deeper vacuum)", C_A, "--")]:
        d = run[ph]; ax.plot(d["t"], d[GAPCH[ph]], color=col, ls=ls, lw=1.1, label=lab)
    d = rr["A2_FWD_HEAT"]
    ax.plot(d["t"], d["vbot"], color=C_A, ls=":", lw=1.1, label="A2 rerun: planned confirmation,\ninconclusive (pump cycling)")
    ax.axvspan(30, 50, color="0.5", alpha=0.1, lw=0)
    ax.set_xlim(0, 50); ax.set_ylim(0, 450); ax.set_xlabel("Time within phase (min)")
    ax.set_ylabel("Through-gap TEG (mV)"); ax.legend(loc="lower right", fontsize=5.8)
    ax.grid(alpha=ps.GRID_ALPHA); ps.panel_label(ax, "(a)")

    # (c) glass-glass control: forward phase still rising in its window
    for ph, lab, col in [("A1_FWD_HEAT", "A1 (forward)", C_A), ("B1_REV_HEAT", "B1 (reverse)", C_B)]:
        d = gg[ph]; cx.plot(d["t"], d[GAPCH[ph]], color=col, lw=1.1, label=lab)
    cx.axvspan(20, 40, color="0.5", alpha=0.1, lw=0)
    a1_20, a1_40 = win(gg, "A1_FWD_HEAT", 19.5, 20.5)[0], win(gg, "A1_FWD_HEAT", 39, 40)[0]
    cx.annotate(f"{a1_20:.0f} → {a1_40:.0f} mV\nwithin the window", xy=(30, win(gg, "A1_FWD_HEAT", 29.5, 30.5)[0]),
                xytext=(6, 400), fontsize=6.5, arrowprops=dict(arrowstyle="->", lw=0.7, color=INK))
    cx.set_xlim(0, 40); cx.set_ylim(0, 480); cx.set_xlabel("Time within phase (min)")
    cx.set_ylabel("Through-gap TEG (mV)"); cx.set_title("Glass–glass control (40-min phases)", fontsize=7)
    cx.legend(loc="lower right"); cx.grid(alpha=ps.GRID_ALPHA); ps.panel_label(cx, "(b)")

    # (b) eta_corrected under each analysis choice
    rows = []
    for wlab, ws, wg in [("paper windows\nSG 30–50 / GG 20–40", (30, 50), (20, 40)),
                         ("same phase time\n20–40 min", (20, 40), (20, 40)),
                         ("same phase time\n30–40 min", (30, 40), (30, 40)),
                         ("last 10 min\nof each run", (40, 50), (30, 40))]:
        for metric in ("gap", "sum"):
            sv = {p: win(sg, p, *ws, metric)[0] for p in PH}; gv = {p: win(gg, p, *wg, metric)[0] for p in PH}
            sr = dict(sv); sr["A2_FWD_HEAT"] = win(rr, "A2_FWD_HEAT", *ws, metric)[0]
            rows.append((wlab, metric, eta(sv, "A1/B1") / eta(gv, "A1/B1"), eta(sv, "ABBA") / eta(gv, "ABBA"),
                         eta(sr, "ABBA") / eta(gv, "ABBA")))
    y = 0; yt, yl = [], []
    for i, (wlab, metric, e_a1b1, e_abba, e_rerun) in enumerate(rows):
        col = C_GAP if metric == "gap" else C_SUM
        bx.plot([min(e_a1b1, e_abba), max(e_a1b1, e_abba)], [y, y], color=col, lw=4, alpha=0.35, solid_capstyle="butt")
        bx.plot(e_a1b1, y, "o", color=col, ms=5); bx.plot(e_abba, y, "s", color=col, ms=5)
        bx.plot(e_rerun, y, "D", mfc="white", mec=col, ms=5)
        if i % 2 == 0:
            yt.append(y - 0.5); yl.append(wlab)
        y += 1
        if i % 2 == 1:
            y += 0.6
    bx.axvline(1.0, color=INK, lw=1)
    bx.set_yticks(yt); bx.set_yticklabels(yl, fontsize=6.5)
    bx.set_xlim(0.80, 1.10); bx.set_xlabel("η$_{corrected}$ = η$_{steel–glass}$ / η$_{glass–glass}$  (vacuum control)")
    bx.set_ylim(y - 0.6, -1.4)
    bx.text(1.003, -0.9, "η = 1: no asymmetry", ha="left", va="center", fontsize=6.5, color=INK)
    handles = [Line2D([], [], color=C_GAP, lw=4, alpha=0.5, label="through-gap metric"),
               Line2D([], [], color=C_SUM, lw=4, alpha=0.5, label="sum metric"),
               Line2D([], [], marker="o", ls="", color=INK, ms=5, label="A1 / B1 only"),
               Line2D([], [], marker="s", ls="", color=INK, ms=5, label="full ABBA (overnight A2)"),
               Line2D([], [], marker="D", ls="", mfc="white", mec=INK, ms=5, label="ABBA with A2 rerun (inconclusive)")]
    bx.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=6)
    bx.grid(alpha=ps.GRID_ALPHA, axis="x"); ps.panel_label(bx, "(c)")
    save(fig, "fig6_vacuum_result")
    gaps = [r[2:] for r in rows if r[1] == "gap"]; sums = [r[2:] for r in rows if r[1] == "sum"]
    return dict(gap_range=(min(map(min, gaps)), max(map(max, gaps))),
                sum_range=(min(map(min, sums)), max(map(max, sums))), reported=rows[0][2])


# --------------------------------------------------------------------------
# Figure 7: Simulation 2 bound on what the gap itself can do
# --------------------------------------------------------------------------
def fig7_gap_bound(gap_range, sum_range):
    dT = np.linspace(5, 60, 60)
    fig, ax = plt.subplots(figsize=(ps.COLUMN_WIDTH_IN * 1.6, 2.9))
    for p_torr, lab, ls in [(36.0, "~36 Torr (Feb 2026)", "-"), (7.5e-6, "10⁻⁵ mbar (new chamber)", "--")]:
        p = float(mc.torr_to_pa(p_torr))
        for n, col in [(0.5, "#009E73"), (1.0, "#0072B2"), (1.5, "#D55E00")]:
            r = [100 * sim2.total_rectification(t, n, 0.0, p) for t in dT]
            ax.plot(dT, r, color=col, ls=ls, lw=1.2, label=f"n = {n}, {lab}" if n == 1.0 else None)
    ax.axhspan(100 * (1 - gap_range[1]), 100 * (1 - gap_range[0]), color=C_GAP, alpha=0.15, lw=0)
    ax.axhspan(100 * (sum_range[0] - 1), 100 * (sum_range[1] - 1), color=C_SUM, alpha=0.15, lw=0)
    ax.text(6, 100 * (1 - gap_range[0]) - 0.6, "measured |asymmetry|, through-gap metric", ha="left", va="top", fontsize=6, color=C_GAP)
    ax.text(58, 100 * (sum_range[1] - 1) - 0.4, "measured |asymmetry|, sum metric", ha="right", va="top", fontsize=6, color=C_SUM)
    ax.set_xlabel("Surface temperature difference across gap, ΔT (K)")
    ax.set_ylabel("|Rectification| from the gap alone (%)")
    ax.set_xlim(5, 60); ax.set_ylim(0, 20)
    h = [Line2D([], [], color=c, lw=1.2, label=f"steel ε ∝ T^{n}") for n, c in [(0.5, "#009E73"), (1.0, "#0072B2"), (1.5, "#D55E00")]]
    h += [Line2D([], [], color=INK, ls="-", label="~36 Torr"), Line2D([], [], color=INK, ls="--", label="10⁻⁵ mbar")]
    ax.legend(handles=h, loc="upper left", ncol=2); ax.grid(alpha=ps.GRID_ALPHA)
    ax.text(0.98, 0.03, "constant emissivity: exactly 0 (Sim 2)", transform=ax.transAxes, ha="right", fontsize=6)
    fig.tight_layout(); save(fig, "fig7_gap_bound")


if __name__ == "__main__":
    ps.apply_style()
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Figure 3"); r3 = fig3_gap_sweep()
    print(f"  V_bot drop {r3['drop_b']:.1f}%, sum drop {r3['drop_s']:.1f}%")
    print("Figure 4"); r4 = fig4_pressure_map()
    print(f"  steel-glass radiation share at 36 Torr: {r4['share_sg_36torr']:.1f}%")
    print("Figure 5"); r5 = fig5_air_null_artifact()
    print(f"  air eta_corrected: sum {r5['res']['sum'][0]:.4f} ± {r5['res']['sum'][1]:.4f}, "
          f"through-gap {r5['res']['gap'][0]:.4f} ± {r5['res']['gap'][1]:.4f}; "
          f"heater offset {r5['dT']:.1f} °C; artifact {r5['artifact'][0]:.2f}–{r5['artifact'][1]:.2f}% vs measured {r5['measured']:.2f}%")
    print("Figure 6"); r6 = fig6_vacuum_result()
    print(f"  reported-method eta {r6['reported']:.4f}; through-gap range {r6['gap_range'][0]:.3f}–{r6['gap_range'][1]:.3f}; "
          f"sum range {r6['sum_range'][0]:.3f}–{r6['sum_range'][1]:.3f}")
    print("Figure 7"); fig7_gap_bound(r6["gap_range"], r6["sum_range"])
    print(f"Done. Figures in {os.path.abspath(OUT_DIR)}")
