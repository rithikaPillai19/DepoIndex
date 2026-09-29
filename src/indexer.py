"""
Coarse Page Index Builder.
Inspects dialogue blocks without regex to prepare the coarse routing catalog.
"""
import pymupdf
import json
import os
from typing import List, Dict, Any

def build_document_page_index(pdf_path: str, output_path: str = "data/page_index.json") -> List[Dict[str, Any]]:
    doc = pymupdf.open(pdf_path)
    page_catalog = []

    for page_num in range(1, len(doc) + 1):
        # Exclude administrative indices and errata
        if page_num < 7 or page_num > 88:
            continue

        page = doc[page_num - 1]
        text = page.get_text("text").strip()
        if not text or len(text.split()) < 10:
            continue

        text_upper = text.upper()
        if any(marker in text_upper for marker in ["WORD INDEX", "CONCORDANCE", "CERTIFICATE OF NOTARY"]):
            continue

        split_lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().isdigit()]
        clean_preview = " | ".join(split_lines[:5])

        page_catalog.append({
            "page": int(page_num),
            "preview": clean_preview[:200]
        })

    doc.close()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(page_catalog, f, indent=2)

    print(f"✓ Generated Coarse Page Index across {len(page_catalog)} substantive pages.")
    return page_catalog