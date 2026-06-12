"""
Parses MCA Director Master Data CSV and loads into DB.

MCA CSV columns (typical):
DIN, NAME_OF_DIRECTOR, DATE_OF_BIRTH, FATHER_NAME, PRESENT_ADDRESS,
PERMANENT_ADDRESS, NATIONALITY, MOBILE_NO, EMAIL_ID, COMPANY_NAME, DESIGNATION

Run: python -m scrapers.mca_parser --file ./data/mca/director_master_data.csv
"""
import argparse
import os
import sys
import pandas as pd
from datetime import date, datetime
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import Lead, SourceType, GenderType

# Column name variants seen in different MCA exports
COL_MAP = {
    "din": ["DIN", "din_no", "DIN_NO"],
    "name": ["NAME_OF_DIRECTOR", "DIRECTOR_NAME", "name"],
    "dob": ["DATE_OF_BIRTH", "DOB", "dob"],
    "address": ["PRESENT_ADDRESS", "ADDRESS", "present_address"],
    "mobile": ["MOBILE_NO", "MOBILE", "mobile_no"],
    "email": ["EMAIL_ID", "EMAIL", "email"],
    "company": ["COMPANY_NAME", "company_name"],
    "designation": ["DESIGNATION", "designation"],
}


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _calc_age(dob_str: str) -> tuple[int | None, date | None]:
    if not dob_str or pd.isna(dob_str):
        return None, None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            d = datetime.strptime(str(dob_str).strip(), fmt).date()
            age = (date.today() - d).days // 365
            return age, d
        except ValueError:
            continue
    return None, None


def _extract_state_district(address: str) -> tuple[str, str, str, str]:
    """
    Best-effort address parsing.
    Returns (area, city, district, state).
    """
    if not address or pd.isna(address):
        return "", "", "", ""
    parts = [p.strip() for p in str(address).split(",")]
    state = parts[-1].strip().title() if len(parts) >= 1 else ""
    district = parts[-2].strip().title() if len(parts) >= 2 else ""
    city = parts[-3].strip().title() if len(parts) >= 3 else ""
    area = ", ".join(parts[:-3]).strip().title() if len(parts) > 3 else ""
    return area, city, district, state


def parse_and_load(csv_path: str, batch_size: int = 1000) -> int:
    print(f"Reading {csv_path} ...")
    df = pd.read_csv(csv_path, dtype=str, low_memory=False, encoding="utf-8", errors="replace")
    df.columns = [c.strip() for c in df.columns]
    print(f"  Rows: {len(df):,}  Columns: {list(df.columns)}")

    col = {k: _find_col(df, v) for k, v in COL_MAP.items()}

    db = SessionLocal()
    loaded = 0
    batch = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Loading MCA directors"):
        def g(key):
            c = col.get(key)
            return str(row[c]).strip() if c and pd.notna(row.get(c)) else None

        age, dob = _calc_age(g("dob"))
        area, city, district, state = _extract_state_district(g("address"))
        name = g("name")
        if not name:
            continue

        lead = Lead(
            full_name=name.title(),
            age=age,
            date_of_birth=dob,
            phone_primary=g("mobile"),
            email=g("email"),
            address_line=g("address"),
            area=area or None,
            city=city or None,
            district=district or None,
            state=state or None,
            din=g("din"),
            source_id=g("din"),
            company_name=g("company"),
            designation=g("designation"),
            source=SourceType.MCA_DIRECTOR,
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
    print(f"Done. Loaded {loaded:,} directors.")
    return loaded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to MCA director master CSV")
    args = parser.parse_args()
    parse_and_load(args.file)
