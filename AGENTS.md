# Working agreement for Hackaton Winner

## Product and current objective

This project connects a Telegram bot to an LLM agent that can call MCP tools.

The current milestone is deliberately narrow:

```text
Telegram message
  -> aiogram handler
  -> agent_loop(mcp_client, tools, user_message)
  -> LLM and MCP tool calls
  -> final text returned by agent_loop
  -> Telegram reply
```

The definition of done for this milestone is practical: a user sends `/start`
or a text message to the configured Telegram bot; the message reaches the
agent; MCP tool calls work when needed; and the final text arrives back in
Telegram.

Do not expand this milestone with history, locks, TDD/BDD infrastructure,
refactors, new abstractions, or unrelated features. Record follow-up ideas
instead of implementing them early.

## Plan for the current milestone

1. Inspect the existing agent, MCP client, LLM client, tool list, and Telegram
   entry point. Preserve unrelated work already present in the worktree.
2. Make `agent_loop(...)` return the assistant's final text instead of only
   printing it. Keep its existing LLM -> tool call -> MCP -> LLM behaviour.
3. Keep one MCP connection open around `dp.start_polling(...)`.
4. Put the live `mcp_client` and the loaded `tools` into aiogram workflow data
   so handlers receive them by dependency injection.
5. Make the text-message handler intentionally thin: pass `message.text`,
   `mcp_client`, and `tools` to `agent_loop`, then send its returned text with
   `message.answer(...)`.
6. Ensure `/start` is handled separately and that the catch-all handler does
   not copy/echo an incoming message before the agent responds.
7. Run the bot at the integration checkpoints below and test a real Telegram
   message. Stop after the vertical slice works; only then inspect observed
   failures and plan the next improvement.

## Engineering rules

- Start with a small written contract: purpose, inputs, output, failure
  behaviour, and how the result will be checked. Do this before changing code.
- Make one small, fixed change per iteration: one hypothesis, normally no more
  than 15–20 changed lines. Do not combine cleanup, refactoring, and a feature
  in the same iteration.
- "Minimal" means the smallest coherent, production-correct behaviour, not
  the smallest possible diff. Delete obsolete, sample, or broken code in the
  same change when it conflicts with its correct replacement.
- Do not repurpose misleading sample code (for example an echo handler) into
  production behaviour merely to reduce a diff. Replace it with clearly named,
  direct code.
- Do not create mocks, dummy tests, wrappers, or abstractions when they add
  more complexity than the behaviour they verify.
- Add a focused test only when it gives real signal without creating test
  scaffolding larger than the change. Run it, report the result, and wait for
  user review before starting the next implementation change.
- Prefer the smallest change that proves the current hypothesis. Do not
  redesign working components merely because a cleaner design is possible.
- Keep transport code dumb. Telegram handlers translate Telegram input/output;
  agent code owns LLM/MCP orchestration; MCP code owns MCP communication.
- Preserve existing public interfaces unless the current milestone explicitly
  requires changing them. When an interface changes, update every in-repo
  caller in the same change.
- Do not silently swallow errors. At integration boundaries, log enough
  context to diagnose the failing layer without logging secrets or tokens.
- Report observed incorrect behaviour with the concrete evidence that exposed
  it. Do not silently accept it, present an inference as a verified result, or
  hide it behind a prompt-only change.
- Treat `message.text` as optional. Non-text Telegram updates need an explicit
  user-facing response or deliberate filtering; never pass `None` to the LLM
  by accident.
- Never commit credentials. Read `BOT_TOKEN` and API keys from environment
  variables; keep `.env` untracked.
- Do not modify unrelated dirty files. Check `git status` before and after a
  task, and call out any pre-existing changes that overlap the requested work.
- Use `apply_patch` for source edits. Avoid destructive Git commands unless the
  user explicitly asks for them.

## Run and verification discipline

Running the application and its tests is part of development, not a final
afterthought. Ask the user to provide required external configuration only
when it is truly missing; otherwise execute the relevant checks.

Run the application at these critical moments:

1. **Baseline, before integration edits:** start the current bot/agent entry
   point long enough to confirm imports, configuration, and MCP startup.
2. **After wiring MCP around polling:** start the bot and verify it reaches
   polling without a dependency-injection or connection-startup error.
3. **After handler wiring:** send `/start` and one plain text message from
   Telegram; confirm the reply arrives.
4. **After a tool-call path is reachable:** send one message that requires an
   MCP tool; confirm the tool is called and the final answer returns to
   Telegram.
5. **Before hand-off:** repeat the happy-path Telegram check after the full
   test suite passes.

For every code change:

- Run the narrowest relevant automated test first.
- Run the complete test suite before claiming the task is complete.
- Run a syntax/import check when tests do not cover the changed entry point.
- Report the exact command, result, and any check that could not run because
  it requires an external service, token, or a real Telegram interaction.

For this repository, discover the authoritative commands from project config
before inventing them. The expected first candidates are:

```bash
pytest
python -m src.bot.bot
python -m src.agent.loop
```

Use the project's virtual environment/interpreter when its configuration
requires it. Do not leave a polling process running after a verification step;
stop it cleanly.

## Test strategy after the vertical slice

Only after end-to-end messaging works:

- Describe user-visible behaviours in BDD-style language.
- Add focused tests for agent final-response return, tool-call continuation,
  Telegram dependency injection, and non-text/error paths.
- Use TDD as an execution discipline for new behaviour: failing focused test,
  minimal implementation, test pass, then refactor.
- Keep real LLM/MCP/Telegram calls out of ordinary unit tests; use fakes or
  mocks there, and reserve real services for explicit integration checks.

## Collaboration protocol

Before implementation, communicate the current hypothesis and the next
verifiable step. After each small iteration, stop for review and report: the
changed file and line count, the exact behaviour changed, the test/run command
and result, and the next proposed hypothesis. Never continue to the next code
change without the user's approval.
