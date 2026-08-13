"""
RQ5 (exploratory): how diverse are the code locations edited by each
algorithm's patches, across independent runs (folds x budgets)?

Diversity metric per (software, algorithm) cell:
    diversity = |union of edit-target locations across all patches in the cell|
                / (sum of patch_length across all patches in the cell)

A location is a (file, node_type, node_id) triple taken from the FIRST
tuple of each edit operation in a .patch file (the edit's target, i.e.
the place in the code being deleted/replaced/inserted-before/etc.),
regardless of edit type (XmlNodeDeletion/Replacement/Insertion/
TextSetting/TextWrapping).

diversity close to 1: almost every edit lands on a location not touched
    by any other run in the same cell -> highly diverse exploration.
diversity close to 0: runs repeatedly converge on the same few
    locations -> low diversity.

Restricted to the 4 base (non-LLM) algorithms, same scope as RQ1/RQ2,
since that's the cleanest comparison and the one the paper's Related
Work diversity comment refers to.
"""
import os
import re
import pandas as pd
import matplotlib.pyplot as plt

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_CSV = os.path.join(REPO_ROOT, "experiments", "results", "results.csv")
LOGS_DIR = os.path.join(REPO_ROOT, "_magpie_logs")
PLOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")

ALGO_LABELS = {
    "FirstImprovement": "FI",
    "GeneticProgrammingUniformConcat": "GP",
    "RandomSearch": "RandomS",
    "UMDAAlgorithm": "UMDA4GI",
}

# matches e.g. XmlNodeDeletion<stmt>(('file.xml', 'stmt', 81))
# or        XmlNodeReplacement<stmt>(('file.xml', 'stmt', 40), ('file.xml', 'stmt', 356))
EDIT_RE = re.compile(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(\d+)\s*\)")


def parse_patch_targets(patch_path):
    """Return the set of (file, node_type, node_id) target locations in a .patch file.
    Only the first tuple of each ' | '-separated edit is the target being edited."""
    with open(patch_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read().strip()
    if not content:
        return set()
    targets = set()
    for edit in content.split("|"):
        m = EDIT_RE.search(edit)
        if m:
            targets.add((m.group(1), m.group(2), int(m.group(3))))
    return targets


def main():
    df = pd.read_csv(RESULTS_CSV)
    base = df[df["algorithm"].isin(ALGO_LABELS.keys()) & df["llm_model"].isna()].copy()

    rows = []
    missing_patch_files = 0
    for _, row in base.iterrows():
        if pd.isna(row["patch_length"]) or row["patch_length"] <= 0:
            continue
        stem = os.path.splitext(os.path.basename(row["train_log"]))[0]
        patch_path = os.path.join(LOGS_DIR, stem + ".patch")
        if not os.path.exists(patch_path):
            missing_patch_files += 1
            continue
        targets = parse_patch_targets(patch_path)
        rows.append({
            "software": row["software"],
            "algorithm": row["algorithm"],
            "max_evals": row["max_evals"],
            "fold": row["fold"],
            "patch_length": row["patch_length"],
            "targets": targets,
        })

    runs = pd.DataFrame(rows)
    print(f"Parsed {len(runs)} runs with a valid patch ({missing_patch_files} .patch files missing locally).")

    # per (software, algorithm) diversity
    cells = []
    for (software, algorithm), g in runs.groupby(["software", "algorithm"]):
        union_locations = set()
        for t in g["targets"]:
            union_locations |= t
        total_edits = g["patch_length"].sum()
        diversity = len(union_locations) / total_edits if total_edits > 0 else float("nan")
        cells.append({
            "software": software,
            "algorithm": ALGO_LABELS[algorithm],
            "n_runs": len(g),
            "unique_locations": len(union_locations),
            "total_edits": int(total_edits),
            "diversity": diversity,
        })
    cell_df = pd.DataFrame(cells)
    cell_df = cell_df.sort_values(["software", "algorithm"])
    print("\n=== Per (software, algorithm) diversity ===")
    print(cell_df.to_string(index=False))

    pivot = cell_df.pivot(index="algorithm", columns="software", values="diversity")
    pivot = pivot[sorted(pivot.columns)]

    # ranking: 1 = most diverse (highest ratio) per software
    rank = pivot.rank(ascending=False, method="min").astype(int)
    rank["Sum"] = rank.sum(axis=1)
    rank = rank.sort_values("Sum")
    print("\n=== Global ranking by diversity (1 = most diverse per software) ===")
    print(rank.to_string())

    # overall (software-agnostic) diversity per algorithm, for the headline claim
    overall = []
    for algorithm, g in runs.groupby("algorithm"):
        union_locations = set()
        for t in g["targets"]:
            union_locations |= t
        total_edits = g["patch_length"].sum()
        overall.append({
            "algorithm": ALGO_LABELS[algorithm],
            "n_runs": len(g),
            "unique_locations": len(union_locations),
            "total_edits": int(total_edits),
            "diversity": len(union_locations) / total_edits if total_edits > 0 else float("nan"),
        })
    overall_df = pd.DataFrame(overall).sort_values("diversity", ascending=False)
    print("\n=== Overall diversity per algorithm (all software combined) ===")
    print(overall_df.to_string(index=False))

    # plot: 2x2 grid, one subplot per software, bar per algorithm
    os.makedirs(PLOTS_DIR, exist_ok=True)
    softwares = sorted(pivot.columns)
    algo_order = ["UMDA4GI", "FI", "GP", "RandomS"]
    fig, axes = plt.subplots(2, 2, figsize=(9, 7), sharey=True)
    for ax, sw in zip(axes.flat, softwares):
        vals = [pivot.loc[a, sw] if a in pivot.index else float("nan") for a in algo_order]
        colors = ["#2b6cb0" if a == "UMDA4GI" else "#a0aec0" for a in algo_order]
        ax.bar(algo_order, vals, color=colors)
        ax.set_title(sw)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("diversity ratio")
    fig.suptitle("Patch-location diversity per algorithm and software\n(unique edited locations / total edits, higher = more diverse)")
    fig.tight_layout()
    out_path = os.path.join(PLOTS_DIR, "RQ5_patch_diversity.svg")
    fig.savefig(out_path)
    print(f"\nSaved plot to {out_path}")

    cell_df.to_csv(os.path.join(PLOTS_DIR, "RQ5_patch_diversity_data.csv"), index=False)


if __name__ == "__main__":
    main()
