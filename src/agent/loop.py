from llm.client import llm_client
from mcp import Client
import asyncio
from mcp_client.client import mcp_connection

AGENT_LOOP = True


async def agent_loop(mcp_client: Client):
    tools = await mcp_client.list_tools()

    print(tools)
    # while AGENT_LOOP:
    response = llm_client.chat.completions.create(
        messages=[
            {
                'role': 'user',
                'content': 'Hello, how are you?',
            }
        ],
        model='gemma4:12b',
    )
    print(response.choices[0].message.content)

async def main() -> None:
    async with mcp_connection() as mcp_client:
        await agent_loop(mcp_client)

if __name__ == "__main__":
    asyncio.run(main())