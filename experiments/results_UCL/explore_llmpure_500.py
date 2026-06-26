import pandas as pd
import numpy as np

df = pd.read_csv('experiments/results/results.csv').copy()
df['max_evals'] = df['max_evals'].astype(int)
llm = df[df['algorithm'] == 'LLMAlgorithm'].copy()

print("=== change_perc_validate por budget (media y mediana) ===")
g = llm.groupby('max_evals')['change_perc_validate']
print(pd.DataFrame({'mean': g.mean(), 'median': g.median(), 'std': g.std()}).round(3))

print("\n=== 500 steps: desglose por software y llm_model ===")
s500 = llm[llm['max_evals'] == 500]
print(s500.groupby(['software', 'llm_model'])[['change_perc_train', 'change_perc_validate']].mean().round(3))

print("\n=== 500 steps: todos los valores de change_perc_validate ===")
print(s500[['software', 'llm_model', 'fold', 'change_perc_train', 'change_perc_validate']].sort_values('change_perc_validate').to_string())

print("\n=== Comparar mediana por budget (más robusta a outliers) ===")
for steps in [100, 250, 500, 750, 1000]:
    sub = llm[llm['max_evals'] == steps]['change_perc_validate']
    print(f"steps={steps}: mean={sub.mean():.3f}  median={sub.median():.3f}  min={sub.min():.3f}  max={sub.max():.3f}")
