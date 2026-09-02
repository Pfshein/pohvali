# Production deploy: один VPS, Docker Compose и Caddy

Runbook закрывает PH-705 для текущей простой схемы: один VPS с Ubuntu 24.04,
Docker Compose, Caddy, frontend, один backend и PostgreSQL. Kubernetes, отдельный
reverse proxy и панель управления не нужны.

> Важно: запускайте ровно один экземпляр `backend`. Внутри backend работает
> APScheduler напоминаний; `docker compose up --scale backend=2` приведёт к
> дублированию фоновых заданий.

## 0. Что подготовить

- VPS с чистой Ubuntu 24.04 LTS, минимум 2 vCPU, 4 GB RAM и 30 GB SSD;
- публичный IPv4;
- домен или поддомен, например `app.example.com`;
- токен Telegram-бота от [@BotFather](https://t.me/BotFather);
- SSH-ключ на компьютере администратора.

Не присылайте токен бота, пароли или приватный SSH-ключ в чат и не коммитьте
`.env`. Репозиторий публичный, поэтому на сервере он клонируется по HTTPS без
GitHub-токена.

Если образ VPS содержит ISPmanager, nginx или Apache, проще переустановить VPS на
чистую Ubuntu: порты 80 и 443 нужны Caddy.

## 1. DNS

В панели регистратора создайте запись:

| Тип | Имя | Значение | TTL |
| --- | --- | --- | --- |
| `A` | `app` или `@` | публичный IPv4 VPS | `300` |

Не добавляйте `AAAA`, пока IPv6 на VPS не настроен и не проверен. После изменения
DNS проверьте со своего компьютера:

```bash
nslookup app.example.com
```

Ответ должен содержать IPv4 нового VPS. Получение сертификата Caddy запускайте
только после этого.

## 2. Первый вход и отдельный пользователь

Если SSH-ключа ещё нет, создайте его на своём компьютере.

Linux/macOS:

```bash
ssh-keygen -t ed25519 -C "pohvali-vps"
cat ~/.ssh/id_ed25519.pub
```

Windows PowerShell:

```powershell
ssh-keygen -t ed25519 -C "pohvali-vps"
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

Первый раз войдите по данным из панели VPS:

```bash
ssh root@203.0.113.10
```

Создайте пользователя для деплоя:

```bash
adduser deploy
usermod -aG sudo deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
nano /home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
```

В `authorized_keys` вставьте **публичный** ключ одной строкой. Не закрывая первый
сеанс, откройте второй терминал и проверьте:

```bash
ssh deploy@203.0.113.10
sudo true
```

Только после успешной проверки ключа можно запретить root/password login:

```bash
sudo nano /etc/ssh/sshd_config.d/99-pohvali.conf
```

Содержимое файла:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Проверьте конфигурацию до перезагрузки SSH:

```bash
sudo sshd -t
sudo systemctl reload ssh
```

Снова проверьте вход `ssh deploy@203.0.113.10` в отдельном терминале. Не
отключайте парольный вход, если вход по ключу не работает.

## 3. Обновление ОС и firewall

Все следующие команды выполняются пользователем `deploy`:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y ca-certificates curl git openssl ufw unattended-upgrades
sudo ss -lntup | grep -E ':(80|443)\b' || true
```

Последняя команда не должна показывать nginx, Apache или панель управления.

Разрешите SSH, HTTP и HTTPS. UDP 443 нужен HTTP/3 Caddy:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
sudo ufw status verbose
```

Если у провайдера есть отдельный сетевой firewall, разрешите в нём те же входящие
порты: TCP 22, 80, 443 и UDP 443. Порты 5432 и 8000 открывать нельзя.

## 4. Docker из официального репозитория

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker containerd
sudo docker run --rm hello-world
sudo docker compose version
```

Пользователь `deploy` намеренно не добавляется в группу `docker`: членство в ней
практически эквивалентно root. Для Docker-команд ниже используется `sudo`.

Если на VPS меньше 4 GB RAM и swap отсутствует (`swapon --show` ничего не
возвращает), перед первой сборкой можно создать 2 GB swap:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Этот блок выполняется один раз.

## 5. Код и первый запуск: `sudo ./scripts/deploy.sh`

```bash
sudo install -d -o deploy -g deploy /opt/pohvali
git clone https://github.com/Pfshein/pohvali.git /opt/pohvali
cd /opt/pohvali
git switch main
git status --short --branch
```

Первый запуск — одна команда:

```bash
cd /opt/pohvali
sudo ./scripts/deploy.sh
```

Скрипт видит, что `.env` ещё нет, и проводит интерактивный bootstrap:

1. Спрашивает только то, что нельзя сгенерировать: production-домен (без
   `https://` можно — скрипт сам приведёт к `https://<domain>`, без завершающего
   `/`), токен бота от [@BotFather](https://t.me/BotFather) (ввод скрыт, как
   пароль), и опционально Telegram ID первого администратора (пусто — пропустить,
   роль можно назначить позже).
2. Генерирует `POSTGRES_PASSWORD`, `TELEGRAM_WEBHOOK_SECRET` и
   `TELEGRAM_WEBHOOK_PATH` через `openssl rand -hex`, добавляет производные
   значения (`APP_ENV=production`, `CORS_ORIGINS=<домен>`, `DATABASE_URL` и т.д.)
   и атомарно пишет `.env` с правами `600`. Существующий `.env` скрипт никогда не
   трогает — при повторном запуске он переходит к обновлению (раздел 8).
3. Проверяет конфигурацию (`docker compose config --quiet`), собирает образы,
   тегированные текущим git SHA, и поднимает стек (`docker compose up -d
   --build`); `migrate` применяет миграции и сид маскотов до старта backend.
4. Дожидается healthcheck backend и рабочего `https://<домен>/api/v1/health`.
5. Настраивает Telegram: `getMe` (проверяет токен), `setWebhook` — **только на
   этом первом запуске** со сбросом ожидающих updates (боту терять нечего),
   `setChatMenuButton` и `getWebhookInfo` для проверки.
6. Если был указан ID администратора — ждёт, пока владелец откроет бота или Mini
   App (жмите Enter для повтора, Ctrl-C — чтобы назначить роль позже вручную).

Ничего из выведенного в терминал не содержит токен, пароль БД или webhook
secret/path — только домен, статус контейнеров и подтверждения. Не используйте
`docker compose up --scale backend`: внутри backend работает APScheduler
напоминаний, второй экземпляр продублирует фоновые задания. Caddy автоматически
запросит TLS-сертификат; DNS и открытые порты 80/443 должны уже указывать на этот
VPS.

## 6. Проверка HTTPS и webhook

`sudo ./scripts/deploy.sh status` в любой момент печатает состояние контейнеров,
текущий/предыдущий SHA, результат HTTPS healthcheck и `getWebhookInfo` — без
секретов:

```bash
cd /opt/pohvali
sudo ./scripts/deploy.sh status
```

Если нужно вручную перерегистрировать webhook (например, домен поменяли не через
bootstrap), используйте пакетную Telegram-команду напрямую — она не требует
монтирования `scripts/` внутрь контейнера:

```bash
cd /opt/pohvali
sudo docker compose run --rm backend \
  python -m app.modules.telegram.setup set-webhook
```

По умолчанию (без флага) она **сохраняет** ожидающие updates
(`--keep-pending`); сбросить их можно только явным `--drop-pending`, и это
осмысленно исключительно при первом запуске нового бота. Откройте бота в
Telegram, отправьте `/start` и нажмите inline-кнопку.

## 7. Smoke test перед пользователями

```bash
cd /opt/pohvali
sudo ./scripts/deploy.sh status
sudo docker compose logs --since=10m backend caddy
df -h
free -h
```

Проверьте руками в Telegram:

1. `/start` отвечает и открывает Mini App.
2. Создаётся тестовая похвала, появляется звезда.
3. После перезагрузки запись читается.
4. Открываются календарь и коллекция маскотов.
5. В логах нет traceback и секретов.

Проверьте автоматический старт после reboot:

```bash
sudo reboot
```

После повторного входа:

```bash
cd /opt/pohvali
sudo ./scripts/deploy.sh status
```

## 8. Обновление production

Та же команда, что и для первого запуска, — `sudo ./scripts/deploy.sh` — при уже
существующем `.env` идёт по пути релиза, а не bootstrap:

```bash
cd /opt/pohvali
sudo ./scripts/deploy.sh
```

Один прогон делает всё по порядку: `git fetch origin main`; отказ, если рабочее
дерево грязное; безопасный no-op (выход `0`, без изменений), если новых коммитов
в `origin/main` нет; проверка CI-статуса целевого коммита через GitHub API
(красный статус останавливает деплой — обойти можно `--allow-red` или
`DEPLOY_ALLOW_RED=1`; недоступность API — только предупреждение); резервная копия
БД перед миграцией (см. [`docs/backup.md`](backup.md), либо запасной `pg_dump`,
если офсайт-бэкап не настроен); `git merge --ff-only origin/main`; сборка и
запуск образов, тегированных новым SHA; ожидание health и HTTPS; и обновление
webhook **без сброса** ожидающих updates (`set-webhook --keep-pending`) — иначе
каждый релиз терял бы сообщения, пришедшие во время выкладки.

`.env` и секреты релиз не трогает — ротация только через раздел 10.

## 9. Откат приложения

Если новая версия не проходит smoke test, откатите **код и контейнеры**, но не
делайте автоматический downgrade базы:

```bash
cd /opt/pohvali
sudo ./scripts/deploy.sh rollback
```

`rollback` переключает `POHVALA_IMAGE_TAG` на SHA из `.deploy-previous` и
поднимает стек **без пересборки** (`docker compose up -d`, без `--build`). Перед
этим скрипт сравнивает текущую ревизию Alembic в БД с ревизиями, известными коду
предыдущего релиза: если новая миграция уже применилась и предыдущий код её не
знает, `rollback` **останавливается** и просит восстановить БД из бэкапа — он
никогда не выполняет `alembic downgrade` автоматически. Без записанного
`.deploy-previous` (например, сразу после bootstrap) команда тоже отказывает с
понятным сообщением.

Миграции production должны оставаться обратно совместимыми (expand→contract), тогда
откат кода без отката схемы безопасен. `alembic downgrade base` в production
запрещён: он удаляет таблицы и данные. При несовместимой или повреждённой схеме
нужен forward-fix либо восстановление из проверенного backup — `rollback` сам на
это укажет, если обнаружит несовместимость.

## 10. Ротация секретов

Обычный деплой и bootstrap никогда не перегенерируют и не перезаписывают
`.env`. Если нужно сменить webhook secret/path (например, после подозрения на
утечку) — отдельная явная подкоманда:

```bash
cd /opt/pohvali
sudo ./scripts/deploy.sh rotate-secrets
```

Она ротирует `TELEGRAM_WEBHOOK_SECRET` и `TELEGRAM_WEBHOOK_PATH`, атомарно
обновляет `.env` (права `600` сохраняются), перезапускает стек и
перерегистрирует webhook с сохранением ожидающих updates. Пароль PostgreSQL по
умолчанию не трогается; чтобы сменить и его, добавьте `--rotate-db-password` —
это на несколько секунд прерывает соединения backend с базой, скрипт
предупреждает об этом перед выполнением.

## 11. Эксплуатационный минимум

- Логи каждого контейнера ограничены тремя файлами по 10 MB в `compose.yaml`.
- Раз в неделю проверяйте `df -h` и `sudo ./scripts/deploy.sh status` (контейнеры,
  SHA, health, webhook).
- Нового маскота владелец добавляет без deploy и правки БД: после назначения роли
  отправьте в личном чате с ботом PNG-документ (до 1 MiB, 256–1024 px, с alpha-каналом)
  с подписью `/add_mascot <code> <порог> | <Имя> | <Описание>`. Повторная отправка
  того же сообщения безопасна. Маскот сразу появляется в каталоге приложения, картинка
  отдаётся с backend по `/api/v1/mascots/{code}/image`.
- Установленные пакеты безопасности обновляет `unattended-upgrades`; reboot после
  обновления ядра выполняйте в запланированное окно и повторяйте smoke test.
- База хранится в Docker volume `postgres_data`; удалять volumes командами
  `docker compose down -v` или `docker volume rm` на production нельзя.
- Для закрытой альфы настройте локальный зашифрованный backup и выполните первый
  restore drill по [`docs/backup.md`](backup.md). Backup запускается host-side
  systemd timer и не добавляет долгоживущий Compose-сервис.
- Snapshot провайдера не заменяет внешний backup. PH-704A/704B реализованы:
  локальный зашифрованный dump и offsite-выгрузка в приватное S3-совместимое
  хранилище описаны в [`docs/backup.md`](backup.md). Операционная активация на
  production (реальный bucket, `offsite.env` на VPS, первый off-host restore
  drill) — PH-707.
- PH-706 (privacy/legal gate) реализован: privacy policy публикуется автоматически
  по `/privacy.html`, удаление данных — через `DELETE /api/v1/session` и панель
  «Приватность и данные» в приложении; юрисдикция — раздел 12 ниже. Остаётся
  убедиться при создании production VPS/bucket, что регион соответствует
  зафиксированному решению.

## 12. Юрисдикция и data residency (PH-706)

Зафиксированное решение для публичного запуска:

- Production VPS размещается у провайдера в ЕС, рекомендуемый регион — Германия
  (Hetzner `fsn1`/`nbg1`). При создании VPS выбирайте именно регион ЕС; для
  закрытой альфы допустим любой регион, но перед публичным запуском миграция
  обязательна.
- Offsite bucket (PH-704B/PH-707) создаётся в том же регионе ЕС.
- Приватность пользователей описывает публичная страница `/privacy.html`. Текст
  политики лежит в единственном месте — `frontend/src/lib/privacy-policy.ts`;
  из него приложение показывает политику внутри себя, а Vite-плагин собирает
  статическую страницу в образ frontend. Отдельных сервисов это не требует.
  При изменении политики правьте только этот модуль и обновляйте в нём `version`
  и `revised`.
- Telegram обрабатывает собственные данные (идентификация, доставка, storage
  adapter) по своей политике — это явно оговорено в тексте политики.
- Проверка после deploy: `curl -fsS https://app.example.com/privacy.html | head`
  отдаёт страницу политики; `DELETE /api/v1/session` без авторизации возвращает
  401 (см. также smoke-тесты в `docs/backlog.md`, PH-706).
