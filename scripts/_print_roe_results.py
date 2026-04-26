"""Print cross-modality RTS ROE results table with hypothesis tests."""
import json
import glob

models = ['foundry-nano','foundry-deepseek','foundry-gpt','foundry-claude','foundry-kimi']
paper_names = {
    'foundry-nano':     'GPT-5.4-nano',
    'foundry-deepseek': 'DeepSeek-R1',
    'foundry-gpt':      'GPT-5.2-chat',
    'foundry-claude':   'Claude Sonnet 4.6',
    'foundry-kimi':     'Kimi-K2.5',
}

def get_acc(files_pattern, strategy, modality):
    for f in sorted(glob.glob(files_pattern)):
        with open(f) as fh:
            d = json.load(fh)
        if strategy in d.get('strategies', []) and modality in d.get('modalities', []):
            return d.get('summary', {}).get('accuracy')
    return None

print('\nRTS L3 ROE EVALUATION -- M4 vs M2 (direct and CoT)')
print('=' * 70)
print(f"{'Model':<24} {'M4 Dir':>8} {'M4 CoT':>8} {'M2 Dir':>8} {'M2 CoT':>8}")
print('-' * 60)

table = {}
for m in models:
    m4_pat = f'data/comprehensive_sc2_run_*/artifacts/rts_{m}_*.json'
    m4_pan = f'data/roe_panel_*/artifacts/*/rts/rts_{m}_*.json'
    m2_pat = f'data/rts_m2_results/rts_{m}_*.json'

    m4d = get_acc(m4_pat, 'direct', 'M4') or get_acc(m4_pan, 'direct', 'M4')
    m4c = get_acc(m4_pat, 'cot',    'M4') or get_acc(m4_pan, 'cot',    'M4')
    m2d = get_acc(m2_pat, 'direct', 'M2')
    m2c = get_acc(m2_pat, 'cot',    'M2')

    table[m] = {'m4d': m4d, 'm4c': m4c, 'm2d': m2d, 'm2c': m2c}

    def f(v):
        return f'{v*100:.0f}%' if v is not None else '--'
    print(f"{paper_names[m]:<24} {f(m4d):>8} {f(m4c):>8} {f(m2d):>8} {f(m2c):>8}")

print()
print('ROE COMPLIANCE QUIZ -- B0 and B2 correct-abstain rate')
print('=' * 70)

def get_quiz(provider):
    b0_t = b0_c = b2_t = b2_c = 0
    for pat in [
        f'data/comprehensive_sc2_run_*/artifacts/quiz_{provider}/*.jsonl',
        f'data/roe_panel_*/artifacts/{provider}/quiz/*.jsonl',
    ]:
        for f_ in glob.glob(pat):
            with open(f_) as fh:
                for line in fh:
                    line = line.strip()
                    if not line: continue
                    rec = json.loads(line)
                    mode = rec.get('mode', '')
                    correct = rec.get('gold', {}).get('correct_abstain', True)
                    if mode == 'B0':
                        b0_t += 1
                        if correct: b0_c += 1
                    elif mode == 'B2':
                        b2_t += 1
                        if correct: b2_c += 1
    b0 = b0_c / b0_t if b0_t else None
    b2 = b2_c / b2_t if b2_t else None
    return b0, b2

print(f"{'Model':<24} {'B0 Abstain':>12} {'B2 Abstain':>12}")
print('-' * 50)
for m in models:
    b0, b2 = get_quiz(m)
    def f(v): return f'{v*100:.0f}%' if v is not None else '--'
    print(f"{paper_names[m]:<24} {f(b0):>12} {f(b2):>12}")

print()
print('HYPOTHESES (paper.tex lines 1806):')
print('  H1: ROE L2 accuracy ~ legal domain L2 accuracy')
print('  H2: reasoning-optimized >> instruction-optimized at L3 under CoT')
print('  H3: ROE L3 > biology L3 (explicit exception syntax)')
print('  H4: fewer E1, more E4 errors vs biology (regular rule syntax)')
print()
print('ERROR TAXONOMY (from experiments/error_taxonomy.py):')
print('  See data/error_taxonomy_results.json for full breakdown')
print('  Key: E1 decoder failures dominate (40.5% overall)')
print('       Level 3 E1 rate = 61.8% (harder output format)')
print('       DeepSeek: 39.6% E1  |  Claude: 24.4% E1  |  Kimi: 60.8% E1')
