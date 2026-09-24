import fitz  
import re
import json
import os
from typing import List, Dict, Any

# Common termination markers in federal & state depositions
TERMINATION_MARKERS = [
    r"CERTIFICATE OF (?:OFFICER|NOTARY|REPORTER|SHORTHAND)",
    r"IN WITNESS WHEREOF",
    r"SUBSCRIBED AND SWORN",
    r"COURT REPORTER'?S CERTIFICATE",
    r"^INDEX$",
    r"^WORD INDEX$",
    r"^ERRATA SHEET"
]

def parse_deposition_pdf(pdf_path: str, output_path: str = "data/parsed_transcript.json") -> List[Dict[str, Any]]:
    """
    Parses ANY deposition PDF dynamically:
    - Reads every page sequentially from start to finish.
    - Strips running headers, court reporter footers, and concordance indices.
    - Captures standardized (page, line, text) tuples with global monotonic line IDs.
    """
    doc = fitz.open(pdf_path)
    total_doc_pages = len(doc)
    extracted_lines = []
    global_id = 0
    substantive_started = False

    # Regex patterns for line-numbered legal transcripts
    # Matches lines starting with 1-28 followed by dialogue or Q/A markers
    line_pattern = re.compile(r"^\s*([1-9]|[12][0-9])\s+(.*)$")
    q_or_a_pattern = re.compile(r"^\s*(?:Q\.|A\.|Q\s|A\s|THE WITNESS:|MR\.|MS\.|THE COURT:)", re.IGNORECASE)

    for page_num in range(1, total_doc_pages + 1):
        page = doc[page_num - 1]
        text_lines = page.get_text("text").splitlines()

        # Check for end of deposition / reporter certificate / word index
        page_raw_text = "\n".join(text_lines).upper()
        if substantive_started and any(re.search(marker, page_raw_text, re.MULTILINE) for marker in TERMINATION_MARKERS):
            # If word index or certificate is reached, stop extracting
            break

        page_buffer = []

        for line in text_lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = line_pattern.match(line_str)
            if match:
                l_num = int(match.group(1))
                content = match.group(2).strip()

                # Detect when substantive examination starts
                if not substantive_started:
                    if q_or_a_pattern.match(content) or "EXAMINATION" in content.upper():
                        substantive_started = True

                if substantive_started and content:
                    page_buffer.append((l_num, content))

        # Sort lines monotonically by page line number to prevent PDF column order jitter
        page_buffer.sort(key=lambda x: x[0])

        for l_num, content in page_buffer:
            extracted_lines.append({
                "global_id": global_id,
                "page": page_num,
                "line": l_num,
                "text": content
            })
            global_id += 1

    doc.close()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_lines, f, indent=2)

    print(f"✓ Parsed {len(extracted_lines)} substantive lines across {total_doc_pages} input pages.")
    return extracted_lines