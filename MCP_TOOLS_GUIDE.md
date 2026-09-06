# Silpo MCP — Як Колити Тули

## Підключення

```python
import httpx2
from dotenv import load_dotenv
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent
import os, json, asyncio

load_dotenv("src/.env")
TOKEN = os.getenv("SILPO_MCP_TOKEN")

async with httpx2.AsyncClient(
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=httpx2.Timeout(30.0, read=300.0),
    follow_redirects=True,
) as http_client:
    transport = streamable_http_client("https://mcp.silpo.ua/mcp", http_client=http_client)
    async with Client(transport) as client:
        result = await client.call_tool("tool_name", arguments={...})
        # result.content → список TextContent блоків
        # result.is_error → bool
        text = result.content[0].text  # JSON string
        data = json.loads(text)
```

---

## Порядок Виклику Тулів

### Крок 1 — Чи є кошик?

```python
await client.call_tool("silpo_get_my_shopping_cart")
```

Відповідь:
```json
{"success": true, "shoppingCartId": null, "exists": false}
```

- `exists: true` → маємо `shoppingCartId`, переходимо до Кроку 3
- `exists: false` → треба створити кошик, переходимо до Кроку 2

---

### Крок 2 — Створення кошика (тільки якщо exists=false)

#### 2a. Знайти адресу

```python
await client.call_tool("silpo_find_address", arguments={
    "address": "Київ, вулиця Хрещатик, 1"
})
```

Відповідь — ключ `addresses[]`:
```json
{
  "city": "Київ",
  "street": "вулиця Хрещатик",
  "houseNumber": "30/1",
  "district": "Центр",
  "latitude": 50.44747065,
  "longitude": 30.521505797601343
}
```

Зберігаємо: `latitude`, `longitude`, `city`, `street`, `houseNumber`, `district`.

#### 2b. Доступні типи доставки

```python
await client.call_tool("silpo_get_available_delivery_types", arguments={
    "latitude": 50.44747065,
    "longitude": 30.521505797601343
})
```

**УВАГА: ключ у відповіді — `options`, НЕ `deliveryTypes`.**

```json
{
  "options": [
    {"deliveryType": "DeliveryHome", "branchId": "1edb6b38-..."},
    {"deliveryType": "WideAssortDelivery", "branchId": "1edee42d-..."},
    {"deliveryType": "B2B", "branchId": "1ee11bac-..."},
    {"deliveryType": "NovaPoshta", "branchId": null},
    {"deliveryType": "SelfPickup", "branchId": null}
  ]
}
```

Для демо беремо `DeliveryHome` — він має `branchId`.

#### 2c. Знайти таймслот

```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

await client.call_tool("silpo_get_time_slots", arguments={
    "branchId": "1edb6b38-...",
    "deliveryTypes": ["DeliveryHome"],
    "limit": 25,
    "start": now  # "2026-09-06T14:30:00Z"
})
```

**УВАГА: `start` — чистий ISO формат з `Z`. Python `.isoformat()` з мікросекундами дає 400 Bad Request.**

Відповідь — ключ `slots[]`:
```json
{
  "start": "2026-09-06T13:30:00+00:00",
  "end": "2026-09-06T15:00:00+00:00",
  "available": true,
  "deliveryType": "DeliveryHome",
  "deliveryCost": 99,
  "minOrderCost": 799,
  "maxWeight": 30
}
```

Беремо перший слот де `available: true`. Зберігаємо `start` і `end`.

#### 2d. Створити кошик

```python
await client.call_tool("silpo_create_shopping_cart", arguments={
    "addressType": "house",
    "latitude": 50.44747065,    # float, не string
    "longitude": 30.521505797601343,
    "city": "Київ",
    "street": "вулиця Хрещатик",
    "house": "30/1",            # houseNumber → house
    "district": "Центр",
    "deliveryType": "DeliveryHome",
    "timeslot": {
        "start": "2026-09-06T13:30:00+00:00",
        "end": "2026-09-06T15:00:00+00:00"
    },
    "branchId": "1edb6b38-..."
})
```

Відповідь:
```json
{"success": true, "shoppingCartId": "a02f6327-..."}
```

---

### Крок 3 — Деталі кошика

```python
await client.call_tool("silpo_get_shopping_cart_by_id", arguments={
    "shoppingCartId": "a02f6327-..."
})
```

Звідси витягуємо **все** для подальших викликів:

```
branchId     = cart.shipments[0].branchId
companyId    = cart.shipments[0].companyId
deliveryType = cart.deliveryType
timeslotStart = cart.timeslot.start
timeslotEnd   = cart.timeslot.end
totalAfterDiscounts = cart.calculation.totalAfterDiscounts
validations  = cart.calculation.validations[]
```

Також перевіряємо:
- `calculation.validations[]` — помилки блокують checkout
- `calculation.delivery.deliveryExpressByPromise` — чи доступна експрес-доставка
- `loyalty.bonusAvailable` — балабонуси для оплати

---

### Крок 4 — Персоналізація (паралельно)

```python
# Дієтичні обмеження
await client.call_tool("silpo_get_my_food_restrictions")
# → {"restrictions": []}

# Улюблені товари
await client.call_tool("silpo_get_my_favorites", arguments={
    "branchId": "...",
    "deliveryType": "DeliveryHome",
    "timeslotStart": "2026-09-06T13:30:00+00:00",
    "limit": 25
})
# → {"products": [...]}
```

---

### Крок 5 — Пошук продуктів

#### Batch пошук (основний)

```python
await client.call_tool("silpo_find_products_batch", arguments={
    "branchId": "...",
    "deliveryType": "DeliveryHome",
    "timeslotStart": "2026-09-06T13:30:00+00:00",
    "timeslotEnd": "2026-09-06T15:00:00+00:00",
    "products": ["піца", "чіпси", "вино біле сухе", "хумус", "сир", "лимонад"],
    "limit": 5
})
```

Відповідь — ключ `queries[]`:
```json
{
  "query": "піца",
  "totalFound": 10,
  "products": [
    {
      "id": "1f05d751-...",          // productId для кошика
      "name": "Піца Шимеджі...",
      "slug": "pitsa-shymedzhi-...",
      "price": 359,
      "stock": 4,
      "available": true,
      "weighted": false,
      "step": 1,                     // мін. крок кількості
      "displayRatio": "500г",        // що саме в одиниці
      "companyId": "1ec88c5d-...",   // для add_to_cart
      "branchId": "1edb6b38-...",   // для add_to_cart
      "externalProductId": 991721    // для пошуку по article code
    }
  ]
}
```

**Для кошика потрібні 3 поля з product: `id`, `companyId`, `branchId`.**

#### Пошук з фільтрами / по акціях

```python
await client.call_tool("silpo_get_products", arguments={
    "branchId": "...",
    "deliveryType": "DeliveryHome",
    "timeslotStart": "...",
    "timeslotEnd": "...",
    "mustHavePromotion": True,
    "limit": 10,
    "sortBy": "popularity"
})
```

Відповідь — ключ `products[]`, аналогічна структура.

---

### Крок 6 — Акції

```python
await client.call_tool("silpo_get_promotions", arguments={
    "branchId": "...",
    "deliveryType": "DeliveryHome",
    "timeslotStart": "...",
    "timeslotEnd": "..."
})
```

Відповідь — `promotions[]`:
```json
{"code": "only_online", "title": "Тільки Онлайн", "productCount": 1401}
```

`code` передається в `silpo_get_products(promotionCode=...)`.

---

### Крок 7 — Додати товари в кошик

```python
await client.call_tool("silpo_add_or_update_cart_products", arguments={
    "shoppingCartId": "a02f6327-...",
    "products": [
        {
            "productId": "1f05d751-...",
            "companyId": "1ec88c5d-...",
            "branchId": "1edb6b38-...",
            "quantity": 1,          # для штучних: ціле число
            "addQuantity": False    # False = замінити, True = додати до існуючого
        },
        {
            "productId": "...",
            "companyId": "...",
            "branchId": "...",
            "quantity": 0.3,        # для вагових: кратно step (тут step=0.1)
            "addQuantity": False
        }
    ]
})
```

**ОБОВ'ЯЗКОВО після цього → Крок 3 (silpo_get_shopping_cart_by_id) для верифікації.**

`success: true` **НЕ** означає що все ок — перевищення stock з'явиться тільки у `validations[]`.

---

### Крок 8 — Видалити товар (якщо over budget)

```python
await client.call_tool("silpo_remove_cart_products", arguments={
    "shoppingCartId": "a02f6327-...",
    "products": [
        {"productId": "1f0cd807-..."}
    ]
})
```

Після цього знову → Крок 3 для верифікації.

---

### Крок 9 — Оновити кошик (timeslot/delivery/bonuses)

```python
await client.call_tool("silpo_update_shopping_cart", arguments={
    "shoppingCartId": "...",
    "deliveryType": "DeliveryHome",
    "timeslot": {"start": "...", "end": "..."},
    "address": { /* повністю скопіювати з cart response */ },
    "shipments": [{"companyId": "...", "branchId": "..."}],
    "bonusRequested": 40.36  # або null
})
```

---

## Підсумок: Правила та Пастки

| Правило | Деталі |
|---------|--------|
| Ключ delivery types | `options`, не `deliveryTypes` |
| Формат часу для `start` | `strftime("%Y-%m-%dT%H:%M:%SZ")`, не `.isoformat()` |
| Після будь-якої мутації кошика | ОБОВ'ЯЗКОВО `get_shopping_cart_by_id` |
| Мін. сума замовлення | ₴799 (інакше error в validations) |
| `houseNumber` → `house` | Mapping при create_shopping_cart |
| `latitude`/`longitude` | float при create, string у cart response |
| Вагові товари | `quantity` кратна `step`, `displayRatio` = що в одиниці |
| Пластикові пакети | Ніколи не додавати |
| `success: true` при add_to_cart | Не гарантія — stock errors в validations |
| Часи від API | UTC (+00:00), показувати юзеру в локальному часі |
| Доставка | base ₴99, від ₴1399 → ₴69, від ₴1999 → ₴1 |
| Експрес | ~59 хв, ₴119 (якщо `isAvailable: true`) |

## Повний Flow Для Демо

```
1. get_my_shopping_cart
   ├─ exists: true  → 3
   └─ exists: false → 2a → 2b → 2c → 2d → 3
3. get_shopping_cart_by_id  → branchId, deliveryType, timeslot
4. get_my_food_restrictions + get_my_favorites (паралельно)
5. find_products_batch      → шукаємо продукти для меню
6. get_promotions           → знижки для оптимізації бюджету
7. get_products             → промо-товари для добивання бюджету
8. add_or_update_cart_products → додаємо в кошик
9. get_shopping_cart_by_id  → верифікація (total, validations)
   ├─ over budget → remove_cart_products → 9
   ├─ under budget → add ще товарів → 8
   └─ validations ok → фінальна відповідь
```
