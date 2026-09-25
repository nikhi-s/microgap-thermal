#!/usr/bin/env python3
"""
Thermal Rectification Experiment — Complete Figure Set
======================================================
Generates all plots for the DRSEF/ISEF project on micro-gap
thermal rectification.

Data sources (raw logs in ../data, see DATA_FILES below):
  - Gap sweep: Module-B/C gap-sweep logs (firmware PLATEAU windows)
  - SiO2-SiO2 contact ABBA: Module-A_contact_G-G_ABBA_16Feb_Control.txt
  - Steel-Glass 508 um ABBA (air): Module-D_20mil_S-G_Rectification_19Feb_retake.txt
  - Glass-Glass 508 um ABBA (air): Module-E_20mil_G-G_Rectification_20Feb_Control.txt
  - Glass-Glass 508 um ABBA (~36 Torr): Module-E_..._22Feb_control_Vacuum_fixedTime.txt

Updated Sept 2026: all values computed from the raw logs (no hardcoded
gap-sweep numbers); smallest gap is 7.62 um (0.3 mil Kapton); Plot 2 uses a
far-field gray-body radiation model at 340 K; Plot 8 no longer draws a
hand-entered "vacuum prediction" curve (see simulations/ for the pressure
model). Figures are written to ../figures/regenerated/.

Author: Nikhitha Swaminathan
Date: February 2026
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import statistics
import os

# ============================================================================
# GLOBAL STYLE
# ============================================================================
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'serif',
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.dpi': 200,
    'savefig.dpi': 200,
    'axes.grid': True,
    'grid.alpha': 0.3,
})

COLORS = {
    'forward': '#2196F3',   # blue
    'reverse': '#F44336',   # red
    'neutral': '#4CAF50',   # green
    'steel':   '#607D8B',   # blue-grey
    'glass':   '#FF9800',   # orange
    'air':     '#9C27B0',   # purple
    'rad':     '#E91E63',   # pink
    'contact': '#795548',   # brown
    'highlight': '#FFD600', # yellow
}

# ============================================================================
# PATHS — run from the repo's analysis/ folder; raw logs are read from ../data
#   Override with environment variables MGTD_DATA_DIR / MGTD_OUT_DIR if needed.
# ============================================================================
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('MGTD_DATA_DIR', os.path.join(HERE, '..', 'data'))
OUTPUT_DIR = os.environ.get('MGTD_OUT_DIR', os.path.join(HERE, '..', 'figures', 'regenerated'))
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_FILES = {
    # Atmospheric ABBA runs (508 um unless noted)
    'contact_air':  'Module-A_contact_G-G_ABBA_16Feb_Control.txt',              # SiO2-SiO2 contact
    'sg_air':       'Module-D_20mil_S-G_Rectification_19Feb_retake.txt',        # steel-glass, air
    'gg_air':       'Module-E_20mil_G-G_Rectification_20Feb_Control.txt',       # glass-glass, air
    # Partial-vacuum ABBA runs (~36 Torr, 28.5 inHg gauge)
    'gg_vac':       'Module-E_20mil_G-G_Rectification_22Feb_control_Vacuum_fixedTime.txt',  # TEST 16B
    'sg_vac':       'Module-E_20mil_S-G_Rectification_23Feb_Vacuum_fixedTime.txt',          # TEST 16C
    'sg_vac_a2':    'Module-E_20mil_S-G_Rectification_24Feb_Vacuum_fixedTime_A2_Rerun.txt', # TEST 16E
    # Forward-only gap sweep, glass-glass, air (gap in um -> file)
    'sweep_7.62':   'Module-C_1by3Mil_G-G_GapSweep_17Feb.txt',   # 0.3 mil Kapton (firmware header says 8.5um)
    'sweep_25.4':   'Module-B_1Mil_G-G_GapSweep_17Feb.txt',
    'sweep_254':    'Module-B_10Mil_G-G_GapSweep_16Feb.txt',
    'sweep_508':    'Module-B_20mil_G-G_GapSweep_20Feb.txt',
}


def data_path(key, required=True):
    """Full path to a raw log; raise a clear error if it is missing."""
    p = os.path.join(DATA_DIR, DATA_FILES[key])
    if not os.path.exists(p):
        if required:
            raise FileNotFoundError(f"Missing raw data file for '{key}': {p}")
        return None
    return p


# ============================================================================
# DATA LOADING UTILITIES
# ============================================================================
def load_abba_data(filepath):
    """Load ABBA CSV data, return dict of phase -> list of dicts."""
    phases = {}
    with open(filepath, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.replace('\x00', '').strip().replace('\r', '')
            if not line or line.startswith('#'):
                continue
            parts = line.split(',')
            if len(parts) < 11:
                continue
            phase = parts[1]
            if phase == 'phase':
                continue
            try:
                entry = {
                    'time_ms': int(parts[0]),
                    'phase_time_ms': int(parts[2]),
                    'vtop': float(parts[4]),
                    'vbot': float(parts[5]),
                    'tt': float(parts[6]),
                    'tb': float(parts[7]),
                    'tamb': float(parts[10]) if parts[10] != '' else -1
                }
                entry['sum'] = entry['vtop'] + entry['vbot']
            except (ValueError, IndexError):
                continue
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(entry)
    return phases


def plateau_stats(data, last_n=600):
    """Compute plateau statistics from last N samples."""
    d = data[-last_n:] if len(data) >= last_n else data
    vt = [x['vtop'] for x in d]
    vb = [x['vbot'] for x in d]
    sums = [x['sum'] for x in d]
    tt = [x['tt'] for x in d]
    tb = [x['tb'] for x in d]
    return {
        'vtop': statistics.mean(vt),
        'vtop_std': statistics.stdev(vt) if len(vt) > 1 else 0,
        'vbot': statistics.mean(vb),
        'vbot_std': statistics.stdev(vb) if len(vb) > 1 else 0,
        'sum': statistics.mean(sums),
        'sum_std': statistics.stdev(sums) if len(sums) > 1 else 0,
        'tt': statistics.mean(tt),
        'tb': statistics.mean(tb),
        'n': len(d),
    }


# ============================================================================
# LOAD ALL DATA
# ============================================================================
print("Loading data...")
steel_glass = load_abba_data(data_path('sg_air'))
glass_glass = load_abba_data(data_path('gg_air'))
sio2_contact = load_abba_data(data_path('contact_air'))


def load_gap_sweep(filepath):
    """Per-run means (vtop, vbot) of the PLATEAU rows of a 13-column gap-sweep log."""
    runs = {}
    with open(filepath, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.replace('\x00', '').strip().replace('\r', '')
            p = line.split(',')
            if line.startswith('#') or len(p) != 13 or p[1] != 'PLATEAU':
                continue
            try:
                runs.setdefault(int(p[2]), []).append((float(p[5]), float(p[6])))
            except ValueError:
                continue
    return [(np.mean([v[0] for v in r]), np.mean([v[1] for v in r])) for r in runs.values()]


# Gap sweep from the raw logs. Contact point: contact ABBA forward phase A1
# (last 600 s). Gapped points: mean of the firmware PLATEAU windows over all
# runs (read ~10 min after heat-on, while V_bot is still rising).
SWEEP_GAPS = [7.62, 25.4, 254, 508]
_ct = plateau_stats(sio2_contact['A1_FWD_HEAT'])
gap_sweep = {'gaps_um': [0], 'sums': [_ct['sum']], 'stds': [_ct['sum_std'] / np.sqrt(_ct['n'])],
             'cvs': [0], 'vtop': [_ct['vtop']], 'vbot': [_ct['vbot']],
             'labels': ['Contact', '7.62 µm\n(0.3 mil)', '25.4 µm\n(1 mil)',
                        '254 µm\n(10 mil)', '508 µm\n(20 mil)']}
for g in SWEEP_GAPS:
    runs = load_gap_sweep(data_path(f'sweep_{g:g}'))
    sums_r = [a + b for a, b in runs]
    gap_sweep['gaps_um'].append(g)
    gap_sweep['sums'].append(float(np.mean(sums_r)))
    gap_sweep['stds'].append(float(np.std(sums_r, ddof=1)))
    gap_sweep['cvs'].append(float(np.std(sums_r, ddof=1) / np.mean(sums_r) * 100))
    gap_sweep['vtop'].append(float(np.mean([r[0] for r in runs])))
    gap_sweep['vbot'].append(float(np.mean([r[1] for r in runs])))
print("  Gap sweep sums (mV):", [round(v, 1) for v in gap_sweep['sums']])
print("  Run-to-run CV of sum (%):", [round(v, 2) for v in gap_sweep['cvs'][1:]])

# One gap-transfer model (paper Section 2.7)
K_AIR, T_GAP, SIGMA_SB = 0.026, 340.0, 5.67e-8
H_RAD_GG = 4 * SIGMA_SB * (1 / (1/0.9 + 1/0.9 - 1)) * T_GAP**3   # ~7.3 W/m2K


# ============================================================================
# PLOT 1: GAP SWEEP — SIGNAL VS GAP DISTANCE
# ============================================================================
print("Plot 1: Gap Sweep...")
fig, ax = plt.subplots(figsize=(8, 5))

gaps = gap_sweep['gaps_um']
sums = gap_sweep['sums']
stds = gap_sweep['stds']
labels = gap_sweep['labels']

bars = ax.bar(range(len(gaps)), sums, yerr=stds, capsize=5,
              color=[COLORS['contact'], COLORS['forward'], COLORS['neutral'], COLORS['air'], COLORS['rad']],
              edgecolor='black', linewidth=0.5, alpha=0.85, width=0.6)

# Annotate values
for i, (s, std) in enumerate(zip(sums, stds)):
    pct = s / sums[0] * 100
    label = f'{s:.1f} mV\n({pct:.1f}%)'
    ax.annotate(label, (i, s + std + 3), ha='center', va='bottom', fontsize=9)

ax.set_xticks(range(len(gaps)))
ax.set_xticklabels(labels)
ax.set_ylabel('TEG Sum (Vtop + Vbot) [mV]')
ax.set_xlabel('Gap Distance')
ax.set_title('Plot 1: Heat Transfer vs Gap Distance\nSiO₂–SiO₂ Stack in Air')
ax.set_ylim(940, 1040)

# Add annotation about air dominance
_drop_ct = (1 - min(sums[1:]) / sums[0]) * 100
_drop_gap = (1 - sums[-1] / sums[1]) * 100
ax.annotate(f'Only {_drop_gap:.1f}% drop over the {gaps[-1]/gaps[1]:.0f}× gap increase\n({_drop_ct:.1f}% from contact) → sum is insensitive to the gap',
            xy=(0.6, 946), fontsize=9, style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot1_gap_sweep.png')
plt.close()


# ============================================================================
# PLOT 2: AIR CONDUCTION VS RADIATION
# ============================================================================
print("Plot 2: Heat transfer mechanisms...")
fig, ax = plt.subplots(figsize=(8, 5))

gap_range = np.array([7.62, 25.4, 50, 100, 254, 508, 1000])  # µm
k_air = K_AIR  # W/mK
h_air = k_air / (gap_range * 1e-6)  # W/m²K

# Radiation: far-field gray body, glass-glass, T = 340 K (~7.3 W/m²K).
# The earlier ad hoc near-field factor was removed: at >= 7.62 µm the gap is far-field.
h_rad = np.full_like(gap_range, H_RAD_GG)

ax.loglog(gap_range, h_air, 'o-', color=COLORS['air'], linewidth=2.5,
            markersize=7, label='Air conduction (h = k/d)', zorder=3)
ax.loglog(gap_range, h_rad, 's--', color=COLORS['rad'], linewidth=2.5,
            markersize=7, label='Radiation (glass–glass, far-field)', zorder=3)

# Fill region between
ax.fill_between(gap_range, h_rad, h_air, alpha=0.08, color='gray')

# Ratio annotations at measured points
for g in SWEEP_GAPS:
    h_a = k_air / (g * 1e-6)
    idx = np.argmin(np.abs(gap_range - g))
    h_r = h_rad[idx]
    ratio = h_a / h_r
    ax.annotate(f'{ratio:.0f}×', xy=(g, np.sqrt(h_a * h_r)),
                fontsize=8, ha='center', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

ax.axvline(x=508, color='gray', linestyle=':', alpha=0.5)
ax.annotate('Module D gap\n(508 µm)', xy=(508, 10), fontsize=8, ha='center',
            color='gray')

ax.set_xlabel('Gap Distance [µm]')
ax.set_ylabel('Heat Transfer Coefficient [W/m²K]')
ax.set_title('Plot 2: Air Conduction vs Radiation Across Gap\nWhy Rectification Is Hard in Ambient Conditions')
ax.legend(loc='upper right', framealpha=0.9)
ax.set_xlim(5, 1200)
ax.set_ylim(1, 10000)

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot2_air_vs_radiation.png')
plt.close()


# ============================================================================
# PLOT 3: FULL ABBA HEATING PROFILE (STEEL-GLASS)
# ============================================================================
print("Plot 3: ABBA profile...")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                 gridspec_kw={'height_ratios': [2, 1]})

# Build continuous time series
all_phases_order = ['WAIT_AMBIENT', 'A1_FWD_HEAT', 'A1_COOLDOWN',
                    'B1_REV_HEAT', 'B1_COOLDOWN', 'B2_REV_HEAT',
                    'B2_COOLDOWN', 'A2_FWD_HEAT', 'A2_COOLDOWN']

times_hr = []
sums_ts = []
vtops_ts = []
vbots_ts = []
tts_ts = []
tbs_ts = []
phase_ts = []

for phase_name in all_phases_order:
    if phase_name in steel_glass:
        for d in steel_glass[phase_name]:
            t_hr = d['time_ms'] / 3600000
            times_hr.append(t_hr)
            sums_ts.append(d['sum'])
            vtops_ts.append(d['vtop'])
            vbots_ts.append(d['vbot'])
            tts_ts.append(d['tt'])
            tbs_ts.append(d['tb'])
            phase_ts.append(phase_name)

times_hr = np.array(times_hr)
sums_ts = np.array(sums_ts)

# Subsample for plotting (every 10s)
step = 10
t_plot = times_hr[::step]
sum_plot = sums_ts[::step]
vt_plot = np.array(vtops_ts)[::step]
vb_plot = np.array(vbots_ts)[::step]
tt_plot = np.array(tts_ts)[::step]
tb_plot = np.array(tbs_ts)[::step]

# Top panel: TEG voltages
ax1.plot(t_plot, vt_plot, color=COLORS['forward'], linewidth=0.8, alpha=0.8, label='Vtop')
ax1.plot(t_plot, vb_plot, color=COLORS['reverse'], linewidth=0.8, alpha=0.8, label='Vbot')
ax1.plot(t_plot, sum_plot, color='black', linewidth=1.2, label='Sum (Vtop+Vbot)')

# Shade heating phases
phase_colors = {
    'A1_FWD_HEAT': (COLORS['forward'], 0.12, 'A1\nForward'),
    'A2_FWD_HEAT': (COLORS['forward'], 0.12, 'A2\nForward'),
    'B1_REV_HEAT': (COLORS['reverse'], 0.12, 'B1\nReverse'),
    'B2_REV_HEAT': (COLORS['reverse'], 0.12, 'B2\nReverse'),
}

for pname, (color, alpha, label) in phase_colors.items():
    if pname in steel_glass:
        pdata = steel_glass[pname]
        t_start = pdata[0]['time_ms'] / 3600000
        t_end = pdata[-1]['time_ms'] / 3600000
        ax1.axvspan(t_start, t_end, alpha=alpha, color=color)
        ax2.axvspan(t_start, t_end, alpha=alpha, color=color)
        ax1.text((t_start + t_end) / 2, 1050, label, ha='center', va='bottom',
                fontsize=8, fontweight='bold')

ax1.set_ylabel('TEG Voltage [mV]')
ax1.set_title('Plot 3: Steel–Glass ABBA Protocol — Full 8.7-Hour Run\n508 µm Air Gap, 40 min Heating Phases')
ax1.legend(loc='upper right', ncol=3)
ax1.set_ylim(-50, 1150)

# Bottom panel: temperatures
ax2.plot(t_plot, tt_plot, color=COLORS['forward'], linewidth=0.8, alpha=0.8, label='T_top')
ax2.plot(t_plot, tb_plot, color=COLORS['reverse'], linewidth=0.8, alpha=0.8, label='T_bot')
ax2.axhline(y=24, color='gray', linestyle='--', alpha=0.5, label='Ambient (~24°C)')
ax2.set_ylabel('Temperature [°C]')
ax2.set_xlabel('Time [hours]')
ax2.legend(loc='upper right', ncol=3)
ax2.set_ylim(15, 100)

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot3_abba_profile.png')
plt.close()


# ============================================================================
# PLOT 4: TEG MISMATCH DISCOVERY
# ============================================================================
print("Plot 4: TEG mismatch...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

# Left: Glass-Glass control showing raw A vs B
gg_phases = ['A1_FWD_HEAT', 'B1_REV_HEAT', 'B2_REV_HEAT']
gg_labels = ['A1\n(top heated)', 'B1\n(bot heated)', 'B2\n(bot heated)']
gg_sums = []
gg_stds = []
gg_colors_list = []

for p in gg_phases:
    if p in glass_glass:
        stats = plateau_stats(glass_glass[p])
        gg_sums.append(stats['sum'])
        gg_stds.append(stats['sum_std'])
        gg_colors_list.append(COLORS['forward'] if 'FWD' in p else COLORS['reverse'])

bars = ax1.bar(range(len(gg_sums)), gg_sums, yerr=gg_stds, capsize=5,
               color=gg_colors_list, edgecolor='black', linewidth=0.5, alpha=0.85, width=0.5)

for i, (s, std) in enumerate(zip(gg_sums, gg_stds)):
    ax1.annotate(f'{s:.1f} mV', (i, s + std + 2), ha='center', va='bottom', fontsize=9)

# Draw the difference arrow
if len(gg_sums) >= 2:
    diff = gg_sums[1] - gg_sums[0]
    mid_y = (gg_sums[0] + gg_sums[1]) / 2
    ax1.annotate('', xy=(1, gg_sums[1] - 5), xytext=(0, gg_sums[0] + 5),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax1.text(0.5, mid_y, f'Δ = {diff:.1f} mV\n(TEG mismatch!)',
            ha='center', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

ax1.set_xticks(range(len(gg_labels)))
ax1.set_xticklabels(gg_labels)
ax1.set_ylabel('TEG Sum [mV]')
ax1.set_title('Glass–Glass Control (508 µm)\nSymmetric materials → NO rectification expected')
ax1.set_ylim(980, 1130)

# Right: Cross-comparison of TEGs
# When each TEG is on the hot side vs cold side
teg_data = {
    'Top TEG (hot)': [],
    'Bot TEG (hot)': [],
    'Top TEG (cold)': [],
    'Bot TEG (cold)': [],
}

for exp_name, exp_data in [('Glass-Glass', glass_glass), ('Steel-Glass', steel_glass)]:
    for p in ['A1_FWD_HEAT', 'A2_FWD_HEAT']:
        if p in exp_data:
            s = plateau_stats(exp_data[p])
            teg_data['Top TEG (hot)'].append(s['vtop'])
            teg_data['Bot TEG (cold)'].append(s['vbot'])
    for p in ['B1_REV_HEAT', 'B2_REV_HEAT']:
        if p in exp_data:
            s = plateau_stats(exp_data[p])
            teg_data['Bot TEG (hot)'].append(s['vbot'])
            teg_data['Top TEG (cold)'].append(s['vtop'])

labels2 = ['Hot side\n(near heater)', 'Cold side\n(far from heater)']
top_vals = [np.mean(teg_data['Top TEG (hot)']), np.mean(teg_data['Top TEG (cold)'])]
bot_vals = [np.mean(teg_data['Bot TEG (hot)']), np.mean(teg_data['Bot TEG (cold)'])]

x = np.arange(len(labels2))
width = 0.3
bars1 = ax2.bar(x - width/2, top_vals, width, label='Top TEG', color=COLORS['forward'],
                edgecolor='black', linewidth=0.5, alpha=0.85)
bars2 = ax2.bar(x + width/2, bot_vals, width, label='Bottom TEG', color=COLORS['reverse'],
                edgecolor='black', linewidth=0.5, alpha=0.85)

for bar_group in [bars1, bars2]:
    for bar in bar_group:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 5, f'{h:.0f}',
                ha='center', va='bottom', fontsize=9)

# Ratio annotation
if top_vals[0] > 0:
    ratio = bot_vals[0] / top_vals[0]
    pct = (ratio - 1) * 100
    ax2.annotate(f'Bot/Top ratio: {ratio:.3f}\n({pct:.0f}% mismatch)',
                xy=(0, (top_vals[0] + bot_vals[0])/2), fontsize=9,
                ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

ax2.set_xticks(x)
ax2.set_xticklabels(labels2)
ax2.set_ylabel('Individual TEG Voltage [mV]')
ax2.set_title('TEG Sensitivity Mismatch\nBottom TEG reads ~7% higher than Top TEG')
ax2.legend()

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot4_teg_mismatch.png')
plt.close()


# ============================================================================
# PLOT 5: KEY RESULT — CORRECTED RECTIFICATION
# ============================================================================
print("Plot 5: Key result...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

# Left: Raw eta values
experiments = ['SiO₂–SiO₂\nContact', 'Glass–Glass\n508 µm', 'Steel–Glass\n508 µm']

# Compute etas
sio2_A = np.mean([plateau_stats(sio2_contact[p])['sum'] for p in ['A1_FWD_HEAT', 'A2_FWD_HEAT']])
sio2_B = np.mean([plateau_stats(sio2_contact[p])['sum'] for p in ['B1_REV_HEAT', 'B2_REV_HEAT']])
sio2_eta = sio2_A / sio2_B

sg_A = np.mean([plateau_stats(steel_glass[p])['sum'] for p in ['A1_FWD_HEAT', 'A2_FWD_HEAT']])
sg_B = np.mean([plateau_stats(steel_glass[p])['sum'] for p in ['B1_REV_HEAT', 'B2_REV_HEAT']])
sg_eta = sg_A / sg_B

# Glass-glass: use A1 and both B's (A2 may be incomplete)
gg_A_phases = [p for p in ['A1_FWD_HEAT', 'A2_FWD_HEAT'] if p in glass_glass and len(glass_glass[p]) >= 600]
gg_B_phases = [p for p in ['B1_REV_HEAT', 'B2_REV_HEAT'] if p in glass_glass and len(glass_glass[p]) >= 600]
gg_A = np.mean([plateau_stats(glass_glass[p])['sum'] for p in gg_A_phases])
gg_B = np.mean([plateau_stats(glass_glass[p])['sum'] for p in gg_B_phases])
gg_eta = gg_A / gg_B

raw_etas = [sio2_eta, gg_eta, sg_eta]
colors_raw = [COLORS['contact'], COLORS['glass'], COLORS['steel']]

bars = ax1.bar(range(3), raw_etas, color=colors_raw,
               edgecolor='black', linewidth=0.5, alpha=0.85, width=0.5)

ax1.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, label='η = 1 (no rectification)')

for i, eta in enumerate(raw_etas):
    ax1.annotate(f'η = {eta:.4f}', (i, eta + 0.002), ha='center', va='bottom', fontsize=9)

ax1.set_xticks(range(3))
ax1.set_xticklabels(experiments)
ax1.set_ylabel('Raw η = A_mean / B_mean')
ax1.set_title('Raw Rectification Ratio, atmospheric\n(includes TEG mismatch artifact)')
ax1.set_ylim(0.90, 1.02)
ax1.legend(loc='upper left', fontsize=9)

# Right: Corrected eta
corrected_eta = sg_eta / gg_eta
corrected_err = 0.003  # estimated from spread

ax2.bar([0], [corrected_eta], color=COLORS['steel'],
        edgecolor='black', linewidth=0.5, alpha=0.85, width=0.35)
ax2.axhline(y=1.0, color='black', linestyle='--', alpha=0.5)

# Shade the "no rectification" band
ax2.axhspan(0.997, 1.003, alpha=0.15, color='green', label='±0.3% (noise floor)')

ax2.annotate(f'η = {corrected_eta:.4f}\n({(1-corrected_eta)*100:.2f}% rectification)',
            xy=(0, corrected_eta + 0.003), ha='center', va='bottom', fontsize=11,
            fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

ax2.set_xticks([0])
ax2.set_xticklabels(['Steel–Glass\n÷ Glass–Glass'])
ax2.set_ylabel('Corrected η')
ax2.set_title('Corrected Rectification Ratio\n(TEG mismatch cancelled)')
ax2.set_ylim(0.98, 1.02)
ax2.legend(loc='upper left', fontsize=9)

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot5_key_result.png')
plt.close()


# ============================================================================
# PLOT 6: VTOP/VBOT SPLIT SHIFT WITH GAP
# ============================================================================
print("Plot 6: Vtop/Vbot split...")
fig, ax = plt.subplots(figsize=(8, 5))

gaps_plot = [f'{g:g} µm' for g in SWEEP_GAPS]
vtops = [round(v) for v in gap_sweep['vtop'][1:]]
vbots = [round(v) for v in gap_sweep['vbot'][1:]]

x = np.arange(len(gaps_plot))
width = 0.45

bars1 = ax.bar(x, vtops, width, label='Vtop (heater side)',
               color=COLORS['forward'], edgecolor='black', linewidth=0.5, alpha=0.85)
bars2 = ax.bar(x, vbots, width, bottom=vtops, label='Vbot (insulated side)',
               color=COLORS['reverse'], edgecolor='black', linewidth=0.5, alpha=0.85)

# Add percentage labels
for i, (vt, vb) in enumerate(zip(vtops, vbots)):
    total = vt + vb
    pct_top = vt / total * 100
    pct_bot = vb / total * 100
    ax.text(i, vt / 2, f'{vt} mV\n({pct_top:.0f}%)', ha='center', va='center',
           fontsize=9, fontweight='bold', color='white')
    ax.text(i, vt + vb / 2, f'{vb} mV\n({pct_bot:.0f}%)', ha='center', va='center',
           fontsize=9, fontweight='bold', color='white')
    ax.text(i, total + 5, f'Sum: {total} mV', ha='center', va='bottom', fontsize=9)

ax.set_xticks(x)
ax.set_xticklabels(gaps_plot)
ax.set_ylabel('TEG Voltage [mV]')
ax.set_xlabel('Gap Distance')
ax.set_title('Plot 6: Heat Distribution Shift with Gap Distance\nLarger gaps trap more heat on the heater side')
ax.legend(loc='upper right')
ax.set_ylim(0, 1100)

# Add arrow showing trend
ax.annotate('', xy=(3.3, 750), xytext=(3.3, 350),
           arrowprops=dict(arrowstyle='->', color='black', lw=2))
ax.text(3.45, 550, 'More heat\ntrapped\non top', fontsize=8, va='center')

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot6_vtop_vbot_split.png')
plt.close()


# ============================================================================
# PLOT 7: REPEATABILITY DEMONSTRATION
# ============================================================================
print("Plot 7: Repeatability...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

# Left: A1 vs A2 plateau sums
experiments_rep = {
    'SiO₂–SiO₂\nContact': sio2_contact,
    'Steel–Glass\n508 µm': steel_glass,
}
# Add glass-glass if A2 exists
if 'A2_FWD_HEAT' in glass_glass and len(glass_glass['A2_FWD_HEAT']) >= 600:
    experiments_rep['Glass–Glass\n508 µm'] = glass_glass

x_pos = 0
x_ticks = []
x_labels = []

for exp_name, exp_data in experiments_rep.items():
    a_vals = []
    b_vals = []
    for p in ['A1_FWD_HEAT', 'A2_FWD_HEAT']:
        if p in exp_data and len(exp_data[p]) >= 600:
            a_vals.append(plateau_stats(exp_data[p])['sum'])
    for p in ['B1_REV_HEAT', 'B2_REV_HEAT']:
        if p in exp_data and len(exp_data[p]) >= 600:
            b_vals.append(plateau_stats(exp_data[p])['sum'])
    
    # Plot A values
    for i, v in enumerate(a_vals):
        marker = 'o' if i == 0 else 's'
        label_txt = f'A{i+1}' if i == 0 else f'A{i+1}'
        ax1.plot(x_pos, v, marker, color=COLORS['forward'], markersize=10,
                markeredgecolor='black', markeredgewidth=0.5, zorder=3)
        ax1.annotate(f'A{i+1}: {v:.1f}', (x_pos + 0.05, v), fontsize=8, va='center')
    
    if len(a_vals) == 2:
        spread = abs(a_vals[1] - a_vals[0])
        mid = np.mean(a_vals)
        ax1.plot([x_pos, x_pos], a_vals, '-', color=COLORS['forward'], alpha=0.5)
        ax1.annotate(f'Δ={spread:.1f}', (x_pos - 0.15, mid), fontsize=8,
                    ha='right', color=COLORS['forward'], fontweight='bold')
    
    # Plot B values
    for i, v in enumerate(b_vals):
        ax2.plot(x_pos, v, 'o' if i == 0 else 's', color=COLORS['reverse'],
                markersize=10, markeredgecolor='black', markeredgewidth=0.5, zorder=3)
        ax2.annotate(f'B{i+1}: {v:.1f}', (x_pos + 0.05, v), fontsize=8, va='center')
    
    if len(b_vals) == 2:
        spread = abs(b_vals[1] - b_vals[0])
        mid = np.mean(b_vals)
        ax2.plot([x_pos, x_pos], b_vals, '-', color=COLORS['reverse'], alpha=0.5)
        ax2.annotate(f'Δ={spread:.1f}', (x_pos - 0.15, mid), fontsize=8,
                    ha='right', color=COLORS['reverse'], fontweight='bold')
    
    x_ticks.append(x_pos)
    x_labels.append(exp_name)
    x_pos += 1

for ax, direction, color in [(ax1, 'Forward (A)', COLORS['forward']),
                              (ax2, 'Reverse (B)', COLORS['reverse'])]:
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel('Plateau Sum [mV]')
    ax.set_title(f'Plot 7: {direction} Phase Repeatability\nA1 vs A2, B1 vs B2 across experiments')

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot7_repeatability.png')
plt.close()


# ============================================================================
# PLOT 8: MEASURED TOTAL SIGNAL — AIR GAP SWEEP vs ~36 TORR (glass-glass)
# (Replaces the earlier hand-entered "vacuum prediction" curve, which was not
#  computed from any model and is contradicted by the measured vacuum run.
#  Pressure-dependent predictions are in simulations/sim1_pressure.py.)
# ============================================================================
print("Plot 8: Air vs ~36 Torr, measured...")
fig, ax = plt.subplots(figsize=(8, 5))

air_measured_gaps = np.array(gap_sweep['gaps_um'])
air_measured_sums = np.array(gap_sweep['sums'])
ax.plot(air_measured_gaps, air_measured_sums, 'o--', color=COLORS['air'], markersize=10,
        markeredgecolor='black', zorder=4, label='Air, glass–glass (gap sweep + contact)')

_p_ggv = data_path('gg_vac', required=False)
if _p_ggv:
    gg_vac = load_abba_data(_p_ggv)
    # Forward (A) phases, last 20 min of each 40-min phase (as in the lab notebook)
    vac_A = [np.mean([d['sum'] for d in gg_vac[p] if d['phase_time_ms'] >= 1200000])
             for p in ('A1_FWD_HEAT', 'A2_FWD_HEAT')]
    ax.plot(508, np.mean(vac_A), 's', color=COLORS['rad'], markersize=11,
            markeredgecolor='black', zorder=5,
            label=f'~36 Torr, glass–glass ABBA forward ({np.mean(vac_A):.0f} mV)')

ax.annotate('At ~36 Torr gas conduction across 508 µm\nis essentially unchanged (Simulation 1);\n'
            'the total signal does not fall. Radiation\ndominates only below ~10⁻² Torr.\n'
            '(Heat durations differ: gap sweep ~10 min, ABBA 40 min.)',
            xy=(0.03, 0.05), xycoords='axes fraction', fontsize=9, ha='left', va='bottom',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

ax.set_xlabel('Gap Distance [µm]')
ax.set_ylabel('TEG Sum (Vtop + Vbot) [mV]')
ax.set_title('Plot 8: Measured Total Signal — Air vs ~36 Torr\n'
             'Partial vacuum did not remove gap conduction')
ax.legend(loc='upper right', fontsize=9)
ax.set_ylim(900, 1120)
ax.set_xlim(-20, 540)

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot8_vacuum_prediction.png')
plt.close()


# ============================================================================
# SUMMARY TABLE FIGURE
# ============================================================================
print("Summary table...")
fig, ax = plt.subplots(figsize=(10, 4))
ax.axis('off')

table_data = [
    ['SiO₂–SiO₂ Contact', '0 µm', f'{sio2_A:.1f}', f'{sio2_B:.1f}', f'{sio2_eta:.4f}', 'Apparatus validation'],
    ['Glass–Glass 508 µm', '508 µm', f'{gg_A:.1f}', f'{gg_B:.1f}', f'{gg_eta:.4f}', 'TEG calibration control'],
    ['Steel–Glass 508 µm', '508 µm', f'{sg_A:.1f}', f'{sg_B:.1f}', f'{sg_eta:.4f}', 'Rectification test'],
    ['Corrected', '—', '—', '—', f'{corrected_eta:.4f}', f'{(1-corrected_eta)*100:.2f}% rectification'],
]

col_labels = ['Experiment', 'Gap', 'A mean (mV)', 'B mean (mV)', 'η = A/B', 'Purpose']

table = ax.table(cellText=table_data, colLabels=col_labels,
                cellLoc='center', loc='center',
                colWidths=[0.2, 0.1, 0.12, 0.12, 0.12, 0.22])

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.8)

# Style header
for j in range(len(col_labels)):
    table[0, j].set_facecolor('#37474F')
    table[0, j].set_text_props(color='white', fontweight='bold')

# Highlight corrected row
for j in range(len(col_labels)):
    table[4, j].set_facecolor('#FFF9C4')
    table[4, j].set_text_props(fontweight='bold')

ax.set_title('Summary: ABBA Rectification Measurements', fontsize=13, fontweight='bold', pad=20)

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/summary_table.png')
plt.close()

print(f"\n{'='*50}")
print(f"All plots saved to {OUTPUT_DIR}/")
print(f"{'='*50}")
for f in sorted(os.listdir(OUTPUT_DIR)):
    if f.endswith('.png'):
        print(f"  {f}")
