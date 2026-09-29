"""
CLI Runner Entrypoint.
Provides a clean wrapper to invoke the pipeline from any directory.
"""
import sys
import os
from src.pipeline import run_pipeline

def main():
    pdf_target = "data/Persis_Yu_Deposition_Problem_statement.pdf"
    if len(sys.argv) > 1:
        pdf_target = sys.argv[1]

    if not os.path.exists(pdf_target):
        # Fallback to local root if data/ prefix is absent
        if os.path.exists("Persis_Yu_Deposition_Problem_statement.pdf"):
            pdf_target = "Persis_Yu_Deposition_Problem_statement.pdf"
        else:
            print(f"Error: Target transcript PDF '{pdf_target}' not found.")
            sys.exit(1)

    print(f"Starting DepoIndex execution on target: {pdf_target}")
    run_pipeline(pdf_target)

if __name__ == "__main__":
    main()