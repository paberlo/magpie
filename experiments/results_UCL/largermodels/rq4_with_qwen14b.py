"""
RQ4 extendido: anade UMDA+qwen2.5:14b y LLM-qwen2.5:14b a los 5 grupos ya publicados
(UMDA4GI, UMDA+llama3.1:8b, UMDA+qwen2.5-coder:7b, LLM-llama3.1:8b, LLM-qwen2.5-coder:7b).

Mismo protocolo que el paper (Section 5.4 / sub:rq4results): mediana por fold y budget,
luego media entre budgets; rank-sum por software; patch-finding rate.

READ-ONLY: no toca RQ4.ipynb ni ningun notebook existente. Vive aparte en largermodels/.
"""
import pandas as pd
import numpy as np

CSV_PATH = "../../results/results_larger.csv"
MODELS_KEEP = {'llama3.1:8b', 'qwen2.5-coder:7b', 'qwen2.5:14b'}
swmap = {'minisat_hack': 'MiniSAT-hack', 'sat4j': 'Sat4J', 'weka': 'Weka', 'pngOptim': 'OptimPNG'}
desired_order = ['minisat_hack', 'sat4j', 'weka', 'pngOptim']

GROUP_ORDER = ['UMDA4GI', 'UMDA+llama', 'UMDA+qwen7b', 'UMDA+qwen14b',
               'LLM-llama', 'LLM-qwen7b', 'LLM-qwen14b']

df_all = pd.read_csv(CSV_PATH)
df = df_all[(df_all['fitness'] == 'Perf<Cycles>') &
            (df_all['algorithm'].isin(['UMDAAlgorithm', 'LLMAlgorithm'])) &
            (df_all['llm_model'].isna() | df_all['llm_model'].isin(MODELS_KEEP))].copy()
for col in ['change_perc_validate', 'change_perc_train', 'max_evals']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df['max_evals'] = df['max_evals'].astype(int)


def assign_group(row):
    alg, llm = row['algorithm'], row['llm_model']
    if alg == 'UMDAAlgorithm' and pd.isna(llm): return 'UMDA4GI'
    if alg == 'UMDAAlgorithm' and llm == 'llama3.1:8b': return 'UMDA+llama'
    if alg == 'UMDAAlgorithm' and llm == 'qwen2.5-coder:7b': return 'UMDA+qwen7b'
    if alg == 'UMDAAlgorithm' and llm == 'qwen2.5:14b': return 'UMDA+qwen14b'
    if alg == 'LLMAlgorithm' and llm == 'llama3.1:8b': return 'LLM-llama'
    if alg == 'LLMAlgorithm' and llm == 'qwen2.5-coder:7b': return 'LLM-qwen7b'
    if alg == 'LLMAlgorithm' and llm == 'qwen2.5:14b': return 'LLM-qwen14b'
    return None


df['group'] = df.apply(assign_group, axis=1)
df = df[df['group'].notna()]
df['overfit'] = df['change_perc_validate'] - df['change_perc_train']

print("Filas por grupo (esperado 100 cada uno):")
print(df.groupby('group').size().reindex(GROUP_ORDER))

agg = df.groupby(['software', 'group', 'max_evals'], as_index=False).agg(
    change_perc_validate=('change_perc_validate', 'median'),
    overfit=('overfit', 'median'))

# ---- Validation improvement ----
avg = agg.groupby(['software', 'group'], as_index=False)['change_perc_validate'].mean()
piv = avg.pivot(index='group', columns='software', values='change_perc_validate').reindex(GROUP_ORDER)
piv.columns = [swmap[c] for c in piv.columns]
piv = piv[['MiniSAT-hack', 'OptimPNG', 'Sat4J', 'Weka']]
print("\n=== Validation improvement (median-then-mean), 1 decimal ===")
print(piv.round(1))

avg['rank'] = avg.groupby('software')['change_perc_validate'].rank(method='min')
rank_piv = avg.pivot(index='group', columns='software', values='rank').reindex(GROUP_ORDER)
rank_piv.columns = [swmap[c] for c in rank_piv.columns]
rank_piv = rank_piv[['MiniSAT-hack', 'OptimPNG', 'Sat4J', 'Weka']]
rank_piv['Sum'] = rank_piv.sum(axis=1)
print("\n=== Ranking validation improvement (1=best), Sum ===")
print(rank_piv.sort_values('Sum'))

# ---- Generalisation gap ----
avg_of = agg.groupby(['software', 'group'], as_index=False)['overfit'].mean()
piv_of = avg_of.pivot(index='group', columns='software', values='overfit').reindex(GROUP_ORDER)
piv_of.columns = [swmap[c] for c in piv_of.columns]
piv_of = piv_of[['MiniSAT-hack', 'OptimPNG', 'Sat4J', 'Weka']]
print("\n=== Generalisation gap (median-then-mean), 1 decimal ===")
print(piv_of.round(1))

avg_of['rank'] = avg_of.groupby('software')['overfit'].rank(method='min')
rank_of = avg_of.pivot(index='group', columns='software', values='rank').reindex(GROUP_ORDER)
rank_of.columns = [swmap[c] for c in rank_of.columns]
rank_of = rank_of[['MiniSAT-hack', 'OptimPNG', 'Sat4J', 'Weka']]
rank_of['Sum'] = rank_of.sum(axis=1)
print("\n=== Ranking generalisation gap (1=generalises best), Sum ===")
print(rank_of.sort_values('Sum'))

# ---- Patch-finding rate ----
df['missing'] = df['validate_log'].isna() | (df['validate_log'].astype(str).str.strip() == '')
tbl = df.groupby('group').agg(total=('missing', 'size'), missing=('missing', 'sum'))
tbl['found'] = tbl['total'] - tbl['missing']
tbl['pct_missing'] = (tbl['missing'] / tbl['total'] * 100).round(1)
print("\n=== Patch-finding rate ===")
print(tbl.reindex(GROUP_ORDER))
