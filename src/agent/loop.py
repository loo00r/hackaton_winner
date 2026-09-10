import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from mcp import Client

from src.llm.client import llm_client
from src.llm.prompt import SYSTEM_PROMPT
from src.mcp_client.client import mcp_connection

FILTER_TOOLS = [
    "silpo_get_my_shopping_cart",
    "silpo_create_shopping_cart",
    "silpo_get_shopping_cart_by_id",
    "silpo_update_shopping_cart",
    "silpo_find_address",
    "silpo_get_available_delivery_types",
    "silpo_list_branches",
    "silpo_get_time_slots",
    "silpo_find_products_batch",
    "silpo_get_products",
    "silpo_get_promotions",
    "silpo_add_or_update_cart_products",
    "silpo_remove_cart_products",
    "silpo_get_my_food_restrictions",
    "silpo_get_my_favorites",
]

# Шлях відносно цього файлу, не cwd
_THIS_DIR = Path(__file__).resolve().parent
_TOOLS_PATH = os.path.join(_THIS_DIR, "tools.jsonl")
sys.path.insert(0, str(_THIS_DIR))

with open(_TOOLS_PATH, "r") as json_file:
    tools = [json.loads(line) for line in json_file if line.strip()]
    tools = [tool for tool in tools if tool["function"]["name"] in FILTER_TOOLS]


history_by_chat: dict[int, list[dict]] = {}
logger = logging.getLogger(__name__)

async def agent_loop(mcp_client: Client, tools: list, user_message: str, chat_id: int):
    history = history_by_chat.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_message})
    logger.info("Agent input: chat_id=%s, history_items=%s", chat_id, len(history))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
    ]
        
    while True:
        logger.info("LLM input: %s", json.dumps(messages, ensure_ascii=False, default=str))
        response = llm_client.chat.completions.create(
            messages=messages,
            model="gpt-4o",
            tools=tools,
        )
        message = response.choices[0].message
        assistant_message = message.model_dump(exclude_none=True)
        messages.append(assistant_message)
        history.append(assistant_message)
        logger.info("LLM output: %s", json.dumps(assistant_message, ensure_ascii=False))

        if not message.tool_calls:
            logger.info("Agent finished: chat_id=%s, history_items=%s", chat_id, len(history))
            return message.content

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            logger.info("MCP call: tool=%s, arguments=%s", name, tool_call.function.arguments)

            result = await mcp_client.call_tool(name, arguments)



            tool_text = json.dumps(result.structured_content, ensure_ascii=False) if result.structured_content is not None else result.content[0].text

            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_text,
            }
            messages.append(tool_message)
            history.append(tool_message)
            logger.info("MCP result: tool=%s, content=%s", name, tool_text)


async def main() -> None:
    user_message = input(" You: ").strip()
    if not user_message:
        user_message = (
            "Організуй вечірку на 5 людей, бюджет 2000 грн, "
            "адреса Київ вулиця Хрещатик 1, одна людина веган. "
            "Доставка на сьогодні ввечері."
        )
        print(f"   (using default: {user_message})")

    async with mcp_connection() as mcp_client:
        await agent_loop(mcp_client, tools, user_message, chat_id=0)


if __name__ == "__main__":
    asyncio.run(main())
