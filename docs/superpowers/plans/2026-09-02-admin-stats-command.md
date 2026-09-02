# PH-802 — Admin statistics command

> **Исполнитель:** документ самодостаточен. Сначала прочитай `AGENTS.md`, затем
> выполняй задачи по порядку. Не расширяй scope. Если фактическая структура
> отличается, выбери минимальное совместимое изменение и объясни его в отчёте.

## Цель и пользовательский интерфейс

Добавить Telegram-команду `/stats`, доступную только пользователю с
`users.role='admin'` и только в private chat. Статистика агрегированная: backend
никогда не читает `body_ciphertext`/`iv`, не выводит Telegram ID и не сохраняет
имя, username, IP, request body или произвольные analytics events.

`/stats` возвращает блоки «Сегодня (UTC)», «Последние 7 дней (UTC)» и «За всё
время». `/stats 30` возвращает «Последние 30 дней (UTC)» и «За всё время».
Поддержать `/stats@BotName` и `/stats@BotName 30`. Другие аргументы дают admin
короткую подсказку `Формат: /stats или /stats 30`.

Периодный блок:

```text
Сегодня (UTC)
• Открыли приложение: 18
• Оставили похвалу: 7
• Всего похвал: 11
• Конверсия: 38,9%
```

All-time блок:

```text
За всё время
• Пользователей: 247
• Оставили хотя бы одну похвалу: 103
• Всего похвал: 684
• Конверсия: 41,7%
```

Конверсия периода = distinct авторы похвал периода / distinct открывавшие
приложение периода. All-time = пользователи с хотя бы одной похвалой / все
users. При нулевом знаменателе показывать `0,0%`; формат — одна цифра после
запятой. Не выводить содержимое, даты или показатели отдельных пользователей.

## Зафиксированные архитектурные решения

1. Новая таблица `user_activity_days`, а не event log/SDK.
2. UTC-день определяется backend; клиент дату не передаёт.
3. Один row на `(user_id, activity_date)`. Повторный session увеличивает
   `open_count`, обновляет `last_opened_at`; первая отметка сохраняется.
4. Отметка активности записывается в той же транзакции `open_session`, что и
   user upsert. Ошибка отметки откатывает session upsert.
5. Исторический backfill не выдумывает открытия: один row создаётся для дня
   `users.created_at` и для каждого UTC-дня, когда у пользователя создана
   praise. При совпадении даты строки объединяются; `open_count=1` означает
   «известно как минимум одно открытие».
6. Периоды полуоткрытые по UTC timestamp: от UTC-полуночи первого дня до
   UTC-полуночи после последнего дня. Для activity используется inclusive
   диапазон дат.
7. Авторизация только через `is_admin_user`/DB-role из PH-801. Никаких env IDs,
   request role, JWT или отдельного admin token.
8. Команда user и неизвестного аккаунта отвечает одинаковым существующим
   generic-текстом «Эта команда доступна только администратору сервиса.».
   Команды из group/supergroup/channel полностью игнорируются.
9. Удаление users каскадно удаляет activity. Никаких retention-исключений.

## Схема и индексы

Создать revision `20260902_0012`, `down_revision='20260902_0011'`:

- `user_id UUID NOT NULL`, FK `users.id ON DELETE CASCADE`;
- `activity_date DATE NOT NULL`;
- `first_opened_at TIMESTAMPTZ NOT NULL DEFAULT now()`;
- `last_opened_at TIMESTAMPTZ NOT NULL DEFAULT now()`;
- `open_count INTEGER NOT NULL DEFAULT 1`;
- composite PK `(user_id, activity_date)`;
- CHECK `open_count > 0` с корректным naming convention;
- index на `activity_date`;
- index на `praises.created_at` для периодных агрегатов.

Downgrade удаляет индекс praises и таблицу. Имена в downgrade помечать через
`op.f(...)`, чтобы naming convention не применялся дважды (урок PH-801).

Добавить ORM `UserActivityDay` и импорт в `app/models.py`. Модель не должна
содержать Telegram ID или произвольный event payload.

## Ожидаемая структура кода

Создать (названия можно минимально адаптировать к проекту):

- `backend/app/migrations/versions/20260902_0012_add_user_activity_days.py`;
- `backend/app/modules/admin_stats/models.py`;
- `backend/app/modules/admin_stats/repository.py`;
- `backend/app/modules/admin_stats/service.py`;
- `backend/app/modules/bot/stats.py`;
- `backend/tests/test_admin_stats_command.py`;
- `backend/tests/test_admin_stats_db.py`.

Изменить:

- `backend/app/models.py`;
- `backend/app/modules/users/service.py` (activity в session-транзакции);
- `backend/app/api/v1/telegram.py` (stats handler);
- `backend/app/modules/bot/messages.py`;
- migration/model/session deletion/webhook tests по контрактам;
- `docs/backlog.md`, `docs/product-brief.md`, при необходимости `README.md`.

Не добавлять frontend, HTTP admin endpoint, dashboard, dependency, cron, Redis,
очередь или общий `analytics_events`.

## Task 1 — RED: миграция и модель

- [ ] Model test проверяет точный набор колонок, composite PK, FK cascade,
  timestamptz, positive CHECK и отсутствие PII/payload полей.
- [ ] Migration integration test делает downgrade/upgrade и проверяет таблицу,
  индексы, constraints и clean downgrade.
- [ ] Backfill test на revision 0011 создаёт: user без praise, user с praise в
  другой UTC-день, и совпадение created/praise day. После head ожидает только
  правдивые unique user/day rows, без дублей, `open_count=1`.
- [ ] Проверить единственный Alembic head и offline SQL.

## Task 2 — GREEN: безопасная запись активности

- [ ] Repository-функция принимает `user_id` и aware UTC `observed_at`.
- [ ] PostgreSQL upsert по composite PK: conflict увеличивает `open_count` на
  один и ставит `last_opened_at=observed_at`; `first_opened_at` не меняется.
- [ ] `open_session` после user upsert вызывает activity repository внутри уже
  существующего `session.begin()`; repository не делает commit/begin.
- [ ] Не брать дату из payload timezone; всегда `observed_at` в UTC.
- [ ] DB tests: первое, повторное и два конкурентных открытия дают один row и
  правильный count; другой UTC-день создаёт второй row.
- [ ] Existing session API по-прежнему возвращает только `id/timezone/role`.
- [ ] Account deletion contract включает `user_activity_days` и подтверждает
  cascade.

Для детерминированных тестов допустим keyword-only `observed_at: datetime | None`
в `open_session`, default `datetime.now(UTC)`. HTTP не принимает это поле.

## Task 3 — RED/GREEN: агрегаты

- [ ] Ввести immutable dataclasses/typed records `PeriodStats` и `StatsSnapshot`.
- [ ] Service принимает aware `now` (default UTC now) и считает today/7/30/all.
- [ ] `opened_users`: `count(distinct user_id)` в activity date range.
- [ ] `praised_users`: `count(distinct Praise.user_id)` по `created_at` range.
- [ ] `praises`: `count(Praise.id)` по тому же range.
- [ ] All-time users считает `users`, authors/praises — `praises`.
- [ ] Ни один запрос не выбирает ciphertext/iv и не загружает Praise entities;
  только SQL aggregate columns.
- [ ] DB test фиксирует now и набор пользователей на границах UTC: начало дня,
  7/30 дней, ровно за пределом. Проверить distinct, totals и нулевой период.
- [ ] Stats service владеет одной транзакцией чтения и завершает её до send.

## Task 4 — RED/GREEN: parser и formatter `/stats`

- [ ] Pure helper извлекает actor только для private text-команды `/stats` или
  `/stats@name`; malformed `from.id`, caption, group и похожие `/statss` — None.
- [ ] Parser после authorization возвращает typed command default или 30;
  invalid args — typed refused/usage; non-admin получает generic denial до
  разбора аргументов (не раскрывать admin grammar).
- [ ] Formatter выдаёт точные русские labels выше, integer counts и percent с
  comma decimal. Не включает ID, ciphertext и строки отдельных users.
- [ ] Tests: default, 30, mention, whitespace, invalid arg, non-admin,
  unknown/group, zero conversion и округление (например 1/3 = 33,3%).

## Task 5 — webhook wiring и security matrix

- [ ] После start/add_mascot вызвать отдельный `_handle_stats`; unrelated update
  не делает DB role query.
- [ ] actor -> `is_admin_user` -> parse -> stats service -> `send_reply`.
- [ ] Admin `/stats` получает агрегаты; admin `/stats 30` — 30-day вариант.
- [ ] User и неизвестный аккаунт получают одинаковый denial и stats query не
  вызывается. Group получает no reply и no query.
- [ ] Stats service exception: webhook не должен утекать stack/data в Telegram;
  вернуть спокойное generic retry сообщение и залогировать только outcome.
- [ ] Логи не содержат actor/chat ID, command text, counts, DATABASE_URL или
  praise data. Допустимы только event name и outcome.
- [ ] Webhook всегда отвечает Telegram HTTP 200 после обработанной команды.

## Task 6 — verification и handoff

- [ ] Обновить product brief: храним только UUID/date/timestamps/count для
  дневной активности ради агрегированной admin stats; cascade deletion.
- [ ] `cd backend && .venv/bin/ruff check .`.
- [ ] `cd backend && .venv/bin/pytest -q` (DB tests могут skip локально).
- [ ] Если Docker/PostgreSQL доступен, повторить CI env с `RUN_DATABASE_TESTS=1`.
- [ ] `cd frontend && npm run check` — подтверждение отсутствия регрессии.
- [ ] `git diff --check`; Alembic exactly one head.
- [ ] Отчёт: changed files, exact test counts, skipped DB status, отклонения.

## Definition of done

Задача не готова, пока migration downgrade/upgrade, concurrent activity upsert,
period boundaries, admin/user/unknown/group matrix и account cascade не покрыты
тестами. Локальный green без PostgreSQL помечается как ожидающий GitHub DB CI.
