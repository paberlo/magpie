"""
Verifica que RQ1, RQ2 y RQ3 (que no usan LLMs) dan las mismas conclusiones ya publicadas
en el paper al recalcularlas desde results_larger.csv, en vez de results.csv.

READ-ONLY: no modifica ningun notebook existente (RQ1-4.ipynb). Todo el analisis de
modelos grandes (14b/32b) vive en esta carpeta, aparte.
"""
import pandas as pd
import numpy as np
from scipy import stats

CSV_PATH = "../../results/results_larger.csv"
NOLLM_ALGOS = ['FirstImprovement', 'GeneticProgrammingUniformConcat', 'RandomSearch', 'UMDAAlgorithm']
legend = {'FirstImprovement': 'FI', 'GeneticProgrammingUniformConcat': 'GP',
          'RandomSearch': 'RandomS', 'UMDAAlgorithm': 'UMDA4GI'}
swmap = {'minisat_hack': 'MiniSAT-hack', 'sat4j': 'Sat4J', 'weka': 'Weka', 'pngOptim': 'OptimPNG'}

df_all = pd.read_csv(CSV_PATH)
df = df_all[(df_all['fitness'] == 'Perf<Cycles>') & (df_all['algorithm'].isin(NOLLM_ALGOS))
            & (df_all['llm_model'].isna())].copy()
df['max_evals'] = pd.to_numeric(df['max_evals'], errors='coerce').astype(int)
df['fold'] = pd.to_numeric(df['fold'], errors='coerce').astype(int)
df['change_perc_validate'] = pd.to_numeric(df['change_perc_validate'], errors='coerce')
df['change_perc_train'] = pd.to_numeric(df['change_perc_train'], errors='coerce')
df['patch_length'] = pd.to_numeric(df['patch_length'], errors='coerce')
df['Vt'] = pd.to_numeric(df['Vt'], errors='coerce')
df['Vc'] = pd.to_numeric(df['Vc'], errors='coerce')

print(f"Filas no-LLM: {len(df)} (esperado 400)\n")

# ============================== RQ1 ==============================
print("=" * 60)
print("RQ1 - Global ranking por validation improvement")
print("=" * 60)
agg = df.groupby(['software', 'algorithm', 'max_evals'], as_index=False)['change_perc_validate'].median()
avg = agg.groupby(['software', 'algorithm'], as_index=False)['change_perc_validate'].mean()
avg['rank'] = avg.groupby('software')['change_perc_validate'].rank(method='min')
piv = avg.pivot(index='algorithm', columns='software', values='rank')
piv.index = [legend[i] for i in piv.index]
piv.columns = [swmap[c] for c in piv.columns]
piv['Sum'] = piv.sum(axis=1)
print(piv.sort_values('Sum'))
print("Esperado (paper): FI=7, UMDA4GI=9, RandomS=9, GP=15")

# ============================== RQ2 ==============================
print("\n" + "=" * 60)
print("RQ2 - Global ranking por generalisation gap")
print("=" * 60)
agg2 = df.groupby(['software', 'algorithm', 'max_evals'], as_index=False).agg(
    change_perc_validate=('change_perc_validate', 'median'),
    change_perc_train=('change_perc_train', 'median'))
agg2['gap'] = agg2['change_perc_validate'] - agg2['change_perc_train']
avg2 = agg2.groupby(['software', 'algorithm'], as_index=False)['gap'].mean()
avg2['rank'] = avg2.groupby('software')['gap'].rank(method='min')
piv2 = avg2.pivot(index='algorithm', columns='software', values='rank')
piv2.index = [legend[i] for i in piv2.index]
piv2.columns = [swmap[c] for c in piv2.columns]
piv2['Sum'] = piv2.sum(axis=1)
print(piv2.sort_values('Sum'))
print("Esperado (paper): UMDA4GI=6, RandomS=11, GP=11, FI=12")

# ============================== RQ3 ==============================
print("\n" + "=" * 60)
print("RQ3 - Correlacion max_evals vs validation improvement, por software (pooled)")
print("=" * 60)
df3 = df[df['change_perc_validate'].notna() & (df['change_perc_validate'] != 0.0)].copy()
df3['gap'] = df3['change_perc_validate'] - df3['change_perc_train']
print(f"n={len(df3)} (esperado 383)")
for sw in ['minisat_hack', 'sat4j', 'weka', 'pngOptim']:
    sub = df3[df3['software'] == sw]
    rho, p = stats.spearmanr(sub['max_evals'], sub['change_perc_validate'])
    sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else 'ns'))
    print(f"  {swmap[sw]:15s} rho={rho:+.3f} {sig} (p={p:.4f})")
print("Esperado (paper): MiniSAT-hack=-0.362***, Sat4J=-0.273**, Weka=ns, OptimPNG=-0.355***")

print("\n=== RQ3 - correlaciones significativas Vc/Vt dentro de algoritmo (n=21-25) ===")
checks = [
    ('minisat_hack', 'GeneticProgrammingUniformConcat', 'Vt', -0.411),
    ('minisat_hack', 'GeneticProgrammingUniformConcat', 'Vc', -0.408),
    ('minisat_hack', 'RandomSearch', 'Vc', -0.573),
    ('sat4j', 'FirstImprovement', 'Vt', -0.574),
    ('sat4j', 'FirstImprovement', 'Vc', -0.540),
]
for sw, alg, pred, expected_rho in checks:
    sub = df3[(df3['software'] == sw) & (df3['algorithm'] == alg)]
    rho, p = stats.spearmanr(sub[pred], sub['change_perc_validate'])
    sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else 'ns'))
    match = "OK" if abs(rho - expected_rho) < 0.01 else "MISMATCH"
    print(f"  {swmap[sw]:12s} {legend[alg]:8s} {pred} rho={rho:+.3f} {sig}  (esperado {expected_rho:+.3f}) [{match}]")
