# User Roles and Admin Authorization Implementation Plan

> **Исполнитель:** этот документ самодостаточен. Сначала полностью прочитай
> `AGENTS.md` и дизайн-спеку, затем выполняй задачи строго по порядку. Не
> расширяй scope и не заменяй решения «более простыми» без согласования.

**Goal:** Реализовать PH-801: серверные роли `user/admin`, CLI управления ролью,
общую admin dependency и перевод `/add_mascot` на роль из PostgreSQL.

**Architecture:** Telegram `initData`/webhook определяет Telegram ID, PostgreSQL
является единственным источником полномочий. Роль — `VARCHAR(16)` + check
constraint. Обычная сессия не может изменить роль. Визуальной админки в задаче
нет.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL,
pytest; React/TypeScript transport contract.

**Spec:**
`docs/superpowers/specs/2026-09-02-user-roles-admin-authorization-design.md`

## Запрещённые отклонения

- Не добавлять JWT, cookies, API keys, Redis, отдельный admin service или новые
  зависимости.
- Не делать `is_admin` boolean и не создавать отдельную таблицу admins.
- Не использовать PostgreSQL native enum; использовать `VARCHAR(16)` + CHECK.
- Не выдавать/снимать роли через HTTP API.
- Не читать и не изменять чужие praises/ciphertext.
- Не доверять роли из request/frontend/session response.
- Не оставлять `TELEGRAM_ADMIN_IDS` fallback в исполняемом коде.
- Не логировать Telegram ID, caption, file_id, image bytes или DATABASE_URL.
- Не менять tone-of-voice пользовательских сообщений.
- Не коммитить `.env`, токены или реальные Telegram ID.

## Ожидаемые файлы

Создать:

- `backend/app/migrations/versions/20260902_0011_add_user_role.py`
- `backend/app/modules/users/set_role.py`
- `backend/tests/test_user_roles_db.py`
- `backend/tests/test_set_user_role_cli.py`
- `backend/tests/test_admin_authorization.py`

Изменить:

- `backend/app/modules/users/models.py`
- `backend/app/modules/users/repository.py`
- `backend/app/modules/users/service.py`
- `backend/app/modules/users/schemas.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/v1/telegram.py`
- `backend/app/modules/bot/add_mascot.py`
- релевантные tests существующих session/migration/webhook/parser контрактов;
- `frontend/src/lib/api.ts`
- `frontend/src/lib/session.ts`
- `frontend/src/lib/session.test.ts`
- `.env.example`, `compose.yaml`, `README.md`, `docs/product-brief.md`,
  `docs/deploy.md`, `docs/backlog.md`.

Список может измениться только если тестовая структура проекта требует этого;
в финальном отчёте объяснить любое отклонение.

---

## Task 1: RED — модель и миграционный контракт

- [ ] В `test_user_model.py` обновить точный набор колонок, добавив `role`.
- [ ] Проверить тип `String(16)`, `nullable=False`, Python default `user`, server
  default `user` и наличие table check constraint.
- [ ] Проверить, что forbidden PII-набор по-прежнему отсутствует.
- [ ] Обновить `test_migrations.py`: clean head содержит `role`, direct insert
  без роли получает `user`, произвольная роль и NULL отвергаются БД.
- [ ] Добавить migration-safety тест: создать пользователя на ревизии
  `20260902_0010`, обновиться на head, убедиться, что id/telegram_id/timezone
  сохранены, а role=`user`.
- [ ] Запустить только новые/изменённые тесты и убедиться, что они падают по
  ожидаемой причине до реализации.

## Task 2: GREEN — enum, модель и Alembic

- [ ] В `users/models.py` добавить `UserRole(StrEnum)` со значениями только
  `USER="user"`, `ADMIN="admin"`.
- [ ] Добавить `User.role` как `Mapped[str]`, `String(16)`, Python/server default
  `UserRole.USER.value`, `nullable=False`.
- [ ] Добавить именованный `CheckConstraint` на `user/admin`, совместимый с
  naming convention проекта.
- [ ] Создать ревизию `20260902_0011`, `down_revision="20260902_0010"`.
- [ ] Upgrade: колонка с default + CHECK. Downgrade: CHECK, затем колонка.
- [ ] Не удалять server default после backfill.
- [ ] Прогнать тесты Task 1.

## Task 3: RED/GREEN — repository/service управления ролью

- [ ] В repository добавить `get_user_by_telegram_id(session, *, telegram_id)`.
- [ ] Добавить update-returning функцию назначения роли существующей строке; не
  делать upsert и не создавать пользователя.
- [ ] В service добавить транзакционную `set_user_role(...)` и явную ошибку
  `UserNotFound` (или эквивалентное доменное имя).
- [ ] Добавить helper `is_admin_user(session, *, telegram_id) -> bool` для
  webhook; неизвестный пользователь возвращает `False`.
- [ ] DB-тесты:
  - новый/opened пользователь имеет `user`;
  - `set_user_role` меняет `user → admin → user`;
  - повторное назначение той же роли идемпотентно;
  - неизвестный ID не создаёт строку;
  - после назначения admin повторный `open_session` обновляет timezone, но
    сохраняет `admin`.
- [ ] Не делать commit внутри repository; транзакцией владеет service.

## Task 4: RED/GREEN — CLI `set_role`

- [ ] Реализовать `python -m app.modules.users.set_role TELEGRAM_ID ROLE`.
- [ ] `argparse`: ID — положительный integer; ROLE choices `user`, `admin`;
  лишние/невалидные аргументы дают ненулевой exit code.
- [ ] Использовать существующие `get_session_factory()` и service; не создавать
  второй engine/configuration path.
- [ ] При успехе вывести нейтральное подтверждение без Telegram ID и завершиться
  `0`.
- [ ] При `UserNotFound` вывести инструкцию сначала открыть бота/Mini App, без
  повторения ID, завершиться ненулевым кодом.
- [ ] Unit-тестировать parser/main через mocks; DB-поведение уже закрыто Task 3.
- [ ] Убедиться, что captured stdout/stderr не содержит тестовый Telegram ID или
  `DATABASE_URL`.

## Task 5: RED/GREEN — session API и frontend transport

- [ ] В `UserProfile` добавить `role: Literal["user", "admin"]` либо строгий
  enum, сериализующийся ровно этими строками.
- [ ] Backend integration test ожидает ровно `{id, timezone, role}` и `user` для
  нового аккаунта.
- [ ] Добавить test: назначить admin через service, повторить `/session`, получить
  `role=admin` и новую timezone без сброса роли.
- [ ] В `frontend/src/lib/api.ts` добавить `UserRole` и `SessionProfile.role`.
- [ ] В `openSession` строго проверить наличие `role` и допустимое значение.
- [ ] Возвращать role; не доверять дополнительным полям ответа.
- [ ] Frontend tests: user/admin проходят, неизвестная или отсутствующая role
  даёт generic session error, лишние PII-поля игнорируются.
- [ ] Не добавлять кнопку или route админки.

## Task 6: RED/GREEN — общая FastAPI admin dependency

- [ ] В `api/dependencies.py` добавить async `require_admin_user` и alias
  `AdminUser` согласно спеке.
- [ ] Dependency использует уже проверенный `TelegramAuth`, DB session и
  repository/service lookup; не принимает role параметром.
- [ ] Валидный admin возвращает объект `User`.
- [ ] User и неизвестный пользователь получают одинаковые status `403` и body.
- [ ] Невалидный/missing initData остаётся `401` и не доходит до DB role check.
- [ ] Тесты не должны сравнивать или выводить реальный Telegram ID.

## Task 7: RED — webhook authorization cases

- [ ] Переписать parser tests с `admin_ids` на явный `authorized` и helper
  извлечения actor ID.
- [ ] Покрыть helper: private `/add_mascot`, `/add_mascot@botname`, не-команда,
  group chat, отсутствующий/не-int `from.id`.
- [ ] Webhook tests:
  - DB admin скачивает PNG, вызывает service и получает preview;
  - DB user получает прежний спокойный отказ;
  - неизвестный пользователь получает тот же status/body, что user;
  - user/unknown не вызывает downloader и `add_mascot`;
  - malformed command от non-admin не раскрывает format details;
  - admin с malformed command получает существующую format-подсказку;
  - sensitive значения отсутствуют в caplog.
- [ ] В тестах мокать `is_admin_user`, а не Settings admin IDs.

## Task 8: GREEN — перевести `/add_mascot` на БД

- [ ] В чистом parser module добавить минимальный helper actor extraction.
- [ ] Изменить `parse_add_mascot(update, *, authorized: bool)`; проверка
  `authorized` происходит до полной проверки document/arguments.
- [ ] В `_handle_add_mascot` запрашивать БД только для распознанного private
  admin-command token.
- [ ] Проверять роль по `message.from.id`, отвечать по private `chat.id`.
- [ ] Для user/unknown завершать обработку до download/PNG/catalog service.
- [ ] Сохранить текущую идемпотентность, PNG validation, ошибки конфликтов и
  privacy-safe logging.
- [ ] Полностью удалить использование `settings.telegram_admin_id_set`.

## Task 9: Удалить env-authority и обновить эксплуатацию

- [ ] Удалить `telegram_admin_ids`, validator и property из `Settings`.
- [ ] Удалить `TELEGRAM_ADMIN_IDS` из `.env.example` и `compose.yaml`.
- [ ] Обновить актуальные README/deploy инструкции: назначение и снятие роли
  через container CLI, пользователь должен сначала открыть bot/Mini App.
- [ ] В deploy checklist добавить одноразовое назначение первого admin после
  выкладки и удаление старой переменной из production `.env`.
- [ ] В `docs/product-brief.md` зафиксировать role как допустимое минимальное
  техническое поле и отсутствие admin-доступа к praise bodies.
- [ ] Исторические документы PH-405 под `docs/superpowers/*` не переписывать:
  они описывают решение на дату реализации. Поиск `TELEGRAM_ADMIN_IDS` после
  изменений допустим только в исторических PH-405 spec/plan и в PH-801 тексте.

## Task 10: Полная проверка и статус

- [ ] Backend без DB: `cd backend && ruff check . && pytest`.
- [ ] Backend с isolated PostgreSQL:
  `APP_ENV=test RUN_DATABASE_TESTS=1 DATABASE_URL=... pytest`.
- [ ] Frontend: `cd frontend && npm run check`.
- [ ] Проверить `git diff --check`.
- [ ] Проверить миграционную цепочку: один head, `0011 -> 0010`.
- [ ] Проверить production Compose parse: `docker compose config --quiet`, если
  Docker доступен; иначе честно указать, что не запускалось.
- [ ] Обновить PH-801 в `docs/backlog.md` на «выполнено» только после всех
  обязательных проверок. Если PostgreSQL недоступен, оставить статус
  «реализовано, ожидает DB verification».
- [ ] Не менять статусы PH-704/PH-707.

## Обязательный self-review перед handoff

- [ ] Source of truth ровно один: поиск runtime-кода не находит env admin IDs.
- [ ] `open_session` не меняет `role` в `ON CONFLICT DO UPDATE`.
- [ ] CLI не создаёт аккаунты и не раскрывает входные/секретные значения.
- [ ] Session role используется frontend только для информации, не как backend
  authorization.
- [ ] `/add_mascot` user path не скачивает файл и не пишет в БД.
- [ ] Нет новых endpoint'ов чтения/изменения пользовательских данных.
- [ ] Все десять пунктов приёмки дизайн-спеки сопоставлены с тестом или явной
  проверкой в финальном отчёте.

## Формат отчёта исполнителя

Вернуть Sol короткий отчёт:

1. какие решения реализованы;
2. список изменённых файлов;
3. результаты backend/frontend/DB проверок с числами тестов;
4. что не удалось проверить и почему;
5. SHA коммита, если исполнитель делал commit.

Не пересказывать всю спеку и не вставлять полные логи тестов.

