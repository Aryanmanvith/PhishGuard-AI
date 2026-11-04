# Data for PhishGuard AI

## What ships with the project

`sample_urls.csv` is a **synthetic demo dataset** made by `python -m ml.generate_sample_data`
(columns: `url,label`, label 1 = phishing, 0 = benign). The URLs are invented from word lists. It is
**not** real phishing data. It exists so the project runs offline. Metrics computed from it say nothing
about real-world accuracy, and the dashboard labels any model trained on it as "demo sample data".

## Training on a real dataset (recommended before showing results to anyone)

Recommended source: **PhiUSIIL Phishing URL Dataset**, UCI Machine Learning Repository, licensed CC BY 4.0
<https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset>

1. Download the CSV in your browser (do not open any of the URLs inside it) and save it as
   `backend/data/raw/PhiUSIIL_Phishing_URL_Dataset.csv`.
2. From the `backend` folder, with the virtual environment active:

```powershell
python -m ml.prepare_dataset --input data/raw/PhiUSIIL_Phishing_URL_Dataset.csv --preset phiusiil
python -m ml.train --data data/processed/urls_clean.csv `
  --dataset-name "PhiUSIIL Phishing URL Dataset (UCI)" `
  --source "https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset"
```

The PhiUSIIL file uses label 1 = legitimate, 0 = phishing (the opposite of PhishGuard). The `phiusiil`
preset flips it. Always compare the printed class counts with the dataset's documentation.

Never open or visit URLs from a phishing dataset. PhishGuard only reads them as text.
