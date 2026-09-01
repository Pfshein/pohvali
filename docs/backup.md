# Backup и восстановление PostgreSQL

Этот runbook реализует PH-704A для закрытой альфы: семь последних зашифрованных
архивов хранятся на production VPS вне Docker volume PostgreSQL. Это помогает
после ошибочного удаления, неудачной миграции или повреждения `postgres_data`, но
не спасает при потере или компрометации всего VPS.

До публичного запуска нужен PH-704B: выгрузка тех же `*.dump.age` в приватное
внешнее object storage с полностью выключенным public access.

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
sudo install -m 0600 /opt/pohvali/ops/backup/backup.env.example \
  /etc/pohvali-backup/config
sudo install -m 0644 /opt/pohvali/ops/backup/pohvala-backup.service \
  /etc/systemd/system/pohvala-backup.service
sudo install -m 0644 /opt/pohvali/ops/backup/pohvala-backup.timer \
  /etc/systemd/system/pohvala-backup.timer
sudo systemctl daemon-reload
```

В `/etc/pohvali-backup/config` нет приватного ключа; поддерживаемая настройка
systemd job — только число сохраняемых архивов. Пути намеренно зафиксированы:
checkout `/opt/pohvali` доступен unit только для чтения, backup-каталог — для
записи. Root запускает установленную root-owned копию script из
`/usr/local/libexec`, поэтому пользователь `deploy` не может подменить её между
запусками timer.

Если `backup.sh` изменился после обновления репозитория, после review повторите:

```bash
sudo install -o root -g root -m 0755 /opt/pohvali/ops/backup/backup.sh \
  /usr/local/libexec/pohvala-backup/backup.sh
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
суточного окна и требует проверки journal/места на диске. Не выводите содержимое
`.env`, recipient-файла или архива в логи и тикеты.

## 4. Restore drill на компьютере администратора

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

## 5. Протокол restore drill

После каждого реального прогона добавляйте строку в таблицу. Не записывайте
Telegram ID, содержимое записей, ключи или другие секреты.

| Дата UTC | Архив UTC | Среда восстановления | Результат | Длительность | Проверил |
| --- | --- | --- | --- | --- | --- |
| — | — | — | Первый production drill ещё не выполнен | — | — |

PH-704A можно отметить завершённой только после замены этой строки записью об
успешном восстановлении production-архива. PH-704 целиком закрывается только
после PH-704B и отдельной проверки восстановления при недоступном VPS.
