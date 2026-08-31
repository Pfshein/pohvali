# Security Hardening Implementation Plan (PH-701 / PH-702 / PH-703)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

Covers three security backlog items delivered together.

---

## PH-703 · Privacy-safe logging (DONE)

**Approach:** Caddy access logging stays disabled (`infra/Caddyfile` has no `log` directive and a
comment recording the intent — no client IPs retained). The backend adds `AccessLogMiddleware`
(`app/core/logging.py`) that emits one JSON line per request with `request_id`, `method`, `path`,
`status`, `duration_ms` and echoes/creates `X-Request-ID`. It never logs the Authorization header,
bodies, ciphertext, query strings, or the Telegram id. The Telegram webhook logs only `update_id`.

**Tests:** `test_access_logging.py` — structured fields present, credential sentinel absent from
every record, request id generated when missing.

---

## PH-702 · Rate limiting & CORS (DONE)

**Approach:** `FixedWindowRateLimiter` (`app/api/rate_limit.py`, in-memory — single instance, no
Redis) keyed by Telegram id. `POST /session` (30/min) and `POST /praises` (60/min) depend on
`SessionRateLimited` / `PraiseRateLimited`, returning `429` when exceeded. CORS already restricts to
`CORS_ORIGINS`; a `Settings` validator now refuses to start in production unless every origin is
`https://` and non-localhost (Mini App origin only). Proxy headers: the backend publishes no ports
(only Caddy is exposed), so forwarded headers can only arrive via Caddy; the backend consumes no
client IP, so header spoofing has no effect.

**Tests:** `test_rate_limit.py` — limiter allow/deny, window reset, per-key isolation, endpoint
`429`, and the production CORS guard.

---

## PH-701 · Authorization matrix (DONE; `unlock` deferred)

**Approach:** Every user route rejects missing/invalid auth with a generic `401` that never hints at
resource existence. Ownership is enforced in the query layer; edit/delete/read/calendar filter by the
caller's `user_id`, and edit/delete raise a uniform `PraiseNotFound → 404` for both non-existent and
not-owned ids (no UUID enumeration signal).

**Tests:**
- `test_authorization_matrix.py` — no-auth `401` for POST session, POST/GET/PATCH/DELETE praises, GET calendar.
- Cross-user negatives + enumeration parity: `test_praise_edit_delete_db.py` (stranger edit/delete → 404, random id → 404), `test_praise_read_db.py` (day read owner-only), `test_calendar_db.py` (calendar owner-only).

**Deferred:** the `unlock` row of the matrix depends on threshold unlocks (**PH-402**, M4) which are
not built yet; add its cross-user negative test when PH-402 lands.
