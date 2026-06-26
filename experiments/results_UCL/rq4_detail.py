import pandas as pd
import numpy as np
from pathlib import Path

CSV_PATH = Path('experiments/results/results.csv')
df = pd.read_csv(CSV_PATH).copy()
df['overfitting'] = df['change_perc_validate'] - df['change_perc_train']
df['max_evals'] = df['max_evals'].astype(int)

def algo_group(row):
    if row['algorithm'] == 'UMDAAlgorithm' and str(row['llm_model']) in ('None', 'nan', ''):
        return 'UMDA'
    elif row['algorithm'] == 'UMDAAlgorithm':
        return 'UMDA+LLM'
    elif row['algorithm'] == 'LLMAlgorithm':
        return 'LLM pure'
    return None

df['group'] = df.apply(algo_group, axis=1)
rq4 = df[df['group'].notna()]

print("=== Overfitting medio (validate - train) ===")
ov = rq4.groupby(['group', 'max_evals'])['overfitting'].mean().round(3).unstack('group')
print(ov)

print("\n=== Std de change_perc_validate (varianza/consistencia) ===")
std_v = rq4.groupby(['group', 'max_evals'])['change_perc_validate'].std().round(3).unstack('group')
print(std_v)

print("\n=== change_perc_validate medio (negativo = mejora) ===")
mean_v = rq4.groupby(['group', 'max_evals'])['change_perc_validate'].mean().round(3).unstack('group')
print(mean_v)

print("\n=== Casos donde validate mejora (< 0) por grupo ===")
rq4_pos = rq4.copy()
rq4_pos['improves'] = rq4_pos['change_perc_validate'] < 0
rate = rq4_pos.groupby(['group', 'max_evals'])['improves'].mean().round(3).unstack('group')
print(rate)
