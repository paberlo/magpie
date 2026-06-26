import json, uuid

NB = 'experiments/results_UCL/analysis.ipynb'

def md_cell(text):
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": text
    }

CONCLUSIONS = {
    "cdd1285a": md_cell("""\
### RQ1 — Findings
- All algorithms achieve similar **median** `change_perc_validate` across budgets (near 0%, with occasional large improvements).
- UMDA is **competitive** with FirstImprovement, GP, and RandomSearch: no algorithm consistently dominates across all budgets and software.
- The means are pulled by a small number of large improvements (skewed distribution); the median is the more representative measure.
- **Answer**: Yes, UMDA obtains competitive results against state-of-the-art GI algorithms."""),

    "a960927c": md_cell("""\
### RQ2 — Findings
- **Overfitting** = `change_perc_validate − change_perc_train`. Positive values indicate the patch generalises worse than it trains (typical in GI).
- At low budgets (100 steps), **UMDA** and **GP** show the lowest median overfitting (~1.3 and 0.5).
- At high budgets (750–1000 steps), **RandomSearch** is the most stable (overfitting does not grow with budget).
- **FirstImprovement** and **GP** show high variance in overfitting, with extreme outlier values at some budgets.
- **Answer**: No single algorithm dominates in all budgets. UMDA and GP are the most reliable at low budgets; RandomSearch at high budgets."""),

    "26752d81": md_cell("""\
### RQ3 — Findings
- **Vt** (valid test ratio) correlates significantly with both `change_perc_validate` (ρ=0.443, p<0.001) and overfitting (ρ=−0.194, p<0.001): higher Vt associates with less overfitting.
- **Vc** (valid compile+test ratio) is also significant but weaker (ρ=0.244 with validate, ρ=−0.089 with overfitting).
- **max_evals (budget) does NOT correlate** with `change_perc_validate` (ρ=−0.029, p=0.41) nor with overfitting (ρ=0.036, p=0.31).
- **Answer**: Vt and Vc are predictors of generalisation quality; budget alone is not."""),

    "64f64c7f": md_cell("""\
### RQ4 — Findings
**Primary metric: median** (means are distorted by outliers — see note below).

- **LLM pure** achieves the best mean `change_perc_validate` at high budgets (750, 1000 steps).
- **UMDA+LLM** does not outperform LLM pure in `change_perc_validate` or overfitting as a general rule.
- **Key advantage of UMDA+LLM**: consistently **lower standard deviation** across all budgets — results are more predictable and stable than LLM pure.

| Budget | LLM pure std | UMDA+LLM std |
|--------|-------------|-------------|
| 100 | 26.9 | **22.5** |
| 250 | 27.9 | **18.8** |
| 500 | 43.6 | **30.6** |
| 750 | 33.8 | **27.5** |
| 1000 | 35.4 | **33.9** |

> **⚠️ Notable outlier — minisat_hack FOLD1, LLM pure, 500 steps:**
> Both LLMs (llama: +107%, qwen: +152% on validate) found patches with massive training improvement
> (−47%, −79%) that generalise catastrophically. This is **not a technical failure** (0 compile errors,
> no timeouts) but genuine overfitting: the training workload (~49B cycles) is ~170× larger than
> the validation workload (~293M cycles), and the LLM exploited training-specific characteristics.
> These cases illustrate the **generalisation risk of LLM pure** and should be discussed in the paper.

**Answer**: UMDA+LLM does not clearly outperform LLM pure in raw improvement, but provides **more consistent results** due to the guiding effect of the learned UMDA distribution."""),
}

with open(NB) as f:
    nb = json.load(f)

new_cells = []
for cell in nb['cells']:
    new_cells.append(cell)
    cid = cell.get('id', '')
    if cid in CONCLUSIONS:
        new_cells.append(CONCLUSIONS[cid])

nb['cells'] = new_cells

with open(NB, 'w') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Done. {len(nb['cells'])} cells total.")
