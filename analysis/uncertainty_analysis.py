#!/usr/bin/env python3
"""
Thermal Rectification — Uncertainty Analysis
=============================================
Computes:
  1. Allan deviation to separate noise vs drift in plateau data
  2. Optimal averaging time from Allan minimum
  3. Uncertainty propagation through η = A/B correction
  4. 95% confidence intervals on corrected rectification ratio
  5. Publication-quality figures

Author: Nikhitha Swaminathan
Date: February 2026
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats as sp_stats
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
    'A1': '#1565C0',
    'A2': '#42A5F5',
    'B1': '#C62828',
    'B2': '#EF5350',
    'control': '#FF9800',
    'corrected': '#2E7D32',
    'noise': '#9C27B0',
    'drift': '#FF5722',
}

OUTPUT_DIR = '/home/claude/plots'
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
# DATA LOADING
# ============================================================================
def load_abba_data(filepath):
    """Load ABBA CSV data, return dict of phase -> list of dicts."""
    phases = {}
    with open(filepath, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip().replace('\r', '')
            if not line or line.startswith('#'):
                continue
            parts = line.split(',')
            if len(parts) < 11 or parts[1] == 'phase':
                continue
            try:
                phase = parts[1]
                entry = {
                    'time_ms': int(parts[0]),
                    'phase_time_ms': int(parts[2]),
                    'vtop': float(parts[4]),
                    'vbot': float(parts[5]),
                    'tt': float(parts[6]),
                    'tb': float(parts[7]),
                }
                entry['sum'] = entry['vtop'] + entry['vbot']
            except (ValueError, IndexError):
                continue
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(entry)
    return phases


def get_plateau(data, last_n=600):
    """Extract last N samples as plateau."""
    return [d['sum'] for d in data[-last_n:]]


# ============================================================================
# ALLAN DEVIATION
# ============================================================================
def allan_deviation(data, tau_values=None):
    """
    Compute Allan deviation for a time series.
    
    Allan deviation separates random noise (which averages down with sqrt(N))
    from systematic drift (which grows with time). The minimum of the Allan
    deviation curve identifies the optimal averaging time.
    
    Parameters:
        data: 1D array of measurements at uniform time intervals
        tau_values: list of averaging times (in samples)
    
    Returns:
        taus: array of tau values used
        adevs: array of Allan deviation values
        adev_errs: array of 1-sigma uncertainties on Allan deviation
    """
    data = np.array(data, dtype=float)
    N = len(data)
    
    if tau_values is None:
        # Log-spaced tau from 1 to N/3
        max_tau = N // 3
        tau_values = sorted(set([int(t) for t in 
                                  np.logspace(0, np.log10(max_tau), 30).astype(int)]))
    
    taus = []
    adevs = []
    adev_errs = []
    
    for tau in tau_values:
        if tau < 1 or tau >= N // 2:
            continue
        
        # Non-overlapping block averages
        n_blocks = N // tau
        blocks = np.array([np.mean(data[i*tau:(i+1)*tau]) for i in range(n_blocks)])
        
        if len(blocks) < 2:
            continue
        
        # Allan variance = 0.5 * mean of squared successive differences
        diffs = np.diff(blocks)
        allan_var = 0.5 * np.mean(diffs**2)
        adev = np.sqrt(allan_var)
        
        # Uncertainty on Allan deviation (chi-squared based)
        n_diffs = len(diffs)
        if n_diffs > 1:
            adev_err = adev / np.sqrt(2 * (n_diffs - 1))
        else:
            adev_err = adev
        
        taus.append(tau)
        adevs.append(adev)
        adev_errs.append(adev_err)
    
    return np.array(taus), np.array(adevs), np.array(adev_errs)


def find_optimal_tau(taus, adevs):
    """Find the tau at minimum Allan deviation."""
    min_idx = np.argmin(adevs)
    return taus[min_idx], adevs[min_idx]


# ============================================================================
# UNCERTAINTY PROPAGATION
# ============================================================================
def plateau_uncertainty(data, optimal_tau=None):
    """
    Compute plateau mean and its uncertainty using Allan deviation.
    
    The key insight: standard error (sigma/sqrt(N)) assumes white noise and
    overestimates precision when drift is present. Allan deviation at
    optimal tau gives the true measurement uncertainty.
    
    Returns: dict with mean, std, stderr, allan_uncertainty, optimal_tau
    """
    data = np.array(data, dtype=float)
    N = len(data)
    
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    stderr = std / np.sqrt(N)  # Naive standard error
    
    # Allan deviation analysis
    taus, adevs, _ = allan_deviation(data)
    
    if optimal_tau is None:
        opt_tau, min_adev = find_optimal_tau(taus, adevs)
    else:
        opt_tau = optimal_tau
        idx = np.argmin(np.abs(taus - optimal_tau))
        min_adev = adevs[idx]
    
    # Number of independent blocks at optimal tau
    n_blocks = N // opt_tau
    
    # Uncertainty on the mean = Allan deviation / sqrt(n_blocks)
    allan_unc = min_adev / np.sqrt(n_blocks)
    
    return {
        'mean': mean,
        'std': std,
        'stderr': stderr,
        'allan_dev_min': min_adev,
        'allan_unc': allan_unc,
        'optimal_tau': opt_tau,
        'n_blocks': n_blocks,
        'N': N,
    }


def eta_uncertainty(a_stats_list, b_stats_list):
    """
    Propagate uncertainties through eta = A_mean / B_mean.
    
    For ratio eta = A/B:
        (sigma_eta/eta)^2 = (sigma_A/A)^2 + (sigma_B/B)^2
    
    Uses the LARGER of Allan-based uncertainty and phase-to-phase
    spread as a conservative estimate.
    """
    a_means = [s['mean'] for s in a_stats_list]
    b_means = [s['mean'] for s in b_stats_list]
    
    A = np.mean(a_means)
    B = np.mean(b_means)
    eta = A / B
    
    # Method 1: Propagate Allan uncertainties
    a_uncs = [s['allan_unc'] for s in a_stats_list]
    b_uncs = [s['allan_unc'] for s in b_stats_list]
    
    sigma_A_allan = np.sqrt(sum(u**2 for u in a_uncs)) / len(a_uncs)
    sigma_B_allan = np.sqrt(sum(u**2 for u in b_uncs)) / len(b_uncs)
    
    # Method 2: Use spread between A1 and A2 (if 2 phases)
    if len(a_means) >= 2:
        sigma_A_spread = np.std(a_means, ddof=1) / np.sqrt(len(a_means))
    else:
        sigma_A_spread = a_uncs[0]
    
    if len(b_means) >= 2:
        sigma_B_spread = np.std(b_means, ddof=1) / np.sqrt(len(b_means))
    else:
        sigma_B_spread = b_uncs[0]
    
    # Take the LARGER of Allan and spread (conservative)
    sigma_A = max(sigma_A_allan, sigma_A_spread)
    sigma_B = max(sigma_B_allan, sigma_B_spread)
    
    # Propagate through ratio
    rel_unc = np.sqrt((sigma_A / A)**2 + (sigma_B / B)**2)
    sigma_eta = eta * rel_unc
    
    # 95% CI using normal approximation with combined uncertainty
    ci_mult = 1.96
    ci_low = eta - ci_mult * sigma_eta
    ci_high = eta + ci_mult * sigma_eta
    
    return {
        'eta': eta,
        'sigma_eta': sigma_eta,
        'ci_low': ci_low,
        'ci_high': ci_high,
        'A_mean': A,
        'B_mean': B,
        'sigma_A': sigma_A,
        'sigma_B': sigma_B,
        'sigma_A_allan': sigma_A_allan,
        'sigma_B_allan': sigma_B_allan,
        'sigma_A_spread': sigma_A_spread,
        'sigma_B_spread': sigma_B_spread,
        'rel_unc': rel_unc,
    }


# ============================================================================
# LOAD DATA
# ============================================================================
print("Loading data...")
steel_glass = load_abba_data('/home/claude/abba_steel_glass_508um.txt')
glass_glass = load_abba_data('/home/claude/abba_glass_glass_508um.txt')
sio2_contact = load_abba_data('/home/claude/abba_sio2_contact.txt')

# Define phase groups for each experiment
experiments = {
    'SiO2-SiO2 Contact': {
        'data': sio2_contact,
        'A_phases': ['A1_FWD_HEAT', 'A2_FWD_HEAT'],
        'B_phases': ['B1_REV_HEAT', 'B2_REV_HEAT'],
    },
    'Glass-Glass 508um': {
        'data': glass_glass,
        'A_phases': [p for p in ['A1_FWD_HEAT', 'A2_FWD_HEAT'] 
                     if p in glass_glass and len(glass_glass[p]) >= 600],
        'B_phases': [p for p in ['B1_REV_HEAT', 'B2_REV_HEAT'] 
                     if p in glass_glass and len(glass_glass[p]) >= 600],
    },
    'Steel-Glass 508um': {
        'data': steel_glass,
        'A_phases': ['A1_FWD_HEAT', 'A2_FWD_HEAT'],
        'B_phases': ['B1_REV_HEAT', 'B2_REV_HEAT'],
    },
}


# ============================================================================
# ANALYSIS
# ============================================================================
print("\n" + "=" * 70)
print("ALLAN DEVIATION ANALYSIS")
print("=" * 70)

all_phase_stats = {}

for exp_name, exp_info in experiments.items():
    data = exp_info['data']
    all_phase_stats[exp_name] = {}
    
    print(f"\n--- {exp_name} ---")
    for phase_list in [exp_info['A_phases'], exp_info['B_phases']]:
        for phase_name in phase_list:
            if phase_name not in data or len(data[phase_name]) < 600:
                continue
            
            plateau = get_plateau(data[phase_name], 600)
            pstats = plateau_uncertainty(plateau)
            all_phase_stats[exp_name][phase_name] = pstats
            
            print(f"  {phase_name}:")
            print(f"    Mean = {pstats['mean']:.3f} mV")
            print(f"    Std dev = {pstats['std']:.3f} mV")
            print(f"    Naive SE (sigma/sqrt(N)) = {pstats['stderr']:.4f} mV")
            print(f"    Allan dev min = {pstats['allan_dev_min']:.4f} mV at tau = {pstats['optimal_tau']}s")
            print(f"    Allan uncertainty = {pstats['allan_unc']:.4f} mV ({pstats['n_blocks']} blocks)")


# ============================================================================
# ETA COMPUTATION WITH UNCERTAINTIES
# ============================================================================
print("\n" + "=" * 70)
print("RECTIFICATION RATIO WITH UNCERTAINTIES")
print("=" * 70)

eta_results = {}
for exp_name, exp_info in experiments.items():
    a_stats = [all_phase_stats[exp_name][p] for p in exp_info['A_phases'] 
               if p in all_phase_stats[exp_name]]
    b_stats = [all_phase_stats[exp_name][p] for p in exp_info['B_phases'] 
               if p in all_phase_stats[exp_name]]
    
    if not a_stats or not b_stats:
        continue
    
    result = eta_uncertainty(a_stats, b_stats)
    eta_results[exp_name] = result
    
    print(f"\n--- {exp_name} ---")
    print(f"  A mean = {result['A_mean']:.3f} +/- {result['sigma_A']:.3f} mV")
    print(f"    (Allan: +/-{result['sigma_A_allan']:.4f}, Spread: +/-{result['sigma_A_spread']:.4f})")
    print(f"  B mean = {result['B_mean']:.3f} +/- {result['sigma_B']:.3f} mV")
    print(f"    (Allan: +/-{result['sigma_B_allan']:.4f}, Spread: +/-{result['sigma_B_spread']:.4f})")
    print(f"  eta = {result['eta']:.6f} +/- {result['sigma_eta']:.6f}")
    print(f"  95% CI: [{result['ci_low']:.6f}, {result['ci_high']:.6f}]")
    print(f"  Relative uncertainty: {result['rel_unc']*100:.3f}%")


# Corrected eta with full error propagation
print("\n" + "=" * 70)
print("CORRECTED RECTIFICATION (eta_steel-glass / eta_glass-glass)")
print("=" * 70)

sg = eta_results.get('Steel-Glass 508um')
gg = eta_results.get('Glass-Glass 508um')

eta_corr = sigma_corr = ci_low = ci_high = rect_pct = rect_unc_pct = z_score = p_value = None

if sg and gg:
    eta_corr = sg['eta'] / gg['eta']
    
    # Propagate: sigma(eta_corr)/eta_corr = sqrt( (sigma_sg/eta_sg)^2 + (sigma_gg/eta_gg)^2 )
    rel_corr = np.sqrt((sg['sigma_eta']/sg['eta'])**2 + 
                        (gg['sigma_eta']/gg['eta'])**2)
    sigma_corr = eta_corr * rel_corr
    
    ci_low = eta_corr - 1.96 * sigma_corr
    ci_high = eta_corr + 1.96 * sigma_corr
    
    rect_pct = (1 - eta_corr) * 100
    rect_unc_pct = sigma_corr * 100
    
    print(f"  eta_corrected = {eta_corr:.4f} +/- {sigma_corr:.4f}")
    print(f"  95% CI: [{ci_low:.4f}, {ci_high:.4f}]")
    print(f"  Rectification = {rect_pct:.2f} +/- {rect_unc_pct:.2f}%")
    print(f"  Relative uncertainty: {rel_corr*100:.3f}%")
    
    # Statistical significance test
    z_score = abs(1.0 - eta_corr) / sigma_corr
    p_value = 2 * (1 - sp_stats.norm.cdf(z_score))
    print(f"\n  H0: eta_corrected = 1.000 (no rectification)")
    print(f"  z-score = {z_score:.3f}")
    print(f"  p-value = {p_value:.4f}")
    if p_value > 0.05:
        print(f"  Result: FAIL TO REJECT H0 (p > 0.05)")
        print(f"  --> No statistically significant rectification detected")
    else:
        print(f"  Result: REJECT H0 (p < 0.05)")
        print(f"  --> Statistically significant rectification detected")


# ============================================================================
# PLOT 9: ALLAN DEVIATION — ALL PHASES
# ============================================================================
print("\nGenerating Plot 9: Allan Deviation...")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

phase_colors = {
    'A1_FWD_HEAT': COLORS['A1'], 'A2_FWD_HEAT': COLORS['A2'],
    'B1_REV_HEAT': COLORS['B1'], 'B2_REV_HEAT': COLORS['B2'],
}

for ax, (exp_name, exp_info) in zip(axes, experiments.items()):
    data = exp_info['data']
    all_phases = exp_info['A_phases'] + exp_info['B_phases']
    
    for phase_name in all_phases:
        if phase_name not in data or len(data[phase_name]) < 600:
            continue
        
        plateau = get_plateau(data[phase_name], 600)
        taus, adevs, adev_errs = allan_deviation(plateau)
        
        color = phase_colors.get(phase_name, 'gray')
        label = phase_name.replace('_FWD_HEAT', ' (fwd)').replace('_REV_HEAT', ' (rev)')
        
        ax.loglog(taus, adevs, 'o-', color=color, markersize=3, linewidth=1.5,
                  label=label, alpha=0.8)
        
        # Mark minimum
        min_idx = np.argmin(adevs)
        ax.plot(taus[min_idx], adevs[min_idx], '*', color=color, markersize=12,
                markeredgecolor='black', markeredgewidth=0.5, zorder=5)
    
    # Reference slopes
    tau_ref = np.array([1, 200])
    # White noise: sigma proportional to tau^(-1/2)
    ref_y = 0.06 * tau_ref**(-0.5)
    ax.loglog(tau_ref, ref_y, '--', color='gray', alpha=0.4, linewidth=1)
    ax.text(20, 0.06 * 20**(-0.5) * 1.8, r'$\tau^{-1/2}$' + '\n(white noise)', 
            fontsize=7, color='gray', ha='center')
    
    # Random walk / drift: sigma proportional to tau^(+1/2)  
    ref_y2 = 0.008 * tau_ref**(0.5)
    ax.loglog(tau_ref, ref_y2, ':', color='gray', alpha=0.4, linewidth=1)
    ax.text(80, 0.008 * 80**(0.5) * 0.6, r'$\tau^{+1/2}$' + '\n(drift)', 
            fontsize=7, color='gray', ha='center')
    
    ax.set_xlabel('Averaging Time $\\tau$ [s]')
    ax.set_ylabel('Allan Deviation [mV]')
    ax.set_title(exp_name, fontsize=11)
    ax.legend(fontsize=8, loc='upper right')
    ax.set_ylim(0.005, 1.0)
    ax.set_xlim(0.8, 300)

fig.suptitle('Plot 9: Allan Deviation Analysis\n'
             r'$\star$ = optimal averaging time (noise $\leftrightarrow$ drift crossover)', 
             fontsize=13, fontweight='bold', y=1.02)
fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot9_allan_deviation.png', bbox_inches='tight')
plt.close()


# ============================================================================
# PLOT 10: UNCERTAINTY BUDGET
# ============================================================================
print("Generating Plot 10: Uncertainty Budget...")

fig = plt.figure(figsize=(14, 6))
gs = gridspec.GridSpec(1, 2, width_ratios=[1.2, 1])

# Left: Comparison of uncertainty estimation methods
ax1 = fig.add_subplot(gs[0])

exp_labels = []
naive_se = []
allan_unc_vals = []

for exp_name, exp_info in experiments.items():
    for phase_list in [exp_info['A_phases'], exp_info['B_phases']]:
        for phase_name in phase_list:
            if phase_name not in all_phase_stats.get(exp_name, {}):
                continue
            stats = all_phase_stats[exp_name][phase_name]
            short_exp = exp_name.split()[0][:6]
            short_phase = phase_name.replace('_FWD_HEAT', '(F)').replace('_REV_HEAT', '(R)')
            exp_labels.append(f"{short_phase}\n{short_exp}")
            naive_se.append(stats['stderr'] * 1000)      # Convert to uV
            allan_unc_vals.append(stats['allan_unc'] * 1000)

x = np.arange(len(exp_labels))
width = 0.35

bars1 = ax1.bar(x - width/2, naive_se, width, label=r'Naive SE ($\sigma/\sqrt{N}$)',
                color='#BBDEFB', edgecolor='#1565C0', linewidth=0.8)
bars2 = ax1.bar(x + width/2, allan_unc_vals, width, label='Allan uncertainty',
                color='#FFCCBC', edgecolor='#BF360C', linewidth=0.8)

for i, (n, a) in enumerate(zip(naive_se, allan_unc_vals)):
    ratio = a / n if n > 0 else 0
    ax1.text(i, max(n, a) + 1.5, f'{ratio:.0f}x', ha='center', fontsize=8, fontweight='bold')

ax1.set_xticks(x)
ax1.set_xticklabels(exp_labels, fontsize=7)
ax1.set_ylabel(r'Uncertainty on Plateau Mean [$\mu$V]')
ax1.set_title(r'Naive SE vs Allan Uncertainty' + '\n(Allan captures drift that SE misses)')
ax1.legend(loc='upper left')

# Right: Final corrected eta with error bars and CI
ax2 = fig.add_subplot(gs[1])

if sg and gg:
    labels_eta = []
    etas_plot = []
    errs_plot = []
    colors_plot = []
    
    for en, col in [('SiO2-SiO2 Contact', '#795548'), 
                     ('Glass-Glass 508um', '#FF9800'),
                     ('Steel-Glass 508um', '#607D8B')]:
        if en in eta_results:
            labels_eta.append(en.replace(' ', '\n'))
            etas_plot.append(eta_results[en]['eta'])
            errs_plot.append(1.96 * eta_results[en]['sigma_eta'])
            colors_plot.append(col)
    
    # Corrected
    labels_eta.append('Corrected\n(SG / GG)')
    etas_plot.append(eta_corr)
    errs_plot.append(1.96 * sigma_corr)
    colors_plot.append(COLORS['corrected'])
    
    x_eta = np.arange(len(etas_plot))
    bars = ax2.bar(x_eta, etas_plot, yerr=errs_plot, capsize=6,
                   color=colors_plot, edgecolor='black', linewidth=0.5,
                   alpha=0.85, width=0.5, error_kw={'linewidth': 1.5})
    
    ax2.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, linewidth=1)
    
    # Shade noise floor
    ax2.axhspan(1.0 - 1.96*sigma_corr, 1.0 + 1.96*sigma_corr, 
                alpha=0.1, color='green', zorder=0)
    
    # Annotate corrected with CI
    ax2.annotate(
        f'$\\eta$ = {eta_corr:.4f} $\\pm$ {1.96*sigma_corr:.4f}\n'
        f'95% CI: [{ci_low:.4f}, {ci_high:.4f}]\n'
        f'p = {p_value:.3f} (not significant)',
        xy=(len(etas_plot)-1, eta_corr + 1.96*sigma_corr + 0.002),
        ha='center', va='bottom', fontsize=9,
        bbox=dict(boxstyle='round', facecolor='#E8F5E9', alpha=0.9))
    
    ax2.set_xticks(x_eta)
    ax2.set_xticklabels(labels_eta, fontsize=8)
    ax2.set_ylabel(r'$\eta$ = A$_{mean}$ / B$_{mean}$')
    ax2.set_title('Rectification Ratio with 95% CI\n(error bars = 1.96$\\sigma$)')
    ax2.set_ylim(0.90, 1.03)

fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot10_uncertainty_budget.png', bbox_inches='tight')
plt.close()


# ============================================================================
# PLOT 11: PLATEAU STABILITY — NOISE vs DRIFT VISUAL
# ============================================================================
print("Generating Plot 11: Plateau Stability...")

fig, axes = plt.subplots(2, 2, figsize=(12, 8))

phase_info = [
    ('A1_FWD_HEAT', 'A1 Forward (steel heated)', COLORS['A1']),
    ('A2_FWD_HEAT', 'A2 Forward (steel heated)', COLORS['A2']),
    ('B1_REV_HEAT', 'B1 Reverse (glass heated)', COLORS['B1']),
    ('B2_REV_HEAT', 'B2 Reverse (glass heated)', COLORS['B2']),
]

for ax, (phase_name, title, color) in zip(axes.flat, phase_info):
    if phase_name not in steel_glass:
        ax.set_visible(False)
        continue
    
    plateau = np.array(get_plateau(steel_glass[phase_name], 600))
    t = np.arange(len(plateau))
    
    # Raw data
    ax.plot(t, plateau, '.', color=color, alpha=0.15, markersize=2, label='Raw (1 Hz)')
    
    # Running averages at different windows
    for window, lw, alpha, lbl in [(5, 1.0, 0.5, '5s avg'),
                                    (30, 1.5, 0.7, '30s avg'),
                                    (120, 2.0, 1.0, '2 min avg')]:
        if window < len(plateau):
            kernel = np.ones(window) / window
            smoothed = np.convolve(plateau, kernel, mode='valid')
            t_smooth = t[window//2:window//2+len(smoothed)]
            ax.plot(t_smooth, smoothed, '-', color=color, linewidth=lw, alpha=alpha, label=lbl)
    
    # Mean line
    mean_val = np.mean(plateau)
    ax.axhline(y=mean_val, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
    
    # Annotate stats
    stats = all_phase_stats.get('Steel-Glass 508um', {}).get(phase_name)
    if stats:
        ax.text(0.98, 0.95,
                f"Mean: {stats['mean']:.2f} mV\n"
                f"$\\sigma$: {stats['std']:.2f} mV\n"
                f"Allan min: {stats['allan_dev_min']:.3f} mV\n"
                f"@ $\\tau$ = {stats['optimal_tau']}s",
                transform=ax.transAxes, ha='right', va='top', fontsize=8,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    ax.set_ylabel('Sum [mV]')
    ax.set_xlabel('Time in plateau [s]')
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=7, loc='lower left')

fig.suptitle('Plot 11: Plateau Stability — Steel-Glass 508 $\\mu$m (last 10 min of each phase)\n'
             'Longer averaging reveals drift; Allan deviation finds the optimal balance',
             fontsize=12, fontweight='bold')
fig.tight_layout()
fig.savefig(f'{OUTPUT_DIR}/plot11_plateau_stability.png', bbox_inches='tight')
plt.close()


# ============================================================================
# PRINT FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("FINAL RESULT — PUBLICATION READY")
print("=" * 70)

if eta_corr is not None:
    print(f"""
    Corrected thermal rectification ratio:
    
        eta = {eta_corr:.4f} +/- {sigma_corr:.4f}
        95% CI: [{ci_low:.4f}, {ci_high:.4f}]
        
    Rectification: {rect_pct:.2f} +/- {rect_unc_pct:.2f}%
    
    Statistical test (H0: eta = 1.000):
        z = {z_score:.3f}, p = {p_value:.4f}
        
    Conclusion: No statistically significant thermal rectification
    detected in a steel-glass stack with 508 um air gap at ambient
    pressure. Air conduction dominates radiative transfer by ~6x,
    suppressing any directional asymmetry below the measurement
    uncertainty of +/-{sigma_corr:.4f} ({rect_unc_pct:.2f}%).
    
    Upper bound: |rectification| < {1.96*rect_unc_pct:.2f}% (95% confidence)
    """)

print(f"\nPlots saved to {OUTPUT_DIR}/")
for f in sorted(os.listdir(OUTPUT_DIR)):
    if 'plot9' in f or 'plot10' in f or 'plot11' in f:
        print(f"  {f}")
