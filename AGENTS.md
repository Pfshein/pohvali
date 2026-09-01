# Project working agreement

## Product guardrails

- This is a calm daily reflection tool, not a productivity tracker.
- Never add streak-loss, missed-day, ranking, pressure, or guilt language.
- Praise bodies are encrypted in the browser. Backend code must treat ciphertext as opaque bytes.
- Persist only the minimum described in `docs/product-brief.md`. Never persist Telegram names, usernames, avatars, language, request bodies, or client IPs.
- The server decides `local_date`; clients never submit a praise date.
- Keep the MVP a modular monolith and a four-service Docker Compose deployment.

## Engineering workflow

- Prefer vertical slices with observable acceptance criteria.
- Add or update tests before implementation for domain and security behavior.
- Run frontend checks with `npm run check` from `frontend/`.
- Run backend checks with `pytest` and `ruff check .` from `backend/`.
- Do not claim completion without running the relevant checks.
- Do not add Redis, Celery, queues, Kubernetes, microservices, AI, analytics SDKs, or a custom auth token to the MVP.
- In Codex Cloud/Work, publish through the connected GitHub connector. If a plain HTTPS `git push` lacks local credentials, do not search for tokens or SSH keys; create blobs/tree/commit and fast-forward the branch ref through the connector.
