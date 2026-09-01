# Local Encrypted Backup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать PH-704A: ежедневный зашифрованный PostgreSQL dump на production VPS и безопасный restore drill для закрытой альфы.

**Architecture:** Host-side Bash-скрипт стримит `pg_dump --format=custom` из существующего Compose-контейнера напрямую в `age`, атомарно публикует архив и оставляет семь последних успешных копий. `systemd timer` запускает one-shot job; отдельный restore script разворачивает архив в одноразовый PostgreSQL 17 без доступа к production volume.

**Tech Stack:** Bash 5, Docker Compose, PostgreSQL 17 (`pg_dump`/`pg_restore`), age, systemd, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-local-encrypted-backup-design.md`

## Global Constraints

- Praise bodies remain opaque ciphertext; backup tooling never inspects application rows.
- Persist no new Telegram PII, request bodies, client IPs, or secrets.
- Keep four long-running Compose services; backup is a host-side one-shot job.
- Never write an unencrypted database dump to disk.
- PH-704 remains open until PH-704B uploads archives to private external storage and passes an off-host restore drill.

---

## File Structure

- `backend/tests/test_backup_scripts.py` — executable behavior tests using isolated fake CLI boundaries.
- `ops/backup/backup.sh` — production backup transaction and retention.
- `ops/backup/restore-drill.sh` — disposable restore and schema verification.
- `ops/backup/backup.env.example` — non-secret defaults for systemd.
- `ops/backup/pohvala-backup.service` — hardened one-shot unit, запускающий
  root-owned копию script из `/usr/local/libexec/pohvala-backup`.
- `ops/backup/pohvala-backup.timer` — daily persistent schedule.
- `docs/backup.md` — operator runbook.
- `docs/backlog.md` and `docs/deploy.md` — release status and runbook link.

### Task 1: Backup transaction

**Files:**
- Create: `backend/tests/test_backup_scripts.py`
- Create: `ops/backup/backup.sh`

**Interfaces:**
- Consumes: Compose project directory, public age recipients file, backup directory.
- Produces: `pohvala-postgres-<UTC timestamp>.dump.age`, exit code 0 only after atomic publication.

- [ ] Write `test_backup_streams_dump_into_encrypted_archive_without_plaintext` with fake `docker` emitting a literal dump and fake `age` writing a literal encrypted result.
- [ ] Run `pytest tests/test_backup_scripts.py -v` from `backend/`; expect failure because `ops/backup/backup.sh` is absent.
- [ ] Implement validation, `flock`, `docker compose exec -T postgres pg_dump | age`, partial cleanup, non-empty check, chmod and atomic rename in `backup.sh`.
- [ ] Run the targeted test; expect PASS.
- [ ] Add and verify RED tests for failed `pg_dump`, failed `age`, retention of exactly seven matching archives, preservation of unrelated files and invalid retention.
- [ ] Implement the minimum retention/error branches and rerun the targeted file; expect PASS.

### Task 2: Disposable restore drill

**Files:**
- Modify: `backend/tests/test_backup_scripts.py`
- Create: `ops/backup/restore-drill.sh`

**Interfaces:**
- Consumes: encrypted archive path and offline age identity path.
- Produces: exit 0 only after `pg_restore --exit-on-error` into an isolated container and verification of `alembic_version`, `users`, and `praises`.

- [ ] Write failing success-path test asserting observable exit/output and disposable-container cleanup.
- [ ] Run the targeted test; expect failure because `restore-drill.sh` is absent.
- [ ] Implement argument validation, dependency checks, temporary container startup/readiness loop, decrypt-to-restore pipe, schema query and trap cleanup.
- [ ] Run the success test; expect PASS.
- [ ] Write failing test for `pg_restore` failure and verify the container is still removed.
- [ ] Implement the minimum failure propagation and rerun all script tests; expect PASS.

### Task 3: systemd operation files

**Files:**
- Create: `ops/backup/backup.env.example`
- Create: `ops/backup/pohvala-backup.service`
- Create: `ops/backup/pohvala-backup.timer`

**Interfaces:**
- Service invokes `/usr/local/libexec/pohvala-backup/backup.sh` as root with `/etc/pohvali-backup/config`.
- Timer runs daily at 03:15 UTC and has `Persistent=true`.

- [ ] Add the non-secret environment example with the four documented defaults.
- [ ] Add a `Type=oneshot` service with `UMask=0077`, a root-owned executable,
  read-only project/config paths, writable backup path and a bounded timeout.
- [ ] Add the daily persistent timer targeting the service.
- [ ] Verify unit syntax with `systemd-analyze verify` when available; otherwise verify exact units during the VPS installation runbook.

### Task 4: Operator documentation and backlog split

**Files:**
- Create: `docs/backup.md`
- Modify: `docs/deploy.md`
- Modify: `docs/backlog.md`

**Interfaces:**
- Runbook covers offline key generation, server installation, manual backup, timer enablement, freshness check, archive copy, restore drill and limitations.

- [ ] Document generating `identity.txt` off-server and copying only `recipient.txt` to `/etc/pohvali-backup/recipients.txt`.
- [ ] Document installing `age`, directories/permissions, config/unit installation, `daemon-reload`, manual run, timer enablement and `journalctl` checks.
- [ ] Document copying one encrypted archive to the admin machine and running `restore-drill.sh` there without exposing a database port.
- [ ] Split PH-704 into completed PH-704A and pending PH-704B without marking overall PH-704 complete; link the runbook from deployment docs.

### Task 5: Verification

**Files:** none.

- [ ] Run `pytest tests/test_backup_scripts.py -v` from `backend/`.
- [ ] Run full backend `pytest` and `ruff check .`.
- [ ] Run frontend `npm run check` because shared deployment docs/operations are release-level changes.
- [ ] Run `docker compose config --quiet` and confirm the service list is unchanged except for existing one-shot `migrate`.
- [ ] Run shell syntax checks for both scripts with Bash 5.
- [ ] Review `git diff --check`, `git status --short` and inspect the final diff against every spec acceptance criterion.

## Self-Review

- Spec coverage: backup success/fail atomicity, retention, locking, offline key boundary, isolated restore, timer and documentation each map to Tasks 1–4.
- Placeholder scan: no implementation placeholder remains; PH-704B is explicitly a separate future subsystem, not unfinished PH-704A code.
- Interface consistency: environment names and default paths match the spec, scripts, systemd unit and runbook.
