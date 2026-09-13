import json
import os
import shutil
import pandas as pd
from rapidfuzz import fuzz
from src.pipeline import run_pipeline

def execute_three_runs():
    os.makedirs("output", exist_ok=True)
    run_files = ["output/run_1.json", "output/run_2.json", "output/run_3.json"]
    if os.path.exists("output/topic_index.json") and not os.path.exists("output/run_1.json"):
        shutil.copy("output/topic_index.json", "output/run_1.json")
        print("✓ Run 1 adopted from existing topic_index.json")

    for i in range(1, 4):
        target_file = f"output/run_{i}.json"
        if not os.path.exists(target_file):
            print(f"\n==========================================")
            print(f"       EXECUTING STABILITY RUN #{i}")
            print(f"==========================================")
            if os.path.exists("output/chunks_cache.json"):
                os.remove("output/chunks_cache.json")
            
            run_pipeline()
            shutil.copy("output/topic_index.json", target_file)
            print(f"✓ Saved: {target_file}")
        else:
            print(f"✓ Run #{i} already exists at {target_file}")
    runs = []
    for f in run_files:
        with open(f, "r", encoding="utf-8") as fp:
            runs.append(json.load(fp))

    print("\n==========================================")
    print("      STABILITY COMPARISON RESULTS        ")
    print("==========================================")
    
    counts = [len(r) for r in runs]
    print(f"Topic Counts: Run 1 = {counts[0]} | Run 2 = {counts[1]} | Run 3 = {counts[2]}")
    for pair_name, r_a, r_b in [("Run 1 vs Run 2", runs[0], runs[1]), ("Run 1 vs Run 3", runs[0], runs[2])]:
        min_len = min(len(r_a), len(r_b))
        exact_spans = 0
        label_sims = []
        line_drifts = []

        for j in range(min_len):
            item_a, item_b = r_a[j], r_b[j]
            sim = fuzz.ratio(item_a["topic"].lower(), item_b["topic"].lower())
            label_sims.append(sim)
            span_a = f"{item_a['start']} - {item_a['end']}"
            span_b = f"{item_b['start']} - {item_b['end']}"
            if span_a == span_b:
                exact_spans += 1
            try:
                l_a = int(item_a["start"].split("Line ")[1])
                l_b = int(item_b["start"].split("Line ")[1])
                line_drifts.append(abs(l_a - l_b))
            except Exception:
                pass

        pct_exact = (exact_spans / min_len) * 100
        avg_sim = sum(label_sims) / len(label_sims) if label_sims else 0
        avg_drift = sum(line_drifts) / len(line_drifts) if line_drifts else 0

        print(f"\n--- {pair_name} ---")
        print(f"• Identical Coordinate Spans: {exact_spans}/{min_len} ({pct_exact:.1f}%)")
        print(f"• Mean Semantic Label Similarity: {avg_sim:.1f}%")
        print(f"• Mean Start Line Drift: {avg_drift:.2f} lines")

if __name__ == "__main__":
    execute_three_runs()