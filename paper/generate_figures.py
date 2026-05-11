"""Generate figures for DeFAb dataset paper (NeurIPS 2026 E&D).

Design system
-------------
Palette (matches TikZ definecolor in paper.tex):
  defabBlue  #1F3A6B  — primary structural blue
  defabTeal  #3D6B7A  — secondary teal
  defabGold  #D9A441  — accent gold
  defabRed   #B0413E  — alarm / worst results
  defabGray  #6B7280  — neutral / annotations

Typography: Times New Roman (serif), 7-8pt labels, 8-9pt titles.
All figures: 300 dpi, tight bbox, hairline axes, white bar edges.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import numpy as np
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), 'figures')
os.makedirs(OUT_DIR, exist_ok=True)

# =====================================================================
# Design system
# =====================================================================
PAL = {
    'blue':  '#1F3A6B',
    'teal':  '#3D6B7A',
    'gold':  '#D9A441',
    'red':   '#B0413E',
    'gray':  '#6B7280',
    # Light tints
    'blue_l':  '#E8EDF5',
    'teal_l':  '#E6EFF1',
    'gold_l':  '#FBF3E2',
    'red_l':   '#F8ECEB',
    'gray_l':  '#F3F4F6',
}

BASE_RC = {
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size': 8,
    'axes.labelsize': 8,
    'axes.titlesize': 9,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
    'axes.linewidth': 0.5,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'grid.linewidth': 0.35,
    'grid.alpha': 0.4,
}
plt.rcParams.update(BASE_RC)


def _wilson_ci(n, p):
    """Wilson 95% CI half-width for proportion p with n trials."""
    z = 1.96
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return half


# =====================================================================
# Figure 4: Main results grid (3 panels)
# =====================================================================

# Shared data for figure 4 panels
_REND_ROB     = [23.5,  9.1, 15.5,  7.8]  # DeepSeek, GPT, Claude, Kimi
_MODELS_SHORT = ['DeepSeek\nR1', 'GPT\n5.2', 'Claude\n4.6', 'Kimi\nK2.5']
_MODELS_HM    = ['DeepSeek-R1', 'Claude 4.6', 'Kimi-K2.5', 'GPT-5.2']
_MODS         = ['M1', 'M2', 'M3', 'M4', 'Rend.\nRob.']
_DATA_HM      = [
    [21.5, 85.6, 94.1, 87.8, 23.5],  # DeepSeek
    [19.0, 87.0, 91.1, 88.1, 15.5],  # Claude
    [14.6, 75.9, 76.5, 75.6,  7.8],  # Kimi
    [22.0, 75.1, 72.8, 75.6,  9.1],  # GPT
]
_GRADED = {
    'DeepSeek-R1': [29.0,  5.4, 6.0, 11.4, 48.2],
    'GPT-5.2':     [50.0,  7.1, 0.0,  6.1, 36.8],
    'Claude 4.6':  [72.0, 13.0, 0.0,  2.9, 12.1],
    'Kimi-K2.5':   [83.7,  2.4, 0.0,  0.0, 13.9],
}
# Score colors: sequential gradient through the palette endpoints
# red(#B0413E) -> burnt-orange(#C07840) -> gold(#D9A441) -> sage-teal(#6A8A7A) -> teal(#3D6B7A)
_SCORE_COLORS = [PAL['red'], '#C07840', PAL['gold'], '#6A8A7A', PAL['teal']]
_SCORE_LABELS = ['Score 0 (unresolved)', '0.25', '0.5', '0.75 (weak conserv.)', '1.0 (conservative)']


def _draw_rend_rob_panel(ax, models_short=None, rend_rob=None):
    """Panel (a): rendering-robust accuracy — all models clearly failing."""
    if models_short is None:
        models_short = _MODELS_SHORT
    if rend_rob is None:
        rend_rob = _REND_ROB

    x    = np.arange(len(models_short))
    n_l2 = 374
    ci   = [_wilson_ci(n_l2, v/100)*100 for v in rend_rob]

    bar_colors = [PAL['red'] if v <= 16.7 else PAL['blue'] for v in rend_rob]

    bars = ax.bar(x, rend_rob, 0.52,
                  color=bar_colors, edgecolor='white', linewidth=0.4,
                  yerr=ci, capsize=2.0,
                  error_kw={'elinewidth': 0.7, 'ecolor': PAL['gray'], 'capthick': 0.7})

    for i, (v, b) in enumerate(zip(rend_rob, bars)):
        ax.text(b.get_x() + b.get_width()/2, v + ci[i] + 1.5, f'{v:.1f}%',
                ha='center', va='bottom', fontsize=5.8,
                color=PAL['red'] if rend_rob[i] <= 16.7 else PAL['blue'],
                fontweight='bold')

    ax.axhline(16.7, color=PAL['red'], linewidth=1.0, linestyle='--', alpha=0.85, zorder=3)
    ax.axhline(100.0, color=PAL['gray'], linewidth=0.8, linestyle='--', alpha=0.65, zorder=3)
    # Labels in pure data coordinates — avoids blended-transform PDF dimension errors
    ax.text(0.05, 18.5, 'Random (1/6)',
            ha='left', va='bottom', fontsize=5.5, color=PAL['red'], fontweight='bold')
    ax.text(0.05, 101.5, 'ASP ceiling',
            ha='left', va='bottom', fontsize=5.5, color=PAL['gray'])

    ax.set_ylabel('Rendering-Robust\nAccuracy (%)', fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(models_short, fontsize=6.5)
    ax.set_ylim(0, 108)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(25))
    ax.tick_params(axis='x', length=0)
    ax.set_title('(a) Rendering-Robust Accuracy', fontsize=8, pad=4)


def _draw_heatmap_panel(ax):
    """Panel (b): accuracy by rendering modality heatmap."""
    from matplotlib.colors import LinearSegmentedColormap
    data_hm = np.array(_DATA_HM)
    mods = _MODS
    models_hm = _MODELS_HM

    cmap_r = LinearSegmentedColormap.from_list(
        'defab_r', ['#F2C9C8', '#F5E6C8', '#C6D9DC', '#D0DBF0'], N=256)
    ax.imshow(data_hm, cmap=cmap_r, aspect='auto', vmin=0, vmax=100)

    ax.set_xticks(np.arange(len(mods)))
    ax.set_yticks(np.arange(len(models_hm)))
    ax.set_xticklabels(mods, ha='center', fontsize=6.5)
    ax.set_yticklabels(models_hm, fontsize=6.5)

    for i in range(len(models_hm)):
        for j in range(len(mods)):
            val = data_hm[i, j]
            fg = 'black' if 25 < val < 85 else ('white' if val >= 85 else 'black')
            fc = PAL['red'] if j == 4 else fg
            ax.text(j, i, f'{val:.0f}', ha='center', va='center',
                    fontsize=6.5, fontweight='bold', color=fc)

    ax.axvline(3.5, color=PAL['red'], linewidth=0.8, alpha=0.6)
    ax.set_title('(b) Accuracy by Modality', fontsize=8, pad=4)
    ax.tick_params(left=False, bottom=False)
    for spine in ax.spines.values():
        spine.set_visible(False)


def _draw_graded_panel(ax):
    """Panel (c): graded score distribution at L3."""
    models_c = list(_GRADED.keys())
    bottoms = np.zeros(len(models_c))
    score_vals = [0, 0.25, 0.5, 0.75, 1.0]

    for k, (sval, sc, sl) in enumerate(zip(score_vals, _SCORE_COLORS, _SCORE_LABELS)):
        vals = [_GRADED[m][k] for m in models_c]
        ax.barh(models_c, vals, left=bottoms,
                color=sc, edgecolor='white', linewidth=0.3,
                label=sl, height=0.55)
        for i, (v, b) in enumerate(zip(vals, bottoms)):
            if v > 8:
                ax.text(b + v/2, i, f'{v:.0f}%',
                        ha='center', va='center', fontsize=5.5,
                        color='white' if sc in (PAL['red'], PAL['teal']) else 'black',
                        fontweight='bold')
        bottoms = bottoms + np.array(vals)

    ax.set_xlim(0, 105)
    ax.set_xlabel('Fraction of L3 responses (%)', fontsize=7)
    ax.set_yticks(range(len(models_c)))
    ax.set_yticklabels(models_c, fontsize=6.5)
    ax.yaxis.set_tick_params(length=0)
    ax.set_title('(c) L3 Graded Score Distribution', fontsize=8, pad=4)
    # No in-axes legend — placed at figure level in fig_results() below
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(25))


def fig_results():
    """Three-panel results figure.

    4a: Rendering-robust accuracy per model — all models below ASP ceiling,
        two models at or below 16.7% random chance. Primary failure visual.
    4b: Accuracy by rendering modality M1-M4 plus rendering-robust column.
    4c: Graded score distribution at L3 — Score=0 dominates for Claude/Kimi.

    The score-color legend for panel (c) is rendered as a horizontal strip
    below panel (c) so it never overlaps the bars and stays readable.
    """
    fig = plt.figure(figsize=(7.2, 4.4), constrained_layout=False)
    gs  = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.05, 1.1],
                           wspace=0.52, left=0.10, right=0.97,
                           top=0.93, bottom=0.30)

    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1])
    ax_c = fig.add_subplot(gs[2])

    _draw_rend_rob_panel(ax_a)
    _draw_heatmap_panel(ax_b)
    _draw_graded_panel(ax_c)

    # Horizontal score-color legend for panel (c), centred under the full
    # figure width at the bottom, outside all three plotting areas.
    score_handles = [mpatches.Patch(color=c, label=l)
                     for c, l in zip(_SCORE_COLORS, _SCORE_LABELS)]
    fig.legend(handles=score_handles,
               loc='lower center',
               bbox_to_anchor=(0.5, 0.0),
               bbox_transform=fig.transFigure,
               fontsize=6.5, handlelength=1.0, handletextpad=0.4,
               columnspacing=1.4,
               framealpha=0.0, edgecolor='none',
               ncol=5, borderpad=0.2,
               title='Panel (c) graded-score key',
               title_fontsize=6.5)

    return fig


def fig_cot_variance():
    """Variance analysis of the chain-of-thought effect.

    For each (model, level) cell we plot the signed delta
    (CoT accuracy - Direct accuracy). A stable prompting regime
    would have all eight cells near zero; the actual spread is
    enormous and the sign reverses between L2 and L3 for every
    reasoning model.

    Bars sorted by signed magnitude. Positive (CoT helps) = teal.
    Negative (CoT hurts) = red. Vertical zero line. Sigma annotation.
    """
    # CoT - Direct, percentage points (model, level, delta)
    cells = [
        ('GPT 5.2',     'L3', 87.1 -  7.9),  # +79.2
        ('DeepSeek R1', 'L3', 92.9 - 37.1),  # +55.8
        ('Kimi K2.5',   'L3', 27.6 -  0.8),  # +26.8
        ('Kimi K2.5',   'L2', 70.4 - 71.9),  # -1.5
        ('DeepSeek R1', 'L2', 71.4 - 73.7),  # -2.3
        ('Claude 4.6',  'L3',  9.3 - 23.6),  # -14.3
        ('Claude 4.6',  'L2', 52.3 - 79.3),  # -27.0
        ('GPT 5.2',     'L2', 47.5 - 78.5),  # -31.0
    ]
    # Sort by signed delta, largest positive at top
    cells = sorted(cells, key=lambda r: -r[2])
    labels = [f'{m}  {lvl}' for m, lvl, _ in cells]
    deltas = [d for _, _, d in cells]
    colors = [PAL['teal'] if d > 0 else PAL['red'] for d in deltas]

    sigma = float(np.std(deltas, ddof=1))
    rng   = max(deltas) - min(deltas)

    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    y = np.arange(len(cells))
    bars = ax.barh(y, deltas, height=0.62, color=colors,
                   edgecolor='white', linewidth=0.4)

    # Annotate each bar with its signed value
    for i, (d, b) in enumerate(zip(deltas, bars)):
        ha = 'left' if d > 0 else 'right'
        x_off = 1.5 if d > 0 else -1.5
        ax.text(d + x_off, i, f'{d:+.1f}',
                ha=ha, va='center', fontsize=6,
                color=PAL['teal'] if d > 0 else PAL['red'],
                fontweight='bold')

    # Zero baseline
    ax.axvline(0, color=PAL['gray'], linewidth=0.7, alpha=0.85, zorder=3)

    # Sigma annotation (upper right corner inside axes)
    ax.text(0.985, 0.97,
            f'$\\sigma = {sigma:.1f}$ pp\nrange = {rng:.0f} pp',
            transform=ax.transAxes,
            ha='right', va='top', fontsize=6.5,
            color=PAL['gray'], fontstyle='italic',
            bbox=dict(boxstyle='round,pad=0.25',
                      facecolor='white', edgecolor=PAL['gray'],
                      linewidth=0.4, alpha=0.92))

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel('CoT effect: $\\mathrm{Acc}_{\\mathrm{CoT}} - \\mathrm{Acc}_{\\mathrm{Direct}}$ (pp)',
                  fontsize=7)
    ax.set_xlim(-40, 90)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(20))
    ax.set_title('CoT effect variance across (model, level) cells',
                 fontsize=8, pad=4)
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)

    fig.tight_layout(pad=0.6)
    return fig


# =====================================================================
# Figure 3: Provenance timeline + composition bars
# =====================================================================

def fig_sources():
    """Two-panel figure:

    3a: KB provenance timeline 1984-2026, color-coded by source class.
    3b: Dataset composition by tier x level (symlog horizontal bars).
    """
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.0, 3.0),
                                      gridspec_kw={'width_ratios': [1.0, 1.2]})

    # --- Panel (a): Provenance timeline ---
    # Each entry: (name, year_start, year_end_or_latest, class)
    # Classes: govt, encyclopedic, biomedical, game
    class_col = {
        'govt':         PAL['blue'],
        'encyclopedic': PAL['teal'],
        'biomedical':   PAL['gold'],
        'game':         PAL['red'],
    }
    class_label = {
        'govt':         'Govt. AI Programs',
        'encyclopedic': 'Encyclopedic / Community',
        'biomedical':   'Biomedical',
        'game':         'Game-Grounded',
    }

    kbs = [
        ('Cyc / OpenCyc',   1984, 2012, 'govt'),
        ('WordNet',         1985, 2012, 'govt'),
        ('LKIF Core',       2007, 2010, 'govt'),
        ('MatOnto',         2015, 2021, 'govt'),
        ('ConceptNet',      2004, 2021, 'encyclopedic'),
        ('Wikidata',        2012, 2026, 'encyclopedic'),
        ('YAGO',            2007, 2025, 'encyclopedic'),
        ('BabelNet',        2010, 2023, 'encyclopedic'),
        ('UMLS',            1990, 2025, 'biomedical'),
        ('Gene Ontology',   2000, 2026, 'biomedical'),
        ('MeSH',            1963, 2026, 'biomedical'),
        ('SUMO',            2001, 2026, 'biomedical'),
        ('FrameNet',        1997, 2016, 'encyclopedic'),
        ('sc2live / RTS',   2026, 2026, 'game'),
    ]

    yticks   = []
    yticklbls = []
    seen_classes = set()

    for i, (name, y0, y1, cls) in enumerate(reversed(kbs)):
        color = class_col[cls]
        bar_len = max(y1 - y0, 0.5)
        ax_a.barh(i, bar_len, left=y0, height=0.55,
                  color=color, edgecolor='white', linewidth=0.3, alpha=0.85)
        yticks.append(i)
        yticklbls.append(name)
        if cls not in seen_classes:
            seen_classes.add(cls)

    ax_a.set_yticks(yticks)
    ax_a.set_yticklabels(yticklbls, fontsize=5.5)
    ax_a.set_xlim(1980, 2028)
    ax_a.set_xlabel('Year', fontsize=7)
    ax_a.set_title('(a) KB Provenance 1984–2026', fontsize=8, pad=4)
    ax_a.xaxis.set_major_locator(mticker.MultipleLocator(10))
    ax_a.tick_params(axis='y', length=0)

    # Legend for classes: placed below the panel as a horizontal strip so it
    # never overlaps the bars (especially the bottom ones: SUMO, FrameNet,
    # sc2live/RTS).
    legend_patches = [mpatches.Patch(color=class_col[c], label=class_label[c])
                      for c in ['govt', 'encyclopedic', 'biomedical', 'game']]
    ax_a.legend(handles=legend_patches, fontsize=5.5,
                loc='upper center', bbox_to_anchor=(0.5, -0.18),
                ncol=4, framealpha=0.0, edgecolor='none',
                handlelength=1.0, columnspacing=1.0, borderpad=0.2)

    # --- Panel (b): Dataset composition ---
    tiers     = ['Tier 0\n(baseline)', 'Tier 1\n(cross-ont.)',
                 'Tier 2\n(domain)',   'Tier 2+\n(UMLS)',
                 'Tier 3\n(encyclopedic)', 'Synthetic']
    l1_counts = [0,      182652, 0,     0,     0,    0]
    l2_counts = [374,    141859, 31477, 13425, 2580, 374]
    l3_counts = [35,     0,      0,     0,     0,    35]

    y    = np.arange(len(tiers))
    hbar = 0.52

    b1 = ax_b.barh(y, l1_counts, hbar, color=PAL['teal'], label='L1 Fact',
                   edgecolor='white', linewidth=0.3, alpha=0.85)
    b2 = ax_b.barh(y, l2_counts, hbar, left=l1_counts, color=PAL['blue'],
                   label='L2 Rule', edgecolor='white', linewidth=0.3, alpha=0.85)

    left_l3 = [a + b for a, b in zip(l1_counts, l2_counts)]
    b3 = ax_b.barh(y, l3_counts, hbar, left=left_l3, color=PAL['red'],
                   label='L3 Defeater', edgecolor='white', linewidth=0.3, alpha=0.9)

    ax_b.set_xscale('symlog', linthresh=100)
    ax_b.set_xlabel('Instance count', fontsize=7)
    ax_b.set_yticks(y)
    ax_b.set_yticklabels(tiers, fontsize=6)
    ax_b.set_xlim(0, 420000)
    ax_b.legend(loc='lower right', framealpha=0.9, edgecolor=PAL['gray'],
                fontsize=6, handlelength=1.0)
    ax_b.set_title('(b) Dataset Composition (symlog)', fontsize=8, pad=4)
    ax_b.tick_params(axis='y', length=0)

    for i, (a, b, c) in enumerate(zip(l1_counts, l2_counts, l3_counts)):
        total = a + b + c
        if total > 0:
            x_pos = (total * 1.08) + 30 if total < 100 else total * 1.03
            ax_b.text(x_pos, i, f'{total:,}',
                      va='center', fontsize=5, color=PAL['gray'])

    fig.tight_layout(w_pad=1.5)
    return fig


# =====================================================================
# Figure 5: Difficulty stratification (appendix)
# =====================================================================

def fig_difficulty():
    """Two-panel difficulty stratification (current L3 set vs DeFAb-Hard).

    Both panels share the same n=35 Tier 0 L3 release. Each shows the
    current distribution in cool color (blue/teal), the DeFAb-Hard target
    region in warm gold, and a labeled gap so the empty space between
    them reads as an explicit pre-registered design target rather than
    a quiet visual annotation.
    """
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(6.4, 2.6),
                                      gridspec_kw={'wspace': 0.30})

    # ---- Panel (a): novelty distribution ----
    # Data: 22 instances at Nov*=0, 8 at 0.25, 5 at 0.5.  Total n=35.
    nov_centers = [0.0, 0.25, 0.5]
    nov_counts  = [22, 8, 5]
    bar_w = 0.10
    bars_a = ax_a.bar(nov_centers, nov_counts, width=bar_w,
                       color=PAL['blue'], edgecolor='white', linewidth=0.5,
                       alpha=0.88, label='current L3 ($n=35$)')
    for x, c in zip(nov_centers, nov_counts):
        ax_a.text(x, c + 0.7, str(c), ha='center', va='bottom',
                  fontsize=7, color=PAL['blue'], fontweight='bold')

    ax_a.axvspan(0.55, 1.02, alpha=0.22, color=PAL['gold'])
    ax_a.text(0.78, 20, 'H1 target',
              ha='center', va='center', fontsize=8,
              color=PAL['gold'], fontweight='bold')
    ax_a.text(0.78, 17, r'$\mathrm{Nov}^* \!\in\! [0.5, 1.0]$',
              ha='center', va='center', fontsize=7,
              color=PAL['gold'])
    ax_a.text(0.78, 14.5, r'(0 of 35 in set)',
              ha='center', va='center', fontsize=6,
              color=PAL['gray'], fontstyle='italic')

    ax_a.set_xlabel(r'Predicate novelty $\mathrm{Nov}^*$', fontsize=8)
    ax_a.set_ylabel('Instance count', fontsize=8)
    ax_a.set_title('(a) Novelty distribution', fontsize=8.5, pad=4)
    ax_a.set_xlim(-0.10, 1.05)
    ax_a.set_ylim(0, 24)
    ax_a.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax_a.yaxis.set_major_locator(mticker.MultipleLocator(5))
    ax_a.tick_params(axis='both', which='major', labelsize=7)
    ax_a.spines['top'].set_visible(False)
    ax_a.spines['right'].set_visible(False)

    # ---- Panel (b): support size on log x-axis ----
    supp_centers = [4, 5, 6, 7, 8, 9, 10]
    supp_counts  = [3, 7, 9, 7, 5, 2, 2]
    for x, c in zip(supp_centers, supp_counts):
        w = x * 0.12
        ax_b.bar(x, c, width=w, color=PAL['teal'],
                 edgecolor='white', linewidth=0.5, alpha=0.88)
        ax_b.text(x, c + 0.4, str(c), ha='center', va='bottom',
                  fontsize=6.5, color=PAL['teal'], fontweight='bold')

    ax_b.axvspan(50, 200, alpha=0.22, color=PAL['gold'])
    ax_b.text(100, 20, 'H2 target',
              ha='center', va='center', fontsize=8,
              color=PAL['gold'], fontweight='bold')
    ax_b.text(100, 17, r'$|\mathcal{D}| \!\in\! \{50,100,200\}$',
              ha='center', va='center', fontsize=7,
              color=PAL['gold'])
    ax_b.text(100, 14.5, r'(0 of 35 in set)',
              ha='center', va='center', fontsize=6,
              color=PAL['gray'], fontstyle='italic')

    # Prominent gap indicator: thick gray double-arrow with explicit label
    ax_b.annotate('', xy=(48, 1.0), xytext=(11, 1.0),
                  arrowprops=dict(arrowstyle='<->', color=PAL['gray'],
                                  lw=1.2, mutation_scale=8, alpha=0.85))
    ax_b.text(np.sqrt(11 * 48), 1.7,
              r'$\mathbf{5\!\times\!}$ gap (empty)',
              ha='center', va='bottom',
              fontsize=7, color=PAL['gray'], fontweight='bold')

    ax_b.set_xscale('log')
    ax_b.set_xlim(3, 260)
    ax_b.set_ylim(0, 24)
    ax_b.set_xlabel(r'Support size $|\mathrm{Supp}|$ (log scale)', fontsize=8)
    ax_b.set_ylabel('Instance count', fontsize=8)
    ax_b.set_title('(b) Support size distribution', fontsize=8.5, pad=4)
    ax_b.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax_b.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax_b.set_xticks([4, 6, 10, 50, 100, 200])
    ax_b.tick_params(axis='both', which='major', labelsize=7)
    ax_b.spines['top'].set_visible(False)
    ax_b.spines['right'].set_visible(False)

    return fig


# =====================================================================
# Figure: DeFAb-Hard provisional results (May 11 2026)
# =====================================================================

def fig_defab_hard():
    """Two-panel DeFAb-Hard results figure.

    Panel (a): per-axis accuracy (H1, H2, H3) under direct vs CoT prompting
    for the two completed frontier models (GPT-5.2 and Claude 4.6).

    Panel (b): pooled accuracy comparison with the symbolic solver baseline,
    visualizing the model-LLM structural gap on the difficulty extension.
    """
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.0, 3.0),
                                      gridspec_kw={'width_ratios': [1.5, 1.0],
                                                   'wspace': 0.35})

    axes_labels = ['H1\nhigh-novelty', 'H2\ndeep-chain', 'H3\nmulti-anomaly']
    n_axes = [35, 100, 100]

    # Per-axis CoT accuracy — complete 4-model panel
    deepseek_cot = [82.1, 98.9, 59.0]
    gpt_cot      = [74.3, 79.8, 54.5]
    kimi_cot     = [17.1, 3.0,  9.1]
    claude_cot   = [5.9,  4.1,  1.0]

    x = np.arange(len(axes_labels))
    bw = 0.18

    bars_ds  = ax_a.bar(x - 1.5*bw, deepseek_cot, bw,
                         color=PAL['teal'], edgecolor='white', linewidth=0.4,
                         label='DeepSeek-R1 CoT')
    bars_gpt = ax_a.bar(x - 0.5*bw, gpt_cot, bw,
                         color=PAL['blue'], edgecolor='white', linewidth=0.4,
                         label='GPT-5.2 CoT')
    bars_kim = ax_a.bar(x + 0.5*bw, kimi_cot, bw,
                         color=PAL['gold'], edgecolor='white', linewidth=0.4,
                         label='Kimi-K2.5 CoT')
    bars_cl  = ax_a.bar(x + 1.5*bw, claude_cot, bw,
                         color=PAL['red'], edgecolor='white', linewidth=0.4,
                         label='Claude 4.6 CoT')

    for bars, vals in [(bars_ds, deepseek_cot), (bars_gpt, gpt_cot),
                       (bars_kim, kimi_cot), (bars_cl, claude_cot)]:
        for b, v in zip(bars, vals):
            if v >= 4.0:
                ax_a.text(b.get_x() + b.get_width()/2, v + 1.5, f'{v:.0f}',
                          ha='center', va='bottom', fontsize=5.0,
                          color=PAL['gray'], fontweight='bold')

    ax_a.axhline(100.0, color=PAL['gray'], linewidth=0.7, linestyle='--', alpha=0.6)
    ax_a.text(0.02, 102, 'Symbolic (100%)',
              ha='left', va='bottom', fontsize=5.5, color=PAL['gray'])
    ax_a.axhline(16.7, color=PAL['red'], linewidth=0.8, linestyle=':', alpha=0.5)
    ax_a.text(2.55, 18.5, 'Random (1/6)',
              ha='right', va='bottom', fontsize=5.5, color=PAL['red'])

    ax_a.set_xticks(x)
    ax_a.set_xticklabels([f'{lbl}\n(n={n})' for lbl, n in zip(axes_labels, n_axes)],
                          fontsize=6.5)
    ax_a.set_ylabel('Per-axis CoT accuracy (%)', fontsize=7)
    ax_a.set_ylim(0, 112)
    ax_a.yaxis.set_major_locator(mticker.MultipleLocator(25))
    ax_a.set_title('(a) DeFAb-Hard per-axis CoT accuracy\n(all direct $\\leq$10%; 4 models complete)',
                    fontsize=7.5, pad=4)
    ax_a.legend(loc='upper left', fontsize=5.8, framealpha=0.92,
                edgecolor=PAL['gray'], handlelength=0.9, ncol=2, columnspacing=0.5)

    pooled_models = ['Symbolic\nverifier', 'DeepSeek\nR1',
                     'GPT-5.2', 'Kimi\nK2.5', 'Claude\n4.6']
    pooled_acc = [100.0, 53.3, 39.1, 3.8, 1.5]
    pooled_n = [235, 409, 466, 468, 464]
    pooled_colors = [PAL['gray'], PAL['teal'], PAL['blue'], PAL['gold'], PAL['red']]

    xb = np.arange(len(pooled_models))
    bars_b = ax_b.bar(xb, pooled_acc, 0.6,
                       color=pooled_colors, edgecolor='white', linewidth=0.4)

    for b, v, n in zip(bars_b, pooled_acc, pooled_n):
        ax_b.text(b.get_x() + b.get_width()/2, v + 2.5, f'{v:.1f}%',
                  ha='center', va='bottom', fontsize=6.0, fontweight='bold',
                  color=PAL['gray'])
        ax_b.text(b.get_x() + b.get_width()/2, -7.5, f'$n={n}$',
                  ha='center', va='top', fontsize=4.8, color=PAL['gray'])

    ax_b.axhline(16.7, color=PAL['red'], linewidth=0.8, linestyle=':', alpha=0.5)
    ax_b.set_xticks(xb)
    ax_b.set_xticklabels(pooled_models, fontsize=6.5)
    ax_b.set_ylabel('Pooled accuracy (%)', fontsize=7)
    ax_b.set_ylim(0, 110)
    ax_b.yaxis.set_major_locator(mticker.MultipleLocator(25))
    ax_b.set_title('(b) Symbolic vs frontier LLM\non DeFAb-Hard',
                    fontsize=8, pad=4)
    ax_b.tick_params(axis='x', length=0)

    fig.suptitle('DeFAb-Hard results (May 11 2026; complete 4-model panel; symbolic solver 100%)',
                  fontsize=8.5, y=1.02, color=PAL['blue'])

    fig.tight_layout(pad=0.6)
    return fig


# =====================================================================
# Figure: Tier 1 cross-ontology pilot results
# =====================================================================

def fig_tier1():
    """Tier 1 cross-ontology L2 accuracy vs Tier 0 reference.

    Grouped bars: Tier-0 vs Tier-1 per model, with delta annotation.
    Shows the ranking inversion: DeepSeek gains, Claude/Kimi lose ~16 pp.
    """
    models = ['DeepSeek\nR1', 'GPT\n5.2', 'Claude\n4.6', 'Kimi\nK2.5']
    tier0  = [73.7, 78.5, 79.3, 71.9]
    tier1  = [85.6, 75.0, 63.5, 55.8]
    delta  = [t1 - t0 for t0, t1 in zip(tier0, tier1)]

    x = np.arange(len(models))
    bw = 0.35

    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    bars0 = ax.bar(x - bw/2, tier0, bw, color=PAL['teal_l'],
                   edgecolor=PAL['teal'], linewidth=0.6, label='Tier~0 (expert, $n=374$)')
    bars1 = ax.bar(x + bw/2, tier1, bw, color=PAL['blue'],
                   edgecolor='white', linewidth=0.4, label='Tier~1 (cross-ontology, $n=104$)')

    for i, (b0, b1, d) in enumerate(zip(bars0, bars1, delta)):
        color = PAL['teal'] if d > 0 else PAL['red']
        sign = '+' if d > 0 else ''
        ax.text(b1.get_x() + b1.get_width()/2, b1.get_height() + 1.2,
                f'{sign}{d:.1f}', ha='center', va='bottom', fontsize=6.5,
                color=color, fontweight='bold')
        ax.text(b0.get_x() + b0.get_width()/2, b0.get_height() + 0.5,
                f'{tier0[i]:.0f}', ha='center', va='bottom', fontsize=5.5,
                color=PAL['gray'])
        ax.text(b1.get_x() + b1.get_width()/2, b1.get_height() + 4.2,
                f'{tier1[i]:.0f}', ha='center', va='bottom', fontsize=5.5,
                color=PAL['blue'])

    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=7)
    ax.set_ylabel('L2 Accuracy (M4 direct, %)', fontsize=7)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
    ax.legend(loc='lower left', fontsize=6.5, framealpha=0.9,
              edgecolor=PAL['gray'], handlelength=1.0)
    ax.set_title('Tier~1 vs Tier~0: cross-ontology vocabulary generalization',
                 fontsize=8, pad=4)
    ax.tick_params(axis='x', length=0)

    ax.text(0.98, 0.97,
            'Structural reasoning transfers (DeepSeek +11.9 pp).\n'
            'Vocabulary-bound performance does not (Claude \u221215.8 pp).',
            transform=ax.transAxes, ha='right', va='top', fontsize=6,
            color=PAL['gray'], fontstyle='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor=PAL['gray'], linewidth=0.4, alpha=0.9))

    fig.tight_layout(pad=0.6)
    return fig


# =====================================================================
# Figure: E4 ROE compliance quiz results
# =====================================================================

def fig_e4_roe():
    """E4 quiz-mode ROE compliance: correct-abstain rate by model x mode.

    Two panels:
    (a) correct-abstain rate (6 scenarios per mode)
    (b) orders admitted per mode (zero = degenerate abstain policy)
    """
    models = ['GPT-5.2', 'Claude 4.6', 'DeepSeek-R1', 'Kimi-K2.5']
    modes  = ['B0', 'B1', 'B2']
    # correct_abstain / 6 per (model, mode)
    ca_data = {
        'GPT-5.2':    [4, 4, 4],
        'Claude 4.6': [4, 4, 4],
        'DeepSeek-R1':[5, 6, 5],
        'Kimi-K2.5':  [6, 6, 6],
    }
    orders_data = {
        'GPT-5.2':    [6, 6, 6],
        'Claude 4.6': [6, 6, 6],
        'DeepSeek-R1':[3, 2, 3],
        'Kimi-K2.5':  [0, 0, 0],
    }
    model_colors = [PAL['blue'], PAL['teal'], PAL['gold'], PAL['red']]

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.0, 3.0),
                                      gridspec_kw={'wspace': 0.38})

    x = np.arange(len(modes))
    bw = 0.18
    for i, (m, col) in enumerate(zip(models, model_colors)):
        offsets = (i - 1.5) * bw
        vals_a = [v / 6 * 100 for v in ca_data[m]]
        vals_b = orders_data[m]
        ax_a.bar(x + offsets, vals_a, bw, color=col,
                 edgecolor='white', linewidth=0.3, label=m)
        ax_b.bar(x + offsets, vals_b, bw, color=col,
                 edgecolor='white', linewidth=0.3)

    ax_a.axhline(100, color=PAL['gray'], linewidth=0.7, linestyle='--', alpha=0.5)
    ax_a.set_xticks(x); ax_a.set_xticklabels(modes, fontsize=7)
    ax_a.set_ylabel('Correct-abstain rate (%)', fontsize=7)
    ax_a.set_ylim(0, 112)
    ax_a.yaxis.set_major_locator(mticker.MultipleLocator(25))
    ax_a.set_title('(a) Correct-abstain rate', fontsize=8, pad=4)
    ax_a.legend(loc='lower right', fontsize=5.8, framealpha=0.9,
                edgecolor=PAL['gray'], handlelength=0.8, handletextpad=0.3,
                ncol=2, columnspacing=0.6)
    ax_a.tick_params(axis='x', length=0)

    ax_b.set_xticks(x); ax_b.set_xticklabels(modes, fontsize=7)
    ax_b.set_ylabel('Orders admitted (of 6 scenarios)', fontsize=7)
    ax_b.set_ylim(0, 8)
    ax_b.yaxis.set_major_locator(mticker.MultipleLocator(2))
    ax_b.set_title('(b) Orders admitted per mode', fontsize=8, pad=4)
    ax_b.tick_params(axis='x', length=0)
    ax_b.text(0.5, 0.92, 'Kimi: 0 orders (degenerate abstain)',
              transform=ax_b.transAxes, ha='center', va='top', fontsize=6,
              color=PAL['red'], fontstyle='italic')

    fig.suptitle('E4 quiz-mode ROE compliance (n=72, six scenarios per model per mode)',
                 fontsize=8.5, y=1.02, color=PAL['blue'])
    fig.tight_layout(pad=0.6)
    return fig


# =====================================================================
# Figure: DeFAb-Hard failure-mode taxonomy
# =====================================================================

def fig_failure_mode():
    """Four-panel failure taxonomy for Claude vs GPT on DeFAb-Hard.

    Top: error type distribution (direct vs CoT) for Claude and GPT.
    Bottom: brief illustrative comparison of response shapes.
    """
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2),
                              gridspec_kw={'wspace': 0.40})

    # --- Panel (a): Claude error distribution ---
    ax = axes[0]
    strategies = ['Direct', 'CoT']
    # Claude: antecedent-fact error dominates direct; extraction-fail dominates CoT
    claude_wrong_pct = [100.0, 94.1]  # % of wrong that are the specific error
    claude_correct_pct = [0.0, 5.9]  # H1 as representative
    labels = ['Antecedent-fact\nerror (direct)', 'Extraction\nfailure (CoT)']
    colors = [PAL['red'], '#C07840']

    x = np.array([0, 1])
    wrong = np.array(claude_wrong_pct)
    correct = np.array(claude_correct_pct)
    other = 100 - wrong - correct

    bars_w = ax.bar(x, wrong, 0.5, color=PAL['red'], edgecolor='white',
                    linewidth=0.4, label='Dominant error mode')
    bars_c = ax.bar(x, correct, 0.5, bottom=wrong, color=PAL['teal'],
                    edgecolor='white', linewidth=0.4, label='Correct')
    bars_o = ax.bar(x, other, 0.5, bottom=wrong+correct, color=PAL['gray_l'],
                    edgecolor=PAL['gray'], linewidth=0.4, label='Other error')

    for b, v in zip(bars_w, wrong):
        if v > 5:
            ax.text(b.get_x()+b.get_width()/2, v/2, f'{v:.0f}%',
                    ha='center', va='center', fontsize=6.5,
                    color='white', fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(['H1\nDirect', 'H1\nCoT'], fontsize=7)
    ax.set_ylabel('Share of evaluations (%)', fontsize=7)
    ax.set_ylim(0, 108)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(25))
    ax.set_title('(a) Claude Sonnet 4.6 failure modes', fontsize=8, pad=4)
    ax.legend(loc='upper right', fontsize=5.8, framealpha=0.9,
              edgecolor=PAL['gray'], handlelength=0.8)
    ax.tick_params(axis='x', length=0)

    # --- Panel (b): GPT H1 direct vs CoT ---
    ax2 = axes[1]
    gpt_direct_h1 = [100.0, 0.0, 0.0]   # wrong (all candidate-bypass), correct, other
    gpt_cot_h1    = [0.0, 74.3, 25.7]   # CoT: mostly correct
    cats = ['Wrong', 'Correct', 'Other']
    colors2 = [PAL['red'], PAL['teal'], PAL['gray_l']]
    ec = ['white', 'white', PAL['gray']]

    x2 = np.array([0, 1])
    bottoms = np.zeros(2)
    for k, (cat, col, ec_) in enumerate(zip(cats, colors2, ec)):
        vals = [gpt_direct_h1[k], gpt_cot_h1[k]]
        ax2.bar(x2, vals, 0.5, bottom=bottoms, color=col,
                edgecolor=ec_, linewidth=0.4, label=cat)
        for i, (b, v) in enumerate(zip(bottoms, vals)):
            if v > 8:
                ax2.text(x2[i], b + v/2, f'{v:.0f}%',
                         ha='center', va='center', fontsize=6.5,
                         color='white' if col != PAL['gray_l'] else PAL['gray'],
                         fontweight='bold')
        bottoms += np.array(vals)

    ax2.set_xticks(x2)
    ax2.set_xticklabels(['H1\nDirect', 'H1\nCoT'], fontsize=7)
    ax2.set_ylabel('Share of evaluations (%)', fontsize=7)
    ax2.set_ylim(0, 108)
    ax2.yaxis.set_major_locator(mticker.MultipleLocator(25))
    ax2.set_title('(b) GPT-5.2-chat failure modes', fontsize=8, pad=4)
    ax2.legend(loc='upper right', fontsize=5.8, framealpha=0.9,
               edgecolor=PAL['gray'], handlelength=0.8)
    ax2.tick_params(axis='x', length=0)

    fig.suptitle(
        'DeFAb-Hard failure taxonomy: format brittleness, not reasoning failure',
        fontsize=8.5, y=1.02, color=PAL['blue'])
    fig.tight_layout(pad=0.6)
    return fig


# =====================================================================
# Entry point
# =====================================================================

if __name__ == '__main__':
    print('Generating Figure 4: results grid (3 panels, panel a = rendering-robust)...')
    fig4 = fig_results()
    fig4.savefig(os.path.join(OUT_DIR, 'fig_results.pdf'), format='pdf')
    plt.close(fig4)
    print(f'  -> {OUT_DIR}/fig_results.pdf')

    print('Generating CoT variance analysis (appendix figure)...')
    figcot = fig_cot_variance()
    figcot.savefig(os.path.join(OUT_DIR, 'fig_cot_variance.pdf'), format='pdf')
    plt.close(figcot)
    print(f'  -> {OUT_DIR}/fig_cot_variance.pdf')

    print('Generating Figure 3: sources provenance + composition...')
    fig3 = fig_sources()
    fig3.savefig(os.path.join(OUT_DIR, 'fig_sources.pdf'), format='pdf')
    plt.close(fig3)
    print(f'  -> {OUT_DIR}/fig_sources.pdf')

    print('Generating Figure 5: difficulty stratification...')
    fig5 = fig_difficulty()
    fig5.savefig(os.path.join(OUT_DIR, 'fig_difficulty.pdf'), format='pdf')
    plt.close(fig5)
    print(f'  -> {OUT_DIR}/fig_difficulty.pdf')

    print('Generating DeFAb-Hard provisional results figure...')
    fig_dh = fig_defab_hard()
    fig_dh.savefig(os.path.join(OUT_DIR, 'fig_defab_hard.pdf'), format='pdf')
    plt.close(fig_dh)
    print(f'  -> {OUT_DIR}/fig_defab_hard.pdf')

    print('Generating Tier 1 cross-ontology results figure...')
    fig_t1 = fig_tier1()
    fig_t1.savefig(os.path.join(OUT_DIR, 'fig_tier1.pdf'), format='pdf')
    plt.close(fig_t1)
    print(f'  -> {OUT_DIR}/fig_tier1.pdf')

    print('Generating E4 ROE compliance figure...')
    fig_roe = fig_e4_roe()
    fig_roe.savefig(os.path.join(OUT_DIR, 'fig_e4_roe.pdf'), format='pdf')
    plt.close(fig_roe)
    print(f'  -> {OUT_DIR}/fig_e4_roe.pdf')

    print('Generating failure-mode taxonomy figure...')
    fig_fm = fig_failure_mode()
    fig_fm.savefig(os.path.join(OUT_DIR, 'fig_failure_mode.pdf'), format='pdf')
    plt.close(fig_fm)
    print(f'  -> {OUT_DIR}/fig_failure_mode.pdf')

    print('Done.')
    print('Note: Figure 1 (pipeline+generation) is TikZ in fig_pipeline.tex')
    print('      Figure 2 (IDP worked example) is TikZ in fig_level3_example.tex')
    print('      Figure 6 (finetuning) is TikZ in fig_finetuning.tex')
