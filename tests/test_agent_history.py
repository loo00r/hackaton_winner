import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

from src.agent import loop


def show_messages(title, messages):
    print(f"\n{title}")
    for message in messages:
        print(json.dumps(message, ensure_ascii=False))


def assistant(content, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    payload = {"role": "assistant", "content": content}
    if tool_calls:
        payload["tool_calls"] = [{
            "id": call.id,
            "type": "function",
            "function": {"name": call.function.name, "arguments": call.function.arguments},
        } for call in tool_calls]
    message.model_dump = lambda **_: payload
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_history_keeps_completed_tool_turn_for_next_user_message(monkeypatch):
    calls = []
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="silpo_get_my_shopping_cart", arguments="{}"),
    )
    responses = iter([assistant(None, [tool_call]), assistant("Потрібно число гостей."), assistant("Продовжую.")])
    def create(**kwargs):
        calls.append(deepcopy(kwargs["messages"]))
        return next(responses)

    monkeypatch.setattr(loop.llm_client.chat.completions, "create", create)
    mcp_client = SimpleNamespace(call_tool=lambda *_: asyncio.sleep(0, SimpleNamespace(structured_content={"exists": True})))
    loop.history_by_chat.clear()

    asyncio.run(loop.agent_loop(mcp_client, [], "Організуй вечірку", chat_id=1))
    asyncio.run(loop.agent_loop(mcp_client, [], "Буде 5 людей", chat_id=1))

    show_messages("GPT input after the user's second message:", calls[2])
    assert [item["role"] for item in calls[2][1:]] == ["user", "assistant", "tool", "assistant", "user"]
    assert calls[2][2]["tool_calls"][0]["id"] == calls[2][3]["tool_call_id"] == "call_1"
    assert calls[2][-1]["content"] == "Буде 5 людей"


def test_history_is_isolated_by_chat_id(monkeypatch):
    calls = []
    def create(**kwargs):
        calls.append(deepcopy(kwargs["messages"]))
        return assistant("Готово")

    monkeypatch.setattr(loop.llm_client.chat.completions, "create", create)
    loop.history_by_chat.clear()

    asyncio.run(loop.agent_loop(None, [], "Чат один", chat_id=1))
    asyncio.run(loop.agent_loop(None, [], "Чат два", chat_id=2))

    show_messages("GPT input for chat_id=2:", calls[1])
    assert [item["content"] for item in calls[1][1:]] == ["Чат два"]
