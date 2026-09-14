"""
Тестування всіх MCP тулів Silpo для демо.

Порядок тестування відповідає demo flow:
1. silpo_get_my_shopping_cart        — отримати ID кошика
2. silpo_get_shopping_cart_by_id     — деталі кошика (branchId, deliveryType, timeslot)
   АБО silpo_create_shopping_cart flow:
     2a. silpo_find_address
     2b. silpo_get_available_delivery_types
     2c. silpo_get_time_slots
     2d. silpo_create_shopping_cart
3. silpo_get_time_slots              — перевірка таймслоту
4. silpo_get_my_food_restrictions    — дієтичні обмеження
5. silpo_get_my_favorites            — улюблені товари
6. silpo_find_products_batch         — пошук продуктів для меню
7. silpo_get_products                — продукти за категорією/промо
8. silpo_get_promotions              — акції
9. silpo_add_or_update_cart_products — додати товари в кошик
10. silpo_get_shopping_cart_by_id    — верифікація кошика
11. silpo_remove_cart_products       — видалити товар (якщо over budget)
12. silpo_update_shopping_cart       — оновити delivery/timeslot

Кожен тест зберігає відповідь у JSON файл для аналізу.
"""

import sys
import os

# Додаємо src до path щоб імпортувати mcp_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import httpx2
from dotenv import load_dotenv
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent
import asyncio
import json
from datetime import datetime, timezone

# Завантажуємо токен
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'src', '.env'))
TOKEN = os.getenv("SILPO_MCP_TOKEN")

RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)


def save_result(tool_name: str, result_data: dict | str | None, is_error: bool = False):
    """Зберегти результат виклику тула в JSON файл."""
    filepath = os.path.join(RESULTS_DIR, f"{tool_name}.json")
    output = {
        "tool": tool_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_error": is_error,
        "data": result_data
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  💾 Saved to {filepath}")


def extract_text(result) -> str:
    """Витягнути текст з MCP result."""
    texts = []
    for block in result.content:
        if isinstance(block, TextContent):
            texts.append(block.text)
    return "\n".join(texts)


def parse_response(result) -> dict | str | None:
    """Спробувати розпарсити відповідь як JSON."""
    text = extract_text(result)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


async def call_tool(client: Client, tool_name: str, arguments: dict | None = None) -> dict | str | None:
    """Виклик MCP тула з логуванням."""
    args = arguments or {}
    print(f"\n{'='*60}")
    print(f"🔧 Calling: {tool_name}")
    if args:
        print(f"   Args: {json.dumps(args, ensure_ascii=False, indent=4)}")
    print(f"{'='*60}")

    try:
        result = await client.call_tool(tool_name, arguments=args)
        parsed = parse_response(result)
        is_error = result.is_error

        if is_error:
            print(f"  ❌ ERROR: {parsed}")
        else:
            # Показати скорочений результат
            text = json.dumps(parsed, ensure_ascii=False, indent=2) if isinstance(parsed, (dict, list)) else str(parsed)
            preview = text[:500] + "..." if len(text) > 500 else text
            print(f"  ✅ OK")
            print(f"  📄 Response preview:\n{preview}")

        save_result(tool_name, parsed, is_error)
        return parsed

    except Exception as e:
        print(f"  💥 EXCEPTION: {type(e).__name__}: {e}")
        save_result(tool_name, {"error": str(e), "type": type(e).__name__}, is_error=True)
        return None


async def main():
    print("🚀 Starting Silpo MCP Tools Test Suite")
    print(f"   Token: {TOKEN[:20]}..." if TOKEN else "   ⚠️  NO TOKEN FOUND!")
    print(f"   Results dir: {RESULTS_DIR}")
    print()

    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=httpx2.Timeout(30.0, read=300.0),
        follow_redirects=True,
    ) as http_client:
        transport = streamable_http_client("https://mcp.silpo.ua/mcp", http_client=http_client)
        async with Client(transport) as client:

            # ============================================================
            # ТЕСТ 1: silpo_get_my_shopping_cart
            # Стартова точка — дізнатись чи є кошик
            # ============================================================
            cart_info = await call_tool(client, "silpo_get_my_shopping_cart")

            shopping_cart_id = None
            cart_exists = False
            if isinstance(cart_info, dict):
                shopping_cart_id = cart_info.get("shoppingCartId")
                cart_exists = cart_info.get("exists", False)

            print(f"\n  📋 Cart exists: {cart_exists}, ID: {shopping_cart_id}")

            # ============================================================
            # ТЕСТ 2a: silpo_find_address
            # Пошук адреси для delivery
            # ============================================================
            address_result = await call_tool(client, "silpo_find_address", {
                "address": "Київ, вулиця Хрещатик, 1"
            })

            latitude = None
            longitude = None
            city = None
            street = None
            house = None
            district = None
            if isinstance(address_result, dict) and "addresses" in address_result:
                first_addr = address_result["addresses"][0]
                latitude = first_addr.get("latitude")
                longitude = first_addr.get("longitude")
                city = first_addr.get("city")
                street = first_addr.get("street")
                house = first_addr.get("houseNumber")
                district = first_addr.get("district")
                print(f"  📍 Found: {city}, {street} {house} ({latitude}, {longitude})")

            # ============================================================
            # ТЕСТ 2b: silpo_get_available_delivery_types
            # Які типи доставки доступні за цією адресою
            # ============================================================
            delivery_types = None
            branch_id = None
            delivery_type = None

            if latitude and longitude:
                delivery_types = await call_tool(client, "silpo_get_available_delivery_types", {
                    "latitude": latitude,
                    "longitude": longitude
                })

                # API повертає ключ "options" 
                options_key = "options" if "options" in delivery_types else "deliveryTypes"
                if isinstance(delivery_types, dict) and options_key in delivery_types:
                    for dt in delivery_types[options_key]:
                        dt_name = dt.get("deliveryType") or dt.get("type")
                        dt_branch = dt.get("branchId")
                        print(f"  🚚 {dt_name}: branchId={dt_branch}")
                        # Шукаємо DeliveryHome з branchId
                        if dt_name == "DeliveryHome" and dt_branch:
                            delivery_type = dt_name
                            branch_id = dt_branch

            if not branch_id:
                # fallback — шукаємо будь-який тип з branchId
                options_key = "options" if isinstance(delivery_types, dict) and "options" in delivery_types else "deliveryTypes"
                if isinstance(delivery_types, dict) and options_key in delivery_types:
                    for dt in delivery_types[options_key]:
                        dt_branch = dt.get("branchId")
                        if dt_branch:
                            delivery_type = dt.get("deliveryType") or dt.get("type")
                            branch_id = dt_branch
                            break

            print(f"  🏬 Selected: deliveryType={delivery_type}, branchId={branch_id}")

            # ============================================================
            # ТЕСТ 2c: silpo_get_time_slots
            # Доступні слоти доставки
            # ============================================================
            timeslot_start = None
            timeslot_end = None

            if branch_id:
                # Запитуємо слоти починаючи від поточного часу (чистий ISO формат)
                now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                time_slots_result = await call_tool(client, "silpo_get_time_slots", {
                    "branchId": branch_id,
                    "deliveryTypes": [delivery_type] if delivery_type else [],
                    "limit": 25,
                    "start": now_utc
                })

                # Fallback: якщо 400 error — спробуємо без start
                if isinstance(time_slots_result, str) and "400" in str(time_slots_result):
                    print("  ⚠️  Retrying without start parameter...")
                    time_slots_result = await call_tool(client, "silpo_get_time_slots", {
                        "branchId": branch_id,
                        "deliveryTypes": [delivery_type] if delivery_type else [],
                        "limit": 25
                    })

                if isinstance(time_slots_result, dict) and "slots" in time_slots_result:
                    for slot in time_slots_result["slots"]:
                        if slot.get("available"):
                            timeslot_start = slot["start"]
                            timeslot_end = slot["end"]
                            print(f"  ⏰ First available slot: {timeslot_start} → {timeslot_end}")
                            break

            # ============================================================
            # ТЕСТ 2d: silpo_create_shopping_cart (тільки якщо немає кошика)
            # ============================================================
            if not cart_exists and branch_id and timeslot_start:
                create_result = await call_tool(client, "silpo_create_shopping_cart", {
                    "addressType": "house",
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": city or "",
                    "street": street or "",
                    "house": house or "",
                    "district": district or "",
                    "deliveryType": delivery_type,
                    "timeslot": {
                        "start": timeslot_start,
                        "end": timeslot_end
                    },
                    "branchId": branch_id
                })

                if isinstance(create_result, dict):
                    shopping_cart_id = create_result.get("shoppingCartId")
                    print(f"  🛒 Created cart: {shopping_cart_id}")
            elif cart_exists:
                print(f"\n  ℹ️  Cart already exists, skipping create. ID: {shopping_cart_id}")

            # ============================================================
            # ТЕСТ 3: silpo_get_shopping_cart_by_id
            # Повні деталі кошика — branchId, deliveryType, timeslot, totals
            # ============================================================
            cart_details = None
            if shopping_cart_id:
                cart_details = await call_tool(client, "silpo_get_shopping_cart_by_id", {
                    "shoppingCartId": shopping_cart_id
                })

                # Витягуємо контекст кошика для подальших тулів
                if isinstance(cart_details, dict):
                    cart = cart_details.get("cart", cart_details)
                    shipments = cart.get("shipments", [])
                    if shipments:
                        branch_id = shipments[0].get("branchId", branch_id)
                    delivery_type = cart.get("deliveryType", delivery_type)
                    ts = cart.get("timeslot", {})
                    if ts:
                        timeslot_start = ts.get("start", timeslot_start)
                        timeslot_end = ts.get("end", timeslot_end)

                    calc = cart.get("calculation", {})
                    total = calc.get("totalAfterDiscounts", calc.get("total"))
                    print(f"  💰 Cart total: {total}")
                    print(f"  🏬 branchId: {branch_id}")
                    print(f"  🚚 deliveryType: {delivery_type}")
                    print(f"  ⏰ timeslot: {timeslot_start} → {timeslot_end}")

            # ============================================================
            # ТЕСТ 4: silpo_get_my_food_restrictions
            # Дієтичні обмеження користувача
            # ============================================================
            food_restrictions = await call_tool(client, "silpo_get_my_food_restrictions")

            # ============================================================
            # ТЕСТ 5: silpo_get_my_favorites
            # Улюблені товари
            # ============================================================
            if branch_id and delivery_type and timeslot_start:
                favorites = await call_tool(client, "silpo_get_my_favorites", {
                    "branchId": branch_id,
                    "deliveryType": delivery_type,
                    "timeslotStart": timeslot_start,
                    "limit": 10
                })

            # ============================================================
            # ТЕСТ 6: silpo_find_products_batch
            # Batch пошук продуктів для меню вечірки
            # ============================================================
            found_products = []
            if branch_id and delivery_type and timeslot_start and timeslot_end:
                products_batch = await call_tool(client, "silpo_find_products_batch", {
                    "branchId": branch_id,
                    "deliveryType": delivery_type,
                    "timeslotStart": timeslot_start,
                    "timeslotEnd": timeslot_end,
                    "products": [
                        "піца",
                        "чіпси",
                        "вино біле сухе",
                        "хумус",
                        "сир",
                        "лимонад"
                    ],
                    "limit": 5
                })

                # Збираємо знайдені продукти для додавання в кошик
                if isinstance(products_batch, dict) and "queries" in products_batch:
                    for query in products_batch["queries"]:
                        query_name = query.get("query", "?")
                        products_in_query = query.get("products", [])
                        print(f"  🔍 '{query_name}': {len(products_in_query)} products found (total: {query.get('totalFound', 0)})")
                        if products_in_query:
                            p = products_in_query[0]
                            found_products.append({
                                "productId": p.get("id"),
                                "companyId": p.get("companyId"),
                                "branchId": p.get("branchId", branch_id),
                                "title": p.get("title"),
                                "price": p.get("price"),
                                "stock": p.get("stock"),
                                "step": p.get("addToBasketStep", p.get("step", 1)),
                                "slug": p.get("slug")
                            })

                if found_products:
                    print(f"\n  📦 Products to add to cart:")
                    for fp in found_products:
                        print(f"     - {fp['title']}: ₴{fp['price']} (stock: {fp['stock']})")

            # ============================================================
            # ТЕСТ 7: silpo_get_promotions
            # Активні акції
            # ============================================================
            if branch_id and delivery_type and timeslot_start and timeslot_end:
                promotions = await call_tool(client, "silpo_get_promotions", {
                    "branchId": branch_id,
                    "deliveryType": delivery_type,
                    "timeslotStart": timeslot_start,
                    "timeslotEnd": timeslot_end
                })

            # ============================================================
            # ТЕСТ 8: silpo_get_products (з категорією/промо)
            # Перегляд продуктів з фільтрами
            # ============================================================
            if branch_id and delivery_type and timeslot_start and timeslot_end:
                products_promo = await call_tool(client, "silpo_get_products", {
                    "branchId": branch_id,
                    "deliveryType": delivery_type,
                    "timeslotStart": timeslot_start,
                    "timeslotEnd": timeslot_end,
                    "mustHavePromotion": True,
                    "limit": 5,
                    "sortBy": "popularity"
                })

            # ============================================================
            # ТЕСТ 9: silpo_add_or_update_cart_products
            # Додати перші 2 знайдені товари в кошик
            # ============================================================
            if shopping_cart_id and found_products:
                products_to_add = []
                for fp in found_products[:2]:  # беремо перші 2
                    if fp["productId"] and fp["companyId"]:
                        products_to_add.append({
                            "productId": fp["productId"],
                            "companyId": fp["companyId"],
                            "branchId": fp["branchId"] or branch_id,
                            "quantity": fp["step"],  # мінімальна кількість
                            "addQuantity": False
                        })

                if products_to_add:
                    add_result = await call_tool(client, "silpo_add_or_update_cart_products", {
                        "shoppingCartId": shopping_cart_id,
                        "products": products_to_add
                    })

            # ============================================================
            # ТЕСТ 10: silpo_get_shopping_cart_by_id (верифікація після додавання)
            # ============================================================
            if shopping_cart_id:
                cart_after_add = await call_tool(client, "silpo_get_shopping_cart_by_id", {
                    "shoppingCartId": shopping_cart_id
                })

                if isinstance(cart_after_add, dict):
                    cart = cart_after_add.get("cart", cart_after_add)
                    calc = cart.get("calculation", {})
                    total_after = calc.get("totalAfterDiscounts", calc.get("total"))
                    validations = calc.get("validations", [])
                    print(f"  💰 Cart total after add: {total_after}")
                    if validations:
                        print(f"  ⚠️  Validations: {json.dumps(validations, ensure_ascii=False)[:300]}")

                    # Збираємо ID продуктів для тесту видалення
                    cart_product_ids = []
                    for shipment in cart.get("shipments", []):
                        for product in shipment.get("products", []):
                            cart_product_ids.append(product.get("productId"))

                    # Зберігаємо checkout links
                    checkout_web = cart.get("checkoutWebLink")
                    checkout_mobile = cart.get("checkoutMobileLink")
                    if checkout_web:
                        print(f"  🔗 Checkout Web: {checkout_web}")
                    if checkout_mobile:
                        print(f"  📱 Checkout Mobile: {checkout_mobile}")

            # ============================================================
            # ТЕСТ 11: silpo_remove_cart_products
            # Видалити останній доданий продукт (щоб не забруднювати кошик)
            # ============================================================
            if shopping_cart_id and cart_product_ids:
                # Видаляємо тільки те, що ми додали
                product_to_remove = cart_product_ids[-1]
                if product_to_remove:
                    remove_result = await call_tool(client, "silpo_remove_cart_products", {
                        "shoppingCartId": shopping_cart_id,
                        "products": [{"productId": product_to_remove}]
                    })

            # ============================================================
            # ФІНАЛЬНА верифікація
            # ============================================================
            if shopping_cart_id:
                final_cart = await call_tool(client, "silpo_get_shopping_cart_by_id", {
                    "shoppingCartId": shopping_cart_id
                })
                save_result("final_cart_state", parse_response(final_cart) if hasattr(final_cart, 'content') else final_cart)

            # ============================================================
            # SUMMARY
            # ============================================================
            print("\n" + "=" * 60)
            print("📊 TEST SUMMARY")
            print("=" * 60)
            results_files = os.listdir(RESULTS_DIR)
            for f in sorted(results_files):
                filepath = os.path.join(RESULTS_DIR, f)
                with open(filepath, 'r') as fh:
                    data = json.load(fh)
                status = "❌ ERROR" if data.get("is_error") else "✅ OK"
                print(f"  {status}  {data.get('tool', f)}")

            print(f"\n📁 All results saved to: {RESULTS_DIR}")
            print("🏁 Done!")


if __name__ == "__main__":
    asyncio.run(main())
