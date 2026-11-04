# Architecture

```
Browser (React + TypeScript, Vite, Recharts)
   |  fetch /api/*   (Vite dev server proxies to port 8000, so no CORS in development)
   v
FastAPI app  (backend/app/main.py)
   |-- middleware: body-size limit, per-IP rate limit, security headers, CORS allow-list
   |-- api/        thin HTTP routes: analyze, scans, reports, model, health
   |-- services/   scan_service (orchestrates) -> url_analyzer / email_analyzer
   |                                           -> url_features (pure string parsing)
   |                                           -> ml_service (loads saved scikit-learn pipeline)
   |-- database/   SQLite via the standard library sqlite3 (db.py, repository.py)
   '-- schemas/    Pydantic models = the JSON contract (mirrored in frontend/src/types/api.ts)

backend/ml/   prepare_dataset.py -> train.py -> artifacts/model.joblib + metrics.json
```

## Request flow for "analyze URL"

1. `POST /api/analyze/url` validates `{url}` (Pydantic: 1-2048 chars, no extra fields).
2. `url_features.parse_url` splits the string with `urllib.parse` only. Nothing is resolved or fetched.
3. `url_analyzer` turns the parsed pieces into **indicators** (id, severity, points, evidence, explanation).
   The heuristic score is the capped sum of points. Thresholds live in `models/risk.py`
   (below 20 low, 20 to 49 suspicious, 50+ high).
4. `ml_service` scores the same 27 numeric features with the saved model, if one exists, and
   `comparison` says whether the rule engine and the model agree.
5. The result is stored in SQLite and returned. Credentials in the URL are redacted before storage.

Email analysis follows the same pattern: regex rule groups for urgency, credential requests, payments,
threats and so on, plus every extracted link run through the URL analyzer, plus sender / Reply-To
domain checks. The raw email body is never stored, only a short summary.

## Design choices worth defending

- **Static only.** There is no code path that makes an outbound request to a submitted URL. Tests and
  review can confirm this by searching for `requests`, `urllib.request`, `httpx` and `socket` in `app/`.
- **Explainable first.** Every point in the score maps to a named indicator with evidence.
- **Honest scores.** The 0-100 value is a heuristic, never called a probability. ML output is also
  labelled uncalibrated.
- **Graceful degradation.** No model, wrong scikit-learn version or failed hash check means the app
  still works and says why the ML section is unavailable.
- **Plain SQL, no ORM.** Two small files, parameterized queries only, easy to explain.
- **Contract in one place.** `schemas/scan.py` and `types/api.ts` mirror each other.

## API summary

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | status, model availability, database check |
| POST | /api/analyze/url | analyze and store a URL scan |
| POST | /api/analyze/email | analyze and store an email scan |
| GET | /api/scans | paged history (`limit`, `offset`, `category`, `input_type`) |
| GET | /api/scans/{id} | one stored scan |
| DELETE | /api/scans?confirm=true | clear history (`demo_only=true` clears only demo rows) |
| GET | /api/stats | dashboard numbers |
| GET | /api/model | training metadata and test-set metrics |
| POST | /api/demo/seed | add clearly labelled demo scans |
| GET | /api/scans/{id}/report.json | download one scan report |
| GET | /api/reports/history.csv | download full history |

Interactive docs are served at http://127.0.0.1:8000/docs while the backend runs.
