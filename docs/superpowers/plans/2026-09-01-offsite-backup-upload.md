# Offsite Backup Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать PH-704B: выгрузку готовых `*.dump.age` в приватное внешнее S3-совместимое object storage и off-host restore drill при недоступном VPS.

**Architecture:** Фаза offsite-выгрузки добавляется в существующий `backup.sh` после локального retention и включается флагом из отдельного секретного env-файла. `rclone` на хосте копирует только отсутствующие объекты и поддерживает удалённый retention по имени `pohvala-postgres-*.dump.age`. Новый `fetch-offsite-archive.sh` скачивает архив из bucket на администраторский компьютер; `restore-drill.sh` не меняется.

**Tech Stack:** Bash 5, rclone (S3-compatible), существующие age/systemd/pytest-инфраструктура PH-704A.

**Spec:** `docs/superpowers/specs/2026-09-01-offsite-backup-upload-design.md`

## Global Constraints

- Схема dump, шифрование, имена файлов и `restore-drill.sh` не меняются.
- Без offsite-конфигурации поведение PH-704A идентично; `rclone` не требуется.
- Никаких новых долгоживущих сервисов; offsite — фаза существующего one-shot job.
- Credentials только в root-owned 0600 env; секреты не попадают в логи.
- Удалённый retention удаляет только `pohvala-postgres-*.dump.age` в заданном prefix.

---

## File Structure

- `backend/tests/test_backup_scripts.py` — тесты offsite-фазы и fetch-скрипта на фейковых CLI-границах.
- `ops/backup/offsite-common.sh` — конфигурация, валидация, обёртка `rclone`.
- `ops/backup/backup.sh` — фаза выгрузки после локального retention.
- `ops/backup/fetch-offsite-archive.sh` — скачивание архива для off-host drill.
- `ops/backup/offsite.env.example` — шаблон секретного конфига.
- `ops/backup/pohvala-backup.service` — опциональный `EnvironmentFile` для offsite.env.
- `docs/backup.md`, `docs/backlog.md`, `docs/deploy.md` — runbook и статусы.

### Task 1: RED-тесты offsite-фазы backup

**Files:**
- Modify: `backend/tests/test_backup_scripts.py`

- [ ] Добавить `_rclone_body()` (fake copy/copyto/lsf/deletefile с логом вызовов), параметр `rclone_body` в `_backup_fixture`, хелпер `_offsite_env()`.
- [ ] Написать тесты: без offsite-конфигурации rclone не нужен; успешная выгрузка копирует и делает удалённый retention; ошибка выгрузки сохраняет локальный архив; неполная конфигурация/не-https endpoint/невалидный retention дают код 2 до dump; отсутствие `rclone` при включённой выгрузке даёт код 2.
- [ ] Прогнать `pytest tests/test_backup_scripts.py -v`; новые тесты — RED.

### Task 2: RED-тесты fetch-offsite-archive

**Files:**
- Modify: `backend/tests/test_backup_scripts.py`

- [ ] Тесты: скачивание самого свежего архива; явное имя без листинга; пустой bucket → `no offsite archives found`; ошибка скачивания; отказ перезаписи существующего файла.
- [ ] Прогнать; новые тесты — RED (скрипта нет).

### Task 3: реализация скриптов

**Files:**
- Create: `ops/backup/offsite-common.sh`
- Modify: `ops/backup/backup.sh`
- Create: `ops/backup/fetch-offsite-archive.sh`
- Create: `ops/backup/offsite.env.example`
- Modify: `ops/backup/pohvala-backup.service`
- Modify: `ops/backup/backup.env.example`

- [ ] `offsite-common.sh`: `offsite_load_config`, `offsite_validate` (exit 2 с сообщением), `offsite_remote_root`, `offsite_rclone` с env-only S3-конфигурацией.
- [ ] `backup.sh`: source хелпера, условная зависимость `rclone`, фаза copy→lsf→удалённый retention после локального retention, `offsite upload complete` в stdout.
- [ ] `fetch-offsite-archive.sh`: валидация аргументов, листинг/выбор свежего архива, `copyto`, проверка непустого размера, 0600, без перезаписи.
- [ ] systemd unit: `EnvironmentFile=-/etc/pohvali-backup/offsite.env`.
- [ ] Прогнать `pytest tests/test_backup_scripts.py -v`; все — PASS. `bash -n` на всех скриптах.

### Task 4: документация и статусы

**Files:**
- Modify: `docs/backup.md`
- Modify: `docs/backlog.md`
- Modify: `docs/deploy.md`
- Create: `docs/superpowers/specs/2026-09-01-offsite-backup-upload-design.md`
- Create: `docs/superpowers/plans/2026-09-01-offsite-backup-upload.md`

- [ ] `docs/backup.md`: раздел 4 (bucket, минимальная policy, включение, поведение при сбое), раздел 6 (off-host drill), обновлённые интро и протокол.
- [ ] `docs/backlog.md`: PH-704B — реализовано, открыто до production-настройки и первого off-host восстановления.
- [ ] `docs/deploy.md`: обновить пункт про PH-704 в эксплуатационном минимуме.

### Task 5: Verification

- [ ] `pytest tests/test_backup_scripts.py -v` из `backend/`.
- [ ] Полный backend `pytest` и `ruff check .`.
- [ ] Frontend `npm run check` (release-level изменение общих ops-документов).
- [ ] `bash -n` для `backup.sh`, `fetch-offsite-archive.sh`, `offsite-common.sh`.
- [ ] Инспекция финального диффа по каждому критерию приёмки спеки.

## Self-Review

- Spec coverage: каждый пункт приёмки покрыт тестом или проверкой Task 5.
- Placeholder scan: заглушек нет; открытые пункты (production bucket, реальный off-host drill) явно вынесены в спеку и backlog.
- Interface consistency: имена переменных совпадают в спеке, скриптах, env-примере, systemd unit и runbook.
