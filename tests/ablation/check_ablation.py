"""Checks the ablation options on the real MiniSAT software (run from the repository root)."""
import configparser
import copy
import random
import sys

sys.path.insert(0, '.')
import magpie
from magpie.algos import UMDAAlgorithm, FirstImprovement, GeneticProgrammingUniformConcat

SCENARIO = 'experiments/minisat_hack/_magpie/scenario_cycles_xml_FOLD1_steps100.txt'
failures = 0


def check(name, cond):
    global failures
    print(('ok   ' if cond else 'FAIL ') + name)
    failures += not cond


def build(klass, search_extra=None, eda_extra=None):
    config = configparser.ConfigParser()
    config.read_dict(magpie.core.default_scenario)
    config.read(SCENARIO)
    for k, v in (search_extra or {}).items():
        config['search'][k] = v
    for k, v in (eda_extra or {}).items():
        config['search.eda'][k] = v
    magpie.core.pre_setup(config)
    magpie.core.setup(config)
    software = magpie.utils.software_from_string(config['software']['software'])(config)
    algo = klass()
    algo.software = software
    algo.setup(config)
    algo.reset()
    return algo


def random_patch(algo, n):
    p = magpie.core.Patch()
    for _ in range(n):
        p.edits.append(algo.create_edit(algo.software.noop_variant))
    return p


# --- FI: without the option, moves and random draws are those of the original mutate
fi = build(FirstImprovement)
check('FI: max_patch_edits unset by default', fi.config['max_patch_edits'] is None)


def original_ls_mutate(algo, patch):
    n = len(patch.edits)
    if n == 0:
        patch.edits.append(algo.create_edit(algo.software.noop_variant))
    elif random.random() < algo.config['delete_prob']:
        del patch.edits[random.randrange(0, n)]
    else:
        patch.edits.append(algo.create_edit(algo.software.noop_variant))


random.seed(5)
start = [random_patch(fi, random.randint(0, 6)) for _ in range(200)]
random.seed(9); new = [copy.deepcopy(p) for p in start]
for p in new: fi.mutate(p)
random.seed(9); old = [copy.deepcopy(p) for p in start]
for p in old: original_ls_mutate(fi, p)
check('FI: unchanged behaviour and random stream without the option',
      [str(p) for p in new] == [str(p) for p in old])

fi2 = build(FirstImprovement, search_extra={'max_patch_edits': '2'})
random.seed(1)
patches = [random_patch(fi2, 2) for _ in range(100)]
for p in patches: fi2.mutate(p)
check('FI with max_patch_edits=2: a 2-edit patch always loses an edit', all(len(p.edits) == 1 for p in patches))
p = random_patch(fi2, 0)
lengths = []
for _ in range(500):
    fi2.mutate(p)
    lengths.append(len(p.edits))
check(f'FI with max_patch_edits=2: a random walk never exceeds 2 (max {max(lengths)})', max(lengths) <= 2)

# --- GP
gp = build(GeneticProgrammingUniformConcat)
check('GP: max_patch_edits unset by default', gp.config['max_patch_edits'] is None)
random.seed(3)
long_child = random_patch(gp, 7)
before = str(long_child)
check('GP: limit_length is a no-op without the option', str(gp.limit_length(long_child)) == before)
gp2 = build(GeneticProgrammingUniformConcat, search_extra={'max_patch_edits': '2'})
ok_order = True
for _ in range(100):
    child = random_patch(gp2, random.randint(3, 8))
    edits = [str(e) for e in child.edits]
    kept = [str(e) for e in gp2.limit_length(child).edits]
    pos = [edits.index(e) for e in kept]
    ok_order &= len(kept) == 2 and pos == sorted(pos)
check('GP with max_patch_edits=2: long children keep 2 edits in their order', ok_order)
patches = [random_patch(gp2, 2) for _ in range(100)]
for p in patches: gp2.mutate(p)
check('GP with max_patch_edits=2: mutation of a 2-edit patch deletes', all(len(p.edits) == 1 for p in patches))

# --- UMDA select
umda = build(UMDAAlgorithm)
check('UMDA: select = valid by default', umda.config['select'] == 'valid')


class Run:
    def __init__(self, status, fitness=None):
        self.status, self.fitness = status, fitness


a, b, c = random_patch(umda, 1), random_patch(umda, 1), random_patch(umda, 1)
pop = {a: Run('SUCCESS', 90), b: Run('SUCCESS', 110), c: Run('COMPILE_CODE_ERROR')}
umda.report['reference_fitness'] = 100
check('UMDA select=valid: learns from both valid variants', len(umda.select(pop)) == 2)
umda_imp = build(UMDAAlgorithm, eda_extra={'select': 'improving'})
umda_imp.report['reference_fitness'] = 100
sel = umda_imp.select(pop)
check('UMDA select=improving: learns only from the faster one', [str(s) for s in sel] == [str(a)])
pop2 = {b: Run('SUCCESS', 110)}
dist = umda_imp._next_distribution(pop2, {'x': 1.0})
check('UMDA select=improving, nothing faster: previous distribution kept', dist == {'x': 1.0})
try:
    build(UMDAAlgorithm, eda_extra={'select': 'best'})
    check('UMDA: invalid select rejected', False)
except magpie.core.ScenarioError:
    check('UMDA: invalid select rejected', True)

print('ALL OK' if failures == 0 else f'{failures} FAILURES')
