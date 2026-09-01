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

## 5. Код и production `.env`

```bash
sudo install -d -o deploy -g deploy /opt/pohvali
git clone https://github.com/Pfshein/pohvali.git /opt/pohvali
cd /opt/pohvali
git switch main
git status --short --branch
```

Сгенерируйте три независимых значения и сохраните их временно в менеджере
паролей:

```bash
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 24
```

Это соответственно пароль PostgreSQL, secret webhook и случайная часть пути
webhook. Затем создайте файл:

```bash
umask 077
nano .env
```

Шаблон (замените все значения в угловых скобках):

```dotenv
APP_ENV=production
APP_DOMAIN=https://app.example.com
VITE_TELEGRAM_MODE=telegram

BOT_TOKEN=<token-from-BotFather>
TELEGRAM_WEBHOOK_SECRET=<second-openssl-value>
TELEGRAM_WEBHOOK_PATH=<third-openssl-value>

POSTGRES_DB=pohvala
POSTGRES_USER=pohvala
POSTGRES_PASSWORD=<first-openssl-value>
DATABASE_URL=postgresql+asyncpg://pohvala:<first-openssl-value>@postgres:5432/pohvala

CORS_ORIGINS=https://app.example.com
```

В `POSTGRES_PASSWORD` и `DATABASE_URL` должно стоять одно и то же первое hex-
значение. Hex выбран специально: его не нужно URL-кодировать. Домен в
`APP_DOMAIN` и `CORS_ORIGINS` должен совпадать, без завершающего `/`.

Проверьте права и итоговую Compose-конфигурацию. Вторая команда не печатает
секреты:

```bash
chmod 600 .env
sudo docker compose config --quiet
```

Не публикуйте вывод `docker compose config`: он содержит раскрытые секреты.

## 6. Первый запуск

Одна команда собирает образы, поднимает PostgreSQL, применяет миграции и сид
маскотов (сервис `migrate`) и только затем стартует backend, frontend и Caddy:

```bash
cd /opt/pohvali
sudo docker compose up -d --build
sudo docker compose ps -a
sudo docker compose logs --tail=100 caddy backend migrate
```

Сервис `migrate` — одноразовый: он завершается с кодом 0 после `alembic upgrade
head` и идемпотентного сида каталога маскотов, и `backend` стартует только после
его успешного завершения. В `docker compose ps -a` он отображается как `exited (0)`
— это нормально.

Не используйте `--scale backend`. Caddy автоматически запросит TLS-сертификат;
DNS и открытые порты 80/443 должны уже указывать на этот VPS.

## 7. Проверка HTTPS и регистрация webhook

С VPS:

```bash
curl -fsS https://app.example.com/api/v1/health
curl -I https://app.example.com/
```

Health должен вернуть:

```json
{"status":"ok"}
```

Если сертификат не выпустился:

```bash
sudo docker compose logs --tail=200 caddy
```

Проверьте DNS, часы сервера (`timedatectl`), порт 80 и лимиты Let's Encrypt.

После рабочего HTTPS зарегистрируйте Telegram webhook из backend-контейнера:

```bash
cd /opt/pohvali
sudo docker compose run --rm \
  -v "$PWD/scripts:/srv/scripts:ro" \
  backend python /srv/scripts/set_telegram_webhook.py
```

Команда должна вывести только подтверждение домена. Она передаёт Telegram тот же
secret, который backend проверяет в заголовке webhook, и удаляет старые ожидающие
updates.

Откройте бота в Telegram, отправьте `/start` и нажмите inline-кнопку. Отдельная
настройка Menu Button в BotFather необязательна; при желании задайте ей тот же
HTTPS URL.

## 8. Smoke test перед пользователями

```bash
cd /opt/pohvali
sudo docker compose ps -a
curl -fsS https://app.example.com/api/v1/health
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
sudo docker compose ps -a
curl -fsS https://app.example.com/api/v1/health
```

## 9. Обновление production

Каждый деплой сохраняет SHA предыдущей версии, делает только fast-forward и одной
командой пересобирает образы, применяет миграции и сид (сервис `migrate`) и лишь
затем заменяет работающие контейнеры:

```bash
cd /opt/pohvali
git switch main
git fetch origin main
git rev-parse HEAD > .deploy-previous
git merge --ff-only origin/main
sudo docker compose config --quiet
sudo docker compose up -d --build --remove-orphans
sudo docker compose ps -a
curl -fsS https://app.example.com/api/v1/health
```

Если `.env`, домен или webhook-путь менялись, после успешного healthcheck снова
запустите скрипт регистрации webhook из раздела 7.

## 10. Откат приложения

Если новая версия не проходит smoke test, откатите **код и контейнеры**, но не
делайте автоматический downgrade базы:

```bash
cd /opt/pohvali
git checkout --detach "$(cat .deploy-previous)"
sudo docker compose up -d --build --remove-orphans
sudo docker compose ps -a
curl -fsS https://app.example.com/api/v1/health
```

Миграции production должны оставаться обратно совместимыми. `alembic downgrade
base` здесь запрещён: он удаляет таблицы и данные. При несовместимой или
повреждённой схеме нужен forward-fix либо восстановление из проверенного backup.
Перед следующим обычным обновлением вернитесь на ветку:

```bash
git switch main
```

## 11. Эксплуатационный минимум

- Логи каждого контейнера ограничены тремя файлами по 10 MB в `compose.yaml`.
- Раз в неделю проверяйте `df -h`, `sudo docker compose ps -a` и health endpoint.
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
- Приватность пользователей описывает публичная страница `/privacy.html`: она
  собирается в образ frontend из `frontend/public/privacy.html` и не требует
  отдельных сервисов. При изменении политики обновляйте версию и дату редакции
  на странице.
- Telegram обрабатывает собственные данные (идентификация, доставка, storage
  adapter) по своей политике — это явно оговорено в тексте политики.
- Проверка после deploy: `curl -fsS https://app.example.com/privacy.html | head`
  отдаёт страницу политики; `DELETE /api/v1/session` без авторизации возвращает
  401 (см. также smoke-тесты в `docs/backlog.md`, PH-706).
