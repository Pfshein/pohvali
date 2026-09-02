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

**Статус:** выполнено — команда `/add_mascot <code> <порог> | <Имя> | <Описание>`
с PNG-документом обрабатывается webhook'ом для Telegram ID из
роли `admin` в PostgreSQL; PNG (≤1 MiB, 256–1024 px, alpha) хранится в БД, картинка
отдаётся по `/api/v1/mascots/{code}/image`, каталог подхватывает нового маскота
без deploy. Инструкция — в [`docs/deploy.md`](deploy.md), § 11.

**Цель:** владелец проекта добавляет нового маскота из личного чата с Telegram-ботом без изменения кода, пересборки frontend и ручной правки БД.

**Интерфейс:** PNG отправляется как документ с подписью `/add_mascot <code> <unlock_threshold> | <name> | <blurb>`. Команда принимается только в личном чате пользователем с ролью `admin`; для остальных пользователей она недоступна.

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

**Статус:** выполнено — one-time offer при прямом входе (`?from=reminder`
отличает вход из напоминания), ответ фиксируется локально и не переспрашивается;
в приложении есть секция «Напоминания» с переключателем на `GET/PUT
/api/v1/reminders` и честной подсказкой про чат с ботом при `dm_available=false`.

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

**Статус:** выполнено — privacy policy публикуется по `/privacy.html`
(генерируется из `frontend/src/lib/privacy-policy.ts`; тот же текст читается
внутри приложения, без перехода на внешнюю страницу), удаление данных
реализовано эндпоинтом `DELETE /api/v1/session` и панелью
«Приватность и данные» в приложении,
юрисдикция и data residency зафиксированы в [`docs/deploy.md`](deploy.md),
раздел 12 (VPS и bucket в ЕС).

**Приёмка:** определены юрисдикция и data residency; опубликованы privacy policy, deletion path и честное объяснение Telegram trust boundary/recovery limitations.

### PH-707 · P0 · Активация offsite backup на production

**Зависит от:** PH-704B (реализация), PH-705 (production VPS).

**Результат:** зашифрованные архивы реально уходят с VPS в приватный S3 bucket и восстанавливаются из него без VPS.

**Конфигурация:** выбран провайдер и создан приватный S3-совместимый bucket с выключенным public access и зафиксированным регионом (ЕС); access key имеет права только на `BUCKET/PREFIX/*` (Put/Get/Delete) и `ListBucket` по префиксу. На production VPS установлены `rclone`, файл `/etc/pohvali-backup/offsite.env` (root, 0600) и обновлённые root-owned копии `backup.sh`/`offsite-common.sh` с unit; `POHVALA_OFFSITE_ENABLED=1`. Секреты не покидают сервер и не попадают в логи/репозиторий.

**Приёмка:** ручной запуск unit'а завершается строками `backup complete` и `offsite upload complete`; в bucket появляются объекты `pohvala-postgres-*.dump.age`, удалённый retention держит заданное число архивов; выполнен первый реальный off-host restore drill из внешнего хранилища при недоступном VPS и записан в протокол [`docs/backup.md`](backup.md); после этого PH-704 закрывается целиком.

### PH-708 · P0 · Anti-abuse hardening без CAPTCHA

**Зависит от:** PH-101, PH-105, PH-702.

**Цель:** автоматизированный Telegram-аккаунт, повтор валидного `initData` или
прямой HTTP-флуд не должны бесконтрольно нагружать backend и увеличивать БД.
Telegram-подпись подтверждает аккаунт, но не доказывает, что запрос сделал
человек; CAPTCHA в спокойный пользовательский сценарий не добавляется.

**Границы:** защита остаётся внутри текущих Caddy и одного backend-процесса,
без Redis, стороннего anti-bot SDK, собственного auth-токена и хранения либо
логирования IP. Volumetric DDoS, фильтрация на стороне VPS-провайдера/CDN и
компрометация bot token не входят в задачу.

**Ingress и перегрузка:** Caddy и ранний ASGI middleware отклоняют тело любого
`/api/*` запроса больше 1 MiB с `413` до JSON parsing и вызова endpoint. Лимит
зашифрованной похвалы 4 KiB остаётся отдельной доменной проверкой. Общий
process-wide overload guard ограничивает суммарную частоту и число одновременно
обрабатываемых API-запросов; при насыщении быстро отвечает `429`/`503`, не
открывая сессию PostgreSQL. Порог выбирается выше нормальной нагрузки и
фиксируется константой с тестом, чтобы защита не зависела от IP.

**Лимиты Telegram-пользователя:** после проверки `initData` действуют общие
корзины на Telegram ID, а не независимый лимит каждого endpoint: `/session` —
30 запросов/мин, все пользовательские чтения вместе — 120/мин, все мутации
вместе — 60/мин; для покупки/активации маскота и настройки напоминаний можно
сохранить более строгий предел 30/мин. В лимит включаются ранее не защищённые
чтение календаря/похвал, edit и delete. Ответ содержит `429` и корректный
`Retry-After`. In-memory limiter удаляет просроченные ключи и имеет фиксированную
верхнюю границу памяти; рестарт backend по-прежнему может сбросить окна, что
приемлемо для одного MVP-инстанса.

**Защита хранилища:** у пользователя одновременно хранится не более 100 похвал
на одну server-owned `local_date`. Проверка выполняется в транзакции под
per-user row lock до insert, поэтому конкурентные запросы не обходят лимит;
лишний запрос получает `429` без записи, звезды и других side effects. Удаление
освобождает место; это ограничение объёма хранилища, а не механика прогресса и
не показывается в обычном UI.

**Webhook:** успешно обработанный Telegram `update_id` запоминается в
ограниченном TTL/LRU-кэше; повторная доставка получает `200` без второго ответа
и side effects. `/start` и прочие обрабатываемые команды имеют спокойный
per-actor лимит, неавторизованные admin-команды не запускают скачивание файлов
или тяжёлые DB-операции. `setWebhook` задаёт `max_connections=10`, чтобы Telegram
не создавал backend резкий входящий burst. Секретный path и
`X-Telegram-Bot-Api-Secret-Token` остаются обязательными.

**Приёмка:** oversized body с `Content-Length` и chunked body дают `413`; общий
guard отклоняет перегрузку до DB dependency; shared read/write buckets нельзя
обойти переключением endpoint; каждый `429` содержит `Retry-After`; TTL/LRU
limiter не растёт бесконечно; 100 конкурентных create допустимы, 101-й не
создаёт praise/star/unlock; повтор одного `update_id` не отправляет второе
сообщение; webhook setup передаёт `max_connections=10`; production CORS,
privacy-safe logs и существующие authorization tests остаются зелёными.

## M8 — фундамент админ-панели

### PH-801 · P1 · Роли пользователей и admin-авторизация

**Статус:** выполнено; backend PostgreSQL CI, frontend и quality gates зелёные. Подробный дизайн:
[`docs/superpowers/specs/2026-09-02-user-roles-admin-authorization-design.md`](superpowers/specs/2026-09-02-user-roles-admin-authorization-design.md),
пошаговая реализация:
[`docs/superpowers/plans/2026-09-02-user-roles-admin-authorization.md`](superpowers/plans/2026-09-02-user-roles-admin-authorization.md).

**Цель:** заменить feature-specific список admin IDs одной серверной
моделью ролей. Каждый аккаунт имеет роль `user` или `admin` в PostgreSQL;
Telegram подтверждает личность, а полномочия всегда проверяет backend по БД.

**Границы:** миграция роли, CLI назначения/снятия admin, общий FastAPI guard,
поле role в session contract и перевод `/add_mascot` на DB-role. Визуальная
админ-панель, список пользователей и HTTP-управление ролями не входят.

**Приёмка:** существующие и новые аккаунты безопасно получают `user`; обычная
сессия не может изменить роль; CLI идемпотентно меняет роль только существующей
строке; user/неизвестный получают одинаковый `403` от admin guard;
`/add_mascot` работает только для DB-admin и не скачивает файл для остальных;
старый список admin IDs удалён из runtime-конфигурации; backend, DB integration и
frontend quality gates зелёные.

### PH-802 · P1 · Админская статистика `/stats`

**Статус:** выполнено; backend PostgreSQL CI, frontend и quality gates зелёные.
Пошаговая спецификация:
[`docs/superpowers/plans/2026-09-02-admin-stats-command.md`](superpowers/plans/2026-09-02-admin-stats-command.md).

**Цель:** дать DB-администратору агрегированную продуктовую статистику через
Telegram-команду `/stats`, не раскрывая содержимое похвал и Telegram PII.

**Границы:** дневная активность пользователей, уникальные открытия, авторы и
количество похвал, конверсия за сегодня/7/30 дней и за всё время. Команда
доступна только DB-admin в личном чате; web-admin UI и сторонний analytics SDK
не входят.

**Приёмка:** успешный `/session` атомарно отмечает UTC-день активности;
повторные и конкурентные открытия не создают дубликатов; удаление аккаунта
каскадно удаляет активность; `/stats` и `/stats 30` возвращают только агрегаты;
user/неизвестный получают одинаковый отказ; групповые команды игнорируются;
PostgreSQL integration и остальные quality gates зелёные.

### PH-803 · P1 · Единый deploy-скрипт (bootstrap + релиз + откат)

**Статус:** в работе. Пошаговый план:
[`docs/superpowers/plans/2026-09-02-deploy-script.md`](superpowers/plans/2026-09-02-deploy-script.md).

**Цель:** свести и первый запуск, и каждый последующий релиз на VPS к одной
команде `sudo ./scripts/deploy.sh` поверх Docker Compose. Скрипт знает специфику
проекта: секреты, production `.env`, Telegram, тегированную по SHA раскатку с
безопасным откатом, бэкап перед миграцией, healthcheck, статус.

**Границы:** bootstrap (генерация секретов, атомарный `.env` 600, производные
значения, `getMe`/webhook/menu button, назначение первого админа через
существующий `set_role`); релиз из `main` (flock, dirty-guard, ff-only, бэкап
перед миграцией, пересборка+миграции, повторная проверка webhook без сброса
pending); тегирование образов по git SHA;
подкоманды `status`, `logs`, `rollback` (только код/образы, без авто-downgrade
БД), отдельный `rotate-secrets`; перенос Telegram-настройщика внутрь
backend-пакета. НЕ входят: `vX.Y.Z`/changelog/GitHub Releases, публикация
образов в registry, автозапуск деплоя из GitHub Actions → SSH.

**Приёмка:** на чистом VPS `sudo ./scripts/deploy.sh` проходит bootstrap до
зелёных health и HTTPS с настроенным webhook/menu; повторный запуск без новых
коммитов — no-op, не перегенерирует секреты и не перезаписывает `.env`; новый
зелёный коммит в `main` выкатывается тем же вызовом (ff-only, `setWebhook` без
`drop_pending_updates`); `rollback` возвращает предыдущие образы без пересборки
и останавливается при несовместимой схеме; `status`/`logs` не раскрывают
секретов; ротация секретов — только явной подкомандой.

## Рекомендуемые релизы

- **R0 / Foundation:** PH-001…105.
- **R1 / Closed alpha:** PH-201, 203…206, 301…305, 601, 602, 604, 701–703.
- **R2 / MVP:** PH-202, 401–403, 501–503, 704–708.
- **R2.1:** задачи P1 после обратной связи закрытой группы.
- **R3 / Admin foundation:** PH-801 и последующие задачи admin UI.
