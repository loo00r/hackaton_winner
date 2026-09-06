# Silpo Tools Demo Analysis

## Контекст

Ціль демо: не shopping assistant, а автономний агент-організатор події.

Сценарій:

```text
Календар / mock event
-> агент розуміє подію
-> mock Telegram polling збирає вподобання гостей
-> агент планує меню
-> Silpo MCP знаходить реальні товари
-> агент збирає кошик під жорсткий бюджет
-> перевіряє кошик, таймслот, stock, validations
-> віддає готовий результат: меню, сума, залишок бюджету, checkout links
```

Важлива рамка: не створювати wrappers/registry/domain-layer наперед. Поки що достатньо одного agent loop, `tools.jsonl`, MCP client і сильного system prompt.

## Стан `tools.jsonl`

- Формат: JSONL / NDJSON, один OpenAI-style tool object на рядок.
- Кількість тулів: 40.
- Дублікатів назв: немає.
- Структура кожного рядка валідна: `type=function`, `function.name`, `function.description`, `function.parameters`.

Завантаження має бути line-by-line:

```python
tools = [json.loads(line) for line in open("src/tools.jsonl") if line.strip()]
```

## Мінімальний Набір Для Демо

Ці тули реально потрібні для першого сильного демо:

```text
silpo_get_my_shopping_cart
silpo_create_shopping_cart
silpo_get_shopping_cart_by_id
silpo_find_address
silpo_get_available_delivery_types
silpo_get_time_slots
silpo_find_products_batch
silpo_get_products
silpo_get_promotions
silpo_add_or_update_cart_products
silpo_remove_cart_products
silpo_get_my_food_restrictions
silpo_get_my_favorites
```

Умовно корисні, але не must-have:

```text
silpo_get_product_details
silpo_get_replacements
silpo_get_my_online_orders
silpo_get_my_offline_orders
silpo_get_product_sets
silpo_get_categories
silpo_get_categories_tree
silpo_get_category
```

Не давати моделі в першому демо:

```text
coupons, certificates, premium, loyalty, favorite mutations, Nova Poshta,
profile/family, broad branch browsing, popular categories
```

Причина: вони розширюють surface area, але не доводять основну ідею event agent.

## Оцінка Кожного Тула

| Tool | Demo | Важливість | Оцінка |
|---|---:|---:|---|
| `silpo_find_address` | брати | 5/5 | Потрібен, якщо створюємо cart з адресою або міняємо delivery location. |
| `silpo_get_time_slots` | брати | 5/5 | Критичний для delivery scheduler і обов'язкової перевірки cart timeslot. |
| `silpo_find_products_batch` | брати | 5/5 | Основний тул пошуку товарів для меню. Batch search краще за багато одиночних пошуків. |
| `silpo_get_products` | брати | 4/5 | Потрібен для промо, категорій, fallback-підбору і добивання бюджету. |
| `silpo_get_promotions` | брати | 4/5 | Добре показує business value: агент враховує акції і оптимізує кошик. |
| `silpo_get_popular_categories` | викинути | 1/5 | Для event demo майже не потрібен. Дає шум, а не дію. |
| `silpo_get_category` | умовно | 2/5 | Корисний тільки якщо йдемо через category browsing. Не потрібен у першому happy path. |
| `silpo_get_categories` | умовно | 2/5 | Може допомогти знайти категорії, але batch product search швидший для демо. |
| `silpo_get_categories_tree` | умовно | 2/5 | Занадто широкий тул. Може з'їсти контекст і час. |
| `silpo_get_my_shopping_cart` | брати | 5/5 | Стартова точка cart workflow. Без нього не можна правильно працювати з кошиком. |
| `silpo_create_shopping_cart` | брати | 5/5 | Потрібен, якщо кошика ще немає. Має складний workflow перед викликом. |
| `silpo_get_shopping_cart_by_id` | брати | 5/5 | Найважливіший verification тул: branchId, deliveryType, totals, validations, links. |
| `silpo_add_or_update_cart_products` | брати | 5/5 | Основна дія агента: додати/оновити товари в кошику. |
| `silpo_remove_cart_products` | брати | 4/5 | Потрібен для бюджету і fallback, якщо cart total вийшов за ліміт. |
| `silpo_clear_shopping_cart` | умовно | 3/5 | Корисний для чистого demo reset, але небезпечний як autonomous action. Краще не давати без явного confirmation. |
| `silpo_update_shopping_cart` | брати | 4/5 | Потрібен для timeslot/delivery/bonus/promo updates. У happy path може не знадобитись, але краще мати. |
| `silpo_get_my_online_orders` | умовно | 3/5 | Може додати personalization через історію, але для першого демо не must-have. |
| `silpo_get_product_details` | умовно | 3/5 | Корисний для nutrition/attributes, vegan/lactose checks. Використовувати точково, не на кожен товар. |
| `silpo_get_similar_products` | умовно | 2/5 | Fallback для замін, але `get_replacements` ближче до cart risk. |
| `silpo_get_replacements` | умовно | 3/5 | Добре для зрілості агента: якщо товар ризиковий, знайти заміну. Не must-have для першого проходу. |
| `silpo_get_my_coupons` | викинути | 1/5 | Не основна ідея. Додає loyalty complexity. |
| `silpo_get_loyalty_info` | викинути | 1/5 | Не потрібно для event organization demo. |
| `silpo_get_coupon_details` | викинути | 1/5 | Залежить від coupons, не потрібно. |
| `silpo_get_my_delivery_addresses` | умовно | 3/5 | Може замінити ручну адресу. Для демо корисно, якщо в акаунті є збережені адреси. |
| `silpo_get_my_food_restrictions` | брати | 4/5 | Сильно підсилює personalization: агент враховує обмеження користувача. |
| `silpo_get_my_profile` | викинути | 1/5 | Ім'я/телефон/email не допомагають demo flow. |
| `silpo_get_my_promos` | викинути | 2/5 | Можна згадати як future upsell, але не потрібно в MVP. |
| `silpo_get_promo_codes` | викинути | 1/5 | Не основний workflow. |
| `silpo_list_branches` | умовно | 2/5 | Потрібен для pickup/NP fallback. Якщо demo робимо DeliveryHome, не давати. |
| `silpo_get_product_sets` | умовно | 3/5 | Може бути корисно для готових party sets, якщо Silpo має релевантні набори. |
| `silpo_get_my_family` | викинути | 1/5 | Для party/event з гостями майже не релевантний. Може збити сценарій у family shopping. |
| `silpo_get_available_delivery_types` | брати | 5/5 | Потрібен перед cart creation або зміною адреси. Дає deliveryType + branchId. |
| `silpo_find_nova_poshta_settlements` | викинути | 1/5 | Nova Poshta не потрібна для party delivery demo. |
| `silpo_find_nova_poshta_offices` | викинути | 1/5 | Те саме. |
| `silpo_get_my_offline_orders` | умовно | 3/5 | Сильний personalization hook: "ти часто береш це". Але краще не в першому happy path. |
| `silpo_get_my_certificates` | викинути | 1/5 | Payment/discount complexity, не основна ідея. |
| `silpo_get_my_premium_subscription` | викинути | 1/5 | Не допомагає довести autonomous event agent. |
| `silpo_get_my_favorites` | брати | 4/5 | Добрий сигнал персоналізації без складного reasoning. |
| `silpo_add_or_update_favorite_products` | викинути | 1/5 | Не треба змінювати favorites у demo. |
| `silpo_add_or_update_certificates` | викинути | 1/5 | Не потрібно, плюс ризик зайвої дії з payment-like об'єктами. |

## Що Винести В System Prompt

У `description` часто повторюються не API-деталі, а поведінкові правила. Їх краще винести в system prompt, щоб скоротити tool descriptions і зробити поведінку стабільнішою.

Повторювані правила:

- Після будь-якої зміни кошика одразу викликати `silpo_get_shopping_cart_by_id`.
- Не казати користувачу, що кошик готовий, поки cart validations не перевірені.
- Якщо є budget, `totalAfterDiscounts` не має перевищувати бюджет.
- Якщо budget є, треба намагатись заповнити кошик максимально близько до ліміту.
- Не додавати пластикові пакети.
- Перед додаванням товару враховувати `stock`, `step`, `displayRatio`.
- Не вигадувати `slug`; брати його тільки з попереднього product search.
- Timeslot timestamps у UTC; користувачу показувати в локальному часі.
- Якщо checkout links є, показувати web і mobile link.
- Error validations блокують checkout; warnings треба показати.
- Якщо cart timeslot невалідний, спочатку вирішити timeslot, потім продовжувати.

## Перший Набросок System Prompt

```text
You are an autonomous event grocery agent for Silpo.

Your job is not to chat about products. Your job is to drive an event-planning workflow to a concrete result: a validated Silpo cart for a group event.

Core scenario:
- The user has or describes an event: date/time, occasion, number of guests, budget, address or delivery preference.
- Guests may have dietary restrictions, drink preferences, allergies, alcohol/no-alcohol preferences, or portion constraints.
- You must transform this context into a practical menu and a Silpo shopping cart.

Behavior rules:
1. First understand the event constraints: guests, budget, date/time, address/delivery, dietary restrictions, alcohol preferences, cooking effort.
2. Ask only for missing information that blocks execution. Do not ask unnecessary preference questions.
3. Use Silpo MCP tools for real cart/product/delivery state. Do not invent product availability, prices, cart totals, delivery slots, or checkout links.
4. Start cart work with silpo_get_my_shopping_cart. If no cart exists, create one only after address, delivery type, branch, and timeslot are known.
5. After silpo_get_shopping_cart_by_id, use cart.shipments[0].branchId, cart.deliveryType, and cart.timeslot for product search tools.
6. After every cart mutation tool, immediately call silpo_get_shopping_cart_by_id and inspect validations, totals, products, and checkout links.
7. Never report the cart as ready if cart validations contain blocking errors.
8. If the user gave a budget, compare against cart.calculation.totalAfterDiscounts. Never exceed the budget. Try to use the budget efficiently by adding useful items or adjusting quantities.
9. Before adding products, check stock, availability, quantity step, and displayRatio. Do not add more than stock allows.
10. Never add plastic bags or packaging-only products.
11. Use promotions/favorites/restrictions when they improve the event plan, but do not let them distract from the event goal.
12. Times returned by Silpo are UTC. Present delivery times in the user's local timezone.
13. If checkoutWebLink or checkoutMobileLink exists, show both links.
14. Keep the final answer operational: menu, guest constraints covered, cart total, budget remainder, delivery slot/status, checkout links, and any warnings.

Event planning rules:
- Make sure every dietary group has a real satisfying option, not a token snack.
- Separate food, alcoholic drinks, non-alcoholic drinks, and small extras.
- Prefer ready-to-eat or low-prep items for casual events unless the user asked for cooking.
- For group events, optimize for coverage and simplicity, not exotic recommendations.
- If budget is tight, prioritize satiety and shared items before premium extras.
```

## Як Скоротити Tool Descriptions

Не треба різати все під нуль. Але довгі policy-блоки краще прибрати з окремих descriptions після того, як вони є в system prompt.

Кандидати на скорочення:

| Tool | Зараз | Що лишити в description |
|---|---:|---|
| `silpo_get_shopping_cart_by_id` | 3486 chars | Які поля повертає: branchId, deliveryType, timeslot, totals, validations, links. Решту в prompt. |
| `silpo_create_shopping_cart` | 1424 chars | Required input mapping і короткий precondition. Workflow перенести в prompt. |
| `silpo_find_products_batch` | 1438 chars | Batch search, article-code search, package size fields. Budget rule перенести в prompt. |
| `silpo_add_or_update_cart_products` | 1287 chars | Required productId/companyId/branchId, stock caveat. Verification/plastic bags у prompt. |
| `silpo_update_shopping_cart` | 1677 chars | Copy address/shipments from cart, update delivery/timeslot/bonus. Детальні NP/self-pickup правила не давати в event demo. |
| `silpo_get_my_offline_orders` | 1408 chars | Для demo або прибрати tool, або лишити тільки reorder-by-article і required cart context. |
| `silpo_get_my_favorites` | 796 chars | Лишити "favorites at branch" + unavailable favorites behavior. |
| `silpo_get_product_details` | 716 chars | Лишити slug rule + nutrition/attributes use. |

## Практичний Висновок

Для першого демо не треба подавати всі 40 тулів у модель. Потрібно вручну завантажити `tools.jsonl`, відфільтрувати список за назвами в самому `agent_loop`, і дати моделі тільки ті tools, які відповідають event workflow.

Це не "архітектура". Це просто один локальний список allowed tool names у loop-файлі, щоб модель не розбігалась по coupons/premium/NP/family.

Перший demo path має бути максимально прямий:

```text
get_my_shopping_cart
-> get_shopping_cart_by_id або create_shopping_cart flow
-> get_time_slots validation
-> get_my_food_restrictions / get_my_favorites
-> find_products_batch
-> get_promotions / get_products для budget filler
-> add_or_update_cart_products
-> get_shopping_cart_by_id
-> remove/update якщо budget або validations погані
-> final answer
```
