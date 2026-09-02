# PH-803 · Deploy Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Свести и первый запуск, и каждый последующий релиз «Похвалы» на VPS к
одной команде `sudo ./scripts/deploy.sh`. Скрипт — тонкий адаптер поверх Docker
Compose, который знает специфику проекта: генерацию секретов, production `.env`,
настройку Telegram, тегированную по SHA раскатку с безопасным откатом, бэкап
перед миграцией, healthcheck и статус.

**Architecture:** Один исполняемый `scripts/deploy.sh` с подкомандами
(`deploy` по умолчанию, `status`, `logs`, `rollback`, `rotate-secrets`). Первый
запуск (нет `.env`) — интерактивный bootstrap; при существующем `.env` — релиз
новой версии из `main`; при отсутствии изменений — безопасный no-op. Образы
собираются и неизменяемо тегаются по git SHA (`pohvala-backend:<sha>`,
`pohvala-frontend:<sha>`); `compose.yaml` берёт тег из `${POHVALA_IMAGE_TAG}`.
Telegram-настройщик переезжает из смонтированного `scripts/` внутрь
backend-пакета (`app.modules.telegram.setup`) и расширяется: `getMe`,
`setWebhook`, `setChatMenuButton`, `getWebhookInfo`.

**Tech Stack:** Bash (`set -Eeuo pipefail`, `flock`), Docker Compose, git,
openssl, curl, GitHub REST API (read-only, public repo), aiogram (Telegram
setup внутри backend), Alembic/PostgreSQL, Caddy.

> **Про коммиты:** по рабочему процессу проекта коммиты делаются только по
> явной просьбе. Шаги `commit` ниже — чек-пойнты; фактический `git commit`
> выполняем в конце по подтверждению пользователя. Скрипт — инфраструктура и не
> покрывается юнит-тестами приложения; верификация — через `bash -n`,
> `shellcheck` (если доступен), `docker compose config --quiet` и сухие прогоны
> подкоманд. Логика Telegram-настройщика внутри backend покрывается pytest
> (парсинг аргументов, выбор `drop_pending_updates`, отказ без сети — через
> подменённого бота).

---

## Ключевые решения (зафиксированы с владельцем)

- **Откат — только тегированной раскаткой.** Полноценного «отката всего» не
  существует: БД безопасно не откатывается. Поэтому откатываем **код/образы** на
  прошлый SHA без пересборки, а схему держим вперёд-совместимой
  (expand→contract). `rollback` переключает `POHVALA_IMAGE_TAG` на предыдущий SHA
  и делает `up -d` **без** `--build`. Если код прошлого релиза несовместим с
  текущей схемой — скрипт останавливается и требует явного восстановления БД, а
  не делает `alembic downgrade` молча.
- **CI-гейт — блокирующий с обходом.** Перед ff-merge скрипт читает статус CI
  целевого коммита через GitHub API. Красный/отсутствующий статус останавливает
  деплой; обойти можно явным `--allow-red` (или `DEPLOY_ALLOW_RED=1`). Если API
  недоступен — предупреждение, не блок.
- **Секреты не трогаем на обычном деплое.** Есть `.env` — он источник истины;
  пароль БД, webhook secret/path не перегенерируются и не перезаписываются.
  Ротация — только явной подкомандой `rotate-secrets`.
- **`setWebhook` на повторном деплое — без `drop_pending_updates`.** Иначе при
  каждом релизе теряются ожидающие сообщения. Сброс допустим только при первом
  bootstrap (новый бот, терять нечего).
- **Без Docker Secrets.** Для одного VPS файл `.env` с правами `600` проще и не
  слабее: root всё равно читает контейнеры.

---

## Файловая структура

- `scripts/deploy.sh` — **новый.** Единый вход: bootstrap + release + status +
  logs + rollback + rotate-secrets.
- `scripts/deploy.lib.sh` — **новый (опционально).** Общие функции (логирование
  без секретов, ожидание health/HTTPS, работа с состоянием SHA), чтобы
  `deploy.sh` оставался читаемым. Если проще держать всё в одном файле — сливаем.
- `backend/app/modules/telegram/__init__.py`, `backend/app/modules/telegram/setup.py`
  — **новый пакет.** Перенос и расширение Telegram-настройщика:
  `getMe` / `setWebhook` / `setChatMenuButton` / `getWebhookInfo`.
- `backend/tests/test_telegram_setup.py` — **новый.** pytest на настройщик.
- `scripts/set_telegram_webhook.py` — **удалить** (заменяется пакетом; снимаем
  монтирование `-v scripts:/srv/scripts`).
- `compose.yaml` — тег образа через `${POHVALA_IMAGE_TAG:-latest}` для
  `backend`, `migrate`, `frontend`; у `frontend` появляется явный `image:`.
- `.gitignore` — добавить `.deploy-current` (состояние текущего SHA рядом с уже
  игнорируемым `.deploy-previous`).
- `docs/deploy.md` — переписать разделы 5–10 на `sudo ./scripts/deploy.sh`;
  раздел 7 (webhook) — на пакетную команду вместо смонтированного скрипта.
- `README.md` — упомянуть `scripts/deploy.sh` как канонический путь production.
- `docs/backlog.md` — запись PH-803 (в этом плане уже добавляется отдельной
  задачей).

---

### Task 1: Перенести Telegram-настройщик в backend-пакет и расширить

**Files:**
- Create: `backend/app/modules/telegram/__init__.py`
- Create: `backend/app/modules/telegram/setup.py`
- Create: `backend/tests/test_telegram_setup.py`
- Delete: `scripts/set_telegram_webhook.py`

- [ ] **Step 1 (red):** тест `test_telegram_setup.py` с подменённым `Bot`
  (fake aiogram bot) проверяет:
  - `getMe` возвращает username и не печатает токен;
  - `set-webhook` по умолчанию вызывает `set_webhook(..., drop_pending_updates=False)`;
  - `set-webhook --drop-pending` передаёт `drop_pending_updates=True`;
  - URL webhook собирается как `{APP_DOMAIN}/api/v1/telegram/{TELEGRAM_WEBHOOK_PATH}`
    и `allowed_updates=["message"]`;
  - `set-menu-button` ставит `MenuButtonWebApp` на `APP_DOMAIN`;
  - `get-webhook-info` печатает только host/pending count/last error, но не путь и не секрет.

- [ ] **Step 2 (green):** реализовать `app/modules/telegram/setup.py`. Один
  argparse с подкомандами `get-me`, `set-webhook` (`--drop-pending` /
  `--keep-pending`, по умолчанию keep), `set-menu-button`, `get-webhook-info`.
  Конфиг берём из `app.core.config.get_settings()` (тот же `.env`). Вывод —
  без секретов (как текущий `set_telegram_webhook.py`, строки 37-38). Точка
  входа `python -m app.modules.telegram.setup <command>`.

- [ ] **Step 3:** удалить `scripts/set_telegram_webhook.py`.

- [ ] **Step 4 (verify):** `cd backend && ruff check . && pytest -q -k telegram_setup`.
  Expected: зелено. `grep -rn "srv/scripts\|set_telegram_webhook" .` — не должно
  остаться ссылок на смонтированный скрипт (кроме исторических планов).

- [ ] **Step 5:** Commit (чек-пойнт): `feat: move telegram setup into backend package (PH-803)`.

---

### Task 2: Тегирование образов по SHA в `compose.yaml`

**Files:**
- Modify: `compose.yaml`
- Modify: `.gitignore`

- [ ] **Step 1:** заменить у `migrate` и `backend`
  `image: pohvala-backend:latest` на `image: pohvala-backend:${POHVALA_IMAGE_TAG:-latest}`.

- [ ] **Step 2:** у `frontend` добавить явный
  `image: pohvala-frontend:${POHVALA_IMAGE_TAG:-latest}` (сейчас имя образа
  выводится Compose автоматически — для отката нужен предсказуемый тег).

- [ ] **Step 3:** `.gitignore` — добавить строку `.deploy-current` под уже
  существующей `.deploy-previous`.

- [ ] **Step 4 (verify):**
  - `POHVALA_IMAGE_TAG=testsha docker compose config` — у `backend`, `migrate`,
    `frontend` тег `:testsha`;
  - `docker compose config` без переменной — тег `:latest` (локальная разработка
    не ломается).

- [ ] **Step 5:** Commit (чек-пойнт): `feat: tag compose images by release SHA (PH-803)`.

---

### Task 3: `scripts/deploy.sh` — каркас, общие функции, подкоманды

**Files:**
- Create: `scripts/deploy.sh` (+ опционально `scripts/deploy.lib.sh`)

Общие требования (по образцу `ops/backup/backup.sh`):
- `#!/usr/bin/env bash` + `set -Eeuo pipefail`.
- Требует root (нужны docker, `.env` 600, `compose exec` для `set_role`): если
  `EUID != 0` — понятная ошибка «запускайте через sudo».
- `PROJECT_DIR` = корень репозитория (родитель каталога скрипта), а не хардкод.
- Проверка зависимостей: `docker`, `git`, `openssl`, `curl`, `flock`.
- `flock -n` на `<PROJECT_DIR>/.deploy.lock` — запрет параллельного деплоя.
- Логирование без секретов: helper `log`/`die`; секреты (токен, пароль, путь,
  secret) НИКОГДА не попадают в stdout/stderr.
- Диспетчер подкоманд: `deploy` (по умолчанию), `status`, `logs`, `rollback`,
  `rotate-secrets`, `help`.
- Состояние релиза: `.deploy-current` (SHA задеплоенного) и `.deploy-previous`
  (SHA предыдущего) — оба в `.gitignore`.

- [ ] **Step 1:** каркас: shebang, guard-функции, диспетчер, `help`, `flock`,
  проверка зависимостей и root.
- [ ] **Step 2:** helpers: `wait_for_health` (poll `docker compose ps`/health до
  готовности backend, таймаут), `wait_for_https` (curl `https://<domain>/api/v1/health`
  до `{"status":"ok"}`), `read_env_value`/`load_env` (безопасное чтение из `.env`
  без его печати), `current_domain`.
- [ ] **Step 3 (verify):** `bash -n scripts/deploy.sh`; `shellcheck scripts/deploy.sh`
  (если установлен) — без ошибок; `sudo ./scripts/deploy.sh help` печатает
  подкоманды.
- [ ] **Step 4:** Commit (чек-пойнт): `feat: deploy.sh skeleton and helpers (PH-803)`.

---

### Task 4: Bootstrap (первый запуск, нет `.env`)

**Files:**
- Modify: `scripts/deploy.sh`

Последовательность (спрашиваем только то, что нельзя сгенерировать):
1. Интерактивно: production-домен (валидируем, приводим к `https://<domain>`
   без завершающего `/`); токен BotFather — скрытый ввод (`read -rs`); Telegram
   ID первого админа — опционально (пусто = пропустить).
2. Генерация: `POSTGRES_PASSWORD=$(openssl rand -hex 32)`,
   `TELEGRAM_WEBHOOK_SECRET=$(openssl rand -hex 32)`,
   `TELEGRAM_WEBHOOK_PATH=$(openssl rand -hex 24)`.
3. Производные: `APP_ENV=production`, `VITE_TELEGRAM_MODE=telegram`,
   `POSTGRES_DB=pohvala`, `POSTGRES_USER=pohvala`,
   `DATABASE_URL=postgresql+asyncpg://pohvala:<pwd>@postgres:5432/pohvala`,
   `CORS_ORIGINS=<APP_DOMAIN>`.
4. Атомарная запись `.env`: `umask 077`, во временный файл рядом, `chmod 600`,
   `mv`. Никогда не перезаписываем существующий `.env`.
5. `docker compose config --quiet` (валидирует и наши production-гардрейлы из
   `app/core/config.py`).
6. Билд+тег по SHA и `POHVALA_IMAGE_TAG=<sha> docker compose up -d --build`.
7. `wait_for_health` + `wait_for_https`.
8. `getMe` (через пакетную команду) — подтверждаем валидность токена.
9. `set-webhook --drop-pending` (первый запуск — можно сбросить), затем
   `set-menu-button` и `get-webhook-info` для проверки.
10. Если задан admin ID: цикл `compose exec -T backend python -m
    app.modules.users.set_role <id> admin`; при коде «User account not found»
    (см. `set_role.py`, exit 1) — просим админа открыть Mini App и повторяем с
    паузой, пока не выйдет 0 или пользователь не прервёт.
11. Записать `.deploy-current` (SHA) и короткий итог без секретов (домен, статус
    контейнеров, что webhook/menu настроены).

- [ ] **Step 1:** реализовать промпты и генерацию (скрытый ввод токена; валидация
  домена и Telegram ID — положительное целое).
- [ ] **Step 2:** атомарная запись `.env` (600) + `docker compose config --quiet`.
- [ ] **Step 3:** билд/тег/up + ожидания health и HTTPS.
- [ ] **Step 4:** Telegram: getMe → setWebhook(drop) → menu button → getWebhookInfo.
- [ ] **Step 5:** назначение первого админа с ожиданием открытия Mini App.
- [ ] **Step 6 (verify):** сухой прогон логики валидации на невалидных вводах
  (домен без https, пустой токен, отрицательный ID) — понятные ошибки, `.env` не
  создаётся. Полный прогон — на реальном/локальном стенде вне CI.
- [ ] **Step 7:** Commit (чек-пойнт): `feat: deploy.sh bootstrap flow (PH-803)`.

---

### Task 5: Release (есть `.env`) + CI-гейт + бэкап

**Files:**
- Modify: `scripts/deploy.sh`

Последовательность:
1. `flock` уже держим. `git fetch origin main`.
2. Отказ при грязном worktree (`git status --porcelain` не пуст).
3. Если `HEAD == origin/main` — no-op: сообщаем «нет изменений» и выходим 0
   (перед выходом можно прогнать быстрый health-check).
4. CI-гейт: статус целевого SHA (`origin/main`) через GitHub API
   (`/repos/Pfshein/pohvali/commits/<sha>/status` и/или check-runs). Красный →
   стоп, если нет `--allow-red`/`DEPLOY_ALLOW_RED=1`. API недоступен →
   предупреждение, продолжаем.
5. Записать текущий SHA в `.deploy-previous`.
6. **Бэкап БД перед миграцией:** если настроен `ops/backup/backup.sh`
   (есть age-recipient) — вызвать его; иначе — простой
   `docker compose exec -T postgres pg_dump ... > <PROJECT_DIR>/.deploy-backups/<ts>.dump`
   (каталог 700). Пустой дамп → стоп.
7. `git merge --ff-only origin/main` (не ff → стоп с подсказкой).
8. `docker compose config --quiet`.
9. Билд+тег нового SHA; `POHVALA_IMAGE_TAG=<new-sha> docker compose up -d --build --remove-orphans`.
10. `wait_for_health` (migrate дошёл, backend healthy) + `wait_for_https`.
11. Telegram: `set-webhook --keep-pending` (без сброса!) + `get-webhook-info` +
    сверка menu button.
12. Записать `.deploy-current=<new-sha>`; прунинг локальных образов — оставить
    только теги `current` и `previous`.
13. Итог без секретов: старый SHA → новый SHA, статус контейнеров, webhook OK.

- [ ] **Step 1:** fetch, dirty-guard, no-op-guard, запись previous SHA.
- [ ] **Step 2:** CI-гейт (GitHub API) с `--allow-red` и graceful degradation.
- [ ] **Step 3:** бэкап перед миграцией (reuse `backup.sh` или fallback pg_dump).
- [ ] **Step 4:** ff-only merge → config → build/tag/up → ожидания.
- [ ] **Step 5:** webhook keep-pending + проверки; запись current SHA; прунинг образов.
- [ ] **Step 6 (verify):** прогон no-op (HEAD==origin/main → выход без изменений);
  прогон dirty-guard (искусственно грязный worktree → отказ). Полный релиз —
  на стенде.
- [ ] **Step 7:** Commit (чек-пойнт): `feat: deploy.sh release flow with CI gate and pre-migrate backup (PH-803)`.

---

### Task 6: `status`, `logs`, `rollback`, `rotate-secrets`

**Files:**
- Modify: `scripts/deploy.sh`

- [ ] **Step 1 `status`:** `docker compose ps -a`, current/previous SHA из
  файлов состояния, health/HTTPS, webhook info — всё без секретов.
- [ ] **Step 2 `logs`:** прокидываем в `docker compose logs` (по умолчанию
  `--tail=100` для backend/caddy/migrate; аргументы после `logs` пробрасываем).
- [ ] **Step 3 `rollback`:** прочитать `.deploy-previous`; **проверка
  совместимости схемы** — сравнить `alembic current` (в БД) с ревизиями,
  известными коду прошлого SHA: если у прошлого кода нет текущей head-ревизии
  (значит новая миграция несовместима) — **стоп** с инструкцией по
  восстановлению из бэкапа, без авто-downgrade. Иначе:
  `POHVALA_IMAGE_TAG=<previous-sha> docker compose up -d --remove-orphans`
  (без `--build`), ожидания health/HTTPS, поменять местами current/previous.
- [ ] **Step 4 `rotate-secrets`:** отдельная явная подкоманда (НЕ часть deploy).
  Ротирует webhook secret/path (и по флагу — пароль БД, с явным предупреждением
  про рестарт/пересоздание пользователя), обновляет `.env` атомарно, повторно
  регистрирует webhook. Пароль БД по умолчанию НЕ трогает.
- [ ] **Step 5 (verify):** `sudo ./scripts/deploy.sh status` и `logs` работают на
  поднятом локальном стеке; `rollback` без `.deploy-previous` → понятный отказ.
- [ ] **Step 6:** Commit (чек-пойнт): `feat: deploy.sh status/logs/rollback/rotate-secrets (PH-803)`.

---

### Task 7: Документация — `docs/deploy.md` и `README.md`

**Files:**
- Modify: `docs/deploy.md`
- Modify: `README.md`

- [ ] **Step 1:** `docs/deploy.md` разделы 5–10 → один путь:
  `git clone … /opt/pohvali && cd /opt/pohvali && sudo ./scripts/deploy.sh`.
  Оставить требования 0–4 (DNS, пользователь, firewall, Docker) — их скрипт не
  делает. Раздел про откат переписать на `sudo ./scripts/deploy.sh rollback` с
  честным ограничением про БД.
- [ ] **Step 2:** раздел 7 (webhook) → `docker compose run --rm backend python -m
  app.modules.telegram.setup set-webhook` (без монтирования `scripts/`).
- [ ] **Step 3:** `README.md` — в «Быстром старте»/деплое указать
  `scripts/deploy.sh` как канонический production-путь; локальная разработка
  остаётся на `docker compose up -d --build`.
- [ ] **Step 4 (verify):** `grep -n "set_telegram_webhook\|/srv/scripts" docs/ README.md`
  — не осталось; `grep -n "deploy.sh" docs/deploy.md README.md` — присутствует.
- [ ] **Step 5:** Commit (чек-пойнт): `docs: single deploy.sh runbook (PH-803)`.

---

### Task 8: Сквозная верификация на стенде

**Files:** нет (прогон)

- [ ] **Step 1:** чистый стенд без `.env` → `sudo ./scripts/deploy.sh` проходит
  bootstrap; health + HTTPS зелёные; webhook/menu настроены; (если задан admin)
  роль назначена после открытия Mini App.
- [ ] **Step 2:** повторный `sudo ./scripts/deploy.sh` без новых коммитов → no-op,
  `.env` и секреты не изменились (`stat -c '%a' .env` = 600, mtime `.env` тот же).
- [ ] **Step 3:** новый коммит в `main` → `sudo ./scripts/deploy.sh` делает
  релиз; `.deploy-previous`/`.deploy-current` обновлены; webhook `getWebhookInfo`
  показывает pending не сброшенным (на повторе drop не применялся).
- [ ] **Step 4:** `sudo ./scripts/deploy.sh rollback` возвращает предыдущий образ
  без пересборки; health зелёный.
- [ ] **Step 5:** `status`/`logs` выводят состояние без секретов.

---

## Self-Review

**Spec coverage:**
- Один вход `sudo ./scripts/deploy.sh` (bootstrap/release/no-op) — Task 3–5. ✓
- Интерактив только для несоставимого (домен, токен скрыто, admin ID опц.) — Task 4. ✓
- Генерация pwd/secret/path, атомарный `.env` 600, производные значения — Task 4. ✓
- `docker compose config --quiet`, `up -d --build`, ожидание health+HTTPS — Task 4/5. ✓
- getMe / setWebhook / menu button / getWebhookInfo, настройщик в backend — Task 1/4/5. ✓
- Первый админ через существующий `set_role` с ожиданием Mini App — Task 4. ✓
- Повтор: не перегенерирует секреты, не перезаписывает `.env`, ff-only, пересборка,
  миграции, повторная проверка webhook/menu, smoke — Task 5. ✓
- setWebhook на повторе БЕЗ `drop_pending_updates` — Task 1 (default keep) + Task 5. ✓
- flock, dirty-guard, previous SHA, бэкап перед миграцией — Task 5. ✓
- Тегированная раскатка по SHA + `rollback` без пересборки + стоп при
  несовместимой схеме — Task 2/6. ✓
- CI-гейт зелёного коммита с обходом — Task 5. ✓
- `status`, `logs`, безопасный `rollback`, отдельный `rotate-secrets` — Task 6. ✓
- Без Docker Secrets; `.env` 600 — заложено в Task 4. ✓
- Обновление git main внутри скрипта (ff-only) — Task 5. ✓

**Границы (следующая задача, НЕ PH-803):** формальные версии `vX.Y.Z`,
changelog, GitHub Releases, публикация образов в registry, автозапуск деплоя из
GitHub Actions → SSH. Модель MVP: зелёный commit в `main` → `deploy.sh` →
зафиксированный SHA на сервере.

**Placeholder scan:** плейсхолдеров нет; команды и пути конкретны.

**Consistency:** образы `pohvala-backend`/`pohvala-frontend` с тегом
`${POHVALA_IMAGE_TAG:-latest}`; состояние в `.deploy-current`/`.deploy-previous`;
Telegram-пакет `app.modules.telegram.setup`; подкоманды
`deploy|status|logs|rollback|rotate-secrets` — единообразно во всех задачах.
