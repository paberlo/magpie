"""Sanity checks for rq5_diversity.py's parsing and a length-confound control."""
import os
import re
import glob
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_CSV = os.path.join(REPO_ROOT, "experiments", "results", "results.csv")
LOGS_DIR = os.path.join(REPO_ROOT, "_magpie_logs")

ALGO_LABELS = {
    "FirstImprovement": "FI",
    "GeneticProgrammingUniformConcat": "GP",
    "RandomSearch": "RandomS",
    "UMDAAlgorithm": "UMDA4GI",
}

EDIT_RE = re.compile(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(\d+)\s*\)")


def parse_patch_targets(patch_path):
    with open(patch_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read().strip()
    if not content:
        return set(), 0
    edits = content.split("|")
    targets = set()
    unmatched = 0
    for edit in edits:
        m = EDIT_RE.search(edit)
        if m:
            targets.add((m.group(1), m.group(2), int(m.group(3))))
        else:
            unmatched += 1
    return targets, unmatched, len(edits)


# --- Check 1: does patch_length in results.csv match number of edits parsed from the .patch file? ---
df = pd.read_csv(RESULTS_CSV)
base = df[df["algorithm"].isin(ALGO_LABELS.keys()) & df["llm_model"].isna()].copy()
base = base[base["patch_length"] > 0]

mismatches = []
unmatched_total = 0
checked = 0
for _, row in base.iterrows():
    stem = os.path.splitext(os.path.basename(row["train_log"]))[0]
    patch_path = os.path.join(LOGS_DIR, stem + ".patch")
    if not os.path.exists(patch_path):
        continue
    targets, unmatched, n_edits_in_line = parse_patch_targets(patch_path)
    unmatched_total += unmatched
    checked += 1
    if n_edits_in_line != int(row["patch_length"]):
        mismatches.append((stem, row["algorithm"], row["patch_length"], n_edits_in_line))

print(f"Checked {checked} patch files.")
print(f"Unmatched edit substrings (regex failed to parse): {unmatched_total}")
print(f"Rows where parsed edit count != CSV patch_length: {len(mismatches)}")
for m in mismatches[:20]:
    print("  ", m)

# --- Check 2: patch_length distribution per algorithm (confirms the length asymmetry) ---
print("\n=== patch_length distribution per algorithm (non-LLM, patch_length>0) ===")
print(base.groupby("algorithm")["patch_length"].describe()[["count", "mean", "std", "min", "max"]])

# --- Check 3: length-confound control. Restrict to patch_length==1 runs only, recompute diversity ---
print("\n=== Diversity ratio restricted to single-edit patches only (patch_length==1) ===")
rows = []
for _, row in base[base["patch_length"] == 1].iterrows():
    stem = os.path.splitext(os.path.basename(row["train_log"]))[0]
    patch_path = os.path.join(LOGS_DIR, stem + ".patch")
    if not os.path.exists(patch_path):
        continue
    targets, unmatched, _ = parse_patch_targets(patch_path)
    rows.append({"software": row["software"], "algorithm": ALGO_LABELS[row["algorithm"]], "target": next(iter(targets)) if targets else None})

single = pd.DataFrame(rows).dropna()
for (algorithm), g in single.groupby("algorithm"):
    n = len(g)
    n_unique = g["target"].nunique()
    print(f"  {algorithm}: n_single_edit_runs={n}, unique_targets={n_unique}, ratio={n_unique/n:.3f}")

# --- Check 4: null-model expected ratio using true AST size (count of 'stmt' nodes per software) ---
print("\n=== Candidate pool size (stmt nodes) per software, vs union of locations actually used ===")
xml_map = {
    "minisat_hack": os.path.join(REPO_ROOT, "experiments", "minisat_hack", "sources", "core", "Solver.cc.xml"),
}
for sw, path in xml_map.items():
    if not os.path.exists(path):
        print(f"  {sw}: xml not found at {path}")
        continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    # crude count of stmt-tagged elements; real srcML tag pattern may differ, treat as rough proxy
    n_stmt_like = len(re.findall(r"<stmt[ >]", content))
    print(f"  {sw}: crude <stmt> tag count in xml = {n_stmt_like}")
