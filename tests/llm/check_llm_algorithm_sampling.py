"""Checks LLMAlgorithm.sample_population with canned LLM answers."""
import configparser
import random
import sys

sys.path.insert(0, '.')
import magpie
from magpie.algos import LLMAlgorithm
from magpie.algos.llm_algorithm import RANDOM_FALLBACK

random.seed(3)
config = configparser.ConfigParser()
config.read_dict(magpie.core.default_scenario)
config.read('experiments/minisat_hack/_magpie/scenario_cycles_xml_FOLD1_steps100.txt')
config['search.llm']['llm_model'] = 'fake-model'
config['search.llm']['llm_ip'] = '127.0.0.1'
magpie.core.pre_setup(config)
magpie.core.setup(config)
software = magpie.utils.software_from_string(config['software']['software'])(config)

algo = LLMAlgorithm()
algo.software = software
algo.setup(config)
algo.reset()

e = [str(algo.create_edit(software.noop_variant)) for _ in range(3)]
answer = [
    e[0],                       # valid
    e[0],                       # duplicate of the first
    'XmlNodeDeletion<stmt>((garbage',  # malformed
    e[1],                       # valid
]
pop_size = algo.config['pop_size']


def fake_llm(n):
    algo.stats['llm_patches_requested'] += n
    patches, explanations = list(answer), [''] * len(answer)
    while len(patches) < n:        # same padding as llm_sample_population
        sol = magpie.core.Patch()
        algo.mutate(sol)
        patches.append(str(sol))
        explanations.append(RANDOM_FALLBACK)
        algo.stats['llm_missing_patches'] += 1
    return patches, explanations


algo.llm_sample_population = fake_llm
pop = algo.sample_population()
strs = [str(p) for p in pop]
ok = True
for name, cond in [
    (f'population size is pop_size ({len(pop)})', len(pop) == pop_size),
    ('valid LLM patches kept as given', strs[0] == e[0] and strs[3] == e[1]),
    ('duplicate gets a random edit appended', len(pop[1].edits) == 2 and strs[1].startswith(e[0])),
    ('malformed replaced by a random 1-edit patch', len(pop[2].edits) in (1, 2)),
    ('malformed counted', algo.stats['llm_malformed_patches'] == 1),
    ('missing counted', algo.stats['llm_missing_patches'] == pop_size - 4),
    ('duplicate counted, malformed and missing not', algo.stats['llm_duplicate_patches'] == 1),
]:
    print(('ok   ' if cond else 'FAIL ') + name)
    ok &= cond
print(f"      stats: llm_malformed={algo.stats['llm_malformed_patches']} llm_missing={algo.stats['llm_missing_patches']} llm_duplicate={algo.stats['llm_duplicate_patches']}")
print('ALL OK' if ok else 'FAILURES')
