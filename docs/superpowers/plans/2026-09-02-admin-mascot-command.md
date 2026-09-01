# Admin Mascot Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать PH-405: `/add_mascot <code> <порог> | <Имя> | <Описание>` с PNG-документом из личного чата админа.

**Architecture:** Чистый парсер в `app/modules/bot/add_mascot.py` (без I/O), PNG-валидатор в `app/modules/mascots/png.py` (без зависимостей), скачивание через aiogram behind protocol, `asset_path` нового маскота = `/api/v1/mascots/{code}/image` — фронтенд не меняется. Колонка `image_data BYTEA` deferred.

**Tech Stack:** FastAPI, aiogram 3 (get_file/download_file), SQLAlchemy/Alembic, PostgreSQL, pytest.

**Spec:** `docs/superpowers/specs/2026-09-02-admin-mascot-command-design.md`

## Global Constraints

- Команда только private chat + `TELEGRAM_ADMIN_IDS`; отказ спокойный и одинаковый.
- Логи без текста команды, Telegram ID, file_id, байтов.
- Никаких новых зависимостей (PNG парсим сами), никаких изменений фронтенда.
- Тексты — без давления/guilt (PH-604), у ошибок объясняется, что исправить.
- Один long-running backend; webhook остаётся единственной точкой входа.

---

## File Structure

- `backend/app/migrations/versions/20260902_0010_add_mascot_image_data.py`
- `backend/app/modules/bot/add_mascot.py` — парсер + AdminReply.
- `backend/app/modules/mascots/png.py` — валидатор PNG.
- `backend/app/modules/mascots/models.py` — deferred `image_data`.
- `backend/app/modules/mascots/repository.py`, `service.py` — add/get_image + исключения.
- `backend/app/api/v1/mascots.py` — публичный `/mascots/{code}/image`.
- `backend/app/api/v1/telegram.py` — оркестрация команды.
- `backend/app/api/dependencies.py` — FileDownloader.
- `backend/app/modules/bot/sender.py` — generic BotReply + document-echo.
- `backend/app/modules/bot/messages.py`, `app/core/config.py`, `.env.example`, `compose.yaml`.
- Тесты: `test_add_mascot_command.py`, `test_mascot_png.py`, `test_mascot_add_db.py`, `tests/test_telegram_webhook.py` (расширение).
- Доки: `docs/deploy.md`, `docs/backlog.md`.

### Task 1: RED-тесты чистой логики

- [ ] `test_add_mascot_command.py`: happy path парсинга; не-admin; не-private; без документа; format-ошибки code/порог/имя/описание/аргументы; не-команда → None; file_size > 1 MiB — ранний отказ; тон текстов (запрещённые слова).
- [ ] `test_mascot_png.py`: валидный RGBA 256–1024; битая сигнатура; >1 MiB; 255/1025 px; без alpha (color type 0/2); palette+tRNS проходит.

### Task 2: RED-тесты сервиса, эндпоинта и вебхука

- [ ] `test_mascot_add_db.py`: создание записи с правильным asset_path/байтами; идемпотентный повтор; конфликт code; конфликт порога; image endpoint 200/404; каталог содержит нового маскота (DB-гейты как в существующих).
- [ ] `test_telegram_webhook.py`: happy path с замоканным downloader и сервисом; отказ не-admin; битый PNG; ошибка скачивания; логи без file_id (caplog).

### Task 3: Реализация

- [ ] Миграция `image_data`; deferred-колонка в модели.
- [ ] `parse_add_mascot` + `AdminReply`; сообщения в `messages.py`.
- [ ] `validate_png` (+`_has_trns_chunk`).
- [ ] repository/service: `get_mascot`, `find_by_threshold`, `next_sort_order`, `insert`, `get_image_data`; `add_mascot` с исходами/исключениями.
- [ ] `/mascots/{code}/image`; downloader dependency; sender protocol+document echo; webhook-оркестрация с логированием исходов.
- [ ] `TELEGRAM_ADMIN_IDS` в Settings (+валидатор), `.env.example`, `compose.yaml`.

### Task 4: Доки и статусы

- [ ] `docs/deploy.md`: TELEGRAM_ADMIN_IDS в таблице env + инструкция команды.
- [ ] `docs/backlog.md`: PH-405 статус «выполнено».

### Task 5: Verification

- [ ] Полный backend `pytest` с `RUN_DATABASE_TESTS=1` на PostgreSQL + `ruff check .`.
- [ ] Фронтенд не менялся — `npm run check` не требуется, но прогнать для release-гигиены.
- [ ] Финальный diff по всем семи пунктам приёмки спеки.

## Self-Review

- Spec coverage: приёмка 1–7 закрыта задачами 1–5; идемпотентность покрыта и парсером (одинаковый ввод), и сервисом (сравнение строк), и вебхук-тестом.
- Placeholder scan: заглушек нет; file_id-эхо для превью использует сам Telegram file_id без хранения.
- Interface consistency: формат подписи совпадает в спеке, парсере, сообщениях и deploy-инструкции.
