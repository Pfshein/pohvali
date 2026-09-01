# Reminder Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать PH-504: one-time offer напоминаний при прямом входе и секция настроек с переключателем.

**Architecture:** `?from=reminder` в URL кнопки напоминания (backend-хелпер `reminder_entry_url`); на фронте — `lib/reminders-api.ts` (GET/PUT транспорт), `lib/reminder-offer.ts` (чистая логика показа + storage-флаг как у onboarding), компоненты `ReminderOffer` и `ReminderSettings`, проводка через `App`/`SessionRoot`. Новых эндпоинтов и таблиц нет.

**Tech Stack:** Существующие FastAPI reminders API, React/Vite, vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-09-02-reminder-settings-design.md`

## Global Constraints

- Тексты спокойные, без pressure-слов и без упоминания личных записей.
- Отказ никогда не переспрашивается (локальный флаг + серверный `enabled=false`).
- Сервер — источник истины для `enabled`; локально хранится только «отвечено».
- Никаких изменений БД/endpoint'ов.

---

## File Structure

- `backend/app/modules/reminders/sender.py` — `reminder_entry_url`.
- `backend/app/main.py` — использовать хелпер для кнопки sender'а.
- `backend/tests/test_reminder_delivery.py` — тест URL-хелпера.
- `frontend/src/lib/reminders-api.ts` + тест — транспорт настроек.
- `frontend/src/lib/reminder-offer.ts` + тест — логика показа и storage-флаг.
- `frontend/src/components/ReminderOffer.tsx` + тест.
- `frontend/src/components/ReminderSettings.tsx` + тест.
- `frontend/src/App.tsx`, `SessionRoot.tsx` — интеграция.
- `frontend/src/styles.css` — спокойные стили карточки и переключателя.
- `docs/backlog.md` — статус PH-504.

### Task 1: RED-тесты

- [ ] `reminders-api.test.ts`: GET с tma-заголовком и парсинг `dm_available`; PUT с `{enabled}`; generic-ошибки.
- [ ] `reminder-offer.test.ts`: `enteredFromReminder` по query; матрица `shouldShowReminderOffer`; флаг в storage (load/mark, ошибка storage → не отвечено).
- [ ] `ReminderOffer.test.ts`: спокойный коп, обе кнопки, обработчик не вызывается без клика, нет pressure-слов.
- [ ] `ReminderSettings.test.ts`: switch по `enabled`, подсказка про чат бота при `dmAvailable=false`, отсутствие подсказки при true.
- [ ] backend: `reminder_entry_url` добавляет `?from=reminder` и терпит trailing slash.

### Task 2: Реализация

- [ ] `reminder_entry_url` в sender.py + `main.py`.
- [ ] `lib/reminders-api.ts`, `lib/reminder-offer.ts` (+ storage с CloudStorage/localStorage фолбэком).
- [ ] `ReminderOffer.tsx` (states: asking/working/done/error), `ReminderSettings.tsx` (loading/ready/error + switch).
- [ ] Стили; интеграция в `App.tsx`/`SessionRoot.tsx`.
- [ ] Прогнать целевые тесты — PASS.

### Task 3: Доки и верификация

- [ ] `docs/backlog.md`: PH-504 статус «выполнено».
- [ ] Frontend `npm run check` (включая тон-аудит новых файлов).
- [ ] Backend `pytest` + `ruff check .`.
- [ ] Финальный diff по приёмке спеки.

## Self-Review

- Spec coverage: приёмка 1–4 закрыта задачами 1–3.
- Placeholder scan: заглушек нет; ошибка PUT осознанно не блокирует ответ (зафиксировано в спеке).
- Interface consistency: `?from=reminder` согласован между sender, `enteredFromReminder` и спекой; поле `dm_available` маппится в `dmAvailable` один раз в транспорте.
