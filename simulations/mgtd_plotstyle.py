"""
mgtd_plotstyle.py -- one figure style for every MGTD simulation figure.

Sims 1, 2 and 3 import this so the paper's figures share fonts, colors,
line styles, reference lines and export settings.

Colors are the Okabe-Ito colorblind-safe set; every series also has its
own line style, so the figures still read in grayscale print.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Page geometry (inches). Full width for two-panel figures, one column otherwise.
FULL_WIDTH_IN = 7.0
COLUMN_WIDTH_IN = 3.4
DPI = 300

# Surface pairs: color and line style follow the pair in every figure.
PAIR_COLOR = {"glass-glass": "#0072B2", "steel-glass": "#D55E00", "gold-ceramic": "#009E73"}
PAIR_STYLE = {"glass-glass": "-", "steel-glass": "--", "gold-ceramic": "-."}
PAIR_LABEL = {"glass-glass": "Glass–glass", "steel-glass": "Steel–glass",
              "gold-ceramic": "Gold–ceramic"}

INK = "#222222"          # text, measured data
MUTED = "0.55"           # reference lines, zero line
GRID_ALPHA = 0.18

# Reference pressures shared by all figures: (Torr, short label)
REF_LINES_TORR = [
    (760.0, "Air"),
    (36.0, "Vacuum runs"),
    (10.7, "A2"),
    (7.5e-3, "Scroll floor"),
    (7.5e-6, "Chamber spec"),
]


def apply_style():
    """Set matplotlib defaults for paper figures (8 pt text, white background)."""
    plt.rcParams.update({
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 6.5,
        "legend.frameon": True,
        "legend.framealpha": 0.95,
        "legend.edgecolor": "0.8",
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "lines.linewidth": 1.5,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": DPI,
        "pdf.fonttype": 42,          # editable text in the PDF
        "svg.fonttype": "none",
    })


def draw_ref_lines(ax, refs=REF_LINES_TORR, label=True):
    """Dashed vertical reference lines, labeled just above the axes."""
    for p, text in refs:
        ax.axvline(p, color=MUTED, ls="--", lw=0.6, zorder=0)
        if label:
            ax.text(p, 1.02, text, rotation=90, transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=6, color=INK)


def panel_label(ax, text, right=False):
    """Bold (a)/(b) label inside the top corner of a panel."""
    ax.text(0.97 if right else 0.03, 0.96, text, transform=ax.transAxes, va="top",
            ha="right" if right else "left", fontweight="bold")


def save_figure(fig, path_png):
    """Save PNG (300 DPI) plus vector PDF and SVG next to it."""
    os.makedirs(os.path.dirname(path_png), exist_ok=True)
    base = os.path.splitext(path_png)[0]
    fig.savefig(base + ".png", dpi=DPI)
    fig.savefig(base + ".pdf")
    fig.savefig(base + ".svg")
    plt.close(fig)
