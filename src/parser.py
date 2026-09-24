import pymupdf
import json
import os
from typing import List, Dict, Any

def parse_deposition_pdf(pdf_path: str, output_path: str = "data/parsed_transcript.json") -> List[Dict[str, Any]]:
    """
    Parses arbitrary deposition transcripts using 2D geometric spatial clustering.
    Zero regular expressions: extracts margin line numbers and text based on X/Y coordinates.
    """
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    extracted_lines = []
    global_id = 0

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc[page_idx]

        # Extract words: (x0, y0, x1, y1, word_text, block_no, line_no, word_no)
        words = page.get_text("words")
        if not words:
            continue

        # Cluster words into horizontal lines by Y coordinate (grouping words within 3.5 points)
        line_buckets = {}
        for w in words:
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            
            # Find an existing line bucket within vertical threshold
            matched_y = None
            for base_y in line_buckets:
                if abs(y0 - base_y) <= 3.5:
                    matched_y = base_y
                    break
            
            if matched_y is None:
                matched_y = y0
                line_buckets[matched_y] = []
            
            line_buckets[matched_y].append((x0, text))

        # Sort visual lines vertically from top to bottom
        sorted_y_coords = sorted(line_buckets.keys())

        page_buffer = []
        for y in sorted_y_coords:
            # Sort words horizontally from left to right
            row_items = sorted(line_buckets[y], key=lambda item: item[0])
            if not row_items:
                continue

            first_token = row_items[0][1].strip()

            # If first word is purely numeric (the transcript line index 1-28)
            if first_token.isdigit() and 1 <= int(first_token) <= 30:
                line_number = int(first_token)
                # Remaining tokens form the actual dialogue
                dialogue_tokens = [w[1] for w in row_items[1:]]
                
                # Filter trailing timestamps without regex (timestamps are usually pure time digits with colons)
                if dialogue_tokens and ":" in dialogue_tokens[-1] and any(char.isdigit() for char in dialogue_tokens[-1]):
                    dialogue_tokens.pop()

                line_text = " ".join(dialogue_tokens).strip()

                if line_text:
                    page_buffer.append((line_number, line_text))

        # Sort lines strictly 1 to 25
        page_buffer.sort(key=lambda x: x[0])

        for line_num, text_content in page_buffer:
            extracted_lines.append({
                "global_id": int(global_id),
                "page": int(page_num),
                "line": int(line_num),
                "text": str(text_content)
            })
            global_id += 1

    doc.close()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_lines, f, indent=2)

    print(f"✓ Geometrically parsed {len(extracted_lines)} substantive lines across {total_pages} pages.")
    return extracted_lines