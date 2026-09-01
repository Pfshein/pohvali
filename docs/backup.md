# Backup и восстановление PostgreSQL

Этот runbook реализует PH-704A и PH-704B. PH-704A: семь последних зашифрованных
архивов хранятся на production VPS вне Docker volume PostgreSQL — это помогает
после ошибочного удаления, неудачной миграции или повреждения `postgres_data`.
PH-704B: те же `*.dump.age` выгружаются в приватное внешнее S3-совместимое
object storage с полностью выключенным public access — это спасает при потере
или компрометации всего VPS.

Обе части закрываются только после реальных restore drill: локального и
off-host (архив берётся из внешнего хранилища при недоступном VPS) — см. раздел
с протоколом ниже.

## 1. Создать ключ вне VPS

На доверенном компьютере администратора установите `age` и создайте отдельный
ключ только для backup:

```bash
umask 077
age-keygen -o pohvala-backup-identity.txt
age-keygen -y pohvala-backup-identity.txt > pohvala-backup-recipient.txt
```

`pohvala-backup-identity.txt` — приватный ключ. Не копируйте его на VPS, не
коммитьте и сохраните резервную копию в менеджере секретов. Потеря identity
делает все архивы невосстановимыми.

`pohvala-backup-recipient.txt` содержит только публичный recipient. Его можно
скопировать на сервер:

```bash
scp pohvala-backup-recipient.txt deploy@app.example.com:/tmp/pohvala-backup-recipient.txt
```

## 2. Установить backup job на VPS

После входа пользователем `deploy`:

```bash
sudo apt update
sudo apt install -y age
sudo install -d -m 0700 /etc/pohvali-backup
sudo install -d -m 0700 /var/backups/pohvali/postgres
sudo install -d -m 0755 /usr/local/libexec/pohvala-backup
sudo install -m 0600 /tmp/pohvala-backup-recipient.txt \
  /etc/pohvali-backup/recipients.txt
sudo rm -f /tmp/pohvala-backup-recipient.txt
sudo install -o root -g root -m 0755 /opt/pohvali/ops/backup/backup.sh \
  /usr/local/libexec/pohvala-backup/backup.sh
sudo install -o root -g root -m 0755 /opt/pohvali/ops/backup/offsite-common.sh \
  /usr/local/libexec/pohvala-backup/offsite-common.sh
sudo install -m 0600 /opt/pohvali/ops/backup/backup.env.example \
  /etc/pohvali-backup/config
sudo install -m 0644 /opt/pohvali/ops/backup/pohvala-backup.service \
  /etc/systemd/system/pohvala-backup.service
sudo install -m 0644 /opt/pohvali/ops/backup/pohvala-backup.timer \
  /etc/systemd/system/pohvala-backup.timer
sudo systemctl daemon-reload
```

В `/etc/pohvali-backup/config` нет приватного ключа; поддерживаемая настройка
systemd job — только число сохраняемых архивов. Настройки offsite-выгрузки
живут в отдельном файле `/etc/pohvali-backup/offsite.env` (раздел 4). Пути
намеренно зафиксированы: checkout `/opt/pohvali` доступен unit только для
чтения, backup-каталог — для записи. Root запускает установленную root-owned
копию script из `/usr/local/libexec`, поэтому пользователь `deploy` не может
подменить её между запусками timer.

Если `backup.sh` или `offsite-common.sh` изменились после обновления
репозитория, после review повторите установку обеих копий:

```bash
sudo install -o root -g root -m 0755 /opt/pohvali/ops/backup/backup.sh \
  /usr/local/libexec/pohvala-backup/backup.sh
sudo install -o root -g root -m 0755 /opt/pohvali/ops/backup/offsite-common.sh \
  /usr/local/libexec/pohvala-backup/offsite-common.sh
sudo systemctl start pohvala-backup.service
```

Сначала выполните backup вручную:

```bash
sudo systemctl start pohvala-backup.service
sudo systemctl status pohvala-backup.service --no-pager
sudo journalctl -u pohvala-backup.service -n 50 --no-pager
sudo find /var/backups/pohvali/postgres -maxdepth 1 -type f \
  -name 'pohvala-postgres-*.dump.age' -printf '%TY-%Tm-%Td %TH:%TM %s %f\n'
```

Успешный unit имеет состояние `inactive (dead)` после выхода с кодом 0 — это
нормально для `Type=oneshot`. В каталоге должен появиться непустой
`pohvala-postgres-<UTC timestamp>.dump.age`, без `.partial` и plaintext dump.

После ручной проверки включите ежедневный timer:

```bash
sudo systemctl enable --now pohvala-backup.timer
systemctl list-timers pohvala-backup.timer --all
```

Timer запускается ежедневно в `03:15 UTC` и догоняет пропущенный запуск после
выключения VPS. Скрипт оставляет семь последних успешных архивов. Retention не
выполняется, если новый backup завершился ошибкой.

## 3. Еженедельная проверка

```bash
sudo systemctl is-failed pohvala-backup.service
systemctl list-timers pohvala-backup.timer --all
sudo journalctl -u pohvala-backup.service --since='8 days ago' --no-pager
sudo find /var/backups/pohvali/postgres -maxdepth 1 -type f \
  -name 'pohvala-postgres-*.dump.age' -mmin -1500 -size +0c -print -quit \
  | grep -q .
df -h /var/backups/pohvali/postgres
```

`systemctl is-failed` должен вернуть `inactive`, а pipeline `find | grep` — код 0,
если есть непустой архив моложе 25 часов. Ненулевой код означает нарушение
суточного окна и требует проверки journal/места на диске. Если offsite-выгрузка
включена, в journal за последние сутки должна быть строка
`offsite upload complete`; её отсутствие при успешном локальном backup означает
проблему выгрузки (сеть, credentials, bucket). Не выводите содержимое `.env`,
recipient-файла или архива в логи и тикеты.

## 4. Offsite-выгрузка во внешнее хранилище (PH-704B)

Offsite-шаг догружает уже созданные и зашифрованные `*.dump.age` в приватный
bucket через `rclone`. Схема dump, шифрование, имена файлов и restore script не
меняются. Выгрузка включается только явным флагом в `/etc/pohvali-backup/offsite.env`.

### 4.1 Подготовить bucket

Подойдёт любое S3-совместимое object storage с TLS endpoint (например, Hetzner
Object Storage в регионе ЕС). Требования:

- Bucket приватный: public access полностью выключен, объекты доступны только
  по credentials.
- Отдельный access key только для этого bucket: права `PutObject`, `GetObject`,
  `DeleteObject` на `BUCKET/PREFIX/*` и `ListBucket` по префиксу `PREFIX/`.
  Если провайдер поддерживает IAM-политики, ограничьте ключ примерно так:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::pohvali-backup"],
      "Condition": {"StringLike": {"s3:prefix": ["postgres/*"]}}
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::pohvali-backup/postgres/*"]
    }
  ]
}
```

Ключ с меньшими правами лучше широкого: утечка ключа даёт доступ только к
зашифрованным архивам в одном префиксе bucket. Архивы всё равно остаются
`age`-зашифрованными — приватный ключ на S3 не попадает никогда.

### 4.2 Включить выгрузку на VPS

```bash
sudo apt update
sudo apt install -y rclone
sudo install -m 0600 /opt/pohvali/ops/backup/offsite.env.example \
  /etc/pohvali-backup/offsite.env
sudoedit /etc/pohvali-backup/offsite.env
sudo systemctl start pohvala-backup.service
sudo journalctl -u pohvala-backup.service -n 30 --no-pager
```

Заполните endpoint (`https://…`), region, bucket, prefix, access key и secret
key. Успешный запуск завершается строками `backup complete: …` и
`offsite upload complete: POHVALA:BUCKET/PREFIX`. Дополнительная проверка, что
архив реально скачивается из bucket:

```bash
sudo install -d -m 0700 /tmp/pohvala-offsite-check
sudo bash -c '. /etc/pohvali-backup/offsite.env; \
  exec bash /opt/pohvali/ops/backup/fetch-offsite-archive.sh /tmp/pohvala-offsite-check'
sudo rm -rf /tmp/pohvala-offsite-check
```

Поведение при сбое: ошибка выгрузки делает unit failed (видно в journal), но
локальный архив сохраняется по обычной retention-политике; следующий успешный
запуск дозагружает пропущенное, потому что `rclone copy` копирует только
отсутствующие объекты. Удалённое хранение: `POHVALA_OFFSITE_RETENTION_COUNT`
(по умолчанию 14) последних архивов; удаляются только объекты с именем
`pohvala-postgres-*.dump.age` внутри заданного prefix.

## 5. Restore drill на компьютере администратора

Проверка выполняется минимум после установки и затем раз в месяц. Production
контейнер и volume не используются: script создаёт отдельный PostgreSQL 17 без
опубликованных портов и всегда удаляет его.

На VPS выберите свежий архив и временно скопируйте его в home пользователя:

```bash
sudo install -m 0600 -o deploy -g deploy \
  /var/backups/pohvali/postgres/pohvala-postgres-20260901T031500Z.dump.age \
  /home/deploy/pohvala-restore-test.dump.age
```

На администраторском компьютере с Docker и `age`:

```bash
scp deploy@app.example.com:/home/deploy/pohvala-restore-test.dump.age .
cd /path/to/pohvali
bash ops/backup/restore-drill.sh \
  "$PWD/../pohvala-restore-test.dump.age" \
  "$PWD/../pohvala-backup-identity.txt"
```

Ожидаемый результат:

```text
restore drill passed: archive restored into isolated PostgreSQL
```

После проверки удалите временную серверную копию:

```bash
ssh deploy@app.example.com \
  'sudo rm -f /home/deploy/pohvala-restore-test.dump.age'
```

Сам архив в `/var/backups/pohvali/postgres` остаётся по retention-политике.

## 6. Off-host restore drill (PH-704B, VPS недоступен)

Проверка выполняется перед публичным запуском и затем минимум раз в квартал.
Сценарий: VPS полностью недоступен (удалён, скомпрометирован или потерян),
восстановление идёт напрямую из внешнего хранилища.

На администраторском компьютере нужны Docker, `age`, `rclone` и файл
`offsite.env` — копия серверного `/etc/pohvali-backup/offsite.env` (режим 0600,
хранить вне репозитория). Затем из checkout репозитория:

```bash
install -d -m 0700 "$HOME/pohvala-offsite-drill"
set -a; . ./offsite.env; set +a
archive="$(bash ops/backup/fetch-offsite-archive.sh "$HOME/pohvala-offsite-drill")"
printf 'fetched: %s\n' "$archive"
bash ops/backup/restore-drill.sh "$archive" "$PWD/../pohvala-backup-identity.txt"
rm -rf "$HOME/pohvala-offsite-drill"
```

`fetch-offsite-archive.sh` скачивает самый свежий архив из bucket (или
конкретный, если передать имя вторым аргументом), проверяет, что файл непустой,
и печатает его путь. Дальше работает обычный `restore-drill.sh` — расшифровка
`age`-ключом и восстановление в одноразовый PostgreSQL без портов. Ожидаемый
результат тот же:

```text
restore drill passed: archive restored into isolated PostgreSQL
```

Если fetch завершился ошибкой `no offsite archives found` — bucket пуст,
выгрузка на production не работает. Ключевое отличие от раздела 5: archive
берётся из внешнего хранилища, а не с VPS, то есть проверяет весь путь
восстановления при потере сервера.

## 7. Протокол restore drill

После каждого реального прогона добавляйте строку в таблицу. Off-host прогоны
(раздел 6) помечайте в колонке среды как `off-host (внешнее хранилище)`. Не
записывайте Telegram ID, содержимое записей, ключи или другие секреты.

| Дата UTC | Архив UTC | Среда восстановления | Результат | Длительность | Проверил |
| --- | --- | --- | --- | --- | --- |
| — | — | — | Первый production drill ещё не выполнен | — | — |

PH-704A можно отметить завершённой только после замены этой строки записью об
успешном восстановлении production-архива. PH-704B закрывается только после
успешного off-host восстановления из внешнего хранилища при недоступном VPS;
PH-704 целиком закрывается после обоих прогонов. Операционная активация выгрузки
на production (реальный bucket и `offsite.env` на VPS) — задача PH-707.
