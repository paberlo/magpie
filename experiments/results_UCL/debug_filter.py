import pandas as pd

df = pd.read_csv('experiments/results/results.csv')
print('fitness unique:', df['fitness'].unique())
print('llm_model unique:', df['llm_model'].unique())

rq1_algos = ['FirstImprovement', 'GeneticProgrammingUniformConcat', 'RandomSearch', 'UMDAAlgorithm']
sub = df[df['algorithm'].isin(rq1_algos)]
print('rows with RQ1 algos:', len(sub))
print('llm_model values in RQ1 algos:', sub['llm_model'].unique())
print('dtype:', sub['llm_model'].dtype)

sub2 = sub.copy()
sub2['llm_model_str'] = sub2['llm_model'].astype(str)
print('llm_model_str unique:', sub2['llm_model_str'].unique())
print('rows after isin None/nan:', len(sub2[sub2['llm_model_str'].isin(['None', 'nan'])]))
