"""Recover best_patch_fitness_train / change_perc_train from MAGPIE train logs.

Motivation
----------
42 rows of results.csv carry best_patch_fitness_train=NaN and change_perc_train=0.0
even though the run did find, write and validate a real patch (the .patch file exists
on disk and validate_log is present). Those rows are concentrated in the LLM-guided
groups (LLM-llama 27, LLM-qwen 13, UMDA+qwen 2) and, because RQ4 computes
    overfit = change_perc_validate - change_perc_train
over every row without filtering, a spurious train value of 0 biases the
generalisation gap of exactly those groups.

Recovery
--------
MAGPIE's INFO log lines follow
    format_info = {counter} {status} {best}{fitness} ({ratio}) [{size}] ...
where {best} is '*' when the evaluation is a new global best. The fitness of the
last '*'-marked line is therefore the run's best training fitness, and
    change_perc_train = (best - reference) / reference * 100      (negative = improvement)
with the reference taken from the 'REF' line.

This module is validated against every row where the CSV value is present: see
validate() / the __main__ block, which report exact-match counts.
"""
import os
import re

import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_CSV = os.path.join(REPO_ROOT, "experiments", "results", "results.csv")
LOGS_DIR = os.path.join(REPO_ROOT, "_magpie_logs")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
# e.g. "0-6     SUCCESS              *13309267832.00 (98.60%) [1 edit(s)]"
BEST_RE = re.compile(r"\bSUCCESS\s+\*(\d+(?:\.\d+)?)")
REF_RE = re.compile(r"\bREF\s+SUCCESS\s+\*?(\d+(?:\.\d+)?)")


def parse_log(log_path):
    """Return (reference_fitness, best_fitness) parsed from a train log.

    best_fitness is None when the run never marked a new global best.
    """
    reference = None
    best = None
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = ANSI_RE.sub("", raw)
            if reference is None:
                m = REF_RE.search(line)
                if m:
                    reference = float(m.group(1))
                    continue
            m = BEST_RE.search(line)
            if m:
                best = float(m.group(1))  # keep overwriting: last '*' wins
    return reference, best


def log_path_for(row):
    stem = os.path.basename(row["train_log"])
    return os.path.join(LOGS_DIR, stem)


def recover(df):
    """Add recovered_reference / recovered_best / recovered_change_perc_train columns."""
    refs, bests = [], []
    for _, row in df.iterrows():
        p = log_path_for(row)
        if not os.path.exists(p):
            refs.append(float("nan"))
            bests.append(float("nan"))
            continue
        reference, best = parse_log(p)
        refs.append(reference if reference is not None else float("nan"))
        bests.append(best if best is not None else float("nan"))
    out = df.copy()
    out["recovered_reference"] = refs
    out["recovered_best"] = bests
    out["recovered_change_perc_train"] = (
        (out["recovered_best"] - out["recovered_reference"]) / out["recovered_reference"] * 100
    )
    return out


def validate(out, tol=0.001):
    """Compare recovered values against the CSV on rows where the CSV value is present."""
    known = out[out["best_patch_fitness_train"].notna()]
    got = known["recovered_best"].notna()
    fitness_match = (known["recovered_best"] == known["best_patch_fitness_train"])
    change_match = (
        (known["recovered_change_perc_train"] - known["change_perc_train"]).abs() < tol
    )
    return {
        "rows_with_csv_value": len(known),
        "recovered_something": int(got.sum()),
        "best_fitness_exact_match": int(fitness_match.sum()),
        "change_perc_within_tol": int(change_match.sum()),
        "mismatches": known[~fitness_match][
            ["software", "algorithm", "llm_model", "best_patch_fitness_train", "recovered_best"]
        ],
    }


if __name__ == "__main__":
    df = pd.read_csv(RESULTS_CSV)
    out = recover(df)

    v = validate(out)
    print("=== VALIDATION on rows where the CSV already has a value ===")
    print(f"  rows with CSV best_patch_fitness_train : {v['rows_with_csv_value']}")
    print(f"  recovered a value from the log         : {v['recovered_something']}")
    print(f"  best fitness EXACT match               : {v['best_fitness_exact_match']}")
    print(f"  change_perc_train within 0.001         : {v['change_perc_within_tol']}")
    if not v["mismatches"].empty:
        print("\n  MISMATCHES:")
        print(v["mismatches"].to_string())

    print("\n=== RECOVERY on the corrupted rows (CSV says NaN but a real patch exists) ===")
    corrupt = out[out["best_patch_fitness_train"].isna() & out["validate_log"].notna()]
    print(f"  corrupted rows                         : {len(corrupt)}")
    print(f"  of which recovered                     : {int(corrupt['recovered_best'].notna().sum())}")
    print()
    print(corrupt.groupby(["algorithm", corrupt["llm_model"].fillna("none")])
          ["recovered_change_perc_train"].describe()[["count", "mean", "min", "max"]].to_string())

    print("\n  CSV says change_perc_train = 0.0 for all of these; recovered values above.")
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovered_train_fitness.csv")
    out[["software", "algorithm", "llm_model", "fold", "max_evals", "train_log",
         "best_patch_fitness_train", "change_perc_train",
         "recovered_best", "recovered_change_perc_train"]].to_csv(out_path, index=False)
    print(f"\nWrote {out_path}")
