import pandas as pd

df = pd.read_csv('experiments/results/results.csv')
mask = (
    (df['algorithm'] == 'LLMAlgorithm') &
    (df['software'] == 'minisat_hack') &
    (df['fold'] == 1) &
    (df['max_evals'] == 500)
)
cols = ['llm_model', 'change_perc_train', 'change_perc_validate', 'train_log', 'validate_log']
print(df[mask][cols].to_string())
