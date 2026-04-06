"""Generate figures for DeFAb dataset paper (NeurIPS 2026 E&D)."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), 'figures')
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({
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
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
})


def fig_cot_dissociation():
    """Panel (a): Level 3 accuracy by prompting strategy (Direct vs CoT)."""
    models = ['DeepSeek-R1', 'GPT-5.2', 'Claude\nSonnet 4.6', 'Kimi-K2.5']
    direct = [37.1, 7.9, 23.6, 0.8]
    cot =    [92.9, 87.1, 9.3, 27.6]

    x = np.arange(len(models))
    w = 0.32

    fig, ax = plt.subplots(figsize=(3.2, 2.0))

    bars_d = ax.bar(x - w/2, direct, w, label='Direct', color='#4878A8',
                    edgecolor='white', linewidth=0.3)
    bars_c = ax.bar(x + w/2, cot, w, label='Chain-of-Thought', color='#D4553A',
                    edgecolor='white', linewidth=0.3)

    for bar in bars_d:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 1.5, f'{h:.0f}',
                ha='center', va='bottom', fontsize=6, color='#4878A8')
    for bar in bars_c:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 1.5, f'{h:.0f}',
                ha='center', va='bottom', fontsize=6, color='#D4553A')

    ax.set_ylabel('Level 3 Accuracy (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylim(0, 105)
    ax.legend(loc='upper right', framealpha=0.9, edgecolor='gray')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(25))

    return fig


def fig_modality_heatmap():
    """Panel (b): Accuracy by rendering modality (heatmap)."""
    models = ['DeepSeek-R1', 'Claude 4.6', 'Kimi-K2.5', 'GPT-5.2']
    modalities = ['M1\nNarrative', 'M2\nSemi-formal', 'M3\nAnnotated', 'M4\nFormal']
    data = np.array([
        [21.5, 85.6, 94.1, 87.8],
        [19.0, 87.0, 91.1, 88.1],
        [14.6, 75.9, 76.5, 75.6],
        [22.0, 75.1, 72.8, 75.6],
    ])

    fig, ax = plt.subplots(figsize=(3.0, 1.8))
    im = ax.imshow(data, cmap='YlOrRd_r', aspect='auto', vmin=0, vmax=100)

    ax.set_xticks(np.arange(len(modalities)))
    ax.set_yticks(np.arange(len(models)))
    ax.set_xticklabels(modalities, ha='center')
    ax.set_yticklabels(models)

    for i in range(len(models)):
        for j in range(len(modalities)):
            val = data[i, j]
            color = 'white' if val < 40 else 'black'
            ax.text(j, i, f'{val:.0f}', ha='center', va='center',
                    fontsize=7, fontweight='bold', color=color)

    ax.set_title('Accuracy (%) by Rendering Modality', fontsize=8, pad=4)
    fig.tight_layout()

    return fig


def fig_results_combined():
    """Two-panel figure: (a) CoT dissociation, (b) modality heatmap."""
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(5.5, 2.0),
                                      gridspec_kw={'width_ratios': [1.1, 1.0]})

    # --- Panel (a): CoT dissociation ---
    models = ['DeepSeek\nR1', 'GPT\n5.2', 'Claude\n4.6', 'Kimi\nK2.5']
    direct = [37.1, 7.9, 23.6, 0.8]
    cot =    [92.9, 87.1, 9.3, 27.6]

    x = np.arange(len(models))
    w = 0.32

    bars_d = ax_a.bar(x - w/2, direct, w, label='Direct', color='#4878A8',
                      edgecolor='white', linewidth=0.3)
    bars_c = ax_a.bar(x + w/2, cot, w, label='CoT', color='#D4553A',
                      edgecolor='white', linewidth=0.3)

    for bar in bars_d:
        h = bar.get_height()
        ax_a.text(bar.get_x() + bar.get_width()/2, h + 1.8, f'{h:.0f}',
                  ha='center', va='bottom', fontsize=5.5, color='#4878A8')
    for bar in bars_c:
        h = bar.get_height()
        ax_a.text(bar.get_x() + bar.get_width()/2, h + 1.8, f'{h:.0f}',
                  ha='center', va='bottom', fontsize=5.5, color='#D4553A')

    ax_a.set_ylabel('Level 3 Accuracy (%)')
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(models)
    ax_a.set_ylim(0, 108)
    ax_a.legend(loc='upper left', framealpha=0.9, edgecolor='gray',
                fontsize=6, handlelength=1.0)
    ax_a.spines['top'].set_visible(False)
    ax_a.spines['right'].set_visible(False)
    ax_a.yaxis.set_major_locator(mticker.MultipleLocator(25))
    ax_a.set_title('(a) CoT Dissociation at Level 3', fontsize=8, pad=4)

    # --- Panel (b): Modality heatmap ---
    models_hm = ['DeepSeek-R1', 'Claude 4.6', 'Kimi-K2.5', 'GPT-5.2']
    mods = ['M1', 'M2', 'M3', 'M4']
    data = np.array([
        [21.5, 85.6, 94.1, 87.8],
        [19.0, 87.0, 91.1, 88.1],
        [14.6, 75.9, 76.5, 75.6],
        [22.0, 75.1, 72.8, 75.6],
    ])

    im = ax_b.imshow(data, cmap='YlOrRd_r', aspect='auto', vmin=0, vmax=100)

    ax_b.set_xticks(np.arange(len(mods)))
    ax_b.set_yticks(np.arange(len(models_hm)))
    ax_b.set_xticklabels(mods)
    ax_b.set_yticklabels(models_hm)

    for i in range(len(models_hm)):
        for j in range(len(mods)):
            val = data[i, j]
            color = 'white' if val < 40 else 'black'
            ax_b.text(j, i, f'{val:.0f}', ha='center', va='center',
                      fontsize=6.5, fontweight='bold', color=color)

    ax_b.set_title('(b) Accuracy by Modality', fontsize=8, pad=4)

    fig.tight_layout(w_pad=1.5)
    return fig


def fig_composition():
    """Dataset composition: stacked horizontal bars by tier, colored by level."""
    tiers = ['Tier 0\n(baseline)', 'Tier 1\n(cross-ontology)', 'Tier 2\n(domain)', 'Tier 2+\n(UMLS)',
             'Tier 3\n(encyclopedic)', 'Synthetic']
    l1 = [0, 182652, 0, 0, 0, 0]
    l2 = [374, 141859, 31477, 13425, 2580, 374]
    l3 = [35, 0, 0, 0, 0, 35]

    y = np.arange(len(tiers))
    h = 0.55

    fig, ax = plt.subplots(figsize=(5.5, 1.8))

    ax.barh(y, l1, h, label='Level 1 (fact)', color='#7FCDBB', edgecolor='white', linewidth=0.3)
    ax.barh(y, l2, h, left=l1, label='Level 2 (rule)', color='#41B6C4', edgecolor='white', linewidth=0.3)
    left_l3 = [a + b for a, b in zip(l1, l2)]
    ax.barh(y, l3, h, left=left_l3, label='Level 3 (defeater)', color='#253494', edgecolor='white', linewidth=0.3)

    ax.set_xscale('symlog', linthresh=100)
    ax.set_xlabel('Instance count')
    ax.set_yticks(y)
    ax.set_yticklabels(tiers, fontsize=6.5)
    ax.legend(loc='lower right', framealpha=0.9, edgecolor='gray', fontsize=6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(0, 400000)

    for i, (a, b, c) in enumerate(zip(l1, l2, l3)):
        total = a + b + c
        if total > 0:
            ax.text(total * 1.1 + 50, i, f'{total:,}', va='center', fontsize=5.5, color='black')

    fig.tight_layout()
    return fig


if __name__ == '__main__':
    print('Generating Figure 2: results combined...')
    fig2 = fig_results_combined()
    fig2.savefig(os.path.join(OUT_DIR, 'fig_results.pdf'), format='pdf')
    plt.close(fig2)
    print(f'  -> {OUT_DIR}/fig_results.pdf')

    print('Generating Figure 3: dataset composition...')
    fig3 = fig_composition()
    fig3.savefig(os.path.join(OUT_DIR, 'fig_composition.pdf'), format='pdf')
    plt.close(fig3)
    print(f'  -> {OUT_DIR}/fig_composition.pdf')

    print('Done. Figure 1 (pipeline) is TikZ in fig_pipeline.tex.')
