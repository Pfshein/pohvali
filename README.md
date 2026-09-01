# Похвали себя

Telegram Mini App, где человек за 15–20 секунд замечает, за что может похвалить себя сегодня.

## Сейчас в репозитории

- React + TypeScript + Vite frontend shell;
- FastAPI backend с `/health`, проверкой Telegram `initData`, `POST /api/v1/session` и Telegram webhook (`/start`);
- PostgreSQL, Caddy и четыре сервиса в Docker Compose;
- unit-тесты для локальной валидации, AES-GCM и Telegram-подписи;
- приоритизированный backlog MVP с критериями приёмки.

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и замените секреты.
2. Соберите образы: `docker compose build`.
3. Примените схему: `docker compose run --rm backend alembic upgrade head`.
4. Запустите сервисы: `docker compose up -d`.
5. Откройте `http://localhost`.
6. Backend healthcheck доступен по `http://localhost/api/v1/health`.

Для быстрой разработки интерфейса без Telegram:

```powershell
cd frontend
npm install
npm run dev
```

Локальный Vite использует `VITE_TELEGRAM_MODE=mock` из `frontend/.env.development`. Для
локального Compose задайте то же значение в корневом `.env`. Адаптер создаёт только
фиксированного fake-пользователя и подписывает его публичным placeholder-токеном `dev-token`;
реальные Telegram-данные для этого не нужны. Если в локальном `.env` заменён `BOT_TOKEN`,
browser mock следует отключить либо вернуть backend placeholder `dev-token`.

Для production используется безопасное значение по умолчанию `VITE_TELEGRAM_MODE=telegram`.
В этом режиме приложение берёт неизменённый `window.Telegram.WebApp.initData`, вызывает
`ready()`/`expand()` и не содержит browser-dev credentials в bundle.

## Проверки

Frontend quality gate:

```powershell
cd frontend
npm ci
npm run check
```

Backend quality gate:

```powershell
cd backend
python -m pip install -e ".[dev]"
ruff check .
pytest
```

GitHub Actions автоматически запускает обе независимые проверки для pull request и push в
`main`. Backend-job поднимает изолированный PostgreSQL `pohvala_test`, применяет миграции и
запускает также DB-интеграционные тесты (`RUN_DATABASE_TESTS=1`). Секреты приложения для CI
не требуются.

После первого запуска workflow в GitHub для ветки `main` нужно включить branch protection или
ruleset с правилом **Require status checks to pass** и выбрать проверки `Frontend` и `Backend`.
Именно эта настройка запрещает merge при красном CI; она хранится в GitHub, а не в репозитории.

## Миграции базы данных

После запуска PostgreSQL примените миграции до старта новой версии backend:

```powershell
docker compose run --rm backend alembic upgrade head
```

Текущую ревизию можно проверить командой:

```powershell
docker compose run --rm backend alembic current
```

В production миграции выполняются отдельным шагом между сборкой образов и
`docker compose up -d`. Приложение не вызывает `create_all()` и не изменяет схему при старте.

Не выполняйте `alembic downgrade base` в production: baseline downgrade удаляет таблицу
`users` вместе с данными. Для отката приложения сохраняйте совместимость схемы и делайте
forward-fix; восстановление схемы и данных выполняйте только из проверенного backup.

## Telegram-сессия

`POST /api/v1/session` принимает подписанный Telegram payload в заголовке и актуальную
IANA-таймзону в JSON-теле:

```http
Authorization: tma <initDataRaw>
Content-Type: application/json

{"timezone":"Europe/Moscow"}
```

Успешный ответ содержит только внутренний UUID и сохранённую таймзону:

```json
{"id":"0ecaf26f-ee72-4f06-ae79-41198dd1ac6d","timezone":"Europe/Moscow"}
```

Повторный запрос с тем же Telegram ID возвращает того же пользователя и обновляет таймзону.
Имя, username, язык, аватар и исходный `initData` не сохраняются и не возвращаются. Неверная
Telegram-подпись даёт `401`, неизвестная таймзона — `422`.

## Создание записи

`POST /api/v1/praises` принимает уже зашифрованный на клиенте блоб — сервер не видит
и не хранит открытый текст:

```http
Authorization: tma <initDataRaw>
Content-Type: application/json

{"body_ciphertext":"<base64>","iv":"<base64>"}
```

Дату записи вычисляет backend из сохранённой таймзоны пользователя — клиент её не передаёт
(любое поле даты в теле игнорируется). `iv` должен декодироваться ровно в 12 байт, шифртекст
не может быть пустым и больше 4 KiB (иначе `413`). Запись, начисление звезды и баланс меняются
в одной транзакции; за первую запись локального дня начисляется одна звезда, повторные записи
того же дня звезду не добавляют. Ответ:

```json
{"id":"…","local_date":"2026-09-01","star_awarded":true,"balance":10,"newly_unlocked":["tisha"]}
```

## Фраза восстановления

На главном экране действие **«Доступ к записям»** позволяет явно показать фразу текущего
ключа или ввести ранее сохранённую. Фраза имеет формат
`pohvala-v1.<base64url-key>.<checksum>`; checksum — первые 64 бита SHA-256 от версии и ключа.
До показа пользователь должен отдельно нажать **«Показать мою фразу»**.

Экспорт и импорт выполняются только во frontend через Web Crypto. Фраза и AES-ключ не
отправляются в API и не пишутся в backend-логи. При импорте сначала проверяются версия,
структура и checksum, и лишь затем ключ сохраняется через тот же storage adapter, который
используется при первом запуске. Импорт заменяет ключ на текущем устройстве.

## Чтение записей дня

`GET /api/v1/praises?date=YYYY-MM-DD` возвращает записи **только текущего пользователя** за
указанный день (без `date` — за сегодня по таймзоне пользователя). Ответ содержит лишь
`id`, `local_date`, `created_at` и зашифрованные `iv`/`body_ciphertext` (base64) — сервер не
расшифровывает. Клиент расшифровывает каждую запись локально; повреждённый шифртекст одной
записи помечается как нечитаемый и не ломает остальной день (см. `loadDay` в
`frontend/src/lib/praise-api.ts`).

## Редактирование и удаление

`PATCH /api/v1/praises/{id}` меняет шифртекст/`iv` собственной записи (тело как у
создания; `updated_at` обновляется, звезда не начисляется).
`DELETE /api/v1/praises/{id}` удаляет собственную запись; начисленная за день звезда не
отзывается. Обе операции строго проверяют владельца: чужой или несуществующий `id` даёт
одинаковый `404` (без раскрытия существования ресурса). Клиентские помощники — `editPraise` и
`deletePraise` в `frontend/src/lib/praise-api.ts`.

## Каталог маскотов

PH-401 добавляет шесть маскотов со стабильными кодами и ассетами в
`frontend/public/assets/mascots`. Ава, Поль и Мира доступны как бесплатный стартовый выбор;
Тиша, Луми и Бим подготовлены для последующих разблокировок. Миграция создаёт и наполняет
таблицу `mascots`; повторно синхронизировать каталог безопасно командой
`docker compose run --rm backend python -m app.modules.mascots.seed`.

Пороговые маскоты открываются по общему числу заработанных daily-звёзд: Тиша на 10, Луми
на 30, Бим на 100. Текущий расходуемый баланс на разблокировку не влияет, поэтому будущая
покупка не закрывает уже доступного спутника. Проверка и запись в `mascot_unlocks` выполняются
в транзакции создания похвалы; новые коды возвращаются в `newly_unlocked`.

## Покупка и выбор маскота

`GET /api/v1/mascots` возвращает каталог с состоянием для текущего пользователя и его
расходуемый баланс:

```json
{
  "balance": 12,
  "active_mascot": "ava",
  "mascots": [
    {"code": "ava", "starter": true, "price": null, "state": "owned", "unlocked": true, "active": true},
    {"code": "tisha", "starter": false, "price": 10, "state": "affordable", "unlocked": true, "active": false}
  ]
}
```

Состояния: `owned` (starter — бесплатно у всех — или уже купленный), `affordable`
(порог достигнут и хватает баланса), `locked` (порог ещё не достигнут либо не хватает звёзд).

`POST /api/v1/mascots/{code}/purchase` покупает не-starter маскота за `unlock_threshold` звёзд.
Списание баланса, запись владения и запись в ledger (`reason='purchase'`) выполняются в одной
транзакции. Строка баланса блокируется через `SELECT … FOR UPDATE` до проверки владения, поэтому
конкурентные запросы не могут потратить одни и те же звёзды дважды. Повторная покупка идемпотентна
и не списывает баланс (`newly_purchased=false`). Пока порог не достигнут — `409` (locked); при
нехватке звёзд — `409` (insufficient). Заработанные daily-звёзды (пороги PH-402) не расходуются
при покупке — списывается только `balance`.

`PUT /api/v1/mascots/{code}/active` делает маскота активным. Активировать можно только owned
(starter или купленного); иначе `409`. Выбор хранится в `users.active_mascot_code`.

Экран коллекции (`frontend/src/components/Collection.tsx`) показывает эти же состояния:
`owned` (бейдж «Рядом сейчас» или кнопка «Выбрать»), `affordable` (кнопка «Открыть за ⭐N»)
и `locked` (спокойная подсказка о пороге). Без таймеров и scarcity-формулировок. Данные и
действия идут через `frontend/src/lib/mascots-api.ts`; контейнер `CollectionPanel` грузит каталог
и обновляет его после покупки или выбора. Активный выбор сразу обновляет маскота главного экрана
и сохраняется одновременно в backend и Telegram CloudStorage/localStorage.

## Календарь

`GET /api/v1/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD` возвращает отмеченные дни текущего
пользователя за диапазон: `[{ "local_date": "2026-09-01", "count": 3 }, …]`. Оба параметра
обязательны, диапазон ограничен 366 днями (иначе `422`). В ответе нет содержимого записей —
только даты и число записей за день (несколько записей за день — один отмеченный день).
Запрос использует индекс `(user_id, local_date)`. Клиентский помощник — `loadCalendar` в
`frontend/src/lib/calendar.ts`. Главный экран запрашивает фактический текущий месяц, показывает
реальный баланс из коллекции и расшифровывает записи выбранного дня только в браузере.

## Напоминания

Состояние вечернего напоминания живёт в таблице `reminder_states` (одна строка на пользователя,
PH-501). Затухание однонаправленное и задокументировано в `app/modules/reminders/state.py`:

```
active ──(напоминание проигнорировано)──▶ dormant ──(окно затухания прошло)──▶ silent
```

`active` — обычный мягкий нудж в 22:00; `dormant` — после проигнорированного пуша ритм снижается;
`silent` — после окна затухания бот присылает одно спокойное возвращающее сообщение и больше не
напоминает. Само затухание назад не идёт; выйти из `dormant`/`silent` можно только повторным
вовлечением (сброс в `active`). Триггеры затухания применяют PH-502/PH-503; здесь — только модель
и разрешённые переходы.

Приватный `/start` отмечает, что боту можно писать пользователю (`dm_available=true`); строка
пользователя при этом создаётся, если её ещё нет, и сохранённая timezone не перезаписывается.
`GET /api/v1/reminders` возвращает `{enabled, dm_available}`; `PUT /api/v1/reminders`
(`{"enabled": false}`) позволяет пользователю выключить напоминания. Отключение не сбрасывает
`dm_available`. Тексты и Telegram-id в логи не попадают.

**Выбор кандидатов на 22:00 (PH-502).** Фоновая job (APScheduler) раз в ~10 минут выбирает
кандидатов на вечерний нудж. Кандидат: `enabled`, `dm_available`, фаза `active`, локальное время
в часе 22:xx (через IANA timezone с учётом DST), сегодня ещё не напоминали (`last_reminded_on`) и
сегодня нет записи. Дедуп по локальной дате гарантирует, что за локальный день уходит не больше
одного пуша, даже при шести прогонах в течение часа. Селекция — `select_reminder_candidates` в
`app/modules/reminders/service.py`; планировщик — `scheduler.py` (запускается в lifespan везде,
кроме тестов). Job — in-process, поэтому backend должен быть в одном экземпляре (PH-705).

**Отправка и затухание (PH-503).** `deliver_reminders` (`app/modules/reminders/delivery.py`)
за один прогон превращает состояние каждого доступного пользователя в действие:

- `daily` — активному пользователю уходит вечерний нудж;
- `fade` — активный проигнорировал предыдущий пуш (нет записи в тот локальный день) → переходит в
  `dormant`, сообщение не отправляется;
- `return` — пользователю, пробывшему в `dormant` 30 дней, уходит **ровно одно** спокойное
  возвращающее сообщение, затем `silent`.

`silent`, уже обработанные сегодня и написавшие сегодня — не трогаются. Повторное вовлечение
(создание записи) сбрасывает фазу в `active` в той же транзакции `create_praise`
(`reactivate_on_praise`). Отправка учитывает Telegram rate limit: `send_with_backoff` уважает
`retry_after` с backoff, и состояние (`last_reminded_on`/фаза) двигается только после успешной
отправки — заглушённый пуш повторяется на следующем прогоне, а не теряется. Тексты нудж/return —
в `app/modules/bot/messages.py`, без формулировок о сериях, пропущенных днях и давлении. Если
Telegram сообщает, что бот заблокирован, `dm_available` сбрасывается; прочие ошибки одной
отправки не останавливают обработку остальных пользователей.

## Безопасность и логирование

- **Авторизация.** Каждый пользовательский запрос требует свежий Telegram `initData`; чужой или
  несуществующий `id` записи даёт одинаковый `404` (без раскрытия существования). См. матрицу в
  `backend/tests/test_authorization_matrix.py`.
- **Rate limit.** `POST /session` (30/мин), `POST /praises` (60/мин), запись маскотов
  (`purchase`/`active`, 30/мин) и `PUT /reminders` (30/мин) ограничены in-memory лимитером по
  Telegram-id (один инстанс backend, без Redis); превышение — `429`.
- **CORS.** В production приложение не стартует, если `CORS_ORIGINS` содержит не-https или localhost
  (допускается только origin Mini App); разрешены все используемые методы, включая `PUT`.
- **Секреты.** Production не стартует с dev/placeholder значениями bot token, webhook secret/path
  или пароля PostgreSQL.
- **Логи.** Caddy access-log отключён (не хранит IP). Backend пишет по одной JSON-строке на запрос:
  `request_id/method/path/status/duration_ms` — без Authorization, тела, ciphertext и telegram_id.
- **Proxy.** Backend не публикует порты наружу (доступен только через Caddy), поэтому forwarded-заголовки
  приходят только от Caddy; клиентский IP приложением не используется.

## Telegram-бот и webhook

Бот отвечает на `/start` в личном чате мягким приветствием и inline-кнопкой, открывающей
Mini App (`web_app` на `APP_DOMAIN`). Другие сообщения и не-личные чаты игнорируются.

Обновления Telegram приходят на `POST /api/v1/telegram/{TELEGRAM_WEBHOOK_PATH}`. Endpoint
защищён двумя слоями: неугадываемый путь и заголовок `X-Telegram-Bot-Api-Secret-Token`,
который сверяется с `TELEGRAM_WEBHOOK_SECRET` в constant-time. Неверный путь даёт `404`,
неверный/отсутствующий secret — `403`. Тело update никогда не пишется в лог (в логе только
числовой `update_id`).

Зарегистрируйте webhook один раз для окружения после того, как backend доступен по HTTPS:

```powershell
cd backend
python ../scripts/set_telegram_webhook.py
```

Скрипт берёт `BOT_TOKEN`, `APP_DOMAIN`, `TELEGRAM_WEBHOOK_PATH` и `TELEGRAM_WEBHOOK_SECRET`
из окружения приложения и запрашивает у Telegram только `message`-обновления.

## Документы

- [Product brief](docs/product-brief.md)
- [Backlog MVP](docs/backlog.md)
- [Definition of Done](docs/definition-of-done.md)
