import asyncio
import logging
import re
import sys
from contextlib import suppress
from os import getenv

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from src.agent.loop import FILTER_TOOLS, agent_loop, tools
from src.mcp_client.adapter import mcp_tool_to_openai_tool
from src.mcp_client.client import mcp_connection

load_dotenv()

TOKEN = getenv("BOT_TOKEN")
logger = logging.getLogger(__name__)

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()
follow_up_tasks: dict[int, asyncio.Task] = {}
follow_up_active: set[int] = set()
chat_locks: dict[int, asyncio.Lock] = {}
SILENCE_PROMPT = "[SILENCE FOLLOW-UP] No user reply for 15 seconds. Use MCP to find safe options and continue; do not repeat the question."
BOT_ART = r"""       ✧      ●      ✧
              │
     ╭────────┴────────╮
     │                 │
     │   ◠         ◠   │
     │                 │
     │  ░░  ╰───╯  ░░  │
     │                 │
     ╰───────┬─┬───────╯
   ╲         │ │         ╱
    ╲    ╭───┴─┴───╮    ╱
     ╰───┤   ♥ ♥   ├───╯
         │  ▰▰▰▰▰  │
         ╰─────────╯"""
STARTUP_STATUS = r"""
    ╭─────────────────────────────────────────────╮
    │ ........Ініціалізую протоколи доставки      │
    │ ......Людство  довірило ШІ вибір чипсів     │
    ╰─────────────────────────────────────────────╯"""
APP_LOGGERS = ("src.agent.loop", "src.bot.bot")


class TypewriterLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.addFilter(lambda record: record.levelno == logging.INFO)
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.worker: asyncio.Task | None = None

    def emit(self, record: logging.LogRecord) -> None:
        self.queue.put_nowait(self.format(record))

    def start(self) -> None:
        self.worker = asyncio.create_task(self._write_logs())

    async def stop(self) -> None:
        await self.queue.join()
        if self.worker:
            self.worker.cancel()
            with suppress(asyncio.CancelledError):
                await self.worker

    async def _write_logs(self) -> None:
        while True:
            line = await self.queue.get()
            try:
                await typewrite(line, delay=0.002)
            finally:
                self.queue.task_done()


class InstantLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.name in APP_LOGGERS and record.levelno == logging.INFO)


typewriter_logs = TypewriterLogHandler()


def telegram_text(text: str) -> str:
    """Keep LLM replies readable without relying on Telegram Markdown parsing."""
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1: \2", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "• ", text)
    text = re.sub(r"(?m)^>\s?", "", text)
    return text.replace("**", "").replace("__", "").replace("`", "")


async def resume_after_silence(message: Message, mcp_client) -> None:
    await asyncio.sleep(15)
    chat_id = message.chat.id
    follow_up_active.add(chat_id)
    try:
        async with chat_locks.setdefault(chat_id, asyncio.Lock()):
            response = await agent_loop(
                mcp_client=mcp_client, tools=tools, user_message=SILENCE_PROMPT,
                chat_id=chat_id,
                on_progress=lambda text: message.answer(telegram_text(text)),
            )
            await message.answer(telegram_text(response))
    finally:
        follow_up_active.discard(chat_id)


async def typewrite(text: str, delay: float) -> None:
    for symbol in text:
        sys.stdout.write(symbol)
        sys.stdout.flush()
        await asyncio.sleep(delay)
    sys.stdout.write("\n")


async def show_startup_banner() -> None:
    await typewrite("ACHUTNG: Initializing gatherly_bot", delay=0.008)
    await asyncio.sleep(2)
    await typewrite(BOT_ART, delay=0.008)
    await asyncio.sleep(2)
    await typewrite(STARTUP_STATUS, delay=0.012)


async def keep_typing(message: Message) -> None:
    while True:
        await asyncio.sleep(4)
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    for handler in logging.getLogger().handlers:
        handler.addFilter(InstantLogFilter())
    typewriter_logs.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    for name in APP_LOGGERS:
        logging.getLogger(name).addHandler(typewriter_logs)
    for noisy_logger in ("httpx", "httpx2", "openai._base_client", "aiogram.event"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "друже"
    await message.answer(f"Привіт, {name}! Допоможу зібрати кошик для твоєї події.")


@dp.message(F.text)
async def message_handler(message: Message, mcp_client) -> None:
    if task := follow_up_tasks.pop(message.chat.id, None):
        if message.chat.id in follow_up_active:
            task = None
    if task:
        task.cancel()

    async def send_progress(text: str) -> None:
        await message.answer(telegram_text(text))

    async with chat_locks.setdefault(message.chat.id, asyncio.Lock()):
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        typing = asyncio.create_task(keep_typing(message))
        try:
            response_text = await agent_loop(
                mcp_client=mcp_client, tools=tools, user_message=message.text,
                chat_id=message.chat.id, on_progress=send_progress,
            )
        finally:
            typing.cancel()
            with suppress(asyncio.CancelledError):
                await typing
        await message.answer(telegram_text(response_text))
    if "?" in response_text:
        follow_up_tasks[message.chat.id] = asyncio.create_task(
            resume_after_silence(message, mcp_client)
        )


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    await show_startup_banner()
    typewriter_logs.start()
    try:
        bot = Bot(token=TOKEN)

        async with mcp_connection() as mcp_client:
            result = await mcp_client.list_tools()
            tools[:] = map(
                mcp_tool_to_openai_tool,
                (tool for tool in result.tools if tool.name in FILTER_TOOLS),
            )
            if not tools:
                raise RuntimeError("MCP returned no enabled tools; polling will not start")
            logger.info("Loaded %d enabled tools from MCP server", len(tools))
            await dp.start_polling(bot, mcp_client=mcp_client)
    finally:
        await typewriter_logs.stop()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
