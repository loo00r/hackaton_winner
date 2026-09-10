import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from src.agent.loop import agent_loop, tools
from src.bot.mood import mood_status
from src.mcp_client.client import mcp_connection

load_dotenv()

TOKEN = getenv("BOT_TOKEN")

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()



@dp.message(F.text)
async def message_handler(message: Message, mcp_client) -> None:

    response_text = await agent_loop(
        mcp_client=mcp_client,
        tools=tools,
        user_message=message.text,
        chat_id=message.chat.id,
    )
    await message.answer(f"{mood_status(message.text)}\n{response_text}")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    async with mcp_connection() as mcp_client:
        await dp.start_polling(bot, mcp_client=mcp_client)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
