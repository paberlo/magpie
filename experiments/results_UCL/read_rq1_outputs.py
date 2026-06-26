import json
with open("experiments/results_UCL/RQ1.ipynb") as f:
    nb = json.load(f)
for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code" and cell.get("outputs"):
        print(f"=== Cell {i} ===")
        for out in cell["outputs"]:
            if out.get("output_type") == "stream":
                print("".join(out["text"]))
            elif out.get("output_type") == "error":
                print("ERROR:", out["ename"], out["evalue"])
