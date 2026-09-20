import pymupdf as fitz
import json
import re
import os

TERMINATION_TRIGGERS = [
    "(WHEREUPON, THE DEPOSITION CONCLUDED",
    "(WHEREUPON, THE DEPOSITION WAS CONCLUDED",
    "(WHEREUPON, PROCEEDINGS CONCLUDED",
    "CERTIFICATE OF REPORTER",
    "REPORTER'S CERTIFICATE",
    "ERRATA SHEET",
    "WORD INDEX"
]

def parse_deposition_pdf(pdf_path: str, start_page: int = 7, output_path: str = "data/parsed_transcript.json"):
    doc = fitz.open(pdf_path)
    structured_lines = []
    global_id = 0

    TIME_PATTERN = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b', re.IGNORECASE)
    LINE_NO_PATTERN = re.compile(r'^\s*([1-9]|1[0-9]|2[0-5])\b')

    for page_idx in range(start_page - 1, len(doc)):
        page = doc[page_idx]
        actual_page = page_idx + 1
        raw_text = page.get_text("text")

        # Dynamic End-of-Deposition Detection
        if any(trig in raw_text.upper() for trig in TERMINATION_TRIGGERS):
            print(f"✓ Deposition conclusion marker identified on Page {actual_page}. Bypassing back-matter.")
            break

        lines = raw_text.split("\n")
        line_counter = 1

        for raw_line in lines:
            cleaned = raw_line.strip()
            if not cleaned:
                continue

            cleaned = TIME_PATTERN.sub('', cleaned).strip()

            # Filter headers and noise
            if cleaned.upper().startswith("PAGE ") and len(cleaned) < 15:
                continue
            if "MAGNA LEGAL SERVICES" in cleaned.upper():
                continue
            if "VIDEOGRAPHER" in cleaned.upper() and ("OFF THE RECORD" in cleaned.upper() or "ON THE RECORD" in cleaned.upper()):
                continue

            cleaned = LINE_NO_PATTERN.sub('', cleaned).strip()

            if len(cleaned) >= 2:
                structured_lines.append({
                    "page": actual_page,
                    "line": line_counter,
                    "text": cleaned,
                    "global_id": global_id
                })
                global_id += 1
                line_counter += 1

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured_lines, f, indent=2)

    print(f"✓ Parsed {len(structured_lines)} clean lines.")
    return structured_lines

if __name__ == "__main__":
    parse_deposition_pdf("data/Persis_Yu_Deposition_Problem_statement.pdf")