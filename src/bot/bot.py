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
follow_up_tasks: dict[int, asyncio.Task] = {}
follow_up_active: set[int] = set()
chat_locks: dict[int, asyncio.Lock] = {}
SILENCE_PROMPT = "[SILENCE FOLLOW-UP] No user reply for 7 seconds. Use MCP to find safe options and continue; do not repeat the question."


async def resume_after_silence(message: Message, mcp_client) -> None:
    await asyncio.sleep(15)
    chat_id = message.chat.id
    follow_up_active.add(chat_id)
    try:
        async with chat_locks.setdefault(chat_id, asyncio.Lock()):
            response = await agent_loop(
                mcp_client=mcp_client, tools=tools, user_message=SILENCE_PROMPT,
                chat_id=chat_id, on_progress=message.answer,
            )
            await message.answer(f"{response}")
    finally:
        follow_up_active.discard(chat_id)



@dp.message(F.text)
async def message_handler(message: Message, mcp_client) -> None:
    if task := follow_up_tasks.pop(message.chat.id, None):
        if message.chat.id in follow_up_active:
            task = None
    if task:
        task.cancel()

    async def send_progress(text: str) -> None:
        await message.answer(f"{mood_status(message.text)}\n🧠 {text}")

    async with chat_locks.setdefault(message.chat.id, asyncio.Lock()):
        response_text = await agent_loop(
            mcp_client=mcp_client, tools=tools, user_message=message.text,
            chat_id=message.chat.id, on_progress=send_progress,
        )
    await message.answer(f"{mood_status(message.text)}\n{response_text}")
    if "?" in response_text:
        follow_up_tasks[message.chat.id] = asyncio.create_task(
            resume_after_silence(message, mcp_client)
        )


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    async with mcp_connection() as mcp_client:
        await dp.start_polling(bot, mcp_client=mcp_client)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
