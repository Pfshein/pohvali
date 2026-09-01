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
`main`. Секреты приложения для CI не требуются.

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
{"id":"…","local_date":"2026-09-01","star_awarded":true,"balance":1}
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

`PATCH /api/v1/praises/{id}` меняет шифртекст/`iv`/`sticker` собственной записи (тело как у
создания плюс необязательный `sticker`; `updated_at` обновляется, звезда не начисляется).
`DELETE /api/v1/praises/{id}` удаляет собственную запись; начисленная за день звезда не
отзывается. Обе операции строго проверяют владельца: чужой или несуществующий `id` даёт
одинаковый `404` (без раскрытия существования ресурса). Клиентские помощники — `editPraise` и
`deletePraise` в `frontend/src/lib/praise-api.ts`.

## Календарь

`GET /api/v1/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD` возвращает отмеченные дни текущего
пользователя за диапазон: `[{ "local_date": "2026-09-01", "count": 3 }, …]`. Оба параметра
обязательны, диапазон ограничен 366 днями (иначе `422`). В ответе нет содержимого записей —
только даты и число записей за день (несколько записей за день — один отмеченный день).
Запрос использует индекс `(user_id, local_date)`. Клиентский помощник — `loadCalendar` в
`frontend/src/lib/calendar.ts`.

## Безопасность и логирование

- **Авторизация.** Каждый пользовательский запрос требует свежий Telegram `initData`; чужой или
  несуществующий `id` записи даёт одинаковый `404` (без раскрытия существования). См. матрицу в
  `backend/tests/test_authorization_matrix.py`.
- **Rate limit.** `POST /session` (30/мин) и `POST /praises` (60/мин) ограничены in-memory лимитером
  по Telegram-id (один инстанс backend, без Redis); превышение — `429`.
- **CORS.** В production приложение не стартует, если `CORS_ORIGINS` содержит не-https или localhost
  (допускается только origin Mini App).
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
