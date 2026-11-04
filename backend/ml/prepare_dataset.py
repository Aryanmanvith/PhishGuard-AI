"""Clean a real phishing/benign URL dataset into the format train.py expects.

Output CSV columns:  url,label     (label: 1 = phishing, 0 = benign)

Recommended real dataset (documented in backend/data/README.md):
  PhiUSIIL Phishing URL Dataset - UCI Machine Learning Repository, CC BY 4.0
  https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset
  Its columns are `URL` and `label` where label 1 = LEGITIMATE and 0 = PHISHING
  (opposite of ours!), so the `phiusiil` preset flips it for you.

Examples (run from the backend folder):
  python -m ml.prepare_dataset --input data/raw/PhiUSIIL_Phishing_URL_Dataset.csv --preset phiusiil
  python -m ml.prepare_dataset --input my.csv --url-col link --label-col is_phish --phishing-value 1

What this script does (and prints so you can sanity-check it):
  * keeps only the URL and label columns, maps labels to 1/0
  * removes empty / over-long / unparseable URLs and exact duplicates
  * reports class counts - ALWAYS check these match the dataset's documentation
Splitting into train/test happens in train.py (grouped by domain, to avoid leakage).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from app.services.url_features import MAX_URL_LENGTH, InvalidURLError, parse_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
PRESETS = {
    # name: (url column, label column, value that means PHISHING)
    "phiusiil": ("URL", "label", 0),
    "generic": ("url", "label", 1),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, required=True, help="Raw CSV file")
    ap.add_argument("--output", type=Path, default=BACKEND_DIR / "data" / "processed" / "urls_clean.csv")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="generic")
    ap.add_argument("--url-col", help="Override the URL column name")
    ap.add_argument("--label-col", help="Override the label column name")
    ap.add_argument("--phishing-value", help="Value in the label column that means phishing")
    ap.add_argument("--add-scheme", action="store_true",
                    help="Prepend http:// to URLs that have no scheme (note: this adds a bias, see docs)")
    args = ap.parse_args()

    url_col, label_col, phish_value = PRESETS[args.preset]
    url_col = args.url_col or url_col
    label_col = args.label_col or label_col
    if args.phishing_value is not None:
        phish_value = args.phishing_value

    if not args.input.is_file():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 1

    df = pd.read_csv(args.input, usecols=[url_col, label_col], dtype=str)
    start_rows = len(df)
    df = df.rename(columns={url_col: "url", label_col: "label_raw"}).dropna()
    df["url"] = df["url"].str.strip()
    df["label"] = (df["label_raw"].str.strip() == str(phish_value)).astype(int)

    if args.add_scheme:
        df.loc[~df["url"].str.contains("://", regex=False), "url"] = "http://" + df["url"]

    df = df[(df["url"].str.len() > 0) & (df["url"].str.len() <= MAX_URL_LENGTH)]
    before = len(df)
    df = df.drop_duplicates(subset="url")
    duplicates = before - len(df)

    def parseable(u: str) -> bool:
        try:
            parse_url(u)
            return True
        except InvalidURLError:
            return False

    ok = df["url"].map(parseable)
    unparseable = int((~ok).sum())
    df = df[ok][["url", "label"]]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    phishing = int(df["label"].sum())
    print(f"Input rows:            {start_rows}")
    print(f"Exact duplicates:      {duplicates}")
    print(f"Unparseable/rejected:  {unparseable}")
    print(f"Written:               {len(df)} rows -> {args.output}")
    print(f"  phishing (1):        {phishing}")
    print(f"  benign   (0):        {len(df) - phishing}")
    print("Check these counts against the dataset's documentation before training.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
