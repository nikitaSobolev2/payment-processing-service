# Асинхронный микросервис обработки платежей

Сервис на FastAPI принимает платёжные запросы, сохраняет их с **транзакционным outbox**, публикует события `payments.new` в **RabbitMQ** (FastStream), обрабатывает их асинхронно (эмуляция шлюза + webhook с повторными попытками и **circuit breaker на Redis по нормализованному URL**), кэширует чтения в **Redis** и хранит **снимки состояния** для аудита.

## Архитектура

- **API**: `POST /api/v1/payments`, `GET /api/v1/payments/{id}` — для всех маршрутов нужен заголовок `X-API-Key`, для `POST` дополнительно `Idempotency-Key`.
- **Реле outbox** (`payment_service.workers.outbox_publisher`): опрашивает таблицу `outbox` через `SELECT … FOR UPDATE SKIP LOCKED`, публикует в topic-биржу `payments.events` с ключом маршрутизации `payments.new`, затем помечает строки опубликованными в той же транзакции БД (после успешной публикации в брокер).
- **Consumer** (`payment_service.workers.consumer`): читает `payments.new`, эмулирует шлюз (задержка 2–5 с, ~90% успеха), обновляет PostgreSQL с `SELECT … FOR UPDATE`, добавляет строку снимка, инвалидирует Redis, отправляет webhook. Повторы POST: экспоненциальная задержка с **верхней границей** (`WEBHOOK_BACKOFF_MAX_SECONDS`), отдельные таймауты **connect/read** для `httpx`. **Circuit breaker** (`WebhookCircuitBreaker`): состояние по каждому URL в Redis (закрыт → открыт после N подряд неудачных попыток → пауза T с → полуоткрыт с одной пробной отправкой); при «открытом» breaker запросы к этому URL не выполняются (общий с кэшем клиент Redis в `build_payment_facade_dependencies`). После **3 неудачных попыток обработки** одного и того же сообщения полезная нагрузка публикуется в очередь **DLQ** `payments.new.dlq` через default exchange.
- **Структура в духе DDD**: доменные сущности, DTO уровня приложения + `PaymentFacade`, репозитории инфраструктуры, интерфейсы FastAPI. Тексты ошибок API и репозитория — в [`src/payment_service/constants/errors.py`](src/payment_service/constants/errors.py).

## Требования

- Docker / Docker Compose
- Python 3.12+ (для локального запуска без Docker)

На Windows, если `pip install` падает в пути с не-ASCII символами, перед установкой зависимостей задайте `PYTHONUTF8=1`.

## Конфигурация

Скопируйте `.env.example` в `.env` и при необходимости измените значения. Важные переменные:

| Переменная | Назначение |
|------------|------------|
| `API_KEY` | Значение для заголовка `X-API-Key` |
| `DATABASE_URL` | `postgresql+asyncpg://…` |
| `REDIS_URL` | URL Redis (кэш платежей + circuit breaker webhook) |
| `RABBITMQ_URL` | URL AMQP |
| `WEBHOOK_MAX_RETRIES` | Число повторов POST webhook на одну попытку доставки (по умолчанию 3) |
| `WEBHOOK_BACKOFF_BASE_SECONDS` | База экспоненциальной задержки между повторами (с) |
| `WEBHOOK_BACKOFF_MAX_SECONDS` | Потолок задержки между повторами (с) |
| `WEBHOOK_CONNECT_TIMEOUT_SECONDS` / `WEBHOOK_READ_TIMEOUT_SECONDS` | Таймауты `httpx` для connect и read |
| `WEBHOOK_CB_FAILURE_THRESHOLD` | Подряд неудачных попыток POST до открытия circuit breaker |
| `WEBHOOK_CB_OPEN_SECONDS` | Длительность «открытого» состояния (не слать на URL) |
| `WEBHOOK_CB_KEY_TTL_SECONDS` | TTL ключа состояния в Redis |
| `CONSUMER_MAX_ATTEMPTS` | Попытки обработки сообщения до DLQ (по умолчанию 3) |

## Запуск через Docker Compose

```bash
cp .env.example .env
# задайте API_KEY и при необходимости другие переменные
docker compose up --build
```

Сервисы: `postgres`, `redis`, `rabbitmq`, `migrate` (Alembic `upgrade head`), `api`, `outbox-publisher`, `consumer`.

- API: `http://localhost:8000`
- Веб-интерфейс RabbitMQ: `http://localhost:15672` (guest/guest)

### Пример: создание платежа (202 Accepted)

В **cmd.exe** кавычки в `-d` можно оставить как ниже. В **PowerShell** вызывайте **`curl.exe`** (не алиас `Invoke-WebRequest`) и удобнее передать JSON в **одинарных** кавычках:

```powershell
curl.exe -s -X POST "http://localhost:8000/api/v1/payments" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: change-me-in-production" `
  -H "Idempotency-Key: demo-001" `
  -d '{"amount":"100.50","currency":"RUB","description":"Test","metadata":{"order":"1"},"webhook_url":"https://webhook.site/your-unique-url"}'
```

Классический вариант для `cmd.exe`:

```bash
curl -s -X POST "http://localhost:8000/api/v1/payments" ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: change-me-in-production" ^
  -H "Idempotency-Key: demo-001" ^
  -d "{\"amount\": \"100.50\", \"currency\": \"RUB\", \"description\": \"Test\", \"metadata\": {\"order\": \"1\"}, \"webhook_url\": \"https://webhook.site/your-unique-url\"}"
```

### Пример: получение платежа

```bash
curl -s "http://localhost:8000/api/v1/payments/<PAYMENT_ID>" ^
  -H "X-API-Key: change-me-in-production"
```

## Локальная разработка (без Docker)

1. Запустите локально PostgreSQL, Redis и RabbitMQ.
2. `python -m venv .venv` и активируйте окружение.
3. `pip install -r requirements.txt` (при необходимости на Windows используйте `PYTHONUTF8=1`).
4. Экспортируйте переменные окружения или используйте `.env` в корне проекта.
5. `set PYTHONPATH=src` (Windows) или `export PYTHONPATH=src` (Unix).
6. `alembic upgrade head`
7. API: `uvicorn payment_service.interfaces.api.main:app --reload`
8. Outbox: `python -m payment_service.workers.outbox_publisher`
9. Consumer: `python -m payment_service.workers.consumer`

## Тесты и линтер

Используйте виртуальное окружение проекта (`.venv`). На Windows: `.venv\Scripts\python.exe`.

```bash
set PYTHONPATH=src
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m pytest tests/unit tests/integration -v
```

## Очереди и DLQ

- **Основная очередь**: `payments.new` (привязана к topic-бирже `payments.events`, ключ маршрутизации `payments.new`).
- **DLQ**: `payments.new.dlq` — сюда consumer публикует сообщения после повторных сбоев обработки (это не то же самое, что серверный DLX в RabbitMQ; публикация вручную через default exchange).

## Лицензия

Проект распространяется на условиях **[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)** (идентификатор SPDX: `PolyForm-Noncommercial-1.0.0`). Это **не** самописная лицензия: текст взят из проекта [PolyForm](https://polyformproject.org/).

Разрешено использование в **некоммерческих** целях (в т.ч. личное обучение, исследования, хобби; для ряда некоммерческих и публичных организаций — см. текст лицензии). **Коммерческое использование** (включая типичное корпоративное продуктовое использование в прибыли) **не входит** в разрешённые цели и требует отдельного разрешения правообладателя. Полный текст — в файле [`LICENSE`](LICENSE).
