"""
RQ5 follow-up (exploratory): does combining UMDA4GI with an LLM change
patch-location diversity, compared to UMDA4GI alone and to the LLM used
on its own (LLMAlgorithm, no UMDA distribution)?

Same diversity metric as rq5_diversity.py:
    diversity = |union of edit-target locations across all patches in the cell|
                / (sum of patch_length across all patches in the cell)

Restricted to qwen2.5-coder:7b and llama3.1:8b (same two models used in the
paper's main RQ4 comparison; llama3.2:3b excluded here). Variants: UMDA4GI
base (algorithm == UMDAAlgorithm, llm_model is NaN), UMDA4GI+llm, and the
corresponding pure LLMAlgorithm runs (no UMDA).

Sample-size caveat (LLM-alone variants only): a (software, variant) cell's
n_runs is the number of runs with a successful, non-empty patch out of a
nominal 25 (5 folds x 5 budgets, same as the base algorithms, which is why
UMDA4GI/UMDA4GI+llm cells always land at or near 25). LLMAlgorithm's much
lower patch-finding rate (see RQ4: 8-15% vs 96-99% for UMDA) means several
of its cells rest on far fewer runs. To avoid the diversity ratio being
driven by noise from a handful of runs:
  - cells with n_runs < 40% of nominal (< 10 runs) are EXCLUDED from the
    ranking/overall/plot aggregates entirely, and reported separately.
  - cells with n_runs < 80% of nominal (< 20 runs) are KEPT but flagged
    ("*" in the table, hatched bar in the plot) as resting on a reduced
    sample, so the reader can discount them accordingly.
"""
import os
import re
import pandas as pd
import matplotlib.pyplot as plt

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_CSV = os.path.join(REPO_ROOT, "experiments", "results", "results.csv")
LOGS_DIR = os.path.join(REPO_ROOT, "_magpie_logs")
PLOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")

ALGO_MODEL_LABELS = {
    ("UMDAAlgorithm", "none"): "UMDA4GI",
    ("UMDAAlgorithm", "qwen2.5-coder:7b"): "UMDA4GI+qwen",
    ("UMDAAlgorithm", "llama3.1:8b"): "UMDA4GI+llama3.1",
    ("LLMAlgorithm", "qwen2.5-coder:7b"): "LLM-qwen",
    ("LLMAlgorithm", "llama3.1:8b"): "LLM-llama3.1",
}
VARIANT_ORDER = ["UMDA4GI", "UMDA4GI+qwen", "UMDA4GI+llama3.1", "LLM-qwen", "LLM-llama3.1"]

NOMINAL_N = 25
LOW_N_THRESHOLD = int(0.8 * NOMINAL_N)      # below this: flagged, kept
EXCLUDE_N_THRESHOLD = int(0.4 * NOMINAL_N)  # below this: dropped entirely

EDIT_RE = re.compile(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(\d+)\s*\)")


def parse_patch_targets(patch_path):
    """Return (set of target locations, number of edits) in a .patch file.

    The edit count is taken from the file itself rather than from the CSV's
    patch_length column: for 42 runs (all in the LLM-guided groups) the CSV
    records patch_length=0 and best_patch_fitness_train=NaN even though the
    run did produce and validate a real patch, so trusting patch_length would
    silently drop them. rq5_verify.py (Check 1) confirms the parsed count and
    patch_length agree on every run where the CSV value is valid.
    """
    with open(patch_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read().strip()
    if not content:
        return set(), 0
    targets = set()
    n_edits = 0
    for edit in content.split("|"):
        m = EDIT_RE.search(edit)
        if m:
            targets.add((m.group(1), m.group(2), int(m.group(3))))
            n_edits += 1
    return targets, n_edits


def main():
    df = pd.read_csv(RESULTS_CSV)
    umda = df[df["algorithm"].isin(["UMDAAlgorithm", "LLMAlgorithm"])].copy()
    umda["llm_model_key"] = umda["llm_model"].fillna("none")
    umda["variant"] = [
        ALGO_MODEL_LABELS.get((algo, model))
        for algo, model in zip(umda["algorithm"], umda["llm_model_key"])
    ]
    umda = umda[umda["variant"].notna()]

    rows = []
    missing_patch_files = 0
    empty_patch = 0
    recovered = 0
    for _, row in umda.iterrows():
        stem = os.path.splitext(os.path.basename(row["train_log"]))[0]
        patch_path = os.path.join(LOGS_DIR, stem + ".patch")
        if not os.path.exists(patch_path):
            missing_patch_files += 1
            continue
        targets, n_edits = parse_patch_targets(patch_path)
        if n_edits == 0:
            empty_patch += 1
            continue
        if pd.isna(row["patch_length"]) or row["patch_length"] <= 0:
            recovered += 1
        rows.append({
            "software": row["software"],
            "variant": row["variant"],
            "fold": row["fold"],
            "patch_length": n_edits,
            "targets": targets,
        })

    runs = pd.DataFrame(rows)
    print(f"Parsed {len(runs)} runs with a non-empty patch "
          f"({missing_patch_files} .patch files missing, {empty_patch} empty/unparseable).")
    print(f"  of which {recovered} runs recovered that the CSV's patch_length column reports as 0 "
          f"(patch really exists on disk; see parse_patch_targets docstring).")

    # per (software, variant) diversity
    cells = []
    for (software, variant), g in runs.groupby(["software", "variant"]):
        union_locations = set()
        for t in g["targets"]:
            union_locations |= t
        total_edits = g["patch_length"].sum()
        diversity = len(union_locations) / total_edits if total_edits > 0 else float("nan")
        cells.append({
            "software": software,
            "variant": variant,
            "n_runs": len(g),
            "unique_locations": len(union_locations),
            "total_edits": int(total_edits),
            "diversity": diversity,
        })
    cell_df = pd.DataFrame(cells)
    cell_df = cell_df.sort_values(["software", "variant"])

    excluded_df = cell_df[cell_df["n_runs"] < EXCLUDE_N_THRESHOLD].copy()
    cell_df = cell_df[cell_df["n_runs"] >= EXCLUDE_N_THRESHOLD].copy()
    cell_df["low_n"] = cell_df["n_runs"] < LOW_N_THRESHOLD

    print("\n=== Per (software, variant) diversity ===")
    print("(* = low_n: n_runs < {} out of nominal {}, kept but flagged)".format(LOW_N_THRESHOLD, NOMINAL_N))
    display_df = cell_df.copy()
    display_df["variant"] = display_df.apply(lambda r: r["variant"] + ("*" if r["low_n"] else ""), axis=1)
    print(display_df.drop(columns=["low_n"]).to_string(index=False))

    if not excluded_df.empty:
        print(f"\n=== EXCLUDED cells (n_runs < {EXCLUDE_N_THRESHOLD} out of nominal {NOMINAL_N}) ===")
        print(excluded_df.to_string(index=False))

    # exclude flagged-but-kept rows from ranking/overall too? no -- only drop EXCLUDE_N_THRESHOLD cells.
    runs = runs.merge(
        cell_df[["software", "variant"]].drop_duplicates(),
        on=["software", "variant"],
        how="inner",
    )

    pivot = cell_df.pivot(index="variant", columns="software", values="diversity")
    pivot = pivot[sorted(pivot.columns)]

    rank = pivot.rank(ascending=False, method="min")
    rank["n_cells"] = pivot.notna().sum(axis=1).astype(int)
    rank["Sum"] = pivot.rank(ascending=False, method="min").sum(axis=1, skipna=True)
    rank = rank.sort_values("Sum")
    print("\n=== Global ranking by diversity (1 = most diverse per software; NaN = cell excluded, not ranked) ===")
    print("(Sum is only comparable across variants with the same n_cells -- a variant missing a")
    print(" software due to exclusion sums over fewer terms than the others.)")
    print(rank.to_string())

    # overall (software-agnostic) diversity per variant, excluded cells already dropped from `runs`
    overall = []
    for variant, g in runs.groupby("variant"):
        union_locations = set()
        for t in g["targets"]:
            union_locations |= t
        total_edits = g["patch_length"].sum()
        overall.append({
            "variant": variant,
            "n_runs": len(g),
            "unique_locations": len(union_locations),
            "total_edits": int(total_edits),
            "diversity": len(union_locations) / total_edits if total_edits > 0 else float("nan"),
        })
    overall_df = pd.DataFrame(overall).sort_values("diversity", ascending=False)
    print("\n=== Overall diversity per variant (all software combined, excluded cells dropped) ===")
    print(overall_df.to_string(index=False))

    # plot: 2x2 grid, one subplot per software, bar per variant
    os.makedirs(PLOTS_DIR, exist_ok=True)
    softwares = sorted(pivot.columns)
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    def color_for(v):
        if v == "UMDA4GI":
            return "#2b6cb0"
        if v.startswith("UMDA4GI+"):
            return "#dd6b20"
        return "#718096"

    low_n_lookup = {(r["software"], r["variant"]): r["low_n"] for _, r in cell_df.iterrows()}
    excluded_lookup = {(r["software"], r["variant"]) for _, r in excluded_df.iterrows()}

    for ax, sw in zip(axes.flat, softwares):
        vals = [pivot.loc[v, sw] if v in pivot.index else float("nan") for v in VARIANT_ORDER]
        colors = [color_for(v) for v in VARIANT_ORDER]
        bars = ax.bar(VARIANT_ORDER, [0 if pd.isna(v) else v for v in vals], color=colors)
        for bar, v, variant in zip(bars, vals, VARIANT_ORDER):
            if (sw, variant) in excluded_lookup:
                bar.set_visible(False)
                ax.text(bar.get_x() + bar.get_width() / 2, 0.03, "excluded\n(n<10)",
                        ha="center", va="bottom", fontsize=7, rotation=90, color="#a0aec0")
            elif low_n_lookup.get((sw, variant)):
                bar.set_hatch("//")
                bar.set_edgecolor("white")
        ax.set_title(sw)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("diversity ratio")
        ax.tick_params(axis="x", rotation=30)
    fig.suptitle(
        "Patch-location diversity: UMDA4GI, UMDA4GI+LLM, and LLM alone\n"
        "(unique edited locations / total edits, higher = more diverse)\n"
        "hatched = low n_runs (<20/25, flagged); blank = excluded (n_runs<10)"
    )
    fig.tight_layout()
    out_path = os.path.join(PLOTS_DIR, "RQ5_umda_llm_diversity.svg")
    fig.savefig(out_path)
    print(f"\nSaved plot to {out_path}")

    cell_df.to_csv(os.path.join(PLOTS_DIR, "RQ5_umda_llm_diversity_data.csv"), index=False)


if __name__ == "__main__":
    main()
