"""
LaTeX tables and figures of RQ1-RQ3 for the revised paper, from the output of analysis.py.

    python experiments/revision_analysis/paper_tables.py ANALYSIS_DIR OUT_DIR

ANALYSIS_DIR is experiments/results/revision/analysis. Writes OUT_DIR/tables_rq1_rq3.tex
(one table per \\begin{table}, then the two figure environments; same labels as the submitted
version where the table or figure already existed) and the figures RQ1_convergence and RQ2_generalisation as PDF and EPS. Needs the
LaTeX packages booktabs and multirow.
"""
import argparse
import pathlib

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

BASE = ['FI', 'GP', 'RS', 'UMDA']
NAMES = {'FI': 'FI', 'GP': 'GP', 'RS': 'RandomS', 'UMDA': 'UMDA4GI',
         'ABL-UMDA-imp': 'UMDA4GI-imp', 'ABL-UMDA-k1': 'UMDA4GI $k_{max}{=}1$',
         'ABL-UMDA-k3': 'UMDA4GI $k_{max}{=}3$', 'ABL-FI-2': 'FI-2', 'ABL-GP-2': 'GP-2'}
# row order of the submitted tables, and column order of its ranking tables
SOFTWARE = ['minisat_hack', 'sat4j', 'weka', 'pngOptim']
RANK_SOFTWARE = ['minisat_hack', 'pngOptim', 'sat4j', 'weka']
SW_NAMES = {'minisat_hack': 'MiniSAT-hack', 'sat4j': 'Sat4J', 'weka': 'Weka', 'pngOptim': 'OptimPNG'}
BUDGETS = [100, 250, 500, 750, 1000]
# OptimPNG changes are a fraction of a percentage point: one more decimal
DIGITS = {'pngOptim': 2}
METRIC_NAMES = {'improvement': 'validation improvement', 'gap': 'generalisation gap'}
# validated categorical palette (dataviz skill, slots 1-4); marker and line style also
# identify each algorithm, for print and colour-vision deficiencies
STYLE = {'FI': ('#2a78d6', 'o', '-'), 'GP': ('#eb6834', 's', '--'),
         'RS': ('#1baf7a', '^', ':'), 'UMDA': ('#eda100', 'D', '-.')}


def num(x, digits=1):
    if pd.isna(x):
        return '--'
    s = f'{x:.{digits}f}'
    return '0.0' if s in ('-0.0', '-0.00') else s


def pval(p):
    if pd.isna(p):
        return '--'
    return '$<$0.001' if p < 0.001 else f'{p:.3f}'


def raw_table(cells, friedman, metric, label, caption):
    """Median per software, algorithm and budget, with its bootstrap 95% CI below and the
    p-value of the Friedman test of each budget."""
    lines = [r'\begin{table}[h]', r'\centering', r'\small',
             rf'\caption{{{caption}}}\label{{{label}}}',
             r'\begin{tabular}{llrrrrr}', r'\toprule',
             r'Software & Algorithm & ' + ' & '.join(map(str, BUDGETS)) + r' \\', r'\midrule']
    for i, sw in enumerate(SOFTWARE):
        if i:
            lines.append(r'\midrule')
        for j, g in enumerate(BASE):
            c = cells[(cells.software == sw) & (cells.group == g)].set_index('budget')
            first = rf'\multirow{{{2 * len(BASE)}}}{{*}}{{{SW_NAMES[sw]}}}' if j == 0 else ''
            d = DIGITS.get(sw, 1)
            lines.append(f' {first} & {NAMES[g]} & '
                         + ' & '.join(num(c.loc[b, f'{metric}_median'], d) for b in BUDGETS) + r' \\')
            lines.append(r' & & ' + ' & '.join(
                rf'\scriptsize[{num(c.loc[b, f"{metric}_ci_low"], d)}, {num(c.loc[b, f"{metric}_ci_high"], d)}]'
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


def ranking_table(rank_csv, label, caption):
    r = rank_csv[rank_csv.group.isin(BASE)]
    cols = [f'{sw}_rank' for sw in RANK_SOFTWARE]
    r = ranked(r, cols)
    lines = [r'\begin{table}[h]', r'\centering', rf'\caption{{{caption}}}\label{{{label}}}',
             r'\begin{tabular}{lcccc|c}', r'\toprule',
             'Algorithm & ' + ' & '.join(SW_NAMES[sw] for sw in RANK_SOFTWARE) + r' & Sum \\', r'\midrule']
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
    lines = [r'\begin{table}[h]', r'\centering',
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


def pairwise_table(pairwise):
    """Pairwise comparisons significant after Holm's correction within each (software,
    budget, metric)."""
    s = pairwise[pairwise.p_holm < 0.05].sort_values(['metric', 'software', 'budget'],
                                                      key=lambda col: col.map({sw: i for i, sw in enumerate(SOFTWARE)})
                                                      if col.name == 'software' else col)
    lines = [r'\begin{table}[h]', r'\centering', r'\small',
             r'\caption{Pairwise comparisons that are significant after Holm' "'" r's correction within each '
             r'software, budget and metric (Wilcoxon signed-rank test, 15 runs paired by fold and seed). '
             r'$\hat{A}_{12}$ is the probability that a run of the first algorithm gives a lower (better) value '
             rf'than a run of the second. Out of {len(pairwise)} comparisons, none remains significant with '
             r'Holm' "'" r's correction over all of them.}\label{tab:pairwise}',
             r'\begin{tabular}{llrllrrr}', r'\toprule',
             r'Metric & Software & Budget & \multicolumn{2}{c}{Comparison} & Medians & $\hat{A}_{12}$ & $p_{Holm}$ \\',
             r'\midrule']
    for row in s.itertuples():
        lines.append(f'{METRIC_NAMES[row.metric].capitalize()} & {SW_NAMES[row.software]} & {row.budget} & '
                     f'{NAMES[row.group_a]} & vs {NAMES[row.group_b]} & '
                     f'{num(row.median_a, DIGITS.get(row.software, 1))} vs {num(row.median_b, DIGITS.get(row.software, 1))} & {row.a12_a_better:.2f} & {pval(row.p_holm)} \\\\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def stars(p):
    return '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ' (ns)'


def rq3_tables(corr):
    xs = [('checkpoint', 'Budget'), ('vt', '$V_t$'), ('vc', '$V_c$')]
    pooled = corr[corr.group == 'all']
    lines = [r'\begin{table}[h]', r'\centering',
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
    w = [r'\begin{table}[h]', r'\centering',
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
    lines = [r'\begin{table}[h]', r'\centering', r'\small', rf'\caption{{{caption}}}\label{{{label}}}',
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


def figure(cells, metric, ylabel, path):
    """One panel per software: median of each algorithm per budget, with its bootstrap 95% CI.
    The y-axis is not inverted: lower = more improvement (or smaller gap)."""
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4))
    offsets = dict(zip(BASE, [-24, -8, 8, 24]))  # keeps the error bars apart
    for ax, sw in zip(axes.flat, SOFTWARE):
        ax.axhline(0, color='#b0afa8', linewidth=0.8, zorder=0)
        for g in BASE:
            c = cells[(cells.software == sw) & (cells.group == g)].sort_values('budget')
            colour, marker, ls = STYLE[g]
            x = c.budget + offsets[g]
            med = c[f'{metric}_median']
            ax.errorbar(x, med, yerr=[med - c[f'{metric}_ci_low'], c[f'{metric}_ci_high'] - med],
                        color=colour, marker=marker, markersize=4.5, linestyle=ls, linewidth=1.5,
                        elinewidth=0.8, capsize=2, label=NAMES[g])
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
    fig.legend(handles, labels, loc='lower center', ncol=4, frameon=False, fontsize=9)
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
                      r'medians of Table~\ref{tab:rq1raw} averaged across the 5 budgets. Ties broken by worst '
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
                      r'medians of Table~\ref{tab:rq2raw} averaged across the 5 budgets. Ties broken by worst '
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
        r'\begin{figure}[h]' '\n' r'\centering' '\n'
        r'\includegraphics[width=\textwidth]{figures/RQ1_convergence.pdf}' '\n'
        r'\caption{Median validation improvement vs.\ evaluation budget, per software, with bootstrap 95\% '
        r'confidence intervals (Table~\ref{tab:rq1raw}). Negative values are improvements: the lower the point, '
        r'the larger the improvement. Points are shifted slightly along the x-axis so that the intervals do not '
        r'overlap.}\label{fig:rq1trend}' '\n' r'\end{figure}',
        r'\begin{figure}[h]' '\n' r'\centering' '\n'
        r'\includegraphics[width=\textwidth]{figures/RQ2_generalisation.pdf}' '\n'
        r'\caption{Median generalisation gap (validation $-$ training change of each run, percentage points) vs.\ '
        r'evaluation budget, per software, with bootstrap 95\% confidence intervals (Table~\ref{tab:rq2raw}). '
        r'The lower the point, the better the patches generalise.}\label{fig:rq2overfitting}' '\n' r'\end{figure}',
    ]
    header = ('% Generated by experiments/revision_analysis/paper_tables.py from '
              f'{a.as_posix()} -- do not edit by hand.\n')
    (out / 'tables_rq1_rq3.tex').write_text(header + '\n\n'.join(tables) + '\n')
    figure(cells, 'improvement', 'Validation improvement (%)', out / 'RQ1_convergence')
    figure(cells, 'gap', 'Generalisation gap (pp)', out / 'RQ2_generalisation')
    print('written to', out)


if __name__ == '__main__':
    main()
