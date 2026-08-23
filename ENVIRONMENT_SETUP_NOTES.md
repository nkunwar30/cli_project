# Setting Up This Project on a New Laptop — What We Did and Why

This project was originally set up on an office laptop and the whole folder
(code + `.venv` + caches) was copied over to a personal laptop. Below is a
plain-language walkthrough of what broke, what we fixed, and why — so future
you (or anyone else) can follow the same reasoning if this happens again.

## 1. The problem: a copied `.venv` doesn't work on a new machine

A Python virtual environment (`.venv`) is not just a folder of packages — it
contains a file, `.venv\pyvenv.cfg`, that hardcodes the **exact file path**
of the Python installation it was built from. On the office laptop, that was:

```
C:\Users\Niraj.kumar\AppData\Local\Programs\Python\Python312
```

That path doesn't exist on the personal laptop, so every script inside
`.venv\Scripts\` (including `activate.bat`) was pointing at a dead
location. This is why **virtual environments should never be copied between
machines** — they're a generated build artifact tied to one specific
computer, not portable code.

## 2. The fix: rebuild the environment instead of repairing it

Rather than trying to patch the broken paths, we deleted `.venv` entirely and
rebuilt it using `uv sync`. This works because two files in the project *are*
portable, plain-text, and machine-independent:

- **`pyproject.toml`** — lists the project's dependencies (e.g. `anthropic`,
  `mcp`, `prompt-toolkit`).
- **`uv.lock`** — the exact, pinned versions of every dependency (and
  sub-dependency) that were resolved and tested on the office laptop.

`uv sync` reads those two files and:
1. Picks a Python interpreter available on *this* machine.
2. Creates a brand-new `.venv` pointing at that interpreter.
3. Installs every package at the exact locked version.

Result: a `.venv` that behaves identically to the original, but is physically
built for this machine.

**Takeaway for next time:** when moving this project to a new computer, copy
only the source files, `pyproject.toml`, and `uv.lock`. Never copy `.venv`,
`__pycache__`, or any cache folder — just run `uv sync` fresh on the new
machine.

## 3. A hiccup: Python 3.14 vs. 3.13

`uv sync`'s first attempt auto-selected Python 3.14 (the newest version
installed on this laptop). That failed, because `pydantic-core` (a
dependency of `mcp`) is written in Rust, and its maintainers hadn't published
a precompiled Windows wheel for Python 3.14 yet. `uv` tried to compile it
from source, which itself failed due to a broken local Rust toolchain
installer.

Fix: we re-ran `uv sync`, explicitly pointing it at the Python 3.13
installation already present on this laptop, which *does* have a
precompiled wheel available. Install succeeded cleanly.

## 4. The leftover `uv-cache` folder

The project folder also contained a `uv-cache` directory, brought over from
the office laptop. Investigation showed:

- It was nearly empty (a few KB — just some metadata, not real package
  data).
- Nothing in the current project configuration referenced it.
- `uv`'s actual cache lives globally at `%LOCALAPPDATA%\uv\cache`, shared
  across all projects on a machine — not inside any one project folder.

Best guess: on the office laptop, this may have been created to work around
a OneDrive-related sync/hardlink conflict (OneDrive doesn't handle cache
folders that rely on hardlinks well). On this personal laptop, the project
isn't inside a OneDrive-synced folder, so it wasn't needed — it was deleted
as harmless cleanup.

## 5. Final snag: the interactive CLI needs a *real* console

Even after the environment was fixed, running:

```
uv run python main.py
```

from a Git Bash terminal (or through any tool that redirects/pipes output)
failed with `NoConsoleScreenBufferError`. This is unrelated to packages or
the venv — it's because this app uses `prompt_toolkit` for its interactive
prompt, which requires a **genuine attached Windows console**. Git Bash's
terminal (`mintty`) emulates a Unix-style terminal (`xterm-256color`)
instead of a real Windows console, so `prompt_toolkit` can't talk to it.

**Fix:** run the app from `cmd.exe` or a plain PowerShell console window
(not Git Bash). Confirmed working there.

## 6. `mcp_server.py` isn't meant to be run and typed into directly

Trying to run `mcp_server.py` on its own and typing into the terminal appears
to do nothing. That's expected, not a bug.

`mcp_server.py` ends with `mcp.run(transport="stdio")` (`mcp_server.py:62`) —
it's a backend server that speaks a structured JSON-RPC protocol (MCP =
Model Context Protocol) over `stdin`/`stdout`, not a human-readable chat
interface. When run by hand, it just sits there silently waiting for
properly-formatted protocol messages, not plain typed text.

This server is already used automatically: `main.py` (`main.py:31-39`)
launches `uv run mcp_server.py` itself as a background subprocess every time
you run the app, and talks to it over that same protocol. So running the app
normally already exercises this file — there's no need to run it by hand.

### Testing `mcp_server.py` in isolation with MCP Inspector

If you want to poke at the server's tools and resources directly (without
going through the full chat app), use the **MCP Inspector** — a small web UI
that speaks the MCP protocol for you. Requires Node.js (`npx`), which is
already installed on this machine. There are two equivalent ways to launch
it:

**Option A — the `mcp` CLI shortcut (what the tutorial refers to)**

The `mcp[cli]` package (already a project dependency) ships a `dev` command
that launches the Inspector for you in one step:

```
uv run mcp dev mcp_server.py
```

**Option B — manual `npx` invocation**

```
npx @modelcontextprotocol/inspector uv run mcp_server.py
```

Both do the same thing under the hood. Steps:

1. Open **PowerShell** or **cmd.exe** (not Git Bash — same real-console
   requirement as running `main.py`).
2. Navigate to the project folder:
   ```
   cd "H:\Niraj\Niraj Personal\Learnings\Claude Code\anthropic_tutorial\cli_project"
   ```
3. Run either Option A or Option B above. First run downloads the Inspector
   package (small delay). Once started, it prints `Starting MCP
   inspector...` followed by a URL with an auth token, e.g.:
   ```
   MCP Inspector is up and running at:
   http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=xxxxxxxx...
   ```
4. Open that exact URL (including the token) in your browser.
5. Click **Connect** — it should already show the correct command/arguments
   to launch `mcp_server.py`.
6. To test the **tools**: go to the **Tools** tab. You should see
   `read_doc_contents` and `edit_doc_contents` (defined at
   `mcp_server.py:17-37`). Pick one, fill in a `doc_id` (e.g.
   `deposition.md`), and click **Run Tool** to see it return data live.
7. To test the **resources**: go to the **Resources** tab instead. You
   should see `docs://documents` (lists all doc IDs) and
   `docs://documents/{doc_id}` (returns one doc's contents, defined at
   `mcp_server.py:40-55`). Click a resource, fill in `doc_id` if prompted,
   and read its contents live.
8. Press `Ctrl+C` in the terminal when done to stop the Inspector.

**Troubleshooting — "MCP Inspector PORT IS IN USE at http://localhost:6274":**
this means an earlier Inspector session (from this or a previous run) is
still running somewhere and holding port 6274. Check other open
terminal windows for a still-running `mcp dev` / `npx inspector` process and
stop it with `Ctrl+C`. If you can't find it, open Task Manager and look for
lingering `node.exe`, `mcp.exe`, or `uv.exe` processes tied to this project
and end them, then retry.

## Summary

| Issue | Cause | Fix |
|---|---|---|
| Broken `.venv` | Hardcoded path from office laptop | Deleted `.venv`, rebuilt with `uv sync` |
| Build failure on first `uv sync` | Auto-picked Python 3.14, no wheel for `pydantic-core` | Pinned to Python 3.13 |
| Leftover `uv-cache` folder | Likely a OneDrive workaround from the old machine, unused here | Deleted |
| App crashed with console error | Git Bash doesn't provide a real Windows console | Run from `cmd.exe` / PowerShell instead |
| `mcp_server.py` looked frozen when run directly | It's a stdio protocol server, not a chat interface — waits silently for structured messages | Use it via `main.py` (automatic) or test standalone with MCP Inspector |

**Going forward:** to set this project up on any new machine, copy the
source files + `pyproject.toml` + `uv.lock` only, then run `uv sync`, then
launch the app from `cmd.exe` or PowerShell (not Git Bash).
