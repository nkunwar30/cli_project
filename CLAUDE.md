# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See also `CLAUDE.local.md` (gitignored, local to this machine) for personal working preferences,
including: always show the diff before committing changes, and follow standard indentation
conventions for the language in use.

## Project overview

MCP Chat is a command-line chat client that talks to Claude (Anthropic API) and exposes document
tools/resources/prompts via the MCP (Model Context Protocol). It's a learning/tutorial project
(from Anthropic's MCP course) with several `TODO`-style implementations already filled in.

The app has two halves that communicate over MCP's stdio JSON-RPC transport:
- **`main.py`** — the CLI chat client (what a user runs and types into).
- **`mcp_server.py`** — a `FastMCP` server exposing document tools/resources/prompts, launched
  automatically by `main.py` as a subprocess. It is *not* meant to be run or typed into directly —
  it just sits silently waiting for protocol messages, not plain text.

## Commands

Setup (uv, recommended):
```
uv venv
uv pip install -e .
```

Run the app:
```
uv run main.py
```
(Or plain `python main.py` if not using uv — set `USE_UV=0` in `.env` to match, since `main.py`
uses this to decide whether to shell out to `uv run mcp_server.py` or `python mcp_server.py`.)

Required `.env` vars: `CLAUDE_MODEL`, `ANTHROPIC_API_KEY`, `USE_UV` (`1` if using uv, `0` otherwise).

Inspect the MCP server standalone (tools/resources) without going through the chat client:
```
uv run mcp dev mcp_server.py
```
This launches the MCP Inspector web UI (requires Node/npx). Requires a real Windows console.

There are no lint or type checks configured, and no test suite in this project.

### Windows/PowerShell note

The CLI uses `prompt_toolkit`, which requires a genuine attached Windows console. Run `main.py`
(and `mcp dev`) from `cmd.exe` or PowerShell — **not** Git Bash/mintty, which will fail with
`NoConsoleScreenBufferError`.

## Architecture

**Request flow:** `core/cli.py` (prompt loop) → `core/cli_chat.py` (`CliChat`, extends `core/chat.py`'s
`Chat`) → `core/claude.py` (`Claude`, thin wrapper over the Anthropic SDK) → Anthropic API. Tool calls
in Claude's response are dispatched back out to MCP servers via `core/tools.py`'s `ToolManager`.

- **`core/chat.py` (`Chat`)** — the core agent loop: appends the user query, calls `Claude.chat`
  with all tools aggregated from every connected MCP client, and if the response's `stop_reason`
  is `"tool_use"`, executes those tool calls via `ToolManager` and loops again with the results
  appended as a user message. Loops until Claude returns a non-tool-use response.

- **`core/cli_chat.py` (`CliChat(Chat)`)** — adds document-specific behavior on top of `Chat`:
  - `@doc_id` mentions in a query are extracted and their content is injected into the prompt as
    `<document>` context (see `_extract_resources`), rather than requiring Claude to call a tool.
  - `/command doc_id` input is treated as an MCP *prompt* invocation (`_process_command`), not a
    normal chat turn — it fetches a prompt template from the doc server and converts its messages
    into the Anthropic message format via `convert_prompt_messages_to_message_params`.

- **`core/cli.py`** — `PromptSession`-based REPL (prompt_toolkit) with custom key bindings and a
  `UnifiedCompleter` that autocompletes `/commands` (from MCP prompts) and `@resource` mentions
  (from MCP document resources). Purely a UI layer; delegates actual work to `CliChat.run`.

- **`core/tools.py` (`ToolManager`)** — static/classmethod utility that aggregates tools across all
  connected `MCPClient`s (`get_all_tools`), finds which client owns a given tool by name
  (`_find_client_with_tool`), and executes Claude's `tool_use` requests against the right client,
  building Anthropic `tool_result` blocks from the results.

- **`mcp_client.py` (`MCPClient`)** — async context-manager wrapper around the MCP SDK's
  `ClientSession` + `stdio_client`, connecting to a server subprocess over stdio. One `MCPClient`
  instance per connected MCP server.

- **`mcp_server.py`** — the document server (`FastMCP`), backed by an in-memory `docs` dict
  (doc_id → content string; no persistence). Exposes:
  - Tools: `read_doc_contents`, `edit_doc_contents`
  - Resources: `docs://documents` (list all doc IDs), `docs://documents/{doc_id}` (one doc's content)
  - Prompts: `format` (rewrite a doc as markdown)
  - To add a new document, add an entry to the `docs` dict here.

**Multi-server support:** `main.py` always connects a `doc_client` to `mcp_server.py`, and additionally
spawns one `MCPClient` per extra server script passed as a CLI arg (`python main.py other_server.py`),
each launched via `uv run <script>`. All clients are aggregated in `ToolManager` so tools from any
connected server are available to Claude in the same chat loop.

**Message format bridging:** MCP types (`Tool`, `Prompt`, `PromptMessage`, `CallToolResult`) and
Anthropic SDK types (`MessageParam`, `ToolResultBlockParam`, `Message`) are distinct — most of the
glue code in `core/tools.py` and `core/cli_chat.py` exists to convert between the two.
