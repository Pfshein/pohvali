# Privacy Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать PH-706: privacy policy, путь удаления данных, честное описание границ Telegram/recovery, юрисдикция и data residency.

**Architecture:** `DELETE /api/v1/session` в существующем session-роутере стирает пользователя каскадом (FK `ON DELETE CASCADE` уже в DDL). Политика — самодостаточная статическая страница `frontend/public/privacy.html`; в приложении — панель с выжимкой, ссылкой и двухшаговым удалением (машина состояний в чистой функции). Юрисдикция фиксируется в `docs/deploy.md`.

**Tech Stack:** FastAPI + SQLAlchemy (существующие паттерны), React/Vite, pytest + vitest, PostgreSQL для DB-тестов.

**Spec:** `docs/superpowers/specs/2026-09-02-privacy-deletion-design.md`

## Global Constraints

- Только собственные данные; идентичность — из подписанного initData.
- Никаких новых сервисов, таблиц или миграций: каскады уже существуют.
- Тексты UI и политики — без давления/guilt-языка, только факты.
- Каждый факт политики соответствует реальному поведению системы.
- Логи не содержат Telegram ID и содержимого запросов (включая удаление).

---

## File Structure

- `backend/tests/test_session_api.py` — DB-тесты каскадного удаления + 401.
- `backend/app/modules/users/repository.py`, `service.py` — delete/erase.
- `backend/app/api/v1/session.py` — `DELETE /session`.
- `frontend/src/lib/account.ts` + `account.test.ts` — транспорт и машина состояний.
- `frontend/src/components/PrivacyPanel.tsx` + `PrivacyPanel.test.ts` — UI-панель.
- `frontend/src/App.tsx`, `SessionRoot.tsx` — интеграция.
- `frontend/public/privacy.html` — публикуемая политика.
- `docs/deploy.md`, `docs/backlog.md`, `docs/product-brief.md` — статусы и residency.

### Task 1: RED-тесты удаления (backend)

- [ ] В `test_session_api.py` добавить DB-тест: session + praise (+SQL: reminder_state, mascot, ownership) → `DELETE /api/v1/session` → `204`; прямые подсчёты строк по всем семи таблицам дают 0.
- [ ] DB-тест идемпотентности: DELETE без созданного профиля → `204`.
- [ ] Тест без БД: неавторизованный DELETE → `401`.
- [ ] Прогнать с поднятым PostgreSQL; новые тесты — RED.

### Task 2: Реализация удаления (backend)

- [ ] `delete_user_by_telegram_id` в repository (`DELETE … RETURNING`), `erase_account` в service (одна транзакция).
- [ ] `DELETE /api/v1/session` в роутере: `SessionRateLimited`, `204`, идемпотентно.
- [ ] Прогнать Task 1 — PASS; весь backend `pytest` (с БД) и `ruff` — зелёные.

### Task 3: Фронтенд — account lib и панель

- [ ] RED: `account.test.ts` (DELETE-запрос с tma-заголовком; generic-ошибка; переходы машины состояний, включая запрет повторного confirm из working).
- [ ] `lib/account.ts`: `deleteAccountData`, `nextDeletionStep`.
- [ ] RED: `PrivacyPanel.test.ts` (исходная разметка без вызова удаления; confirm-шаг требует явного действия; спокойные тексты; ссылка на политику).
- [ ] `PrivacyPanel.tsx` в стиле существующих диалогов; интеграция в `App.tsx`/`SessionRoot.tsx` без новых CSS-зависимостей.
- [ ] `npm run check` и все vitest — зелёные.

### Task 4: Политика и документы

- [ ] `frontend/public/privacy.html`: самодостаточная страница со всеми обязательными разделами; версии и дата; без внешних ресурсов.
- [ ] `docs/deploy.md`: раздел «Юрисдикция и data residency» (VPS/bucket в ЕС, публикация политики по `/privacy.html`).
- [ ] `docs/backlog.md` (PH-706 статус) и `docs/product-brief.md` (снятые решения) обновить.

### Task 5: Verification

- [ ] Полный backend `pytest` с `RUN_DATABASE_TESTS=1` на PostgreSQL + `ruff check .`.
- [ ] Frontend `npm run check`.
- [ ] Инспекция политики по каждому разделу спеки на соответствие фактам системы.
- [ ] Финальный diff по всем критериям приёмки.

## Self-Review

- Spec coverage: все шесть пунктов приёмки покрыты задачами 1–5.
- Placeholder scan: не осталось «будет добавлено»; границы удаления сформулированы честно (backup retention, ключ пользователя).
- Interface consistency: путь и метод эндпоинта совпадают в тестах, фронтенд-транспорте, политике и спеке.
