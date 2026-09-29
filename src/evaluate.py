"""
Independent Evaluation & Compliance Reporter.
Audits the production CSV against all required court invariants.
"""
import os
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
    
    # Invariant 1: Topic Count
    if 17 <= len(df) <= 25:
        print(f"✓ Topic Count Invariant: PASSED ({len(df)} topics)")
    else:
        print(f"⚠ Topic Count Warning: Found {len(df)} topics (Expected 17-25)")

    # Invariant 2: Start Anchor
    first_start = df.iloc[0]["Start"]
    if "Page 7, Line 11" in first_start:
        print(f"✓ Deposition Start Anchor: PASSED ({first_start})")
    else:
        print(f"✗ Deposition Start Anchor: FAILED ({first_start})")

    # Invariant 3: End Anchor
    last_end = df.iloc[-1]["End"]
    if "Page 88, Line 17" in last_end:
        print(f"✓ Deposition End Anchor: PASSED ({last_end})")
    else:
        print(f"✗ Deposition End Anchor: FAILED ({last_end})")

    # Invariant 4: Continuous Seams
    print("\n=== Seam Continuity Audit ===")
    gaps_found = 0
    for i in range(len(df) - 1):
        c_end = df.iloc[i]["End"]
        n_start = df.iloc[i+1]["Start"]
        
        c_p = int(c_end.split(',')[0].replace('Page', '').strip())
        n_p = int(n_start.split(',')[0].replace('Page', '').strip())
        
        if n_p > c_p + 1:
            print(f"  [GAP]: Topic {i+1} ({c_end}) -> Topic {i+2} ({n_start})")
            gaps_found += 1
        else:
            print(f"  ✓ Seam {i+1:02d} -> {i+2:02d}: {c_end} ===> {n_start}")

    if gaps_found == 0:
        print("\n✓ Seam Continuity: 100% Contiguous across all pages.")
    else:
        print(f"\n⚠ Seam Continuity: {gaps_found} gap(s) detected.")

    print("\nEvaluation complete.")

if __name__ == "__main__":
    evaluate_pipeline_output()