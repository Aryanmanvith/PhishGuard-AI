# Security model

| Risk | Mitigation |
|---|---|
| Visiting a malicious link | No code path opens, fetches, crawls or follows submitted URLs. URLs are parsed as strings. The UI shows URLs as plain text, never as clickable links. |
| Command injection | No shell calls with user input. SQL uses parameterized queries only. |
| Leaking secrets | No API keys exist by default. `.env` is git-ignored. Nothing secret is bundled into the frontend. |
| Private email content | Analysis runs locally. The raw body is not stored or sent anywhere. Only a short summary is saved. |
| Credentials inside URLs | Passwords are redacted before display and storage. |
| Abuse of the API | Request size limit, per-IP rate limit, strict Pydantic validation, `extra="forbid"`. |
| Browser attacks | CORS allow-list (no `*`), `nosniff`, `X-Frame-Options: DENY`, restrictive CSP on API replies, `no-store`. |
| Information disclosure | One JSON error format. Unhandled errors return a generic message and log details server-side. |
| Malicious model file | Hash check, version check and fixed load directory. |
| External threat intelligence | Not implemented by default. Any future integration must be opt-in and documented. |

## What this tool cannot promise
A low score is not proof of safety. HTTPS is not a safety signal (many phishing sites use it, and
the app only treats missing HTTPS as a weak indicator). Static analysis cannot see page content, redirects,
domain age or reputation.

This is a local learning and portfolio tool. It has no authentication, so do not expose it to the internet as is.
