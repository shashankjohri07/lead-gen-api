"""
Parses voter roll files (PDF / CSV / XLSX) from state CEO portals.
Loads into DB with state + district tags.

Voter roll PDFs typically contain:
  - Serial No, Voter ID (EPIC), Name, Father/Husband Name, Age, Gender, Address

Run:
  python -m scrapers.voter_parser --file voters_pune.pdf --state Maharashtra --district Pune
  python -m scrapers.voter_parser --file voters.csv --state Gujarat --district Ahmedabad

State CEO portals:
  Maharashtra  → https://ceomaharashtra.nic.in/
  Gujarat      → https://ceo.gujarat.gov.in/
  Karnataka    → https://ceo.karnataka.gov.in/
  Tamil Nadu   → https://www.elections.tn.gov.in/
  Rajasthan    → https://ceorajasthan.nic.in/
  UP           → https://ceouttarpradesh.nic.in/
  Delhi        → https://ceodelhi.gov.in/
  All states   → https://electoralsearch.eci.gov.in/
"""
import argparse
import os
import re
import sys
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import Lead, SourceType, GenderType


# ── PDF parser ────────────────────────────────────────────────────────────────

def _parse_pdf(path: str) -> pd.DataFrame:
    import pdfplumber

    records = []
    print("Extracting text from PDF (this may take a few minutes for large files)...")

    with pdfplumber.open(path) as pdf:
        for page in tqdm(pdf.pages, desc="PDF pages"):
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                # Try to use first row as header
                headers = [str(h).strip().lower() if h else "" for h in table[0]]
                for row in table[1:]:
                    if len(row) < 4:
                        continue
                    record = dict(zip(headers, [str(c).strip() if c else "" for c in row]))
                    records.append(record)

            # Fallback: parse raw text for voter entry blocks
            if not tables:
                text = page.extract_text() or ""
                _parse_text_block(text, records)

    return pd.DataFrame(records)


def _parse_text_block(text: str, records: list):
    """
    Voter PDF text often looks like:
    1  ABC1234567  Ram Kumar  Age: 35  M  H.No 12, Main Road, Pune
    """
    lines = text.split("\n")
    current = {}
    for line in lines:
        line = line.strip()
        # Voter ID pattern
        vid = re.search(r"\b([A-Z]{3}\d{7})\b", line)
        if vid:
            if current.get("voter_id"):
                records.append(current)
            current = {"voter_id": vid.group(1)}
            # Try to extract age from same line
            age_m = re.search(r"(?:age|Age)[:\s]+(\d{1,3})", line)
            if age_m:
                current["age"] = age_m.group(1)
            # Gender
            if " M " in line or " Male" in line:
                current["gender"] = "M"
            elif " F " in line or " Female" in line:
                current["gender"] = "F"
        elif current.get("voter_id"):
            if not current.get("name"):
                current["name"] = line
            elif not current.get("address"):
                current["address"] = line
            else:
                current["address"] = current["address"] + " " + line

    if current.get("voter_id"):
        records.append(current)


# ── Column normaliser ─────────────────────────────────────────────────────────

_COL_VARIANTS = {
    "voter_id": ["voter id", "epic", "voter_id", "epic no", "card no", "id"],
    "name": ["name", "elector name", "voter name", "full name", "नाम"],
    "age": ["age", "आयु", "वय"],
    "gender": ["gender", "sex", "लिंग"],
    "address": ["address", "पता", "house no", "residential address"],
    "father_name": ["father name", "husband name", "relation name"],
    "booth": ["booth", "part no", "polling station"],
}


def _match_col(df_cols: list[str], candidates: list[str]) -> str | None:
    dc = [c.lower().strip() for c in df_cols]
    for cand in candidates:
        for i, c in enumerate(dc):
            if cand in c:
                return df_cols[i]
    return None


# ── Main loader ───────────────────────────────────────────────────────────────

def parse_and_load(
    file_path: str,
    state: str,
    district: str,
    constituency: str = "",
    batch_size: int = 500,
) -> int:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        df = _parse_pdf(file_path)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, dtype=str)
    elif ext == ".csv":
        df = pd.read_csv(file_path, dtype=str, encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    df.columns = [str(c).strip() for c in df.columns]
    print(f"Rows: {len(df):,}  Columns: {list(df.columns)}")

    col = {k: _match_col(list(df.columns), v) for k, v in _COL_VARIANTS.items()}
    print(f"Matched columns: { {k: v for k, v in col.items() if v} }")

    def g(row, key):
        c = col.get(key)
        val = row.get(c) if c else None
        return str(val).strip() if val and pd.notna(val) and str(val).strip() not in ("nan", "") else None

    db = SessionLocal()
    loaded = 0
    batch = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Loading {district} voter roll"):
        name = g(row, "name")
        if not name or name.lower() in ("name", "elector name"):
            continue

        raw_age = g(row, "age")
        age = int(raw_age) if raw_age and raw_age.isdigit() else None

        raw_gender = (g(row, "gender") or "").upper()
        if raw_gender in ("M", "MALE", "पुरुष"):
            gender = GenderType.MALE
        elif raw_gender in ("F", "FEMALE", "महिला"):
            gender = GenderType.FEMALE
        else:
            gender = GenderType.UNKNOWN

        lead = Lead(
            full_name=name.title(),
            age=age,
            gender=gender,
            address_line=g(row, "address"),
            district=district.title(),
            state=state.title(),
            voter_id=g(row, "voter_id"),
            source_id=g(row, "voter_id"),
            constituency=constituency or None,
            booth_no=g(row, "booth"),
            source=SourceType.VOTER_ROLL,
        )
        batch.append(lead)

        if len(batch) >= batch_size:
            db.bulk_save_objects(batch)
            db.commit()
            loaded += len(batch)
            batch = []

    if batch:
        db.bulk_save_objects(batch)
        db.commit()
        loaded += len(batch)

    db.close()
    print(f"Done. Loaded {loaded:,} voters from {state} / {district}.")
    return loaded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--district", required=True)
    parser.add_argument("--constituency", default="")
    args = parser.parse_args()
    parse_and_load(args.file, args.state, args.district, args.constituency)
