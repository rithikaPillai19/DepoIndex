import pymupdf as fitz
import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def build_document_page_index(pdf_path: str, output_path: str = "data/page_index.json"):
    doc = fitz.open(pdf_path)
    page_index = []

    print(f"Building Page-Level Index across all {len(doc)} pages...")

    for page_num in range(len(doc)):
        page_text = doc[page_num].get_text("text").strip()
        actual_page = page_num + 1

        # Skip empty pages or raw multi-column concordance tables
        if len(page_text) < 50 or "WORD INDEX" in page_text.upper():
            continue

        # Extract first 400 chars as a fast summary representation
        preview = " ".join(page_text.split()[:75])
        page_index.append({
            "page": actual_page,
            "preview": preview
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(page_index, f, indent=2)

    print(f"✓ Created Document Index for {len(page_index)} substantive pages.")
    return page_index

if __name__ == "__main__":
    build_document_page_index("data/Persis_Yu_Deposition_Problem_statement.pdf")