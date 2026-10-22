"""
Analysis of the major-revision campaign (ASE, UMDA4GI).

    python experiments/revision_analysis/analysis.py RESULTS_CSV OUT_DIR [--val-fail zero|exclude]
    python experiments/revision_analysis/analysis.py --selftest OUT_DIR

RESULTS_CSV is experiments/results/revision/results.csv (galgo/revision_results.py collect):
one row per run and checkpoint (budget). Every table is written to OUT_DIR as CSV.

Definitions (the same in every research question, Reviewer 1, comment 5):
  improvement  change_perc_validate: % change in CPU cycles of the returned patch on the
               validation inputs (negative = faster).
  gap          per run: change_perc_validate - change_perc_train (positive = the patch
               generalises worse than it trained). Aggregated with the median of the runs.
  cell         (software, group, budget): 15 runs = 5 folds x 3 seeds.
  ranking      as in the submitted paper: per software, the median over the 15 runs of a cell,
               averaged over the five budgets, ranked across the compared groups; rank-sum
               over the four systems (lower = better).

--val-fail: a patch that fails the correctness oracle on the validation inputs is counted as
  "zero": 0% improvement (the patch is discarded and the original program is kept), or
  "exclude": left out of improvement and gap. Its rate is reported separately either way
  (val_fail_rate in cells.csv, val_fail_rates.csv per software and group). The default is
  "zero". A checkpoint with no validation status (the validation itself did not run) is
  left out with a warning: it has to be repeated.

Statistics (Reviewer 1, comment 6): runs with the same fold and seed form matched blocks.
Per software and budget: Friedman test over the compared groups, then pairwise Wilcoxon
signed-rank tests with Holm correction and the Vargha-Delaney A12 effect size; bootstrap
95% CI of each cell median. Reviewer 2: UMDA4GI against the two-edit FI and GP (comment 2),
how often the patches asked to the LLM were not used as given (comment 3) and the share of variance due to the fold, with a permutation test (comment 4). RQ3 correlations (Spearman) use every run, with Holm and
Benjamini-Hochberg adjustments, and are reported as exploratory.
"""
import argparse
import itertools
import pathlib
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

BASE = ['FI', 'RS', 'GP', 'UMDA']
LLM = ['UMDA-qwen7b', 'UMDA-llama8b', 'LLM-qwen7b', 'LLM-llama8b']
RQ4 = ['UMDA'] + LLM
ABLATIONS = [('UMDA', 'ABL-UMDA-imp'), ('UMDA', 'ABL-UMDA-k1'), ('UMDA', 'ABL-UMDA-k3'),
             ('FI', 'ABL-FI-2'), ('GP', 'ABL-GP-2')]
SOFTWARE = ['minisat_hack', 'pngOptim', 'sat4j', 'weka']
BUDGETS = [100, 250, 500, 750, 1000]
RNG = np.random.default_rng(20261016)


# ----------------------------------------------------------------------------- data
def load(path, val_fail):
    df = pd.read_csv(path)
    df = df[df['complete'] == 1].copy()
    df['checkpoint'] = df['checkpoint'].astype(int)
    df['validate_status'] = df['validate_status'].fillna('')
    df['val_failed'] = ~df['validate_status'].isin(['SUCCESS', 'NO_PATCH', ''])
    # no status = the validation did not run (infrastructure): it must be repeated, not counted
    missing = df['validate_status'] == ''
    if missing.any():
        print(f'WARNING: {missing.sum()} checkpoints without validation (left out): '
              + ', '.join(f"{r.software} {r.group} id {r.id} @{r.checkpoint}" for r in df[missing].itertuples()))
    if val_fail == 'zero':
        df.loc[df['val_failed'], 'change_perc_validate'] = 0.0
    df['improvement'] = df['change_perc_validate']
    df['gap'] = df['improvement'] - df['change_perc_train']
    df['block'] = df['fold'].astype(str) + '-' + df['seed'].astype(str)
    return df


def boot_ci(values, n=2000):
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 2:
        return np.nan, np.nan
    meds = np.median(RNG.choice(values, size=(n, len(values)), replace=True), axis=1)
    return np.percentile(meds, 2.5), np.percentile(meds, 97.5)


def a12(x, y):
    """Vargha-Delaney A12: probability that a value of x is smaller than one of y
    (here: that the first group gives a lower = better value), ties count half."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    gt = (x[:, None] < y[None, :]).sum()
    eq = (x[:, None] == y[None, :]).sum()
    return (gt + 0.5 * eq) / (len(x) * len(y))


def holm(pvalues):
    p = np.asarray(pvalues, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def bh(pvalues):
    p = np.asarray(pvalues, float)
    order = np.argsort(p)[::-1]
    adj = np.empty_like(p)
    running = 1.0
    for rank, i in enumerate(order):
        running = min(running, p[i] * len(p) / (len(p) - rank))
        adj[i] = running
    return adj


# ----------------------------------------------------------------------------- tables
def cell_summary(df):
    rows = []
    for (sw, g, b), d in df.groupby(['software', 'group', 'checkpoint']):
        lo, hi = boot_ci(d['improvement'])
        rows.append({'software': sw, 'group': g, 'budget': b, 'runs': len(d),
                     'improvement_median': d['improvement'].median(), 'improvement_ci_low': lo,
                     'improvement_ci_high': hi, 'train_median': d['change_perc_train'].median(),
                     'gap_median': d['gap'].median(), 'val_fail_rate': d['val_failed'].mean(),
                     'no_patch_rate': (d['validate_status'] == 'NO_PATCH').mean(),
                     'patch_length_mean': d['patch_length'].mean(),
                     'cached_share_mean': d['cached_share'].mean(),
                     'search_minutes_median': d['search_minutes'].median()})
    return pd.DataFrame(rows)


def val_fail_rates(df):
    """Patches that fail the correctness oracle on the validation inputs, per software and
    group: share of checkpoints over every budget, share at budget 1000 and runs affected."""
    rows = []
    for (sw, g), d in df.groupby(['software', 'group']):
        last = d[d['checkpoint'] == 1000]
        rows.append({'software': sw, 'group': g, 'runs': d['id'].nunique(),
                     'checkpoints': len(d), 'failed_checkpoints': int(d['val_failed'].sum()),
                     'fail_rate': d['val_failed'].mean(),
                     'fail_rate_1000': last['val_failed'].mean() if len(last) else np.nan,
                     'runs_with_failure': d.loc[d['val_failed'], 'id'].nunique()})
    return pd.DataFrame(rows)


def ranking(cells, groups, metric):
    c = cells[cells['group'].isin(groups)]
    per_sw = c.groupby(['software', 'group'])[metric].mean().unstack('software')
    ranks = per_sw.rank(axis=0, method='min')
    out = per_sw.add_suffix('_value').join(ranks.add_suffix('_rank'))
    out['rank_sum'] = ranks.sum(axis=1)
    return out.sort_values('rank_sum').reset_index()


def paired(df, sw, budget, g1, g2, metric):
    d = df[(df['software'] == sw) & (df['checkpoint'] == budget) & df['group'].isin([g1, g2])]
    w = d.pivot_table(index='block', columns='group', values=metric).dropna()
    if g1 not in w or g2 not in w or len(w) < 5:
        return None
    x, y = w[g1].values, w[g2].values
    if np.allclose(x, y):
        p = 1.0
    else:
        p = stats.wilcoxon(x, y, zero_method='zsplit').pvalue
    return {'software': sw, 'budget': budget, 'group_a': g1, 'group_b': g2, 'metric': metric,
            'blocks': len(w), 'median_a': np.median(x), 'median_b': np.median(y),
            'a12_a_better': a12(x, y), 'p': p}


def tests(df, groups, metrics, budgets):
    friedman, pairs = [], []
    for sw, b, m in itertools.product(SOFTWARE, budgets, metrics):
        d = df[(df['software'] == sw) & (df['checkpoint'] == b) & df['group'].isin(groups)]
        w = d.pivot_table(index='block', columns='group', values=m).dropna()
        present = [g for g in groups if g in w]
        if len(present) >= 3 and len(w) >= 5:
            try:
                p = stats.friedmanchisquare(*[w[g].values for g in present]).pvalue
            except ValueError:
                p = np.nan
            friedman.append({'software': sw, 'budget': b, 'metric': m, 'groups': len(present),
                             'blocks': len(w), 'p': p})
        block = [r for g1, g2 in itertools.combinations(present, 2)
                 if (r := paired(df, sw, b, g1, g2, m))]
        if block:
            for r, padj in zip(block, holm([r['p'] for r in block])):
                r['p_holm'] = padj
            pairs += block
    return pd.DataFrame(friedman), pd.DataFrame(pairs)


def correlations(df):
    """RQ3, exploratory: Spearman of Vt, Vc and budget with improvement and gap, every run."""
    base = df[df['group'].isin(BASE)]
    subsets = [(sw, 'all', base[base['software'] == sw]) for sw in SOFTWARE]
    subsets += [(sw, g, base[(base['software'] == sw) & (base['group'] == g)]) for sw in SOFTWARE for g in BASE]
    rows = []
    for sw_name, grp, d in subsets:
        for x, y in itertools.product(['vt', 'vc', 'checkpoint'], ['improvement', 'gap']):
            dd = d[[x, y]].dropna()
            if len(dd) < 5 or dd[x].nunique() < 2 or dd[y].nunique() < 2:
                continue
            rho, p = stats.spearmanr(dd[x], dd[y])
            rows.append({'software': sw_name, 'group': grp, 'x': x, 'y': y, 'n': len(dd),
                         'rho': rho, 'p': p})
    out = pd.DataFrame(rows)
    if len(out):
        out['p_holm'] = holm(out['p'])
        out['p_bh'] = bh(out['p'])
    return out


def llm_fallback(df):
    """Reviewer 2, comment 3: share of the patches asked to the LLM that were not used as the
    LLM gave them. malformed (could not be parsed or applied) and missing (the LLM returned
    too few) are replaced by random 1-edit patches; duplicate (well-formed but already in the
    population, or empty) is replaced by a random 1-edit patch in UMDA4GI and gets a random
    edit appended in the LLM-only algorithm. Counts are per run, so only the last checkpoint
    is used. Logs before the revision did not count duplicates (llm_duplicate empty)."""
    d = df[df['group'].isin(LLM) & (df['checkpoint'] == df['checkpoint'].max())].copy()
    if 'llm_duplicate' not in d:
        d['llm_duplicate'] = np.nan
    cols = ['llm_requested', 'llm_malformed', 'llm_missing', 'llm_duplicate', 'llm_calls', 'llm_minutes']
    for c in cols:
        if c not in d:
            d[c] = np.nan
    g = d.groupby(['group', 'software'])[cols].sum(min_count=1)
    g.insert(0, 'runs', d.groupby(['group', 'software']).size())
    for c in ['malformed', 'missing', 'duplicate']:
        g[f'{c}_rate'] = g[f'llm_{c}'] / g['llm_requested']
    g['fallback_rate'] = (g['llm_malformed'] + g['llm_missing']) / g['llm_requested']
    g['not_used_rate'] = g['fallback_rate'] + g['duplicate_rate']
    g['seconds_per_call'] = g['llm_minutes'] * 60 / g['llm_calls']
    return g.reset_index()


TARGET = re.compile(r"\('([^']*)', '([^']*)', (\d+)\)")


def diversity(df, groups):
    """Distinct edited locations / total edits of the returned patches (budget 1000)."""
    d = df[df['group'].isin(groups) & (df['checkpoint'] == 1000)]
    rows = []
    for (sw, g), dd in d.groupby(['software', 'group']):
        targets = []
        for patch in dd['best_patch'].fillna(''):
            for edit in [e for e in patch.split(' | ') if e]:
                m = TARGET.search(edit)
                if m:
                    targets.append(m.groups())
        if targets:
            rows.append({'software': sw, 'group': g, 'edits': len(targets),
                         'distinct_locations': len(set(targets)),
                         'diversity': len(set(targets)) / len(targets)})
    return pd.DataFrame(rows)


def ablation_table(df):
    rows = []
    for (g1, g2), sw, b, m in itertools.product(ABLATIONS, SOFTWARE, [1000], ['improvement', 'gap', 'patch_length']):
        r = paired(df, sw, b, g2, g1, m)       # a = ablation variant, b = original algorithm
        if r:
            rows.append(r)
    out = pd.DataFrame(rows)
    if len(out):
        out['p_holm'] = holm(out['p'])
    return out


def length_controlled(df):
    """Reviewer 2, comment 2: UMDA4GI against FI and GP limited to two edits (budget 1000)."""
    rows = []
    for g, sw, m in itertools.product(['ABL-FI-2', 'ABL-GP-2'], SOFTWARE, ['improvement', 'gap']):
        r = paired(df, sw, 1000, 'UMDA', g, m)
        if r:
            rows.append(r)
    out = pd.DataFrame(rows)
    if len(out):
        out['p_holm'] = holm(out['p'])
    return out


def eta2_fold(d, metric):
    """Share of the variance of a cell explained by the fold (between-fold sum of squares)."""
    d = d[['fold', metric]].dropna()
    total = ((d[metric] - d[metric].mean()) ** 2).sum()
    if total == 0 or d['fold'].nunique() < 2:
        return np.nan
    m = d.groupby('fold')[metric].agg(['mean', 'size'])
    return (m['size'] * (m['mean'] - d[metric].mean()) ** 2).sum() / total


def fold_variance(df, groups, n_perm=1000):
    """Reviewer 2, comment 4: how much of the variation within a cell (5 folds x 3 seeds)
    comes from the data split. eta2 of the fold, and a permutation test that shuffles the
    fold labels within the cell (with 5 folds of 3 runs, eta2 is 4/14 = 0.29 on average by
    chance alone)."""
    rows = []
    for (sw, g, b), d in df[df['group'].isin(groups)].groupby(['software', 'group', 'checkpoint']):
        for m in ['improvement', 'gap']:
            e = eta2_fold(d, m)
            if np.isnan(e):
                continue
            null = [eta2_fold(d.assign(fold=RNG.permutation(d['fold'].values)), m) for _ in range(n_perm)]
            rows.append({'software': sw, 'group': g, 'budget': b, 'metric': m, 'runs': len(d),
                         'eta2_fold': e, 'p_perm': np.mean(np.asarray(null) >= e)})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- main
def run(results, out_dir, val_fail):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = load(results, val_fail)
    written, empty = [], []

    def save(table, name):
        # an empty table (e.g. no budget 1000 yet, or no LLM runs) is reported, not written
        if len(table) and len(table.columns):
            table.to_csv(out / name, index=False)
            written.append(name)
        else:
            (out / name).unlink(missing_ok=True)
            empty.append(name)

    cells = cell_summary(df)
    save(cells, 'cells.csv')
    save(val_fail_rates(df), 'val_fail_rates.csv')
    for name, groups in [('rq1_improvement_ranking', BASE), ('rq4_improvement_ranking', RQ4)]:
        save(ranking(cells, groups, 'improvement_median'), f'{name}.csv')
    for name, groups in [('rq2_gap_ranking', BASE), ('rq4_gap_ranking', RQ4)]:
        save(ranking(cells, groups, 'gap_median'), f'{name}.csv')
    for name, groups in [('rq1_rq2', BASE), ('rq4', RQ4)]:
        fr, pw = tests(df, groups, ['improvement', 'gap'], BUDGETS)
        save(fr, f'{name}_friedman.csv')
        save(pw, f'{name}_pairwise.csv')
    save(correlations(df), 'rq3_correlations.csv')
    save(llm_fallback(df), 'rq4_llm_fallback.csv')
    save(diversity(df, BASE + LLM), 'diversity.csv')
    save(ablation_table(df), 'ablations.csv')
    save(length_controlled(df), 'length_controlled.csv')
    save(fold_variance(df, BASE), 'fold_variance.csv')
    print(f'{len(df)} complete rows, {df["id"].nunique()} runs; val-fail policy: {val_fail}')
    print('written to', out, ':', ', '.join(written))
    if empty:
        print('empty (not enough data yet):', ', '.join(empty))
    return df


def synthetic(path):
    """A results.csv with the shape of the real one, for testing (no real data)."""
    rng = np.random.default_rng(1)
    groups = BASE + LLM + [g for _, g in ABLATIONS]
    rows, rid = [], 0
    for sw, g, fold, rep in itertools.product(SOFTWARE, groups, range(1, 6), range(3)):
        rid += 1
        seed = 100 * rep + fold
        effect = {'UMDA': -12, 'FI': -15, 'RS': -10, 'GP': -6}.get(g, -8)
        final = effect + rng.normal(0, 8)
        for b in BUDGETS:
            train = final * min(1, b / 600) + rng.normal(0, 2)
            status = rng.choice(['SUCCESS', 'NO_PATCH', 'RUN_CODE_ERROR'], p=[0.85, 0.1, 0.05])
            val = 0.0 if status == 'NO_PATCH' else (np.nan if status != 'SUCCESS' else train + rng.normal(4, 5))
            n_edits = rng.integers(1, 4)
            patch = ' | '.join(f"XmlNodeDeletion<stmt>(('f.c.xml', 'stmt', {rng.integers(1, 40)}))"
                               for _ in range(n_edits)) if status != 'NO_PATCH' else ''
            rows.append({'id': rid, 'group': g, 'software': sw, 'fold': fold, 'seed': seed,
                         'checkpoint': b, 'complete': 1, 'change_perc_train': train,
                         'change_perc_validate': val, 'validate_status': status,
                         'best_patch': patch, 'patch_length': n_edits if patch else 0,
                         'vt': rng.uniform(0.2, 0.6), 'vc': rng.uniform(0.3, 0.7),
                         'cached_share': rng.uniform(0, 0.4), 'search_minutes': b * rng.uniform(0.1, 0.5),
                         'llm_requested': 1000 if g in LLM else np.nan,
                         'llm_malformed': rng.integers(0, 300) if g in LLM else np.nan,
                         'llm_missing': rng.integers(0, 100) if g in LLM else np.nan,
                         'llm_duplicate': rng.integers(0, 200) if g in LLM else np.nan,
                         'llm_calls': 19 if g in LLM else 0,
                         'llm_minutes': rng.uniform(5, 40) if g in LLM else 0.0})
    pd.DataFrame(rows).to_csv(path, index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('results', nargs='?')
    parser.add_argument('out_dir')
    parser.add_argument('--val-fail', choices=['zero', 'exclude'], default='zero')
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    if args.selftest:
        out = pathlib.Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        synthetic(out / 'synthetic_results.csv')
        run(out / 'synthetic_results.csv', out, args.val_fail)
        return
    if not args.results:
        sys.exit('RESULTS_CSV is required (or --selftest)')
    run(args.results, args.out_dir, args.val_fail)


if __name__ == '__main__':
    main()
