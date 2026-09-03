import httpx2

from dotenv import load_dotenv
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
import os
from contextlib import asynccontextmanager



load_dotenv()
TOKEN = os.getenv("SILPO_MCP_TOKEN")

# my_oauth_provider має бути оголошений або імпортований тут
@asynccontextmanager
async def mcp_connection():
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=httpx2.Timeout(30.0, read=300.0),
        follow_redirects=True,
    ) as http_client:
        transport = streamable_http_client("https://mcp.silpo.ua/mcp", http_client=http_client)
        async with Client(transport) as client:
            yield client