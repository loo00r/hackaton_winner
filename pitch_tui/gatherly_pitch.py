#!/usr/bin/env python3
"""Interactive terminal pitch for Gatherly × Silpo MCP.

Controls: ←/→ or space to change scene, 1–9 to jump, q to quit.
"""

from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import time
import tty


RESET = "\x1b[0m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
CYAN = "\x1b[38;5;51m"
MINT = "\x1b[38;5;121m"
PINK = "\x1b[38;5;212m"
YELLOW = "\x1b[38;5;228m"
ORANGE = "\x1b[38;5;215m"
RED = "\x1b[38;5;210m"
WHITE = "\x1b[38;5;255m"
NAVY = "\x1b[48;5;17m"

SCENES = (
    ("GATHERLY", "Від наміру до валідного кошика"),
    ("ПРОБЛЕМА", "Групова подія — це не список покупок"),
    ("EVENT PARSER", "Один меседж → структурована подія"),
    ("AUTONOMY", "Агент сам закриває відомі блокери"),
    ("SILPO MCP", "Реальні дані замість вигаданих порад"),
    ("CART", "Збираємо меню в межах бюджету"),
    ("VALIDATION", "Не називаємо кошик готовим без перевірки"),
    ("SILENCE FOLLOW-UP", "Користувач мовчить — агент рухається далі"),
    ("VALUE → SCALE", "Менше координації. Більше готових подій."),
)

BOT_IDLE = (
    ("      ╭───────╮", "      │ ◠   ◠ │", "      │   ▱   │", "      ╰──┬─┬──╯", "         │ │", "      ╭──┴─┴──╮", "      │  ♥ ♥  │", "      ╰───────╯"),
    ("      ╭───────╮", "      │ ◡   ◡ │", "      │   ▱   │", "      ╰──┬─┬──╯", "         │ │", "      ╭──┴─┴──╮", "      │  ♥ ♥  │", "      ╰───────╯"),
)

BOT_WALK = (
    ("  ╭─────╮", "  │◠ ◠│", "  ╰─┬─╯", "   ╱ ╲"),
    ("   ╭─────╮", "   │◠ ◠│", "   ╰─┬─╯", "    ╲ ╱"),
)


def paint(text: str, color: str = WHITE) -> str:
    return f"{color}{text}{RESET}"


def box(lines: list[str], width: int) -> list[str]:
    inner = width - 2
    result = [paint("╭" + "─" * inner + "╮", CYAN)]
    for line in lines:
        raw = strip_ansi(line)
        result.append(paint("│", CYAN) + line + " " * max(0, inner - len(raw)) + paint("│", CYAN))
    result.append(paint("╰" + "─" * inner + "╯", CYAN))
    return result


def strip_ansi(text: str) -> str:
    while "\x1b[" in text:
        start = text.index("\x1b[")
        end = text.find("m", start)
        if end == -1:
            break
        text = text[:start] + text[end + 1 :]
    return text


def label(text: str, color: str = MINT) -> str:
    return paint(text, color)


def bot(frame: int, x: int = 0) -> list[str]:
    return [" " * x + paint(line, MINT) for line in BOT_IDLE[frame % len(BOT_IDLE)]]


def scene_intro(frame: int, width: int) -> list[str]:
    pulse = "●" if frame % 8 < 4 else "○"
    lines = ["", *bot(frame), ""]
    lines += [
        paint("      G A T H E R L Y", BOLD + MINT),
        "",
        f"  {label(pulse, PINK)}  intent  {paint('→', CYAN)}  action  {paint('→', CYAN)}  checkout",
        "",
        paint("  Автономний event-організатор для Сільпо", WHITE),
    ]
    return box(lines, width)


def scene_problem(frame: int, width: int) -> list[str]:
    chat = [
        paint("  GROUP CHAT", PINK),
        "  — Нас п’ятеро. Футбол о 20:00.",
        "  — Я веган.",
        "  — Хтось знає, що з доставкою?",
        "  — А бюджет? А де замовляти?",
        "",
        paint("  17 повідомлень пізніше…", RED),
        "  подія досі не організована.",
    ]
    return box(chat, width)


def scene_event(frame: int, width: int) -> list[str]:
    fields = (
        ("ПОДІЯ", "футбол сьогодні о 20:00"),
        ("ГОСТІ", "5 людей"),
        ("ОБМЕЖЕННЯ", "1 веган"),
        ("БЮДЖЕТ", "4 000 ₴"),
    )
    revealed = min(len(fields), frame // 5 + 1)
    lines = [paint("  USER MESSAGE", PINK), "  «Дивимось футбол, нас п’ятеро…»", ""]
    for index, (name, value) in enumerate(fields):
        if index < revealed:
            lines.append(f"  {label('✓', MINT)} {label(name + ':', CYAN)} {value}")
        else:
            lines.append(f"  {paint('·', DIM)} {paint(name + ':', DIM)}")
    lines += ["", paint("  Один меседж → execution-ready event", YELLOW)]
    return box(lines, width)


def scene_autonomy(frame: int, width: int) -> list[str]:
    steps = ("Saved address", "Delivery type", "Branch", "Available slot")
    active = (frame // 4) % len(steps)
    lines = [paint("  AGENT FLOW", PINK), ""]
    for index, step in enumerate(steps):
        icon = "●" if index == active else "✓" if index < active else "○"
        color = YELLOW if index == active else MINT if index < active else DIM
        lines.append(f"  {paint(icon, color)}  {paint(step, color if index != active else WHITE)}")
    lines += ["", *bot(frame, x=max(0, active * 7 - 2)), ""]
    lines.append(paint("  Питаємо лише про справжній blocker.", YELLOW))
    return box(lines, width)


def scene_mcp(frame: int, width: int) -> list[str]:
    calls = (
        "silpo_get_my_delivery_addresses",
        "silpo_get_available_delivery_types",
        "silpo_get_time_slots",
        "silpo_find_products_batch  [пиво · піца · веганські]",
        "silpo_add_or_update_cart_products",
        "silpo_get_shopping_cart_by_id",
    )
    revealed = min(len(calls), frame // 3 + 1)
    lines = [paint("  MCP / SILPO", PINK), "  live catalog · stock · delivery · cart", ""]
    for index, call in enumerate(calls):
        if index < revealed:
            lines.append(f"  {label('✓', MINT)} {paint('MCP →', CYAN)} {call}")
        else:
            lines.append(f"  {paint('○', DIM)} {paint('awaiting tool call', DIM)}")
    lines += ["", paint("  Ніяких вигаданих цін, слотів чи наявності.", YELLOW)]
    return box(lines, width)


def scene_cart(frame: int, width: int) -> list[str]:
    items = (
        ("🍕  Піца / ready-to-eat", "820 ₴"),
        ("🥗  Веганська опція", "460 ₴"),
        ("🍺  Напої для компанії", "640 ₴"),
        ("🥤  Безалкогольні", "290 ₴"),
        ("🥜  Спільні снеки", "380 ₴"),
    )
    count = min(len(items), frame // 4 + 1)
    total = sum(int(item[1].split()[0]) for item in items[:count])
    lines = [paint("  VALIDATED CART", PINK), ""]
    for title, price in items[:count]:
        lines.append(f"  {label('+', MINT)} {title:<30} {paint(price, YELLOW)}")
    for _ in range(len(items) - count):
        lines.append(paint("  ·", DIM))
    progress = int(16 * total / 4000)
    lines += ["", f"  {paint('BUDGET', CYAN)}  {'█' * progress}{paint('░' * (16 - progress), DIM)}  {total} / 4 000 ₴"]
    return box(lines, width)


def scene_validation(frame: int, width: int) -> list[str]:
    checks = (
        "delivery slot available",
        "products in stock",
        "budget not exceeded",
        "vegan option included",
        "cart validations: no blocking errors",
    )
    revealed = min(len(checks), frame // 3 + 1)
    lines = [paint("  BEFORE 'READY'", PINK), ""]
    for index, check in enumerate(checks):
        icon = "✓" if index < revealed else "○"
        lines.append(f"  {label(icon, MINT if index < revealed else DIM)}  {paint(check, WHITE if index < revealed else DIM)}")
    if revealed == len(checks):
        lines += ["", paint("  CART READY  →  checkout links", MINT + BOLD)]
    return box(lines, width)


def scene_silence(frame: int, width: int) -> list[str]:
    second = max(0, 15 - (frame % 16))
    bars = "█" * (15 - second) + "░" * second
    phase = (frame // 4) % 3
    action = ("перевіряю безпечні варіанти", "шукаю доступний слот", "формую конкретну пропозицію")[phase]
    lines = [
        paint("  USER IS QUIET", PINK),
        "",
        f"  [{bars}]  {second:02d} sec",
        "",
        paint("  [SILENCE FOLLOW-UP]", CYAN),
        f"  {label('→', MINT)} Агент {action}.",
        "",
        paint("  Не повторює питання. Продовжує роботу.", YELLOW),
    ]
    return box(lines, width)


def scene_value(frame: int, width: int) -> list[str]:
    lines = [
        paint("  VALUE", PINK),
        "",
        f"  {label('↓', MINT)} менше ручної координації",
        f"  {label('↑', MINT)} готових групових кошиків",
        f"  {label('✓', MINT)} реальні дані Сільпо",
        "",
        paint("  NEXT", CYAN),
        "  • group voting & preferences",
        "  • event templates: match / party / office",
        "  • proactive replacements & reminders",
        "",
        paint("  Gatherly: intent → action → checkout", YELLOW + BOLD),
    ]
    return box(lines, width)


RENDERERS = (
    scene_intro,
    scene_problem,
    scene_event,
    scene_autonomy,
    scene_mcp,
    scene_cart,
    scene_validation,
    scene_silence,
    scene_value,
)


def render(scene: int, frame: int) -> None:
    columns, rows = shutil.get_terminal_size((64, 28))
    width = min(64, max(42, columns - 4))
    title, subtitle = SCENES[scene]
    content = RENDERERS[scene](frame, width)
    output = ["", paint("  GATHERLY × SILPO MCP", DIM + CYAN)]
    output += [paint(f"  {scene + 1:02d} / {len(SCENES):02d}   {title}", BOLD + WHITE), paint(f"  {subtitle}", DIM)]
    output += [""] + content
    output += ["", paint("  ←/→ next scene   1–9 jump   q quit", DIM)]
    if len(output) < rows:
        output += [""] * (rows - len(output))
    sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(output[:rows]))
    sys.stdout.flush()


def read_key() -> str | None:
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    key = os.read(sys.stdin.fileno(), 3).decode(errors="ignore")
    if key == "\x1b[C":
        return "right"
    if key == "\x1b[D":
        return "left"
    return key


def main() -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit("Run this presentation inside an interactive terminal.")
    original = termios.tcgetattr(sys.stdin)
    scene = 0
    frame = 0
    try:
        tty.setcbreak(sys.stdin.fileno())
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        while True:
            render(scene, frame)
            key = read_key()
            if key in ("q", "Q", "\x03"):
                break
            if key in ("right", " ", "\r", "\n"):
                scene = min(len(SCENES) - 1, scene + 1)
                frame = 0
            elif key == "left":
                scene = max(0, scene - 1)
                frame = 0
            elif key and key.isdigit() and 1 <= int(key) <= len(SCENES):
                scene = int(key) - 1
                frame = 0
            time.sleep(0.12)
            frame += 1
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original)
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
