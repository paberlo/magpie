"""Figures of MiniSAT-hack fold 4 quoted in the paper (Threats to validity) and in the response
letter, from ms_check.out: CPU cycles of each of the 20 instances, 3 repetitions, for four builds of
Solver.cc measured on one compute node:
  original  the unmodified Solver.cc
  dump      MAGPIE's rendering of it without any edit (the code every variant starts from)
  del432    deletion of statement 432, inside toDimacs, which is never executed (a no-op patch)
  del130    deletion of statement 130, the call to varBumpActivity (Solver_del130.diff)
Run from this folder: python summary.py"""
import collections
import pathlib
import statistics

HERE = pathlib.Path(__file__).parent
VALIDATE4 = HERE / '../../minisat_hack/data/validate4'

runs = collections.defaultdict(list)
for line in (HERE / 'ms_check.out').read_text().splitlines():
    if line.startswith('#') or not line.strip():
        continue
    version, _, cnf, _, cycles = line.split()
    runs[version, cnf].append(int(cycles))
cyc = {k: statistics.median(v) for k, v in runs.items()}
instances = sorted({cnf for _, cnf in cyc})
fold4 = VALIDATE4.read_text().split()


def total(version, cnfs):
    return sum(cyc[version, c] for c in cnfs)


def change(version, cnfs, ref='original'):
    return 100 * (total(version, cnfs) / total(ref, cnfs) - 1)


print(f'share of uf200-02 in the cycles of the fold-4 validation set: '
      f'{100 * cyc["original", "data/uf200-02.cnf"] / total("original", fold4):.1f}%')
for v in ('dump', 'del432', 'del130'):
    print(f'{v}: fold-4 validation {change(v, fold4):+.1f}%, all 20 instances {change(v, instances):+.1f}%')
print(f'del130 on uf200-02: {change("del130", ["data/uf200-02.cnf"]):+.1f}%')
per = {c: change('del130', [c]) for c in instances}
print('del130 per instance:', ', '.join(f'{c[5:-4]} {d:+.0f}%' for c, d in sorted(per.items(), key=lambda kv: kv[1])))
