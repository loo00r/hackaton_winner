from llm.client import llm_client
from mcp import Client
import asyncio
from mcp_client.client import mcp_connection
import json



AGENT_LOOP = True

with open("tools.jsonl", "r") as json_file:
    tools = [json.loads(line) for line in json_file]
    tools = [tool for tool in tools if tool["function"]["name"] in ["silpo_get_my_family", "silpo_get_my_family_by_name"]]

async def agent_loop(mcp_client: Client, tools: list):
    messages = [
        {
            'role': 'system',
            'content': 'cпробуй викликати тулу  silpo_get_my_family і подивись чи ти зможеш побачити що вона поверне'
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