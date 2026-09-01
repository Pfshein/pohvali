# Дизайн: поднятие проекта в одну команду

**Дата:** 2026-09-01
**Статус:** утверждён, готов к плану

## Цель

Свести поднятие всего стека (локально и на VPS) к одной каноничной команде:

```
docker compose up -d --build
```

Сейчас это 5 ручных шагов (build → up postgres → `alembic upgrade head` → сид
маскотов → up остального). Затык — миграции и сид каталога маскотов выполняются
вручную вне `up`. Разница между окружениями должна оставаться только в `.env`.

## Решения (зафиксированы при брейншторме)

- **Окружения:** один и тот же `up -d --build` работает и локально, и на сервере.
- **Сборка:** каноничная команда — `docker compose up -d --build` (сборка на
  самой машине, совпадает с текущим git-clone деплоем; registry/CI-образы не
  вводим).
- **Миграции + сид:** отдельный one-shot сервис `migrate`, а не entrypoint в
  backend. app-контейнер остаётся чистым.
- **Webhook:** регистрация Telegram webhook остаётся отдельной командой на проде,
  в `up -d` не входит.

## Изменения в `compose.yaml`

### 1. Новый one-shot сервис `migrate`

- Собирается из того же контекста, что `backend` (`build: context: ./backend`).
- `command: ["sh", "-c", "alembic upgrade head && python -m app.modules.mascots.seed"]`
- `depends_on: postgres → condition: service_healthy`
- `restart: "no"` — отрабатывает и выходит с кодом 0.
- Использует общий блок env (см. п.3).

Оба шага идемпотентны:
- `alembic upgrade head` — no-op, если схема уже на head;
- сид использует `insert(...).on_conflict_do_update(...)` по `Mascot.code`.

Поэтому повторный прогон на каждый `up` безопасен.

### 2. `backend` зависит от `migrate`

```yaml
depends_on:
  postgres:
    condition: service_healthy
  migrate:
    condition: service_completed_successfully
```

uvicorn стартует только после успешно применённых миграций. Если `migrate`
завершился с ненулевым кодом — backend не поднимается (fail fast, а не работа на
несогласованной схеме).

### 3. Дедуп env через YAML-якорь

Общий блок переменных backend выносится в якорь и переиспользуется в `migrate` и
`backend`:

```yaml
x-backend-env: &backend-env
  APP_ENV: ${APP_ENV:-development}
  APP_DOMAIN: ${APP_DOMAIN:-http://localhost}
  BOT_TOKEN: ${BOT_TOKEN:-dev-token}
  TELEGRAM_WEBHOOK_SECRET: ${TELEGRAM_WEBHOOK_SECRET:-dev-webhook-secret}
  TELEGRAM_WEBHOOK_PATH: ${TELEGRAM_WEBHOOK_PATH:-dev-webhook-path}
  DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://pohvala:pohvala@postgres:5432/pohvala}
  CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost,http://localhost:5173}
```

`migrate` использует `environment: *backend-env`; `backend` — то же самое. При
необходимости `migrate` может ограничиться подмножеством (минимум —
`DATABASE_URL`), но переиспользование общего якоря проще и не хранит секретов
лишнего.

## Что НЕ меняется

- Сервисы `caddy`, `frontend`, `postgres`, их healthcheck'и, logging.
- Требование ровно одной реплики `backend` (внутри APScheduler напоминаний).
- Регистрация webhook (`scripts/set_telegram_webhook.py`) — отдельная команда на
  проде, запускается один раз после того, как HTTPS поднялся, и при смене
  домена/пути.

## Итоговый порядок при `docker compose up -d --build`

```
build образов
  → postgres        (ждём healthy)
  → migrate         (alembic upgrade head + seed, ждём exit 0)
  → backend         (ждём healthy)
  → frontend, caddy
```

`up -d` возвращает управление после того, как зависимости удовлетворены; `migrate`
остаётся в состоянии `exited (0)` — это нормально для one-shot.

## Документация

- `docs/deploy.md`:
  - «Первый запуск» (раздел 6): 5 команд → `docker compose up -d --build`
    (миграции и сид теперь автоматические). Webhook (раздел 7) остаётся отдельно.
  - «Обновление production» (раздел 9): убрать ручные `up -d postgres`,
    `alembic upgrade head`, сид — оставить `git merge --ff-only`, затем
    `docker compose up -d --build`.
  - «Откат» (раздел 10): `build` + `up -d` → `up -d --build`.
- `README.md` / локальный quickstart: `cp .env.example .env` →
  `docker compose up -d --build`.

## Проверка

- `docker compose config --quiet` — конфиг валиден, якоря раскрываются, секреты не
  печатаются.
- Локальный `docker compose up -d --build`:
  - `migrate` завершился с кодом 0 (`docker compose ps` показывает exited 0);
  - `docker compose ps` — postgres/backend healthy, caddy/frontend up;
  - `curl -fsS http://localhost/api/v1/health` → `{"status":"ok"}`.
- Повторный `up -d --build` без изменений схемы — `migrate` отрабатывает как no-op,
  стек остаётся здоровым (проверка идемпотентности).

## Заметки по тестируемости

Инфраструктурное изменение — юнит-тестами не покрывается. Верификация —
`docker compose config` и реальный `up -d --build` локально (см. «Проверка»).
Существующие backend/frontend тесты не затрагиваются.
