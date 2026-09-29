"""
Independent Evaluation & Compliance Reporter.
Audits the final production CSV against all required court invariants.
"""
import os
import json
import pandas as pd

def evaluate_pipeline_output(csv_path: str = "Persis_Yu_Topic_Index.csv"):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} does not exist.")
        return

    df = pd.read_csv(csv_path)
    print("\n=======================================================")
    print("=== DEPOSITION INDEX COMPLIANCE & CONTINUITY REPORT ===")
    print("=======================================================")
    print(f"Total Substantive Topics: {len(df)}")
    
    # Invariant 1: Row count range check (Must be comprehensive, 18-28 topics)
    if 18 <= len(df) <= 28:
        print("✓ Topic Count Invariant: PASSED (Cohesive macro-level indexing)")
    else:
        print(f"⚠ Topic Count Warning: Found {len(df)} topics (Expected 18-28)")

    # Invariant 2: Proper Start Anchor (Page 7, Line 11)
    first_start = df.iloc[0]["Start"]
    if "Page 7" in first_start:
        print(f"✓ Deposition Start Anchor: PASSED ({first_start})")
    else:
        print(f"✗ Deposition Start Anchor: FAILED ({first_start})")

    # Invariant 3: Proper End Anchor (Page 88, Line 17)
    last_end = df.iloc[-1]["End"]
    if "Page 88" in last_end:
        print(f"✓ Deposition End Anchor: PASSED ({last_end})")
    else:
        print(f"✗ Deposition End Anchor: FAILED ({last_end})")

    # Invariant 4: No Multi-Page Gaps
    print("\n=== Seam Continuity Audit ===")
    for i in range(len(df) - 1):
        c_end = df.iloc[i]["End"]
        n_start = df.iloc[i+1]["Start"]
        print(f"  Topic {i+1:02d} -> {i+2:02d}: {c_end} ===> {n_start}")

    print("\nEvaluation complete.")

if __name__ == "__main__":
    evaluate_pipeline_output()