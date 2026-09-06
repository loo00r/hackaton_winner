from llm.client import llm_client
from mcp import Client
import asyncio
from mcp_client.client import mcp_connection
import json

from llm.prompt import SYSTEM_PROMPT



AGENT_LOOP = True
FILTER_TOOLS = [
    "silpo_get_my_shopping_cart",
    "silpo_create_shopping_cart",
    "silpo_get_shopping_cart_by_id",
    "silpo_find_address",
    "silpo_get_available_delivery_types",
    "silpo_get_time_slots",
    "silpo_find_products_batch",
    "silpo_get_products",
    "silpo_get_promotions",
    "silpo_add_or_update_cart_products",
    "silpo_remove_cart_products",
    "silpo_get_my_food_restrictions",
    "silpo_get_my_favorites",
]


with open("tools.jsonl", "r") as json_file:
    tools = [json.loads(line) for line in json_file if line.strip()]
    tools = [tool for tool in tools if tool["function"]["name"] in FILTER_TOOLS]

async def agent_loop(mcp_client: Client, tools: list):
    messages = [
        {
            'role': 'system',
            'content': SYSTEM_PROMPT
        }]

    while AGENT_LOOP:
        response = llm_client.chat.completions.create(
            messages=messages,
            model='gemma4:12b',
            tools=tools
        )
        message = response.choices[0].message
        messages.append(message)
        print(messages)

        if not message.tool_calls:
            print(message.content)
            break

        for tool_call in message.tool_calls:

            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            print("LLM wants:", name)
            print("Arguments:", arguments)

            # ОЦЕ ТУТ реальний MCP call
            result = await mcp_client.call_tool(
                name,
                arguments
            )

            print("MCP result:", result)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result.structured_content)
            })

async def main() -> None:
    async with mcp_connection() as mcp_client:
        await agent_loop(mcp_client, tools)

if __name__ == "__main__":
    asyncio.run(main())