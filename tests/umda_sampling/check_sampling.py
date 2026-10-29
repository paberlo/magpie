"""Checks the invariants of UMDAAlgorithm.sample_population on the real MiniSAT software."""
import configparser
import random
import sys

sys.path.insert(0, '.')
import magpie
from magpie.algos import UMDAAlgorithm

random.seed(7)
config = configparser.ConfigParser()
config.read_dict(magpie.core.default_scenario)
config.read('experiments/minisat_hack/_magpie/scenario_cycles_xml_FOLD1_steps100.txt')
magpie.core.pre_setup(config)
magpie.core.setup(config)
software = magpie.utils.software_from_string(config['software']['software'])(config)


def make_algo(k_max):
    algo = UMDAAlgorithm()
    algo.software = software
    config['search.eda']['k_max'] = str(k_max)
    algo.setup(config)
    algo.reset()
    return algo


base = make_algo(2)
dist_edits = []
while len(dist_edits) < 3:
    e = str(base.create_edit(software.noop_variant))
    if e not in dist_edits:
        dist_edits.append(e)
dist = {dist_edits[0]: 0.6, dist_edits[1]: 0.3, dist_edits[2]: 0.1}

failures = 0


def check(name, cond):
    global failures
    print(('ok   ' if cond else 'FAIL ') + name)
    failures += not cond


for k_max in (1, 2, 3):
    algo = make_algo(k_max)
    pop = algo.sample_population(dist)
    strs = [str(p) for p in pop]
    from_dist = [p for p in pop if all(str(e) in dist for e in p.edits)]
    random_ones = [p for p in pop if p not in from_dist]
    n_dist_patches = sum(len(dist) ** 1 if k == 1 else 0 for k in [1])  # unused, kept simple
    check(f'k_max={k_max}: population size is pop_size ({len(pop)})', len(pop) == algo.config['pop_size'])
    check(f'k_max={k_max}: all patches distinct', len(set(strs)) == len(strs))
    check(f'k_max={k_max}: patches from the distribution have at most k_max edits',
          all(len(p.edits) <= k_max for p in from_dist))
    check(f'k_max={k_max}: no edit repeated inside a patch',
          all(len({str(e) for e in p.edits}) == len(p.edits) for p in pop))
    check(f'k_max={k_max}: replacements are random 1-edit patches',
          all(len(p.edits) == 1 for p in random_ones))
    # with 3 edits, the distribution can yield at most 3 + 3*2 (+ 3*2*1) distinct patches
    max_from_dist = {1: 3, 2: 3 + 6, 3: 3 + 6 + 6}[k_max]
    check(f'k_max={k_max}: {len(from_dist)} patches from the distribution (<= {max_from_dist})',
          0 < len(from_dist) <= max_from_dist)
    print(f'      stats: {dict((k, v) for k, v in algo.stats.items() if k.startswith("sample_"))}')

# a large distribution: almost every patch comes from it, with 1 or 2 edits
algo = make_algo(2)
big = {}
while len(big) < 200:
    big[str(algo.create_edit(software.noop_variant))] = random.random()
total = sum(big.values())
big = {k: v / total for k, v in big.items()}
pop = algo.sample_population(big)
from_dist = [p for p in pop if all(str(e) in big for e in p.edits)]
check(f'large distribution: {len(from_dist)}/{len(pop)} patches from the distribution', len(from_dist) >= len(pop) - 2)
check('large distribution: all distinct', len({str(p) for p in pop}) == len(pop))

# empty distribution: random distinct 1-edit patches
algo = make_algo(2)
pop = algo.sample_population({})
check('empty distribution: pop_size distinct random 1-edit patches',
      len(pop) == algo.config['pop_size'] and len({str(p) for p in pop}) == len(pop)
      and all(len(p.edits) == 1 for p in pop))

# elitism: the best patch is kept and not duplicated
algo = make_algo(2)
best = magpie.core.Patch()
best.edits.append(algo._edit_from_str(dist_edits[0]))
algo.report['best_patch'] = best
pop = algo.sample_population(dist, elitism=True)
check('elitism: best patch first and population still distinct',
      str(pop[0]) == str(best) and len({str(p) for p in pop}) == len(pop) and len(pop) == algo.config['pop_size'])

# generation without valid variants keeps the previous distribution
algo = make_algo(2)


class Run:
    def __init__(self, status, fitness=None):
        self.status, self.fitness = status, fitness


p1 = magpie.core.Patch()
p1.edits.append(algo._edit_from_str(dist_edits[0]))
kept = algo._next_distribution({p1: Run('COMPILE_CODE_ERROR')}, dist)
check('no valid variant: previous distribution kept', kept == dist and algo.stats['gens_without_valid'] == 1)
first = algo._next_distribution({p1: Run('TEST_CODE_ERROR')}, None)
check('no valid variant in the first generation: empty distribution', first == {})
learnt = algo._next_distribution({p1: Run('SUCCESS', 10)}, dist)
check('valid variant: distribution learnt from it', learnt == {dist_edits[0]: 1.0})

print('ALL OK' if failures == 0 else f'{failures} FAILURES')
