# Definition of Done

Задача считается завершённой, когда:

- поведение соответствует acceptance criteria и product guardrails;
- автоматические тесты добавлены и проходят;
- frontend проходит typecheck, lint, unit tests и production build;
- backend проходит ruff и pytest; миграции накатываются на чистую PostgreSQL;
- нет секретов, plaintext praise, PII и request body в коде, фикстурах и логах;
- обработаны loading, empty, error и retry состояния пользовательского сценария;
- ключевой путь проверен в мобильном viewport и внутри Telegram test environment;
- изменение API отражено в OpenAPI и соседней frontend-модели;
- для миграции описан rollback или безопасный forward-fix;
- документация обновлена настолько, чтобы следующий разработчик мог продолжить без устного контекста.

