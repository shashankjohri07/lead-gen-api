"""
Downloads MCA director master data bulk files from mca.gov.in.

Run: python -m scrapers.mca_downloader --out ./data/mca/
"""
import argparse
import os
import zipfile
import requests
from tqdm import tqdm

# MCA data sets page (public, no auth needed)
MCA_DIRECTOR_URL = (
    "https://www.mca.gov.in/bin/dms/getdocument?mds=O0Nh6OF6tGkc7"
    "ug3N8YQqA%3D%3D&type=open"
)

# Fallback — direct search on MCA data portal
MCA_DATA_PAGE = "https://www.mca.gov.in/content/mca/global/en/data-and-reports/data-sets/company-master-data.html"


def download_file(url: str, dest_path: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    with open(dest_path, "wb") as f, tqdm(total=total, unit="B", unit_scale=True) as bar:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))
    print(f"Downloaded → {dest_path}")


def extract_zip(zip_path: str, out_dir: str):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(out_dir)
    print(f"Extracted → {out_dir}")
    return [os.path.join(out_dir, n) for n in os.listdir(out_dir) if n.endswith(".csv")]


def run(out_dir: str = "./data/mca"):
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, "director_master.zip")

    print("Downloading MCA Director Master Data...")
    print(f"If auto-download fails, manually download from:\n  {MCA_DATA_PAGE}")
    print("Look for 'Director Master Data' → download ZIP → place in ./data/mca/\n")

    try:
        download_file(MCA_DIRECTOR_URL, zip_path)
        csvs = extract_zip(zip_path, out_dir)
        print(f"CSV files ready: {csvs}")
        return csvs
    except Exception as e:
        print(f"Auto-download failed: {e}")
        print(f"\nManual steps:")
        print(f"  1. Go to {MCA_DATA_PAGE}")
        print(f"  2. Download 'Director Master Data' ZIP")
        print(f"  3. Extract CSV to ./data/mca/")
        print(f"  4. Run: python -m scrapers.mca_parser --file ./data/mca/director_master_data.csv")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="./data/mca")
    args = parser.parse_args()
    run(args.out)
