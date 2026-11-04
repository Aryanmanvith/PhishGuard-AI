# Interview guide: explaining PhishGuard AI

## 30-second pitch
"PhishGuard AI is a full-stack web app that analyzes suspicious URLs and emails without ever opening
them. A FastAPI backend extracts features from the URL string, applies explainable rules, and compares
the result with a scikit-learn model. A React dashboard shows the evidence, stores history in SQLite
and exports reports."

## Component cheat sheet
- **url_features.py**: parses a URL into signals and a 27-number feature vector. Pure functions, easy to test.
- **url_analyzer.py**: turns signals into indicators with points and plain-language explanations; adds ML comparison.
- **email_analyzer.py**: regex rule groups, link extraction, sender/Reply-To checks.
- **ml/train.py**: domain-grouped split, pipeline with scaler, metrics, saved model plus hash.
- **ml_service.py**: safe loading and per-prediction feature contributions.
- **repository.py**: all SQL in one place.
- **api/**: thin routes; **schemas/**: the JSON contract.
- **Frontend**: pages call `services/api.ts`; `useAsync` handles loading/error; Recharts draws charts.

## Questions to practice
1. *Why not just visit the URL?* Risk of exploitation, tracking, and legal/ethical issues; static analysis is safe and fast. Trade-off: it cannot see page content.
2. *How did you avoid data leakage?* Domain-grouped split, scaler fitted inside the pipeline on train only, deduplication.
3. *Why logistic regression?* Explainable coefficients; the random forest is only a baseline.
4. *Is the score a probability?* No. It is a transparent heuristic; the model output is uncalibrated.
5. *What are the weaknesses?* Synthetic demo data, URL-only features, no reputation data, adversarial adaptation.
6. *How would you improve it?* Real, fresh data; n-grams; calibration; time-based evaluation; opt-in threat intel.
7. *How is it secured?* See SECURITY.md.

## Be ready to demo
Scan a clean URL, an IP-based URL, and the fake sample email; open the ML Model page and point out the
"demo data" banner; export a JSON report; show the tests passing.
