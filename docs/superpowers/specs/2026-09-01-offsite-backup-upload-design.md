# Дизайн PH-704B: offsite-выгрузка зашифрованного backup

**Дата:** 2026-09-01
**Статус:** утверждён для реализации; PH-704 остаётся открытой до реальных прогонов

## Цель

После атомарной публикации локального `*.dump.age` выгрузить его в приватное
внешнее S3-совместимое object storage и уметь восстановиться из внешнего
хранилища при полной недоступности VPS. Это закрывает главный пробел PH-704A:
потерю всего сервера, компрометацию root или удаление аккаунта у
хостинг-провайдера.

Схема dump, `age`-шифрование, имена файлов, локальный retention и
`restore-drill.sh` не меняются.

## Архитектура

Offsite-шаг встроен в существующий host-side `backup.sh` как последняя фаза
после локального retention и включается явным флагом. Выгрузку выполняет `rclone`
на хосте; конфигурация remote передаётся только через переменные окружения,
без конфиг-файла:

```text
*.dump.age (локально, уже зашифрован)
    -> rclone copy -> s3://BUCKET/PREFIX/ (idempotent: дозагружает пропущенное)
    -> rclone lsf  -> удалённый retention (только pohvala-postgres-*.dump.age)
```

Для off-host restore новый скрипт `fetch-offsite-archive.sh` скачивает самый
свежий (или явно указанный) архив из bucket на администраторский компьютер;
дальше работает неизменный `restore-drill.sh`. Новых долгоживущих сервисов нет:
это по-прежнему one-shot job в существующем systemd unit.

## Файлы и интерфейсы

- `ops/backup/offsite-common.sh` — общие для выгрузки и загрузки хелперы:
  чтение конфигурации, валидация, вызов `rclone`.
- `ops/backup/backup.sh` — добавлена фаза offsite-выгрузки после локального
  retention.
- `ops/backup/fetch-offsite-archive.sh` — скачивание архива из bucket для
  off-host restore drill.
- `ops/backup/offsite.env.example` — шаблон секретного конфига выгрузки.
- `ops/backup/pohvala-backup.service` — подключён опциональный
  `EnvironmentFile=-/etc/pohvali-backup/offsite.env`.
- `docs/backup.md` — разделы 4 и 6: включение выгрузки и off-host drill.

Переменные окружения (секретный файл `/etc/pohvali-backup/offsite.env`, root,
0600):

| Переменная | Default | Назначение |
| --- | --- | --- |
| `POHVALA_OFFSITE_ENABLED` | `0` | Выгрузка включается только явной `1` |
| `POHVALA_OFFSITE_ENDPOINT` | — | `https://` endpoint S3-совместимого storage |
| `POHVALA_OFFSITE_REGION` | — | Region/location constraint |
| `POHVALA_OFFSITE_BUCKET` | — | Имя приватного bucket |
| `POHVALA_OFFSITE_PREFIX` | — | Префикс внутри bucket (например `postgres`) |
| `POHVALA_OFFSITE_RETENTION_COUNT` | `14` | Число последних архивов в bucket |
| `POHVALA_OFFSITE_ACCESS_KEY_ID` | — | Access key с правами только на prefix |
| `POHVALA_OFFSITE_SECRET_ACCESS_KEY` | — | Secret access key |

## Инварианты безопасности

- Выгрузка выключена по умолчанию; без `offsite.env` поведение alpha (PH-704A)
  не меняется и `rclone` не требуется.
- Endpoint обязан быть `https://`; bucket, region и prefix проверяются по
  строгим шаблонам, чтобы исключить подмену remote-пути.
- Credentials живут только в root-owned файле 0600 и передаются в `rclone`
  через окружение процесса; в логи не выводятся.
- Удалённый retention удаляет только объекты `pohvala-postgres-*.dump.age`
  внутри заданного prefix; посторонние объекты не трогаются.
- Ошибка выгрузки не удаляет и не ломает локальный архив: unit становится
  failed, архив живёт по локальному retention, следующий запуск дозагружает
  пропущенное (копируются только отсутствующие объекты).
- Приватный `age`-identity никогда не покидает администраторский компьютер;
  bucket бесполезен без него даже при утечке access key.
- `fetch-offsite-archive.sh` не перезаписывает существующие файлы, проверяет
  непустой размер и ставит режим 0600.
- Bucket приватный: public access выключен на уровне провайдера; recommended
  policy ограничивает ключ префиксом `BUCKET/PREFIX/*` и `ListBucket` по
  префиксу.

## Приёмка PH-704B (реализация)

1. Без offsite-конфигурации `backup.sh` работает как раньше и не требует
   `rclone`.
2. Успешный запуск с включённой выгрузкой копирует архивы в
   `POHVALA:BUCKET/PREFIX` и оставляет последние
   `POHVALA_OFFSITE_RETENTION_COUNT` удалённых архивов, удаляя только
   `pohvala-postgres-*.dump.age`.
3. Ошибка `rclone` (copy/lsf/delete) возвращает ненулевой код, локальный архив
   сохраняется, journal содержит причину.
4. Неполная или неправильная offsite-конфигурация (не-https endpoint, пустые
   ключи, некорректные bucket/prefix/retention) отвергается с кодом 2 до
   создания dump.
5. `fetch-offsite-archive.sh` скачивает самый свежий или явно указанный архив,
   не перезаписывает существующие файлы, печатает абсолютный путь.
6. `compose.yaml` не изменился: offsite — часть host-side one-shot job.

## Открытые пункты до закрытия PH-704

Операционная активация вынесена в отдельную задачу PH-707 (см. `docs/backlog.md`):

- Реальная настройка bucket и включение выгрузки на production VPS.
- Первый успешный off-host restore drill из внешнего хранилища при недоступном
  VPS и запись в протокол `docs/backup.md`.
