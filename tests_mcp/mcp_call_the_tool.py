import httpx2

from dotenv import load_dotenv
import os
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent
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
            result = await client.call_tool("silpo_get_my_shopping_cart")

            for block in result.content:
                if isinstance(block, TextContent):
                    print(block.text)

            print(result.structured_content)
            print(result.is_error)


if __name__ == "__main__":
    asyncio.run(main())