"""Checks the LLM branch of UMDAAlgorithm.sample_population with canned LLM answers."""
import configparser
import random
import sys

sys.path.insert(0, '.')
import magpie
from magpie.algos import UMDAAlgorithm

random.seed(3)
config = configparser.ConfigParser()
config.read_dict(magpie.core.default_scenario)
config.read('experiments/minisat_hack/_magpie/scenario_cycles_xml_FOLD1_steps100.txt')
config['search.eda']['llm_model'] = 'fake-model'
magpie.core.pre_setup(config)
magpie.core.setup(config)
software = magpie.utils.software_from_string(config['software']['software'])(config)

algo = UMDAAlgorithm()
algo.software = software
algo.setup(config)
algo.reset()

e = [str(algo.create_edit(software.noop_variant)) for _ in range(4)]
answer = [
    e[0],                       # valid, 1 edit
    f'{e[1]} | {e[2]} | {e[3]}',  # valid, 3 edits (no k_max for the LLM)
    e[0],                       # duplicate of the first
    'XmlNodeDeletion<stmt>((garbage',  # malformed
]
pop_size = algo.config['pop_size']


def fake_llm(edits_prob, n):
    algo.stats['llm_patches_requested'] += n
    patches = list(answer)
    while len(patches) < n:        # same padding as llm_sample_population
        sol = magpie.core.Patch()
        algo.mutate(sol)
        patches.append(str(sol))
        algo.stats['llm_missing_patches'] += 1
    return patches, [''] * len(patches)


algo.llm_sample_population = fake_llm
pop = algo.sample_population({e[0]: 1.0})
strs = [str(p) for p in pop]
ok = True
for name, cond in [
    (f'population size is pop_size ({len(pop)})', len(pop) == pop_size),
    ('all patches distinct', len(set(strs)) == len(strs)),
    ('valid LLM patches kept as given (incl. the 3-edit one)', strs[0] == e[0] and strs[1] == f'{e[1]} | {e[2]} | {e[3]}'),
    ('duplicate replaced by a random 1-edit patch', len(pop[2].edits) == 1 and strs[2] != e[0]),
    ('malformed replaced by a random 1-edit patch', len(pop[3].edits) == 1),
    ('malformed counted', algo.stats['llm_malformed_patches'] == 1),
    ('missing counted', algo.stats['llm_missing_patches'] == pop_size - 4),
]:
    print(('ok   ' if cond else 'FAIL ') + name)
    ok &= cond
print(f"      stats: llm_malformed={algo.stats['llm_malformed_patches']} llm_missing={algo.stats['llm_missing_patches']} random_replacements={algo.stats['sample_random_fallback']}")
print('ALL OK' if ok else 'FAILURES')
