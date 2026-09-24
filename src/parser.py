import pymupdf
import re
import json
import os
from typing import List, Dict, Any

TERMINATION_MARKERS = [
    "CERTIFICATE OF REPORTER",
    "CERTIFICATE OF NOTARY",
    "IN WITNESS WHEREOF",
    "SUBSCRIBED AND SWORN",
    "WORD INDEX"
]

def parse_deposition_pdf(pdf_path: str, output_path: str = "data/parsed_transcript.json") -> List[Dict[str, Any]]:
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    extracted_lines = []
    global_id = 0

    # Pattern to strip trailing timestamps (e.g., "01:17", "12:45:02")
    timestamp_pattern = re.compile(r"\s+\d{1,2}:\d{2}(?::\d{2})?\s*$")

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc[page_idx]
        raw_text = page.get_text("text")

        # Skip administrative/index pages at the end of the document
        if page_num > 88:
            continue
        if page_num > 70 and any(m in raw_text.upper() for m in TERMINATION_MARKERS):
            if "Q." not in raw_text and "A." not in raw_text and "MR." not in raw_text:
                continue

        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        page_buffer = []

        i = 0
        while i < len(lines):
            token = lines[i]

            # Check if this line is an isolated line number (1 to 28)
            if token.isdigit() and 1 <= int(token) <= 28:
                l_num = int(token)
                if i + 1 < len(lines):
                    next_token = lines[i + 1]
                    # If the next token is not another line number, it's the dialogue
                    if not (next_token.isdigit() and 1 <= int(next_token) <= 28):
                        clean_text = timestamp_pattern.sub("", next_token).strip()

                        # Skip header/footer artifacts
                        if not re.search(r"Veritext Legal Solutions|CONFIDENTIAL|^Page \d+$", clean_text, re.IGNORECASE):
                            if len(clean_text) > 2 and clean_text.replace("-", "").strip() != "":
                                page_buffer.append((l_num, clean_text))
                        i += 2
                        continue
            i += 1

        # Monotonically order by line number (1 to 25)
        page_buffer.sort(key=lambda x: x[0])

        for l_num, clean_text in page_buffer:
            extracted_lines.append({
                "global_id": int(global_id),
                "page": int(page_num),
                "line": int(l_num),
                "text": str(clean_text)
            })
            global_id += 1

    doc.close()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_lines, f, indent=2)

    print(f"✓ Successfully parsed {len(extracted_lines)} substantive lines across {total_pages} pages.")
    return extracted_lines