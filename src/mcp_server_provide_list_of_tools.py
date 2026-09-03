
import httpx2

from dotenv import load_dotenv
import os
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
import asyncio
import json

# my_oauth_provider має бути оголошений або імпортований тут
load_dotenv()
TOKEN = os.getenv("SILPO_MCP_TOKEN")

async def main() -> None:
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=httpx2.Timeout(30.0, read=300.0),
        follow_redirects=True,
    ) as http_client:
        transport = streamable_http_client("https://mcp.silpo.ua/mcp", http_client=http_client)
        async with Client(transport) as client:
            result = await client.list_tools()

            for tool in result.tools:
                print(f"Tool name --> {tool.name}")
                print(f"Tool title -> {tool.title}")
                print(f"Tool desc --> {tool.description} \n")
                print(f"Tool schema-> {json.dumps(tool.input_schema, indent=2)} ")


if __name__ == "__main__":
    asyncio.run(main())