# Machine-learning notes

**Task:** classify a URL string as phishing-like or benign-like using 27 numeric features computed from
the string alone (length, dot and hyphen counts, digit ratio, IP host, entropy, keyword hits, and so on).
Feature code is shared by the API and the training script (`app/services/url_features.py`), which avoids
training/serving skew.

**Pipeline (`ml/train.py`):**
1. Load `url,label` CSV, drop exact duplicate URLs, skip unparseable ones (counted in the metrics file).
2. **Leakage control:** `GroupShuffleSplit` grouped by registered domain, so a domain is never in both
   train and test. The `StandardScaler` sits inside the scikit-learn `Pipeline`, so it only learns from
   training data.
3. Train logistic regression (deployed: its coefficients explain predictions) and a random forest
   baseline on the same split.
4. Evaluate on the held-out test set: precision, recall, F1, accuracy, ROC-AUC, confusion matrix.
   Grouped cross-validation F1 (up to 5 folds, on the training portion only) is recorded too.
5. Save `model.joblib` and `metrics.json` (includes a SHA-256 of the model and the scikit-learn version).

**Safe loading:** `joblib` files can execute code when loaded, so the app only loads from the fixed
model folder, checks the SHA-256 recorded in `metrics.json`, and checks the scikit-learn version first.
Never load a model file you did not train yourself.

**Explanations:** for logistic regression, each feature's contribution is `coefficient x standardized
value` (log-odds units). The top contributors are shown per scan.

**Limits to state in an interview:**
- The bundled demo data is synthetic, so its metrics are not evidence of real performance.
- URL-only features cannot see page content, certificates, domain age or reputation.
- Public datasets have collection bias; scores can look better than real-world results.
- The model output is not a calibrated probability.
- Attackers adapt, so retrain on fresh data over time.

**Ideas for week 6:** character n-gram TF-IDF features, calibration (`CalibratedClassifierCV`),
a time-based split, optional opt-in threat-intelligence lookups (off by default).
