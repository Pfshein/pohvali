# One-Command Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Свести поднятие всего стека (локально и на VPS) к одной команде `docker compose up -d --build`, включая миграции и сид маскотов.

**Architecture:** Добавляем one-shot сервис `migrate` (тот же backend-образ), который прогоняет `alembic upgrade head` + сид и выходит; `backend` стартует через `depends_on: migrate → service_completed_successfully`. Общий блок env выносим в YAML-якорь. Регистрация Telegram webhook остаётся отдельной командой.

**Tech Stack:** Docker Compose, Caddy, FastAPI/uvicorn, Alembic, PostgreSQL.

> **Про коммиты:** по рабочему процессу проекта коммиты делаются только по явной просьбе. Шаги `commit` ниже оставлены как чек-пойнты; фактический `git commit` выполняем в конце, когда пользователь подтвердит. Инфра-задача не покрывается юнит-тестами — вместо red-green используется верификация через `docker compose config` и реальный `up -d --build` (Task 4).

---

## Файловая структура

- `compose.yaml` — добавить якорь `x-backend-env`, сервис `migrate`, зависимость `backend → migrate`. **Единственный функциональный файл.**
- `docs/deploy.md` — упростить разделы 6 (первый запуск), 9 (обновление), 10 (откат).
- `README.md` — упростить «Быстрый старт», отметить авто-миграции/сид.

---

### Task 1: Сервис `migrate` и якорь env в `compose.yaml`

**Files:**
- Modify: `compose.yaml`

- [ ] **Step 1: Добавить якорь `x-backend-env` после блока `x-logging`**

Найти (строки 3-8):

```yaml
x-logging: &default-logging
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

Добавить сразу после него (перед `services:`):

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

- [ ] **Step 2: Добавить сервис `migrate` перед сервисом `backend`**

Вставить между сервисом `frontend` и сервисом `backend`:

```yaml
  migrate:
    image: pohvala-backend:latest
    build:
      context: ./backend
    restart: "no"
    logging: *default-logging
    environment: *backend-env
    command: ["sh", "-c", "alembic upgrade head && python -m app.modules.mascots.seed"]
    depends_on:
      postgres:
        condition: service_healthy
```

- [ ] **Step 3: Переписать сервис `backend` — общий образ, якорь env, зависимость от `migrate`**

Найти текущий блок `backend:` (строки 38-59) и заменить целиком на:

```yaml
  backend:
    image: pohvala-backend:latest
    build:
      context: ./backend
    restart: unless-stopped
    # Keep exactly one replica: APScheduler runs inside this process.
    logging: *default-logging
    environment: *backend-env
    depends_on:
      postgres:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"]
      interval: 10s
      timeout: 3s
      retries: 5
```

Пояснение: `image: pohvala-backend:latest` на обоих сервисах (`migrate` и `backend`) с одинаковым `build.context` гарантирует, что образ собирается один раз и переиспользуется — `migrate` не тянет вторую сборку.

- [ ] **Step 4: Проверить, что конфиг валиден и якоря раскрылись**

Run: `docker compose config`
Expected: команда завершается без ошибок; в выводе у сервисов `migrate` и `backend` виден одинаковый блок `environment` (раскрытый из якоря), у `backend` в `depends_on` присутствует `migrate: condition: service_completed_successfully`, у `migrate` — `command` с `alembic upgrade head && python -m app.modules.mascots.seed`.

- [ ] **Step 5: Commit (чек-пойнт — фактический commit по подтверждению пользователя)**

```bash
git add compose.yaml
git commit -m "feat: one-shot migrate service for single-command startup"
```

---

### Task 2: Упростить `docs/deploy.md`

**Files:**
- Modify: `docs/deploy.md`

- [ ] **Step 1: Раздел «6. Первый запуск» — заменить три блока команд на один**

Найти весь блок раздела 6 (от «Сначала соберите образы...» до строки перед «## 7») и заменить тело на:

````markdown
Одна команда собирает образы, поднимает PostgreSQL, применяет миграции и сид
маскотов (сервис `migrate`) и только затем стартует backend, frontend и Caddy:

```bash
cd /opt/pohvali
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=100 caddy backend migrate
```

Сервис `migrate` — одноразовый: он завершается с кодом 0 после `alembic upgrade
head` и идемпотентного сида каталога маскотов, и `backend` стартует только после
его успешного завершения. В `docker compose ps` он отображается как `exited (0)`
— это нормально.

Не используйте `--scale backend`. Caddy автоматически запросит TLS-сертификат;
DNS и открытые порты 80/443 должны уже указывать на этот VPS.
````

- [ ] **Step 2: Раздел «9. Обновление production» — убрать ручные миграции/сид**

Заменить блок команд раздела 9 на:

```bash
cd /opt/pohvali
git switch main
git fetch origin main
git rev-parse HEAD > .deploy-previous
git merge --ff-only origin/main
sudo docker compose config --quiet
sudo docker compose up -d --build --remove-orphans
sudo docker compose ps
curl -fsS https://app.example.com/api/v1/health
```

Вводный абзац раздела 9 заменить на:

```markdown
Каждый деплой сохраняет SHA предыдущей версии, делает только fast-forward и одной
командой пересобирает образы, применяет миграции и сид (сервис `migrate`) и лишь
затем заменяет работающие контейнеры:
```

- [ ] **Step 3: Раздел «10. Откат» — одна команда сборки+подъёма**

Заменить блок команд раздела 10 на:

```bash
cd /opt/pohvali
git checkout --detach "$(cat .deploy-previous)"
sudo docker compose up -d --build --remove-orphans
sudo docker compose ps
curl -fsS https://app.example.com/api/v1/health
```

- [ ] **Step 4: Проверить, что упоминания ручных шагов ушли**

Run: `grep -n "run --rm backend alembic upgrade head\|run --rm backend python -m app.modules.mascots.seed" docs/deploy.md`
Expected: совпадений НЕТ в разделах 6, 9, 10 (раздел 7 про webhook остаётся с `run --rm ... set_telegram_webhook.py` — это ожидаемо и не трогаем).

- [ ] **Step 5: Commit (чек-пойнт)**

```bash
git add docs/deploy.md
git commit -m "docs: single-command deploy runbook"
```

---

### Task 3: Упростить «Быстрый старт» и заметки в `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Заменить нумерованный список «Быстрый старт» (строки 15-20)**

Найти:

```markdown
1. Скопируйте `.env.example` в `.env` и замените секреты.
2. Соберите образы: `docker compose build`.
3. Примените схему: `docker compose run --rm backend alembic upgrade head`.
4. Запустите сервисы: `docker compose up -d`.
5. Откройте `http://localhost`.
6. Backend healthcheck доступен по `http://localhost/api/v1/health`.
```

Заменить на:

```markdown
1. Скопируйте `.env.example` в `.env` и замените секреты. Для локального запуска
   держите `APP_DOMAIN=http://localhost` (иначе Caddy локально попытается выпустить
   TLS-сертификат для внешнего домена).
2. Поднимите всё одной командой: `docker compose up -d --build`. Она собирает
   образы, применяет миграции и сид маскотов (сервис `migrate`) и стартует стек.
3. Откройте `http://localhost`.
4. Backend healthcheck доступен по `http://localhost/api/v1/health`.
```

- [ ] **Step 2: Отметить авто-миграции в разделе «Миграции базы данных»**

Найти абзац (строки 82-83):

```markdown
В production миграции выполняются отдельным шагом между сборкой образов и
`docker compose up -d`. Приложение не вызывает `create_all()` и не изменяет схему при старте.
```

Заменить на:

```markdown
Миграции применяются автоматически one-shot сервисом `migrate` при
`docker compose up -d --build`, до старта backend. Приложение не вызывает
`create_all()` и не изменяет схему при старте. Команды `alembic upgrade head` и
`alembic current` выше остаются доступны для ручной проверки.
```

- [ ] **Step 3: Отметить авто-сид в разделе «Каталог маскотов»**

Найти (строки 167-169):

```markdown
таблицу `mascots`; повторно синхронизировать каталог безопасно командой
`docker compose run --rm backend python -m app.modules.mascots.seed`.
```

Заменить на:

```markdown
таблицу `mascots`. Сид выполняется автоматически сервисом `migrate` при
`docker compose up -d --build`; повторно синхронизировать каталог вручную безопасно
командой `docker compose run --rm backend python -m app.modules.mascots.seed`.
```

- [ ] **Step 4: Проверить согласованность README**

Run: `grep -n "docker compose up -d --build\|сервис .migrate.\|сервисом .migrate." README.md`
Expected: минимум три совпадения (Быстрый старт, Миграции, Каталог маскотов); старый шаг «Соберите образы: `docker compose build`» в «Быстром старте» отсутствует.

- [ ] **Step 5: Commit (чек-пойнт)**

```bash
git add README.md
git commit -m "docs: README single-command quickstart"
```

---

### Task 4: Локальная сквозная верификация

**Files:** нет (только запуск)

- [ ] **Step 1: Убедиться, что локальный `.env` пригоден для localhost**

Run: `grep -E '^APP_DOMAIN=' .env`
Expected: `APP_DOMAIN=http://localhost` (если иное — временно выставить его для локального прогона).

- [ ] **Step 2: Поднять весь стек одной командой**

Run: `docker compose up -d --build`
Expected: сборка проходит; команда завершается без ошибок после того, как зависимости удовлетворены.

- [ ] **Step 3: Проверить, что `migrate` отработал и вышел с кодом 0**

Run: `docker compose ps -a`
Expected: `migrate` в состоянии `Exited (0)`; `postgres` и `backend` — `healthy`/`running`; `frontend` и `caddy` — `running`.

- [ ] **Step 4: Проверить health endpoint**

Run: `curl -fsS http://localhost/api/v1/health`
Expected: `{"status":"ok"}`

- [ ] **Step 5: Проверить идемпотентность повторного запуска**

Run: `docker compose up -d --build` (второй раз, без изменений схемы), затем `docker compose ps -a`
Expected: `migrate` снова `Exited (0)` (миграции — no-op, сид — upsert), стек остаётся здоровым, `curl http://localhost/api/v1/health` → `{"status":"ok"}`.

- [ ] **Step 6: (опционально) остановить стек**

Run: `docker compose down`
Expected: контейнеры остановлены; volume `postgres_data` сохранён (без `-v`).

---

## Self-Review

**Spec coverage:**
- Каноничная команда `up -d --build` — Task 1 (compose), Task 4 (верификация). ✓
- One-shot сервис `migrate` (migrate+seed) — Task 1 Step 2. ✓
- `backend` depends_on `migrate: service_completed_successfully` — Task 1 Step 3. ✓
- Дедуп env через YAML-якорь — Task 1 Step 1. ✓
- Webhook остаётся отдельно (не трогаем раздел 7) — Task 2 Step 4 явно исключает. ✓
- Обновление deploy.md (6/9/10) — Task 2. ✓
- README quickstart + заметки — Task 3. ✓
- Проверка (config + up + health + идемпотентность) — Task 4. ✓

**Placeholder scan:** плейсхолдеров нет; все команды и блоки конкретны.

**Type/имя consistency:** имя сервиса `migrate`, образ `pohvala-backend:latest`, якорь `&backend-env` / `*backend-env` — используются единообразно во всех задачах.
