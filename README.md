# PhishGuard AI

Static phishing and malicious-URL analyzer with explainable scoring, a scikit-learn model, an email
analyzer and a React dashboard.

**Safety rule:** submitted URLs are analyzed as text. The app never opens, fetches, crawls or follows them.
A low score does not guarantee safety, and the 0-100 score is a heuristic, not a probability.

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, Pydantic |
| Database | SQLite (standard-library `sqlite3`) |
| ML | scikit-learn, Pandas, NumPy |
| Tests | pytest (backend), Vitest + Testing Library (frontend) |

## Features
- **URL analyzer:** length and structure, HTTPS, IP and obfuscated-IP hosts, subdomain depth, embedded credentials, keywords, punycode / mixed scripts, unusual ports, shorteners, brand-on-unrelated-domain, risky file extensions and more. Each indicator carries points, evidence and a plain explanation.
- **Email analyzer:** urgency language, credential / payment requests, threats, extracted links (each analyzed), sender and Reply-To mismatches. The raw email text is not stored.
- **ML check:** logistic regression (explainable) with a random-forest baseline, domain-grouped split, precision / recall / F1 / ROC-AUC / confusion matrix, per-scan feature contributions, and a rule-vs-model comparison.
- **Dashboard:** totals, risk distribution, 14-day trend, top indicators, recent scans, history with filters, model page.
- **Reports:** JSON report per scan, CSV export of all history, clear-history with confirmation.

## Quick start (Windows 11)

Requirements: **Python 3.10 or newer, 64-bit** (tick "Add python.exe to PATH") and **Node.js LTS**.
Python 3.10-3.13 uses the existing pinned packages; Python 3.14 and newer uses updated pins.
Python 3.14 is tested; compatibility with later Python releases depends on the availability of compatible dependency releases.

```
setup.bat     (once: virtual environment, packages, offline demo model)
run.bat       (starts backend :8000 and frontend :5173, opens the browser)
```

Then open http://127.0.0.1:5173. On the dashboard, "Load demo data" adds clearly labelled **DEMO** scans.

### Manual alternative (PowerShell)

```powershell
# Terminal 1: backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements-dev.txt
python -m ml.train --demo             # offline demo model (synthetic data)
uvicorn app.main:app --reload --port 8000

# Terminal 2: frontend
cd frontend
npm install
npm run dev
```

Health check: http://127.0.0.1:8000/api/health  ·  API docs: http://127.0.0.1:8000/docs

## Running the tests

```powershell
cd backend
python -m pytest -q          # URL features, analyzers, email, database, reports, ML, API

cd ..\frontend
npm test                     # Vitest component and page tests
npm run typecheck
npm run build
```

## Deploying to Vercel

`vercel.json` builds the frontend and serves the API from `api/index.py`, which reuses the
`backend/app` package unchanged.

```powershell
npm i -g vercel@48          # v65 fails on Windows with an EPERM symlink error
vercel link --project phishguard-ai
vercel deploy --prod
```

Two things differ from running locally:

- **No scikit-learn.** It pulls in scipy, and together they exceed Vercel's 225 MB function
  limit. The model ships as `api/model/model.json` instead and is scored with numpy by
  `app/services/json_model.py`. Regenerate it after retraining:
  `cd backend` then `python -m ml.export_json --output-dir ../api/model`.
  Exports are verified identical to the scikit-learn pipeline.
- **Scan history needs Postgres.** The function filesystem is read-only apart from `/tmp`, so the
  SQLite database starts empty on every cold start. Add a Postgres store and the app uses it
  automatically:

  Create the store from the project's **Storage** tab in the Vercel dashboard (Neon's free
  plan is enough) and connect it to the project. That injects `DATABASE_URL`; the CLI's
  `vercel integration add neon` does the same but prompts interactively.

  ```powershell
  vercel env ls                    # confirm DATABASE_URL is present
  vercel deploy --prod             # env vars only reach a function at deploy time
  ```

  `app/database/postgres.py` runs the same queries as SQLite by rewriting `?` to `%s` and
  SQLite's implicit `rowid` to a real `seq` column, so `repository.py` keeps one set of
  queries. With no `DATABASE_URL` the app silently falls back to SQLite in `/tmp`.

Vercel's Python runtime is 3.14, so `requirements.txt` at the repository root uses the
`python_version >= "3.14"` pins. It is separate from `backend/requirements.txt`, which still
drives local development. The app has no authentication, so keep Vercel's Deployment
Protection enabled on the project.

## Using a real dataset
The bundled `data/sample_urls.csv` is **synthetic**; metrics from it are labelled "demo" in the UI and
prove only that the pipeline works. See `backend/data/README.md` for training on the UCI PhiUSIIL dataset.

## Project layout

```
PhishGuard-AI/
  backend/
    app/ api/ core/ database/ models/ schemas/ services/ main.py
    ml/ (prepare_dataset.py, train.py, generate_sample_data.py, artifacts/)
    data/ (sample_urls.csv, README.md)    tests/    requirements*.txt
  frontend/ src/ (components, pages, hooks, services, types, utils, test)
  docs/ ARCHITECTURE.md  ML_NOTES.md  SECURITY.md  INTERVIEW_GUIDE.md
  setup.bat  run.bat  .env.example  .gitignore
```

Read `docs/ARCHITECTURE.md` first, then `docs/INTERVIEW_GUIDE.md`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Install Python 3.10 or newer from python.org and tick "Add python.exe to PATH", then open a new terminal. |
| `pip install` fails building numpy / scikit-learn | Install 64-bit Python 3.10 or newer and re-run setup. If a new Python release is not yet supported by a dependency, use the latest supported Python release. |
| Setup reports that `backend\.venv` uses a different Python version | Rename or remove the existing generated environment, then re-run `setup.bat`. Setup leaves a mismatched environment untouched. |
| `node` / `npm` not found | Install Node.js LTS from nodejs.org, reopen the terminal. |
| Activate.ps1 blocked | `Set-ExecutionPolicy -Scope Process Bypass`, then activate again. |
| Port 8000 or 5173 in use | Find it: `netstat -ano \| findstr :8000`, then `taskkill /PID <pid> /F` (only for a process you recognize). Or run uvicorn on another port and set `VITE_API_BASE_URL` / `CORS_ORIGINS`. Vite uses `strictPort`, so it fails instead of silently switching to a port CORS does not allow. |
| Header shows "Backend offline" | Start the backend window, check http://127.0.0.1:8000/api/health. |
| Setup warns or the ML page says the model needs retraining | `cd backend` then `python -m ml.train --demo`. Retrain after upgrading scikit-learn. |

## Screenshots (for your GitHub README)
Capture, at 1440 px wide: the dashboard with demo data, a high-risk URL result, the email result, the
ML model page, and the dashboard at phone width. Save them in `docs/screenshots/` and link them here.

## Limitations
Static analysis cannot see page content, redirects, certificates, domain age or reputation. The bundled
model is trained on synthetic demo data unless you train on a real dataset. There is no authentication,
so run it locally only. See `docs/SECURITY.md`.

## License

MIT - see [LICENSE](LICENSE).
