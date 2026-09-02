# Дизайн PH-801: роли пользователей и admin-авторизация

**Дата:** 2026-09-02  
**Статус:** утверждён для реализации

## Цель

Заложить безопасный фундамент будущей админ-панели: каждый аккаунт имеет одну
серверную роль `user` или `admin`, а административные операции проверяют роль в
PostgreSQL. Telegram `initData` по-прежнему подтверждает личность пользователя,
но клиент и Telegram payload никогда не определяют его полномочия.

PH-801 не создаёт визуальную админ-панель. После этой задачи следующая задача
сможет добавлять `/api/v1/admin/*` и admin UI поверх одного общего механизма
авторизации.

## Текущее состояние

- `users` хранит `id`, `telegram_id`, `timezone`, активного маскота и дату
  создания; роли нет.
- `/add_mascot` считает администратором Telegram ID из `TELEGRAM_ADMIN_IDS`.
- `POST /api/v1/session` возвращает только внутренний UUID и timezone.
- Каждый Mini App API-запрос аутентифицируется свежим Telegram `initData`;
  собственного JWT нет и в PH-801 он не появляется.

Проверка через `TELEGRAM_ADMIN_IDS` является отдельным исключением для одной
команды и не подходит для будущей админ-панели. PH-801 удаляет это исключение.

## Границы задачи

### Входит

1. Колонка `users.role` со значениями `user` и `admin`.
2. Безопасная миграция существующих аккаунтов в `user`.
3. Серверная команда назначения и снятия роли существующему пользователю.
4. Общая FastAPI dependency для будущих admin-endpoint'ов.
5. Поле `role` в ответе `POST /api/v1/session` и его frontend transport type.
6. Перевод `/add_mascot` с env-списка на роль в БД.
7. Удаление `TELEGRAM_ADMIN_IDS` из runtime-конфигурации и документации.
8. Unit-, API- и PostgreSQL integration-тесты всех новых границ.

### Не входит

- визуальная админ-панель и ссылка на неё;
- список, поиск, блокировка или удаление других пользователей;
- HTTP API изменения ролей;
- роли `moderator`, `support`, набор permissions или несколько ролей у одного
  пользователя;
- доступ администратора к чужим похвалам, ключам восстановления, Telegram
  профилям или ciphertext;
- отдельная admin-аутентификация, JWT, Redis или новый сервис.

## Модель роли

В `backend/app/modules/users/models.py` определяется строковый enum:

```python
class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
```

`User.role` хранится как `VARCHAR(16) NOT NULL` с Python default и server
default `user`. В БД обязателен `CHECK (role IN ('user', 'admin'))`.
PostgreSQL native enum не используется: строка с check constraint проще для
последующих forward-only миграций.

У одного пользователя ровно одна роль. `admin` не является отдельным видом
аккаунта: администратор сохраняет все обычные пользовательские возможности.
Индекс по `role` в PH-801 не нужен, потому что задача не выбирает списки
пользователей по роли.

## Миграция

Новая ревизия следует сразу после `20260902_0010`.

Upgrade:

1. добавить `users.role VARCHAR(16)` с `server_default='user'` и `nullable=False`;
2. добавить именованный check constraint для `user/admin`;
3. существующие строки автоматически получают `user` за счёт server default.

Server default остаётся после миграции: прямые безопасные inserts из
операционных скриптов также создают обычного пользователя. Downgrade удаляет
constraint, затем колонку; другие данные пользователя не трогает.

Миграция не читает `.env` и никого автоматически не повышает. Это исключает
скрытую смену прав при deploy.

## Источник полномочий

PostgreSQL — единственный источник роли. Ни одно из следующих значений не даёт
admin-доступ:

- поле `role` в request body;
- Telegram username, имя или chat title;
- Telegram ID, просто присутствующий в `.env`;
- данные localStorage/CloudStorage;
- роль из предыдущего ответа `/session`.

Backend каждый раз загружает актуального пользователя по проверенному
`identity.telegram_id` и принимает решение по `users.role`.

Обычный `open_session` при conflict обновляет только timezone. Он не должен
сбрасывать или повышать роль. Это отдельный обязательный regression-test.

## Назначение первого администратора

Роль меняется только из shell на VPS:

```bash
sudo docker compose exec -T backend \
  python -m app.modules.users.set_role 123456789 admin
```

Снятие роли:

```bash
sudo docker compose exec -T backend \
  python -m app.modules.users.set_role 123456789 user
```

В обеих командах `123456789` заменяется на нужный Telegram ID.

Команда принимает ровно два позиционных аргумента: положительный integer
Telegram ID и `user|admin`. Она:

1. подключается через существующий `DATABASE_URL`;
2. меняет роль только уже существующей строки `users`;
3. выполняет изменение в одной транзакции;
4. завершается кодом `0` при успехе;
5. завершается ненулевым кодом с спокойной инструкцией сначала открыть бота или
   Mini App, если пользователь не найден;
6. не создаёт пользователя и не меняет timezone;
7. не печатает DATABASE_URL, Telegram ID или другие секреты.

Команда идемпотентна: повторное назначение той же роли успешно и не создаёт
дополнительных данных. Отдельного audit log в PH-801 нет; shell-доступ к VPS
является административной границей этой версии.

## Mini App session contract

Успешный `POST /api/v1/session` возвращает:

```json
{
  "id": "0ecaf26f-ee72-4f06-ae79-41198dd1ac6d",
  "timezone": "Europe/Moscow",
  "role": "user"
}
```

Backend schema и frontend `SessionProfile` принимают только `user|admin`.
Frontend transport валидирует поле и возвращает его вызывающему коду. В
PH-801 интерфейс роль не отображает и маршрутизацию не меняет.

Поле в ответе нужно только для будущего условного показа admin UI. Оно не
является защитой: любой будущий admin endpoint всё равно использует серверную
проверку роли.

## Общая FastAPI admin dependency

В `backend/app/api/dependencies.py` добавляется async dependency, концептуально:

```python
async def require_admin_user(
    identity: TelegramAuth,
    session: DatabaseSession,
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id=identity.telegram_id)
    if user is None or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

AdminUser = Annotated[User, Depends(require_admin_user)]
```

Неизвестный пользователь и обычный пользователь получают одинаковый `403`,
чтобы endpoint не раскрывал наличие аккаунта. Неверный Telegram `initData`
по-прежнему даёт `401` раньше проверки роли.

Dependency нельзя подменять проверкой роли во frontend. Все будущие
`/api/v1/admin/*` обязаны принимать `AdminUser`.

## Авторизация `/add_mascot`

Webhook защищён secret path/header, но это подтверждает только доставку от
Telegram. Автор команды определяется по `message.from.id`, затем загружается
из `users`.

Порядок обработки admin-команды:

1. определить, что update похож на private `/add_mascot`, и безопасно извлечь
   `chat_id` и `from.id`;
2. проверить `from.id` через `users.role`;
3. для отсутствующего/non-admin пользователя вернуть существующий спокойный
   отказ, не скачивая PNG и не вызывая catalog service;
4. только для admin разобрать аргументы, скачать и проверить PNG, затем вызвать
   `add_mascot`;
5. не логировать Telegram ID, caption, `file_id` или изображение.

Парсер `app/modules/bot/add_mascot.py` остаётся чистым и не обращается к БД.
Разрешение передаётся в него явным boolean `authorized`; список admin IDs в
парсер больше не передаётся. Для безопасной предварительной проверки добавляется
чистый helper, который возвращает actor ID только для private update с token
`/add_mascot` (с учётом суффикса `@botname`). Полная валидация формата остаётся
после проверки роли, поэтому не-admin всегда получает одинаковый отказ.

`TELEGRAM_ADMIN_IDS` после переключения удаляется из `Settings`, `.env.example`,
`compose.yaml`, README/deploy и тестовых fixtures. Fallback к env запрещён:
иначе появятся два противоречащих источника полномочий.

## Приватность и безопасность

- Роль — техническое поле доступа и допустимое расширение минимальной модели
  пользователя; это фиксируется в `docs/product-brief.md`.
- Администратор не получает новых read-path к пользовательским данным.
- `telegram_id` уже хранится для аутентификации, новые PII не добавляются.
- Логи HTTP/webhook не получают роль или Telegram ID.
- CLI не выводит переданный Telegram ID и не принимает DATABASE_URL аргументом.
- Account deletion удаляет строку `users`, поэтому отдельной очистки роли не
  требуется.

## Совместимость deploy

Миграция обратно совместима с предыдущим backend: лишняя колонка с default ему
не мешает. После выкладки все аккаунты сначала `user`, поэтому владелец должен
один раз выполнить `set_role ... admin`. До этого `/add_mascot` спокойно
отказывает, остальные функции приложения работают.

После успешного назначения `TELEGRAM_ADMIN_IDS` удаляется из production `.env`.
Его отсутствие больше не влияет на startup/config validation.

## Приёмка

1. Upgrade существующей БД добавляет валидную роль `user` каждой существующей
   строке без потери данных; clean upgrade и повторный upgrade зелёные.
2. БД не принимает `NULL` или произвольную роль.
3. Новый пользователь создаётся как `user`; повторный `/session` сохраняет
   назначенную `admin` роль и обновляет только timezone.
4. `/session` возвращает ровно `id`, `timezone`, `role`; frontend проверяет и
   возвращает роль, но визуально ничего не меняется.
5. Серверная команда переводит существующего пользователя `user ↔ admin`,
   идемпотентна и отказывает для неизвестного пользователя/невалидных аргументов.
6. Общая FastAPI dependency: валидный admin проходит; user и неизвестный
   пользователь получают одинаковый `403`; неверный initData получает `401`.
7. `/add_mascot` разрешён только `users.role=admin`; user/неизвестный не вызывает
   download/service. Изменение `.env` не выдаёт прав.
8. `TELEGRAM_ADMIN_IDS` отсутствует в исполняемом коде, Compose, env template и
   актуальных пользовательских инструкциях (исторические spec/plan PH-405 можно
   не переписывать).
9. В логах нет Telegram ID, caption, `file_id`, изображения или DATABASE_URL.
10. `ruff check .`, полный backend `pytest` с PostgreSQL и frontend
    `npm run check` проходят.
