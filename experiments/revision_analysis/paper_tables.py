"""
LaTeX tables and figures of RQ1-RQ3 for the revised paper, from the output of analysis.py.

    python experiments/revision_analysis/paper_tables.py ANALYSIS_DIR OUT_DIR

ANALYSIS_DIR is experiments/results/revision/analysis. Writes OUT_DIR/tables_rq1_rq3.tex
(one table per \\begin{table}, then the two figure environments; same labels as the submitted
version where the table or figure already existed) and the figures RQ1_convergence and RQ2_generalisation as PDF and EPS. Needs the
LaTeX packages booktabs and multirow.

When the analysis has the LLM runs, it also writes OUT_DIR/tables_rq4.tex (the RQ4 tables, with
the labels of the submitted version for the tables that already existed, the training change
against validation, and the LLM fallback of Reviewer 2, comment 3) and the figure
RQ4_generalisation.
"""
import argparse
import pathlib

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors
import pandas as pd

BASE = ['FI', 'GP', 'RS', 'UMDA']
NAMES = {'FI': 'FI', 'GP': 'GP', 'RS': 'RandomS', 'UMDA': 'UMDA4GI',
         'ABL-UMDA-imp': 'UMDA4GI-imp', 'ABL-UMDA-k1': 'UMDA4GI $k_{max}{=}1$',
         'ABL-UMDA-k3': 'UMDA4GI $k_{max}{=}3$', 'ABL-FI-2': 'FI-2', 'ABL-GP-2': 'GP-2',
         'UMDA-llama8b': 'UMDA+llama', 'UMDA-qwen7b': 'UMDA+qwen', 'LLM-llama8b': 'LLM-llama',
         'LLM-qwen7b': 'LLM-qwen'}
# row order of the submitted RQ4 tables
RQ4 = ['UMDA', 'UMDA-llama8b', 'UMDA-qwen7b', 'LLM-llama8b', 'LLM-qwen7b']
# five groups with longer names: less space between columns, so that they fit the text width
RQ4_SMALL = r'\footnotesize\setlength{\tabcolsep}{3pt}'
RQ4_PAIRS = r'\footnotesize\setlength{\tabcolsep}{3pt}'
# row order of the submitted tables, and column order of its ranking tables
SOFTWARE = ['minisat_hack', 'sat4j', 'weka', 'pngOptim']
RANK_SOFTWARE = ['minisat_hack', 'pngOptim', 'sat4j', 'weka']
SW_NAMES = {'minisat_hack': 'MiniSAT-hack', 'sat4j': 'Sat4J', 'weka': 'Weka', 'pngOptim': 'OptimPNG'}
BUDGETS = [100, 250, 500, 750, 1000]
# OptimPNG changes are a fraction of a percentage point: one more decimal
DIGITS = {'pngOptim': 2}
# the wide tables must fit the text width of the journal template (sn-jnl)
SMALL = r'\footnotesize\setlength{\tabcolsep}{4pt}'
SHORT_METRIC = {'improvement': 'Improvement', 'gap': 'Gap', 'train': 'Training'}
METRIC_NAMES = {'improvement': 'validation improvement', 'gap': 'generalisation gap'}
# validated categorical palette (dataviz skill, slots 1-4); marker and line style also
# identify each algorithm, for print and colour-vision deficiencies
STYLE = {'FI': ('#2a78d6', 'o', '-'), 'GP': ('#eb6834', 's', '--'),
         'RS': ('#1baf7a', '^', ':'), 'UMDA': ('#eda100', 'D', '-.')}
# RQ4: UMDA4GI keeps its colour; the LLM groups take slots 1, 2, 3 and 5 (palette validated with
# the skill's script: CVD and normal-vision separation pass; the contrast warning is covered by
# markers, line styles and the tables with the same values in Online Resource 1)
RQ4_STYLE = {'UMDA': STYLE['UMDA'], 'UMDA-llama8b': ('#2a78d6', 'o', '-'), 'UMDA-qwen7b': ('#eb6834', 's', '--'),
             'LLM-llama8b': ('#1baf7a', '^', ':'), 'LLM-qwen7b': ('#e87ba4', 'v', (0, (5, 1, 1, 1)))}
# the confidence intervals are drawn in this tint of the series colour (the look of alpha = CI_TINT
# on a white background, without transparency, which EPS does not support), so that the medians
# stand out
CI_TINT = 0.4


def tint(colour, amount=CI_TINT):
    return tuple(amount * c + (1 - amount) for c in matplotlib.colors.to_rgb(colour))


def num(x, digits=1):
    if pd.isna(x):
        return '--'
    s = f'{x:.{digits}f}'
    return '0.0' if s in ('-0.0', '-0.00') else s


def pval(p):
    if pd.isna(p):
        return '--'
    return '$<$0.001' if p < 0.001 else f'{p:.3f}'


def holm(pvalues):
    """Holm-adjusted p-values (as in analysis.py)."""
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    out, running = [0.0] * len(pvalues), 0.0
    for k, i in enumerate(order):
        running = max(running, min(1.0, (len(pvalues) - k) * pvalues[i]))
        out[i] = running
    return out


def raw_table(cells, friedman, metric, label, caption, groups=BASE, size=SMALL):
    """Median per software, algorithm and budget, with its bootstrap 95% CI below and the
    p-value of the Friedman test of each budget."""
    lines = [r'\begin{table}[htbp]', r'\centering', size,
             rf'\caption{{{caption}}}\label{{{label}}}',
             r'\begin{tabular}{llrrrrr}', r'\toprule',
             f'Software & {"Algorithm" if groups == BASE else "Group"} & ' + ' & '.join(map(str, BUDGETS)) + r' \\',
             r'\midrule']
    for i, sw in enumerate(SOFTWARE):
        if i:
            lines.append(r'\midrule')
        for j, g in enumerate(groups):
            c = cells[(cells.software == sw) & (cells.group == g)].set_index('budget')
            first = rf'\multirow{{{2 * len(groups)}}}{{*}}{{{SW_NAMES[sw]}}}' if j == 0 else ''
            d = DIGITS.get(sw, 1)
            lines.append(f' {first} & {NAMES[g]} & '
                         + ' & '.join(num(c.loc[b, f'{metric}_median'], d) for b in BUDGETS) + r' \\')
            # the CI in the font of the table: in the journal class (sn-jnl) \scriptsize is 9pt, larger
            # than \footnotesize (7pt), so it made the CIs larger than the medians and the table too wide
            lines.append(r' & & ' + ' & '.join(
                rf'[{num(c.loc[b, f"{metric}_ci_low"], d)}, {num(c.loc[b, f"{metric}_ci_high"], d)}]'
                for b in BUDGETS) + r' \\')
        f = friedman[(friedman.software == sw) & (friedman.metric == metric)].set_index('budget')
        lines.append(r' & \textit{Friedman $p$} & ' + ' & '.join(
            (r'\textbf{' + pval(f.loc[b, 'p']) + '}') if f.loc[b, 'p'] < 0.05 else pval(f.loc[b, 'p'])
            for b in BUDGETS) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def ranked(table, cols, ascending=True):
    """Sort by rank sum; ties broken by the worst individual rank, then by the number of
    systems in the top 2 (as in the submitted version)."""
    t = table.copy()
    t['worst'] = t[cols].max(axis=1)
    t['top2'] = (t[cols] <= 2).sum(axis=1)
    return t.sort_values(['rank_sum', 'worst', 'top2'], ascending=[True, True, False])


def ranking_table(rank_csv, label, caption, groups=BASE):
    r = rank_csv[rank_csv.group.isin(groups)]
    cols = [f'{sw}_rank' for sw in RANK_SOFTWARE]
    r = ranked(r, cols)
    lines = [r'\begin{table}[htbp]', r'\centering', rf'\caption{{{caption}}}\label{{{label}}}',
             r'\begin{tabular}{lcccc|c}', r'\toprule',
             f'{"Algorithm" if groups == BASE else "Group"} & '
             + ' & '.join(SW_NAMES[sw] for sw in RANK_SOFTWARE) + r' & Sum \\', r'\midrule']
    for row in r.itertuples():
        lines.append(f'{NAMES[row.group]} & '
                     + ' & '.join(f'{int(getattr(row, c))}' for c in cols) + f' & {int(row.rank_sum)} \\\\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def search_time_tables(cells):
    """Search time: median over the 15 runs of each budget, averaged over the 5 budgets;
    then its ranking per software (1 = fastest)."""
    c = cells[cells.group.isin(BASE)]
    t = c.groupby(['group', 'software'])['search_minutes_median'].mean().unstack('software')
    ranks = t.rank(axis=0, method='min')
    lines = [r'\begin{table}[htbp]', r'\centering',
             r'\caption{Search time (minutes) per algorithm and software: median of the 15 runs at each '
             r'evaluation budget, averaged across the 5 budgets.}\label{tab:rq1searchtime}',
             r'\begin{tabular}{lrrrr}', r'\toprule',
             'Algorithm & ' + ' & '.join(SW_NAMES[sw] for sw in RANK_SOFTWARE) + r' \\', r'\midrule']
    for g in BASE:
        lines.append(f'{NAMES[g]} & ' + ' & '.join(num(t.loc[g, sw], 1) for sw in RANK_SOFTWARE) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    r = ranks[RANK_SOFTWARE].add_suffix('_rank')
    r['rank_sum'] = r.sum(axis=1)
    r = r.reset_index()
    rank_lines = ranking_table(r, 'tab:rq1searchtimeranking',
                               'Ranking of algorithms by search time per software (1 = fastest).')
    return '\n'.join(lines), rank_lines


def pairwise_table(pairwise, label='tab:pairwise', what='algorithm', size=SMALL):
    """Pairwise comparisons significant after Holm's correction within each (software,
    budget, metric)."""
    s = pairwise[pairwise.p_holm < 0.05].sort_values(['metric', 'software', 'budget'],
                                                      key=lambda col: col.map({sw: i for i, sw in enumerate(SOFTWARE)})
                                                      if col.name == 'software' else col)
    overall = sum(p < 0.05 for p in holm(list(pairwise.p)))
    remain = 'none remains' if overall == 0 else f'{overall} remain{"s" if overall == 1 else ""}'
    lines = [r'\begin{table}[htbp]', r'\centering', size,
             r'\caption{Pairwise comparisons that are significant after Holm' "'" r's correction within each '
             r'software, budget and metric (Wilcoxon signed-rank test, 15 runs paired by fold and seed). '
             rf'$\hat{{A}}_{{12}}$ is the probability that a run of the first {what} gives a lower (better) value '
             rf'than a run of the second. Out of {len(pairwise)} comparisons, {remain} significant with '
             r'Holm' "'" rf's correction over all of them.}}\label{{{label}}}',
             r'\begin{tabular}{llrllrrr}', r'\toprule',
             r'Metric & Software & Budget & \multicolumn{2}{c}{Comparison} & Medians & $\hat{A}_{12}$ & $p_{Holm}$ \\',
             r'\midrule']
    for row in s.itertuples():
        lines.append(f'{SHORT_METRIC[row.metric]} & {SW_NAMES[row.software]} & {row.budget} & '
                     f'{NAMES[row.group_a]} & vs {NAMES[row.group_b]} & '
                     f'{num(row.median_a, DIGITS.get(row.software, 1))} vs {num(row.median_b, DIGITS.get(row.software, 1))} & {row.a12_a_better:.2f} & {pval(row.p_holm)} \\\\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def stars(p):
    return '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ' (ns)'


def rq3_tables(corr):
    xs = [('checkpoint', 'Budget'), ('vt', '$V_t$'), ('vc', '$V_c$')]
    pooled = corr[corr.group == 'all']
    lines = [r'\begin{table}[htbp]', r'\centering',
             r'\caption{Spearman correlation ($\rho$) of the evaluation budget, $V_t$ and $V_c$ with validation '
             r'improvement and generalisation gap, per software, with all algorithms pooled ($n = 300$: 4 algorithms $\times$ 15 runs $\times$ 5 budgets). '
             r'Significance after Holm' "'" r's correction over the 120 correlations of RQ3: * $p<0.05$, ** $p<0.01$, '
             r'*** $p<0.001$, ns = not significant.}\label{tab:rq3maxevals}',
             r'\begin{tabular}{llcc}', r'\toprule',
             r'Software & Predictor & vs validation improvement & vs generalisation gap \\', r'\midrule']
    for i, sw in enumerate(SOFTWARE):
        if i:
            lines.append(r'\midrule')
        for j, (x, xname) in enumerate(xs):
            cells = []
            for y in ['improvement', 'gap']:
                r = pooled[(pooled.software == sw) & (pooled.x == x) & (pooled.y == y)].iloc[0]
                cells.append(f'${r.rho:+.3f}${stars(r.p_holm)}')
            first = rf'\multirow{{3}}{{*}}{{{SW_NAMES[sw]}}}' if j == 0 else ''
            lines.append(f'{first} & {xname} & ' + ' & '.join(cells) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    within = corr[(corr.group != 'all') & (corr.p_holm < 0.05)]
    w = [r'\begin{table}[htbp]', r'\centering',
         r'\caption{Correlations within a single algorithm and software ($n = 75$: 15 runs $\times$ 5 budgets) that are '
         r'significant after Holm' "'" r's correction over the 120 correlations of RQ3.}\label{tab:rq3vtvc}',
         r'\begin{tabular}{lllcc}', r'\toprule',
         r'Software & Algorithm & Predictor & Target & $\rho$ \\', r'\midrule']
    for r in within.itertuples():
        w.append(f'{SW_NAMES[r.software]} & {NAMES[r.group]} & {dict(xs)[r.x]} & {METRIC_NAMES[r.y]} & '
                 f'${r.rho:+.3f}${stars(r.p_holm)} \\\\')
    w += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines), '\n'.join(w)


def ablation_table(tests, cells, pairs, label, caption):
    """At 1000 evaluations: mean patch length, median improvement and gap of each variant
    against its reference, with the Holm-corrected p-value of the paired Wilcoxon test."""
    c = cells[cells.budget == 1000].set_index(['software', 'group'])
    lines = [r'\begin{table}[htbp]', r'\centering', SMALL, rf'\caption{{{caption}}}\label{{{label}}}',
             r'\begin{tabular}{llrrrrrr}', r'\toprule',
             r' & & \multicolumn{2}{c}{Patch length} & \multicolumn{2}{c}{Improvement} & \multicolumn{2}{c}{Gap} \\',
             r'\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}',
             r'Software & Variant (vs reference) & var. & ref. & var. & ref. & var. & ref. \\', r'\midrule']
    for i, sw in enumerate(SOFTWARE):
        if i:
            lines.append(r'\midrule')
        for j, (ref, var) in enumerate(pairs):
            cell = []
            for metric in ['improvement', 'gap']:
                t = tests[(tests.software == sw) & (tests.metric == metric)
                          & (tests.group_a.isin([ref, var])) & (tests.group_b.isin([ref, var]))].iloc[0]
                mark = '$^\\dagger$' if t.p_holm < 0.05 else ''
                d = DIGITS.get(sw, 1)
                cell.append(f'{num(c.loc[(sw, var), metric + "_median"], d)}{mark} & {num(c.loc[(sw, ref), metric + "_median"], d)}')
            length = tests[(tests.software == sw) & (tests.metric == 'patch_length')
                           & (tests.group_a.isin([ref, var])) & (tests.group_b.isin([ref, var]))]
            mark = '$^\\dagger$' if len(length) and length.iloc[0].p_holm < 0.05 else ''
            first = rf'\multirow{{{len(pairs)}}}{{*}}{{{SW_NAMES[sw]}}}' if j == 0 else ''
            lines.append(f'{first} & {NAMES[var]} (vs {NAMES[ref]}) & '
                         f'{num(c.loc[(sw, var), "patch_length_mean"])}{mark} & {num(c.loc[(sw, ref), "patch_length_mean"])} & '
                         + ' & '.join(cell) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def trainval_table(cells, pairwise):
    """RQ4 at 1000 evaluations: median training change, validation improvement and gap of each
    group, marking the values significantly different from UMDA4GI's."""
    c = cells[cells.budget == 1000].set_index(['software', 'group'])
    p = pairwise[pairwise.budget == 1000]

    def differs(sw, g, metric):
        t = p[(p.software == sw) & (p.metric == metric) & p.group_a.isin(['UMDA', g]) & p.group_b.isin(['UMDA', g])]
        return g != 'UMDA' and len(t) and t.iloc[0].p_holm < 0.05

    lines = [r'\begin{table}[htbp]', r'\centering', SMALL,
             r'\caption{Training and validation at 1000 evaluations: median change in CPU cycles on the training '
             r'inputs and on the validation inputs (\%, negative = improvement) and median generalisation gap '
             r'(percentage points) of the 15 runs. $^\dagger$: significantly different from UMDA4GI (Wilcoxon '
             r'signed-rank test paired by fold and seed, Holm' "'" r's correction over the 10 pairs of the five '
             r'groups). The comparison of the training change was added after seeing the results and is '
             r'exploratory.}\label{tab:rq4trainval}',
             r'\begin{tabular}{llrrr}', r'\toprule',
             r'Software & Group & Training & Validation & Gap \\', r'\midrule']
    for i, sw in enumerate(SOFTWARE):
        if i:
            lines.append(r'\midrule')
        d = DIGITS.get(sw, 1)
        for j, g in enumerate(RQ4):
            first = rf'\multirow{{{len(RQ4)}}}{{*}}{{{SW_NAMES[sw]}}}' if j == 0 else ''
            vals = [num(c.loc[(sw, g), col], d) + ('$^\\dagger$' if differs(sw, g, metric) else '')
                    for col, metric in [('train_median', 'train'), ('improvement_median', 'improvement'),
                                        ('gap_median', 'gap')]]
            lines.append(f'{first} & {NAMES[g]} & ' + ' & '.join(vals) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def fallback_table(fallback):
    """Reviewer 2, comment 3: what happened to the patches asked to the LLM, per group and software."""
    pct = lambda x: f'{100 * x:.1f}'
    lines = [r'\begin{table}[htbp]', r'\centering', SMALL,
             r'\caption{Patches asked to the LLM that could not be used as given, per configuration and software '
             r'(\% of the patches asked in the 15 runs). \emph{Malformed}: could not be parsed or applied; '
             r'\emph{missing}: the LLM returned fewer than asked; both are replaced by a random one-edit patch '
             r'(\emph{random fallback}). \emph{Duplicate}: well-formed but already in the population, or empty, '
             r'and also replaced by a random patch. \emph{Not used} adds up the three.}\label{tab:rq4fallback}',
             r'\begin{tabular}{llrrrrr}', r'\toprule',
             r'Configuration & Software & Malformed & Missing & Random fallback & Duplicate & Not used \\',
             r'\midrule']
    order = ['UMDA-llama8b', 'UMDA-qwen7b', 'LLM-llama8b', 'LLM-qwen7b']
    for i, g in enumerate(order):
        if i:
            lines.append(r'\midrule')
        for j, sw in enumerate(SOFTWARE):
            r = fallback[(fallback.group == g) & (fallback.software == sw)].iloc[0]
            first = rf'\multirow{{{len(SOFTWARE)}}}{{*}}{{{NAMES[g]}}}' if j == 0 else ''
            lines.append(f'{first} & {SW_NAMES[sw]} & {pct(r.malformed_rate)} & {pct(r.missing_rate)} & '
                         f'{pct(r.fallback_rate)} & {pct(r.duplicate_rate)} & {pct(r.not_used_rate)} \\\\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def figure(cells, metric, ylabel, path, groups=BASE, style=STYLE):
    """One panel per software: median of each algorithm per budget, with its bootstrap 95% CI.
    The y-axis is not inverted: lower = more improvement (or smaller gap)."""
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4))
    # keeps the error bars apart
    offsets = dict(zip(groups, [-24, -8, 8, 24] if len(groups) == 4 else [-28, -14, 0, 14, 28]))
    for ax, sw in zip(axes.flat, SOFTWARE):
        ax.axhline(0, color='#b0afa8', linewidth=0.8, zorder=0)
        for g in groups:
            c = cells[(cells.software == sw) & (cells.group == g)].sort_values('budget')
            colour, marker, ls = style[g]
            x = c.budget + offsets[g]
            med = c[f'{metric}_median']
            ax.errorbar(x, med, yerr=[med - c[f'{metric}_ci_low'], c[f'{metric}_ci_high'] - med],
                        color=colour, marker=marker, markersize=4.5, linestyle=ls, linewidth=1.5,
                        elinewidth=0.8, capsize=2, ecolor=tint(colour), label=NAMES[g])
        ax.set_title(SW_NAMES[sw], fontsize=10)
        ax.set_xticks(BUDGETS)
        ax.tick_params(labelsize=8)
        ax.grid(axis='y', color='#e4e3dd', linewidth=0.6)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
    for ax in axes[1]:
        ax.set_xlabel('Evaluation budget', fontsize=9)
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel, fontsize=9)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=len(groups), frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    for ext in ('pdf', 'eps'):
        fig.savefig(path.with_suffix('.' + ext))
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('analysis_dir')
    parser.add_argument('out_dir')
    args = parser.parse_args()
    a = pathlib.Path(args.analysis_dir)
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cells = pd.read_csv(a / 'cells.csv')
    friedman = pd.read_csv(a / 'rq1_rq2_friedman.csv')
    pairwise = pd.read_csv(a / 'rq1_rq2_pairwise.csv')

    tables = [
        raw_table(cells, friedman, 'improvement', 'tab:rq1raw',
                  r'Median validation improvement (\% change in CPU cycles, negative = improvement) of the 15 runs '
                  r'(5 folds $\times$ 3 seeds) per software, algorithm and evaluation budget, with its bootstrap 95\% '
                  r'confidence interval below. The last row of each software gives the $p$-value of the Friedman test '
                  r'over the four algorithms at that budget (bold: $p<0.05$).'),
        ranking_table(pd.read_csv(a / 'rq1_improvement_ranking.csv'), 'tab:rq1ranking',
                      r'Global ranking of algorithms by validation improvement (1 = best per software): '
                      r'medians of Table~S1 of Online Resource~1 averaged across the 5 budgets. Ties broken by worst '
                      r'individual rank, then by number of software systems where the algorithm ranks in the top 2.'),
        *search_time_tables(cells),
        raw_table(cells, friedman, 'gap', 'tab:rq2raw',
                  r'Median generalisation gap (validation $-$ training change of each run, percentage points; '
                  r'negative = generalises better than it trains) of the 15 runs per software, algorithm and '
                  r'evaluation budget, with its bootstrap 95\% confidence interval below. The last row of each '
                  r'software gives the $p$-value of the Friedman test over the four algorithms at that budget '
                  r'(bold: $p<0.05$).'),
        ranking_table(pd.read_csv(a / 'rq2_gap_ranking.csv'), 'tab:rq2ranking',
                      r'Global ranking of algorithms by generalisation gap (1 = generalises best per software): '
                      r'medians of Table~S2 of Online Resource~1 averaged across the 5 budgets. Ties broken by worst '
                      r'individual rank, then by number of software systems where the algorithm ranks in the top 2.'),
        pairwise_table(pairwise),
        *rq3_tables(pd.read_csv(a / 'rq3_correlations.csv')),
        ablation_table(pd.read_csv(a / 'ablations.csv'), cells,
                       [('UMDA', 'ABL-UMDA-imp'), ('UMDA', 'ABL-UMDA-k1'), ('UMDA', 'ABL-UMDA-k3'),
                        ('FI', 'ABL-FI-2'), ('GP', 'ABL-GP-2')], 'tab:ablations',
                       r'Ablations at 1000 evaluations: mean patch length, and median validation improvement and '
                       r'generalisation gap of each variant and of its reference algorithm (15 runs each). '
                       r'$^\dagger$: significant difference (Wilcoxon signed-rank test paired by fold and seed, '
                       r'Holm' "'" r's correction over the 60 comparisons of the ablations: improvement, gap and patch length).'),
        ablation_table(pd.read_csv(a / 'length_controlled.csv'), cells,
                       [('ABL-FI-2', 'UMDA'), ('ABL-GP-2', 'UMDA')], 'tab:lengthcontrolled',
                       r'UMDA4GI against First-Improvement and GP limited to two edits per patch, at 1000 '
                       r'evaluations. $^\dagger$: significant difference (Wilcoxon signed-rank test paired by fold '
                       r'and seed, Holm' "'" r's correction over the 16 comparisons of this table).'),
    ]
    tables += [
        r'\begin{figure}[htbp]' '\n' r'\centering' '\n'
        r'\includegraphics[width=\textwidth]{figures/RQ1_convergence.pdf}' '\n'
        r'\caption{Median validation improvement vs.\ evaluation budget, per software, with bootstrap 95\% '
        r'confidence intervals (Table~S1 of Online Resource~1). Negative values are improvements: the lower the point, '
        r'the larger the improvement. Points are shifted slightly along the x-axis so that the intervals do not '
        r'overlap.}\label{fig:rq1trend}' '\n' r'\end{figure}',
        r'\begin{figure}[htbp]' '\n' r'\centering' '\n'
        r'\includegraphics[width=\textwidth]{figures/RQ2_generalisation.pdf}' '\n'
        r'\caption{Median generalisation gap (validation $-$ training change of each run, percentage points) vs.\ '
        r'evaluation budget, per software, with bootstrap 95\% confidence intervals (Table~S2 of Online Resource~1). '
        r'The lower the point, the better the patches generalise.}\label{fig:rq2overfitting}' '\n' r'\end{figure}',
    ]
    header = ('% Generated by experiments/revision_analysis/paper_tables.py from '
              f'{a.as_posix()} -- do not edit by hand.\n')
    (out / 'tables_rq1_rq3.tex').write_text(header + '\n\n'.join(tables) + '\n')
    figure(cells, 'improvement', 'Validation improvement (%)', out / 'RQ1_convergence')
    figure(cells, 'gap', 'Generalisation gap (pp)', out / 'RQ2_generalisation')
    if (a / 'rq4_llm_fallback.csv').exists():
        rq4_tables(a, cells, out, header)
    print('written to', out)


def rq4_tables(a, cells, out, header):
    friedman = pd.read_csv(a / 'rq4_friedman.csv')
    pairwise = pd.read_csv(a / 'rq4_pairwise.csv')
    ties = 'Ties broken by worst individual rank, then by number of software systems where the group ranks in the top 2.'
    tables = [
        raw_table(cells, friedman, 'improvement', 'tab:rq4validate',
                  r'Median validation improvement (\% change in CPU cycles, negative = improvement) of the 15 runs '
                  r'per software, group and evaluation budget, with its bootstrap 95\% confidence interval below. '
                  r'The last row of each software gives the $p$-value of the Friedman test over the five groups at '
                  r'that budget (bold: $p<0.05$).', groups=RQ4, size=RQ4_SMALL),
        ranking_table(pd.read_csv(a / 'rq4_improvement_ranking.csv'), 'tab:rq4validateranking',
                      r'Global ranking of groups by validation improvement (1 = best per software): medians of '
                      r'Table~S4 of Online Resource~1 averaged across the 5 budgets. ' + ties, groups=RQ4),
        raw_table(cells, friedman, 'gap', 'tab:rq4gap',
                  r'Median generalisation gap (validation $-$ training change of each run, percentage points; '
                  r'negative = generalises better than it trains) of the 15 runs per software, group and evaluation '
                  r'budget, with its bootstrap 95\% confidence interval below. The last row of each software gives '
                  r'the $p$-value of the Friedman test over the five groups at that budget (bold: $p<0.05$).',
                  groups=RQ4, size=RQ4_SMALL),
        ranking_table(pd.read_csv(a / 'rq4_gap_ranking.csv'), 'tab:rq4gapranking',
                      r'Global ranking of groups by generalisation gap (1 = generalises best per software): medians '
                      r'of Table~S5 of Online Resource~1 averaged across the 5 budgets. ' + ties, groups=RQ4),
        pairwise_table(pairwise[pairwise.metric.isin(['improvement', 'gap'])], 'tab:rq4pairwise', 'group', size=RQ4_PAIRS),
        trainval_table(cells, pairwise),
        fallback_table(pd.read_csv(a / 'rq4_llm_fallback.csv')),
        r'\begin{figure}[htbp]' '\n' r'\centering' '\n'
        r'\includegraphics[width=\textwidth]{figures/RQ4_generalisation.pdf}' '\n'
        r'\caption{Median generalisation gap (validation $-$ training change of each run, percentage points) vs.\ '
        r'evaluation budget of UMDA4GI and the four LLM groups, per software, with bootstrap 95\% confidence '
        r'intervals (Table~S5 of Online Resource~1). The lower the point, the better the patches generalise.}'
        r'\label{fig:rq4generalisation}' '\n' r'\end{figure}',
    ]
    (out / 'tables_rq4.tex').write_text(header + '\n\n'.join(tables) + '\n')
    figure(cells, 'gap', 'Generalisation gap (pp)', out / 'RQ4_generalisation', groups=RQ4, style=RQ4_STYLE)


if __name__ == '__main__':
    main()
