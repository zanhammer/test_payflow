# PayFlow

Асинхронный микросервис обработки платежей: REST API, RabbitMQ, transactional outbox, webhook-уведомления.

Клиент создаёт платёж через API и указывает `webhook_url`. Сервис сохраняет платёж, публикует событие в очередь, обрабатывает его в фоне (эмуляция платёжного шлюза) и отправляет результат на webhook.


## Быстрый старт (Docker)

### 1. Файл окружения для контейнеров

```bash
cp .env.example .env.docker
```

Отредактируй `.env.docker` — для Docker хосты сервисов из compose, не `localhost`:

> `API_KEY` — минимум 16 символов, не значение `change-me-to-a-real-secret`.

### 2. Запуск

```bash
docker compose up --build
```

При старте API автоматически выполняет `alembic upgrade head`.

## API

Все эндпоинты требуют заголовок **`X-API-Key`**.

### Создание платежа

```http
POST /api/v1/payments
X-API-Key: api-key
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json
```

```json
{
  "amount": "100.50",
  "currency": "USD",
  "description": "Test payment",
  "metadata": {"order_id": "42"},
  "webhook_url": "https://webhook.com/your-unique-id"
}
```

**Ответы:**

- `201 Created` — новый платёж
- `200 OK` — повтор с тем же `Idempotency-Key` и тем же телом
- `409 Conflict` — тот же ключ, другое тело
- `401 Unauthorized` — неверный `X-API-Key`


### Получение платежа

```http
GET /api/v1/payments/{payment_id}
X-API-Key: api-key
```


### Статусы платежа

- `pending` — создан, ждёт обработки consumer
- `completed` — успешно обработан (~90%)
- `failed` — обработка не удалась (~10%)

## Webhook

После обработки consumer отправляет **POST** на `webhook_url` из запроса создания:

```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "amount": "100.50",
  "currency": "USD",
  "processed_at": "2026-07-03T17:00:00Z"
}
```

При ошибке доставки — до 3 попыток с паузами 2 и 4 секунды. Ошибка webhook **не откатывает** статус в БД.


## RabbitMQ

- Exchange `payments` (direct) — маршрутизация событий
- Queue `payments.new` — новые платежи на обработку
- Exchange `payments.dlx` (fanout) — dead letter exchange
- Queue `payments.new.dlq` — сообщения после 3 неудачных попыток
