"""
Builds the notebooks of the revision artifact in experiments/results_revision/ (one per research
question, plus the ablations and the variance analysis requested by the reviewers).

    python experiments/revision_analysis/build_notebooks.py

The notebooks do not repeat the analysis: they call analysis.py, which writes every table once to
experiments/results_revision/analysis/, and show and explain those tables, so that the paper, the
response letter and the artifact use the same numbers. Execute them afterwards with
    jupyter nbconvert --to notebook --execute --inplace experiments/results_revision/*.ipynb
"""
import pathlib

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT = pathlib.Path(__file__).resolve().parents[1] / 'results_revision'

SETUP = '''\
import pathlib
import sys

import numpy as np
import pandas as pd
from IPython.display import display

sys.path.insert(0, str(pathlib.Path('..', 'revision_analysis').resolve()))
import analysis as A

RESULTS = 'results.csv'           # one row per run and budget (checkpoint)
OUT = pathlib.Path('analysis')    # tables written by analysis.py
REFRESH = False                   # True: recompute every table from results.csv
if REFRESH or not (OUT / 'cells.csv').exists():
    A.run(RESULTS, OUT, 'zero')
df = A.load(RESULTS, 'zero')
cells = pd.read_csv(OUT / 'cells.csv')
SW = {'minisat_hack': 'MiniSAT-hack', 'sat4j': 'Sat4J', 'weka': 'Weka', 'pngOptim': 'OptiPNG'}
pd.set_option('display.precision', 2)
pd.set_option('display.max_rows', 300)
pd.set_option('display.width', 200)'''

DEFINITIONS = '''\
**Definitions** (the same in every notebook, see the docstring of `analysis.py`):

- *improvement*: % change in CPU cycles of the returned patch on the validation inputs (negative = faster).
  A patch that fails the correctness oracle on the validation inputs counts as 0% (the original program is kept).
- *gap*: for each run, validation change minus training change, in percentage points (positive = the patch
  generalises worse than it trained). Aggregated with the median of the runs.
- *cell*: (software, algorithm, budget), 15 runs = 5 folds × 3 seeds. Each run has 1000 evaluations; the budgets
  100, 250, 500 and 750 are checkpoints of the same run.
- *ranking*: per software, the median of each cell, averaged over the five budgets and ranked; rank sum over the
  four systems (lower = better).'''


def nb(cells, name):
    notebook = new_notebook(cells=cells, metadata={
        'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}})
    nbformat.write(notebook, OUT / name)


def md(text):
    return new_markdown_cell(text)


def code(text):
    return new_code_cell(text)


def raw_and_tests(metric):
    """Cells shared by RQ1 and RQ2: medians with CI, Friedman, pairwise tests, ranking."""
    return [
        md(f'## Median {metric} per software, algorithm and budget\n\nMedian of the 15 runs with its bootstrap 95% '
           'confidence interval (2000 resamples).'),
        code(f'''\
c = cells[cells.group.isin(A.BASE)].copy()
c['value'] = c.apply(lambda r: f"{{r.{metric}_median:.2f}} [{{r.{metric}_ci_low:.2f}}, {{r.{metric}_ci_high:.2f}}]", axis=1)
display(c.pivot_table(index=['software', 'group'], columns='budget', values='value', aggfunc='first'))'''),
        md('## Friedman test per software and budget\n\nOver the four algorithms, with the 15 (fold, seed) pairs '
           'as blocks.'),
        code(f'''\
fr = pd.read_csv(OUT / 'rq1_rq2_friedman.csv')
fr = fr[fr.metric == '{metric}']
display(fr.pivot(index='software', columns='budget', values='p'))
print('significant (p < 0.05):', (fr.p < 0.05).sum(), 'of', len(fr))'''),
        md('## Pairwise comparisons\n\nWilcoxon signed-rank tests paired by fold and seed, Holm\'s correction within '
           'each (software, budget, metric), i.e. over its 6 pairs. `a12_a_better` is the probability that a run of '
           '`group_a` gives a lower (better) value than a run of `group_b`.'),
        code(f'''\
pw = pd.read_csv(OUT / 'rq1_rq2_pairwise.csv')
p = pw[pw.metric == '{metric}']
display(p[p.p_holm < 0.05])
print('significant after Holm within each family:', (p.p_holm < 0.05).sum(), 'of', len(p))'''),
        md('## Ranking'),
        code(f'''\
display(pd.read_csv(OUT / '{"rq1_improvement_ranking" if metric == "improvement" else "rq2_gap_ranking"}.csv'))'''),
        md('### Sensitivity: the same ranking with the mean instead of the median\n\nThe median is used because a '
           'few extreme runs would dominate the mean (see below); the tests are rank-based and do not depend on '
           'this choice.'),
        code(f'''\
means = (df[df.group.isin(A.BASE)].groupby(['software', 'group', 'checkpoint'])['{metric}'].mean()
         .rename('{metric}_mean').reset_index())
display(A.ranking(means, A.BASE, '{metric}_mean'))'''),
    ]


def rq1():
    return [
        md('# RQ1: validation improvement of UMDA4GI against First-Improvement, Random Search and GP\n\n' + DEFINITIONS),
        code(SETUP),
        *raw_and_tests('improvement'),
        md('## Why the median: extreme runs\n\nOn MiniSAT, one validation fold gives improvements close to −90%, '
           'while some patches make the solver several times slower on other folds.'),
        code('''\
m = df[df.group.isin(A.BASE) & (df.software == 'minisat_hack')]['improvement']
print(f'MiniSAT: min {m.min():.1f}%, max {m.max():.1f}%, runs x budgets above +50%: {(m > 50).sum()} of {len(m)}')'''),
        md('## Pairwise tests involving UMDA4GI before any correction, and with Holm over all 240'),
        code('''\
pw = pd.read_csv(OUT / 'rq1_rq2_pairwise.csv')
u = pw[((pw.group_a == 'UMDA') | (pw.group_b == 'UMDA')) & (pw.p < 0.05)]
favours = ((u.group_a == 'UMDA') & (u.median_a < u.median_b)) | ((u.group_b == 'UMDA') & (u.median_b < u.median_a))
print(f'comparisons with UMDA4GI and p < 0.05: {len(u)}, in favour of UMDA4GI (lower median): {favours.sum()}')
display(u[~favours])
print('smallest p after Holm over all', len(pw), 'comparisons:', A.holm(pw.p).min().round(3))'''),
        md('## Runs without an improving patch\n\nA run that finds no improving patch returns the original program '
           'and counts as 0%.'),
        code('''\
last = df[df.checkpoint == 1000]
print('runs with no improving patch at 1000 evaluations:', (last.validate_status == 'NO_PATCH').sum(), 'of', len(last))
display(last[last.validate_status == 'NO_PATCH'][['software', 'group', 'fold', 'seed']])'''),
        md('## OptiPNG: the one edit that improves it\n\nThe median validation improvement on OptiPNG is within 0.12 '
           'percentage points of zero for every algorithm, except in the runs whose patch deletes statement 424 of '
           '`optim.c`, the call `png_set_compression_window_bits(..., 9)` that sets a 512-byte compression window '
           'for two of OptiPNG\'s strategies.'),
        code('''\
c = cells[(cells.software == 'pngOptim') & cells.group.isin(A.BASE)]
print('largest |median validation improvement| on OptiPNG:', c.improvement_median.abs().max().round(3))
w = df[df.best_patch.fillna('').str.contains("XmlNodeDeletion<stmt>(('optim.c.xml', 'stmt', 424))", regex=False)]
print('runs whose patch deletes it:', w.id.nunique())
display(w[w.checkpoint == 1000][['group', 'fold', 'seed', 'change_perc_train', 'improvement']])'''),
        md('## Search time\n\nMinutes until the k-th evaluation of each run (median of the 15 runs), averaged over '
           'the five budgets. The runs shared the cluster nodes, so the times include that load.'),
        code('''\
t = cells[cells.group.isin(A.BASE)].groupby(['group', 'software'])['search_minutes_median'].mean().unstack()
display(t)
display(t.rank(method='min').assign(rank_sum=lambda r: r.sum(axis=1)).sort_values('rank_sum'))'''),
    ]


def rq2():
    return [
        md('# RQ2: generalisation of UMDA4GI and the three baselines\n\n' + DEFINITIONS +
           '\n\nThe gap is computed per run and then aggregated (Reviewer 1, comment 5): the median gap is not the '
           'difference between the median validation and the median training change.'),
        code(SETUP),
        *raw_and_tests('gap'),
        md('## Patch length\n\nMean number of edits of the returned patch (0 when the run found no improving patch).'),
        code('''\
b = df[df.group.isin(A.BASE)]
display(pd.DataFrame({'all budgets': b.groupby('group').patch_length.mean(),
                      '1000 evaluations': b[b.checkpoint == 1000].groupby('group').patch_length.mean()}))'''),
        md('## Patch length and gap\n\nSpearman correlation per software over every run and budget of the four '
           'algorithms, leaving out runs without a patch. See `Ablations.ipynb` for the length-controlled '
           'comparison.'),
        code('''\
from scipy.stats import spearmanr
rows = []
for sw, d in b[b.patch_length > 0].dropna(subset=['gap']).groupby('software'):
    rho, p = spearmanr(d.patch_length, d.gap)
    rows.append({'software': sw, 'n': len(d), 'rho': rho, 'p': p})
display(pd.DataFrame(rows))'''),
    ]


def rq3():
    return [
        md('# RQ3: what correlates with validation improvement and generalisation\n\n' + DEFINITIONS +
           '\n\nSpearman correlations of the budget, $V_t$ (share of evaluated variants that pass the tests) and $V_c$ '
           '(share that compile) with improvement and gap, per software (all algorithms pooled, `group = all`) and '
           'per algorithm. Every run and budget is used. With 120 correlations, $p$-values are adjusted with Holm '
           'and with Benjamini-Hochberg; the analysis is exploratory.'),
        code(SETUP),
        code('''\
corr = pd.read_csv(OUT / 'rq3_correlations.csv')
display(corr[corr.group == 'all'])'''),
        md('## Correlations that remain significant after Holm\'s correction'),
        code('display(corr[corr.p_holm < 0.05])'),
    ]


def ablations():
    return [
        md('# Ablations and patch length (Reviewer 2, comments 1 and 2)\n\n' + DEFINITIONS +
           '\n\nAt 1000 evaluations, on all four systems, five folds and three seeds:\n\n'
           '- `ABL-UMDA-imp`: UMDA4GI learning only from improving variants instead of all valid ones;\n'
           '- `ABL-UMDA-k1`, `ABL-UMDA-k3`: UMDA4GI with $k_{max}$ = 1 and 3 (the default is 2);\n'
           '- `ABL-FI-2`, `ABL-GP-2`: First-Improvement and GP limited to at most two edits per patch.\n\n'
           'Wilcoxon signed-rank tests paired by fold and seed; Holm\'s correction over the 60 tests of the '
           'ablations (improvement, gap and patch length).'),
        code(SETUP),
        code('''\
abl = pd.read_csv(OUT / 'ablations.csv')
display(abl)
print('significant after Holm:')
display(abl[abl.p_holm < 0.05])'''),
        md('## UMDA4GI learning only from improving variants: generations with nothing to learn from\n\n'
           'Runs of `ABL-UMDA-imp` in which at least one generation had no improving variant (the previous '
           'distribution is then kept).'),
        code('''\
imp = df[(df.group == 'ABL-UMDA-imp') & (df.checkpoint == 1000)]
display(imp.groupby('software').gens_without_valid.agg(runs='size', runs_with_such_generations=lambda s: (s > 0).sum()))'''),
        md('## Patch length of the two-edit baselines\n\nMedian length of the returned patch at 1000 evaluations.'),
        code('''\
last = df[df.checkpoint == 1000]
display(last[last.group.isin(['FI', 'ABL-FI-2', 'GP', 'ABL-GP-2', 'UMDA'])]
        .pivot_table(index='software', columns='group', values='patch_length', aggfunc='median'))'''),
        md('## Limiting FI and GP to two edits: change in the median gap'),
        code('''\
c = cells[cells.budget == 1000].set_index(['software', 'group'])['gap_median']
rows = [{'software': sw, 'algorithm': g, 'gap': c[(sw, g)], 'gap with two edits': c[(sw, f'ABL-{g}-2')]}
        for sw in ['minisat_hack', 'sat4j', 'weka', 'pngOptim'] for g in ['FI', 'GP']]
t = pd.DataFrame(rows)
t['lower'] = t['gap with two edits'] < t['gap']
display(t)'''),
        md('## UMDA4GI against the length-controlled baselines\n\nHolm\'s correction over these 16 tests.'),
        code("display(pd.read_csv(OUT / 'length_controlled.csv'))"),
    ]


def variance():
    return [
        md('# Fold, seed and evaluation cost (Reviewer 2, comment 4 and minor comment 1)\n\n' + DEFINITIONS),
        code(SETUP),
        md('## Share of the variance due to the fold\n\nFor every cell, $\\eta^2$ of the fold: the share of the '
           'variance of the 15 runs explained by the fold (the rest is due to the seed, i.e. the search). With 5 '
           'folds of 3 runs, a fold label with no effect gives $\\eta^2$ = 4/14 = 0.29 on average. The permutation '
           'test shuffles the fold labels 1000 times within the cell.'),
        code('''\
fv = pd.read_csv(OUT / 'fold_variance.csv')
display(fv.groupby(['metric', 'software']).agg(median_eta2=('eta2_fold', 'median'),
                                               cells_p_below_005=('p_perm', lambda p: (p < 0.05).sum()),
                                               cells=('p_perm', 'size')))
print(fv.groupby('metric').eta2_fold.median().round(2).to_dict())'''),
        md('## Candidates evaluated more than once\n\n`repeated_share`: share of the evaluations of a run whose '
           'patch had already been evaluated earlier in the same run; every algorithm counts them against its '
           'budget. MAGPIE keeps a cache of recently evaluated variants, so only part of them is answered from it '
           '(`cached_share`); the rest is run again.'),
        code('''\
c = cells[cells.group.isin(A.BASE)]
for col in ['repeated_share_mean', 'cached_share_mean']:
    display(c[c.budget == 1000].pivot(index='software', columns='group', values=col).rename_axis(columns=col))
    display(c[c.budget == 1000].groupby('group')[col].mean())'''),
        md('## Patches that fail the correctness oracle on the validation inputs'),
        code("display(pd.read_csv(OUT / 'val_fail_rates.csv'))"),
    ]


def rq4():
    return [
        md('# RQ4: does the distribution of UMDA4GI help LLM-guided search?\n\n' + DEFINITIONS +
           '\n\nGroups: UMDA4GI without LLM, UMDA4GI whose population is proposed by an LLM (`UMDA-qwen7b`, '
           '`UMDA-llama8b`) and the LLM-only algorithm (`LLM-qwen7b`, `LLM-llama8b`). The LLMs are '
           'qwen2.5-coder:7b and llama3.1:8b, served locally with Ollama.'),
        code(SETUP + '''
G = A.RQ4
print('LLM runs:', df[df.group.isin(A.LLM)].id.nunique())'''),
        md('## Median improvement and gap per software, group and budget\n\nMedian of the 15 runs with its '
           'bootstrap 95% confidence interval.'),
        code('''\
c = cells[cells.group.isin(G)].copy()
for m in ['improvement', 'gap']:
    c['value'] = c.apply(lambda r: f"{r[m + '_median']:.2f} [{r[m + '_ci_low']:.2f}, {r[m + '_ci_high']:.2f}]", axis=1)
    print(m)
    display(c.pivot_table(index=['software', 'group'], columns='budget', values='value', aggfunc='first'))'''),
        md('## Rankings'),
        code('''\
display(pd.read_csv(OUT / 'rq4_improvement_ranking.csv'))
display(pd.read_csv(OUT / 'rq4_gap_ranking.csv'))'''),
        md('## Friedman and pairwise tests\n\nFriedman over the five groups, with the 15 (fold, seed) pairs as '
           'blocks; then Wilcoxon signed-rank tests with Holm\'s correction within each (software, budget, metric), '
           'i.e. over its 10 pairs.'),
        code('''\
fr = pd.read_csv(OUT / 'rq4_friedman.csv')
display(fr.pivot_table(index=['metric', 'software'], columns='budget', values='p'))
print('Friedman p < 0.05:', fr[fr.p < 0.05].groupby('metric').size().to_dict(), 'of 20 cells per metric')
pw = pd.read_csv(OUT / 'rq4_pairwise.csv')
s = pw[(pw.p_holm < 0.05) & pw.metric.isin(['improvement', 'gap'])]
display(s)
u = s[(s.group_a == 'UMDA') | (s.group_b == 'UMDA')]
umda_better = ((u.group_a == 'UMDA') & (u.median_a < u.median_b)) | ((u.group_b == 'UMDA') & (u.median_b < u.median_a))
print(f'significant comparisons with UMDA4GI: {len(u)}, in favour of UMDA4GI: {umda_better.sum()}')'''),
        md('## Training against validation\n\nThe LLM groups improve the training inputs more than UMDA4GI, but '
           'not the validation inputs, so their gap is larger. The tests on the training change (`metric = '
           'train`) were added after seeing the results and are exploratory. Medians at 1000 evaluations:'),
        code('''\
last = cells[cells.group.isin(G) & (cells.budget == 1000)]
display(last.pivot(index='software', columns='group', values='train_median')[G].rename_axis(columns='training'))
display(last.pivot(index='software', columns='group', values='improvement_median')[G].rename_axis(columns='validation'))
display(last.pivot(index='software', columns='group', values='gap_median')[G].rename_axis(columns='gap'))'''),
        md('Each LLM group against UMDA4GI, per metric: in how many of the 20 cells (software × budget) it is '
           'significantly better or worse (Holm within the cell).'),
        code('''\
rows = []
for g in A.LLM:
    for m in ['train', 'improvement', 'gap']:
        t = pw[(pw.metric == m) & pw.group_a.isin([g, 'UMDA']) & pw.group_b.isin([g, 'UMDA'])]
        sig = t[t.p_holm < 0.05]
        g_med = np.where(sig.group_a == g, sig.median_a, sig.median_b)
        u_med = np.where(sig.group_a == g, sig.median_b, sig.median_a)
        rows.append({'group': g, 'metric': m, 'cells': len(t),
                     'LLM group better': int((g_med < u_med).sum()), 'UMDA4GI better': int((g_med > u_med).sum())})
display(pd.DataFrame(rows).pivot(index='group', columns='metric', values=['LLM group better', 'UMDA4GI better']))'''),
        md('## Does the hybrid overfit less than the LLM alone?\n\nEach UMDA4GI+LLM group against the LLM-only '
           'algorithm with the same model.'),
        code('''\
for hybrid, alone in [('UMDA-llama8b', 'LLM-llama8b'), ('UMDA-qwen7b', 'LLM-qwen7b')]:
    for m in ['gap', 'train', 'improvement']:
        t = pw[(pw.metric == m) & pw.group_a.isin([hybrid, alone]) & pw.group_b.isin([hybrid, alone])]
        h_med = np.where(t.group_a == hybrid, t.median_a, t.median_b)
        a_med = np.where(t.group_a == hybrid, t.median_b, t.median_a)
        sig = t.p_holm < 0.05
        print(f'{hybrid} vs {alone}, {m}: lower median in {(h_med < a_med).sum()}/20 cells; '
              f'significant: {int((sig & (h_med < a_med)).sum())} for the hybrid, {int((sig & (h_med > a_med)).sum())} for the LLM alone')'''),
        md('## Patch length does not explain it\n\nThe ablations show that the small gap of UMDA4GI goes with its '
           'short patches. The LLM-only patches are as short or shorter, and still generalise worse: mean number of '
           'edits at 1000 evaluations.'),
        code('''\
display(last.pivot(index='software', columns='group', values='patch_length_mean')[G])'''),
        md('## Per fold\n\nMedian gap of the 3 seeds of each fold at 1000 evaluations. On MiniSAT the large gaps '
           'of the LLM groups come mostly from fold 1; on Weka the pattern holds in every fold.'),
        code('''\
d = df[df.group.isin(G) & (df.checkpoint == 1000) & df.software.isin(['minisat_hack', 'sat4j', 'weka'])]
display(d.pivot_table(index=['software', 'group'], columns='fold', values='gap', aggfunc='median').round(1))'''),
        md('## Patches that fail the correctness oracle on the validation inputs\n\nThey count as 0% improvement. '
           'All are on MiniSAT fold 5: the patch cuts about 78% of the training cycles and the program fails on '
           'the validation inputs.'),
        code('''\
f = df[df.val_failed & df.group.isin(G)]
display(f[['software', 'group', 'id', 'fold', 'seed', 'checkpoint', 'change_perc_train', 'validate_status']])'''),
        md('## How much of the LLM output was used (Reviewer 2, comment 3)\n\nPer group and software, share of '
           'the patches asked to the LLM that were malformed, missing (the LLM returned too few) or duplicated '
           '(well-formed but already in the population, or empty). All three are replaced by random one-edit '
           'patches, in UMDA4GI+LLM and in the LLM-only algorithm. `fallback_rate` = malformed + missing; '
           '`not_used_rate` adds the duplicates. Also the time per LLM call.'),
        code('''\
fb = pd.read_csv(OUT / 'rq4_llm_fallback.csv')
display(fb)
display(fb.groupby('group')[['fallback_rate', 'not_used_rate']].agg(['min', 'max']))'''),
        md('## Diversity of the returned patches\n\nDistinct edited locations over total edits of the patches '
           'returned at 1000 evaluations, per software and pooled over the four systems.'),
        code('''\
dv = pd.read_csv(OUT / 'diversity.csv')
dv = dv[dv.group.isin(G)]
display(dv)
t = dv.groupby('group')[['distinct_locations', 'edits']].sum()
display((t.distinct_locations / t.edits).rename('pooled diversity').sort_values(ascending=False))'''),
    ]


def tables():
    return [
        md('# Tables and figures of the paper\n\nWrites the LaTeX tables of RQ1-RQ3 and RQ4 and the three '
           'figures with `paper_tables.py` into `paper/`.'),
        code(SETUP + '''
import subprocess
subprocess.run([sys.executable, str(pathlib.Path('..', 'revision_analysis', 'paper_tables.py')), str(OUT), 'paper'],
               check=True)
print(sorted(p.name for p in pathlib.Path('paper').iterdir()))'''),
    ]


def main():
    OUT.mkdir(exist_ok=True)
    for build, name in [(rq1, 'RQ1.ipynb'), (rq2, 'RQ2.ipynb'), (rq3, 'RQ3.ipynb'), (rq4, 'RQ4.ipynb'),
                        (ablations, 'Ablations.ipynb'), (variance, 'Variance_and_cost.ipynb'),
                        (tables, 'Paper_tables.ipynb')]:
        nb(build(), name)
        print('written', OUT / name)


if __name__ == '__main__':
    main()
