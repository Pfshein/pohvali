# Backlog MVP

Порядок ниже — рекомендуемый порядок реализации. `P0` нужен для запуска MVP, `P1` можно сдвинуть после первого закрытого теста.

## M0 — репозиторий запускается

### PH-001 · P0 · Каркас mono-repo

**Результат:** frontend, backend, Caddy и PostgreSQL запускаются одной командой.

**Приёмка:** `docker compose config` валиден; `/api/v1/health` отвечает `200`; SPA открывается через Caddy; PostgreSQL не публикует порт наружу.

### PH-002 · P0 · CI quality gate

**Результат:** pull request нельзя слить с красными проверками.

**Приёмка:** отдельно выполняются frontend lint/typecheck/test/build и backend ruff/pytest; dependency cache включён; секреты не требуются.

### PH-003 · P0 · Конфигурация и секреты

**Результат:** dev и production параметры валидируются при старте.

**Приёмка:** есть `.env.example`; production не стартует с placeholder-секретами; token/password никогда не логируются.

## M1 — доверенная Telegram-сессия

### PH-101 · P0 · Проверка `initData`

**Результат:** backend доверяет только свежим данным Telegram.

**Приёмка:** HMAC соответствует официальному алгоритму; используется constant-time compare; отсутствующий/битый hash и `auth_date` старше 24 часов дают `401`; из `user` извлекается только integer `id`.

### PH-102 · P0 · User schema и Alembic baseline

**Зависит от:** PH-003.

**Приёмка:** чистая БД мигрирует до head; `telegram_id` уникален; имя/username/avatar/language отсутствуют; timezone имеет безопасный default `UTC`.

### PH-103 · P0 · `POST /api/v1/session`

**Зависит от:** PH-101, PH-102.

**Приёмка:** idempotent upsert; timezone проверяется через IANA database и обновляется на каждом открытии; ответ не раскрывает Telegram PII.

### PH-104 · P0 · Telegram frontend adapter

**Приёмка:** production берёт raw `initData`; обычный браузер использует явный dev mock; приложение вызывает `ready()`/`expand()`; timezone отправляется с fallback `UTC`.

### PH-105 · P0 · Bot `/start` и webhook

**Приёмка:** `/start` возвращает мягкое приветствие и кнопку открытия; webhook проверяет secret header и не пишет update body в лог.

## M2 — зашифрованная похвала end-to-end

### PH-201 · P0 · Client key lifecycle

**Приёмка:** генерируется extractable AES-256-GCM key; storage adapter умеет get/set; повторный запуск использует тот же key; ошибки storage имеют понятный recovery экран; key никогда не уходит в network calls.

### PH-202 · P0 · Recovery phrase v1

**Зависит от:** PH-201.

**Приёмка:** экспорт и импорт имеют versioned format и checksum; фраза показывается только по явному действию; импорт проверяется round-trip тестом.

### PH-203 · P0 · Praise schema и миграция

**Приёмка:** `body_ciphertext BYTEA`, `iv BYTEA`, server-owned `local_date`, timestamps и индекс `(user_id, local_date)`; plaintext column отсутствует.

### PH-204 · P0 · Создание записи и daily star transaction

**Зависит от:** PH-203, PH-301.

**Приёмка:** запись, ledger и balance меняются в одной транзакции; конкурентные запросы начисляют не более одной daily star; payload более 4 KiB даёт `413`; дата клиента не принимается.

### PH-205 · P0 · Composer UI

**Приёмка:** trim length 4–500, есть хотя бы одна Unicode-буква; до валидности кнопка спокойно disabled без красной ошибки; save делает один API round-trip; success-state не удерживает пользователя.

### PH-206 · P0 · Чтение записей дня

**Приёмка:** API проверяет ownership; frontend расшифровывает локально; повреждённый ciphertext не ломает весь день и объясняет, что запись не удалось открыть.

## M3 — календарь, просмотр и изменения

### PH-301 · P0 · Star ledger

**Приёмка:** append-only ledger; partial unique index для `(user_id, local_date)` при `reason='daily'`; баланс нельзя сделать отрицательным.

### PH-302 · P0 · Calendar API

**Приёмка:** bounded `from/to`; только distinct dates и count; нет ciphertext; запрос использует индекс; месяц с несколькими записями считает один отмеченный день.

### PH-303 · P0 · Мобильный календарь

**Приёмка:** месяцы листаются; 28–31 день не ломает сетку; выбранный день доступен с клавиатуры/screen reader; подпись — «⭐ N в месяце», без streak wording.

### PH-304 · P0 · Редактирование записи

**Приёмка:** разрешено для прошлых дат; меняются ciphertext/iv и `updated_at`; звезда не начисляется; ownership обязателен.

### PH-305 · P0 · Удаление записи

**Приёмка:** удаляется только собственная запись; daily star не отзывается; подтверждение нейтральное и отменяемое до запроса.

## M4 — коллекция без давления

### PH-401 · P0 · Каталог маскотов

**Приёмка:** 4–6 маскотов имеют стабильные code; пользователь бесплатно выбирает одного starter; seed idempotent; asset paths существуют во frontend image.

### PH-402 · P0 · Пороговые разблокировки

**Приёмка:** пороги 10/30/100 по числу заработанных daily-звёзд проверяются после создания записи в той же транзакции; повторная проверка idempotent; ответ create содержит `newly_unlocked`.

### PH-403 · P0 · Покупка и выбор маскота

**Приёмка:** row lock/atomic update исключает двойное списание; повторная покупка не списывает баланс; активировать можно только owned mascot.

### PH-404 · P1 · Экран коллекции

**Приёмка:** состояния `owned/affordable/locked`; нет таймеров и scarcity; характеры маскотов поддерживают tone of voice.

### PH-405 · P1 · Admin-команда добавления маскота

**Цель:** владелец проекта добавляет нового маскота из личного чата с Telegram-ботом без изменения кода, пересборки frontend и ручной правки БД.

**Интерфейс:** PNG отправляется как документ с подписью `/add_mascot <code> <unlock_threshold> | <name> | <blurb>`. Команда принимается только в личном чате от Telegram ID из `TELEGRAM_ADMIN_IDS`; для остальных пользователей она недоступна.

**Хранение и выдача:** метаданные и исходный PNG сохраняются в PostgreSQL одной транзакцией; изображение отдаётся через стабильный endpoint `/api/v1/mascots/{code}/image`. `GET /api/v1/mascots` возвращает активный каталог, а frontend использует его вместо зашитого списка, поэтому добавленный маскот появляется без нового deploy.

**Валидация:** `code` соответствует `[a-z][a-z0-9_]{1,31}` и не меняется после создания; `unlock_threshold` — положительное уникальное целое; имя и описание имеют ограниченную длину; принимается только PNG размером до 1 MiB и разрешением 256–1024 px с сохранением alpha-канала. Существующий `code` или порог не перезаписываются.

**Приёмка:** валидная admin-команда создаёт ровно одну запись каталога и возвращает спокойное подтверждение с превью; повторная доставка того же сообщения idempotent и не создаёт дубликат; ошибки формата объясняют, что исправить, без изменения данных; неавторизованный пользователь не может добавить или заменить маскота; новый порог автоматически участвует в PH-402; в логах отсутствуют текст команды, Telegram ID, `file_id` и содержимое изображения; есть тесты happy path, duplicate `code`/порога, битого/слишком большого PNG и запрета для не-admin.

## M5 — мягкие напоминания

### PH-501 · P0 · Reminder state model

**Приёмка:** явно задокументированы переходы `active → dormant → silent`; `/start` отмечает доступность личных сообщений; пользователь может отключить reminders.

### PH-502 · P0 · Выбор кандидатов на 22:00

**Приёмка:** job каждые 10 минут; учитывает IANA timezone/DST; исключает пользователей с записью сегодня; один локальный день не получает два push.

### PH-503 · P0 · Отправка и затухание

**Приёмка:** Telegram rate limit обрабатывается backoff; проигнорированный push переводит в dormant по зафиксированному правилу; через 30 дней ровно один return message, затем silent.

### PH-504 · P1 · Настройки напоминаний

**Приёмка:** мягкий one-time offer для direct Mini App entry; отказ не переспрашивается; тексты не содержат личных записей.

## M6 — onboarding и визуальная полировка

### PH-601 · P0 · Два onboarding экрана

**Приёмка:** не более двух экранов; выбор starter mascot последний; можно продолжить без разрешения на push; повторно не показывается.

### PH-602 · P0 · Design system tokens

**Приёмка:** цвета, type scale, spacing, radii и motion централизованы; light-only решение явно зафиксировано; WCAG contrast проверен для текста и controls.

### PH-603 · P1 · Микроанимации и reduced motion

**Приёмка:** save feedback укладывается примерно в 500–900 ms и не блокирует уход; `prefers-reduced-motion` отключает декоративное движение.

### PH-604 · P0 · Tone-of-voice audit

**Приёмка:** ни в одном UI/push/error тексте нет «серии», «пропустил», «не потеряй», оценки личности или советов от лица психолога.

## M7 — безопасность и запуск

### PH-701 · P0 · Authorization matrix tests

**Приёмка:** для read/update/delete/unlock есть cross-user negative tests; UUID enumeration не раскрывает существование чужого ресурса.

### PH-702 · P0 · Rate limiting и CORS

**Приёмка:** `/session` и create praise ограничены; production CORS допускает только Mini App origin; proxy headers принимаются только от Caddy.

### PH-703 · P0 · Privacy-safe logging

**Приёмка:** Caddy access log выключен либо редактирует IP; backend structured logs содержат request id/method/path/status/duration, но не auth header/body/ciphertext/telegram_id.

### PH-704 · P0 · Backup и restore drill

**Приёмка:** encrypted daily dump уходит во внешнее хранилище; retention описан; восстановление на пустую БД реально выполнено и протокол сохранён.

**PH-704A · закрытая альфа:** реализация локального зашифрованного backup и
изолированного restore drill подготовлена — см. [`docs/backup.md`](backup.md).
Статус остаётся открытым до первого реального восстановления production-архива.

**PH-704B · публичный запуск:** реализованы выгрузка готового `*.dump.age` в
приватное внешнее S3-совместимое object storage (rclone, отдельный секретный
env, удалённый retention) и off-host restore drill — см.
[`docs/backup.md`](backup.md). Реализация завершена; операционная активация на
production вынесена в PH-707. До её выполнения PH-704 остаётся открытой.

### PH-705 · P0 · Production deploy runbook

**Статус:** выполнено — см. [`docs/deploy.md`](deploy.md).

**Приёмка:** DNS/TLS, webhook setup, migrate-before-start, rollback и health smoke test описаны; backend replicas зафиксированы в `1` из-за APScheduler.

### PH-706 · P0 · Privacy/legal launch gate

**Приёмка:** определены юрисдикция и data residency; опубликованы privacy policy, deletion path и честное объяснение Telegram trust boundary/recovery limitations.

### PH-707 · P0 · Активация offsite backup на production

**Зависит от:** PH-704B (реализация), PH-705 (production VPS).

**Результат:** зашифрованные архивы реально уходят с VPS в приватный S3 bucket и восстанавливаются из него без VPS.

**Конфигурация:** выбран провайдер и создан приватный S3-совместимый bucket с выключенным public access и зафиксированным регионом (ЕС); access key имеет права только на `BUCKET/PREFIX/*` (Put/Get/Delete) и `ListBucket` по префиксу. На production VPS установлены `rclone`, файл `/etc/pohvali-backup/offsite.env` (root, 0600) и обновлённые root-owned копии `backup.sh`/`offsite-common.sh` с unit; `POHVALA_OFFSITE_ENABLED=1`. Секреты не покидают сервер и не попадают в логи/репозиторий.

**Приёмка:** ручной запуск unit'а завершается строками `backup complete` и `offsite upload complete`; в bucket появляются объекты `pohvala-postgres-*.dump.age`, удалённый retention держит заданное число архивов; выполнен первый реальный off-host restore drill из внешнего хранилища при недоступном VPS и записан в протокол [`docs/backup.md`](backup.md); после этого PH-704 закрывается целиком.

## Рекомендуемые релизы

- **R0 / Foundation:** PH-001…105.
- **R1 / Closed alpha:** PH-201, 203…206, 301…305, 601, 602, 604, 701–703.
- **R2 / MVP:** PH-202, 401–403, 501–503, 704–707.
- **R2.1:** задачи P1 после обратной связи закрытой группы.
