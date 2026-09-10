import re
from pypdf import PdfReader
import pandas as pd

def parse_deposition_pdf(pdf_path: str) -> pd.DataFrame:
    """
    Parses the Persis Yu deposition PDF.
    Extracts substantive lines from Page 7 to Page 88, tagging each with:
    - global_id (unique integer)
    - page (int)
    - line (int: 1 to 25)
    - text (clean line dialogue)
    """
    reader = PdfReader(pdf_path)
    records = []
    global_id = 0
    line_pattern = re.compile(r"^\s*(\d{1,2})\s+(.*?)(?:\s+\d{2}:\d{2})?$")

    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        raw_lines = text.splitlines()
        page_num = None
        for l in raw_lines:
            m_page = re.search(r"Page\s+(\d+)", l, re.IGNORECASE)
            if m_page:
                page_num = int(m_page.group(1))
                break
        if page_num is None:
            page_num = page_idx + 1
        if page_num < 7 or page_num > 88:
            continue

        for line_str in raw_lines:
            line_str = line_str.strip()
            match = line_pattern.match(line_str)
            if match:
                line_no = int(match.group(1))
                content = match.group(2).strip()
                if content and line_no <= 25:
                    records.append({
                        "global_id": global_id,
                        "page": page_num,
                        "line": line_no,
                        "text": content
                    })
                    global_id += 1

    df = pd.DataFrame(records)
    return df

if __name__ == "__main__":
    df = parse_deposition_pdf("data/Persis_Yu_Deposition_Problem_statement.pdf")
    print(f"Total lines extracted: {len(df)}")
    print(df.head(10))
    df.to_json("data/parsed_transcript.json", orient="records", indent=2)