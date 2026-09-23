# MCP Control Plane (Beta)

> **Status: beta.** The MCP server ships in beta. Tools, schemas, and response
> envelopes can change in a future minor release until the interface is marked
> stable. Feedback is welcome through
> [GitHub issues](https://github.com/pyenvstudio/py-env-studio/issues).

Py Env Studio (PES) exposes a **local, read-only** MCP (Model Context Protocol)
server so AI coding agents can consume authoritative Python environment state
instead of guessing it from files.

PES is **not** an AI model. The client (VS Code Copilot, Copilot CLI, Claude
Desktop, Cursor, …) does the reasoning; PES supplies environment, package,
dependency, security, runtime, and project facts from its own services,
database, and caches.

```text
MCP client (reasoning) ──stdio──▶ PES MCP server ──▶ PES Core services
                                                        environment · packages
                                                        security · runtime
                                                        project · database
```

## Beta scope and guarantees

| Property | Value |
|---|---|
| Transport | Local **stdio** only (no HTTP, no sockets, no network) |
| Access | **Read-only** — no tool mutates environments, packages, or projects |
| Scans | Never triggered by MCP; `pyenv_scan_vulnerabilities` returns the cached PES scan |
| Tools | 8 read-only tools (see the table below) |
| Default state | Enabled, but it runs only when a client launches `py-env-studio mcp` |
| Logging | Diagnostics go to **stderr**; stdout is reserved for protocol traffic |
| Protocol | MCP JSON-RPC 2.0, newline-delimited messages, protocol version `2024-11-05` |

## Requirements

- Python **3.12+**
- Py Env Studio **2.1.0+** installed so the `py-env-studio` command is on `PATH`
- An MCP-capable client (VS Code with Copilot Chat, GitHub Copilot CLI, Claude
  Desktop, Cursor, …)

## Step 1 — Verify the PES CLI works

```bash
py-env-studio --help      # flags, subcommands, and output options
py-env-studio --list      # environments PES knows about
```

`pes` and `pyenvstudio` are equivalent aliases installed alongside
`py-env-studio`, so `pes --help`, `pes --list`, and `pes mcp` all work the same
way (see the [CLI reference](../getting-started/cli.md#command-aliases)).

The installed version is reported by the `initialize` handshake shown below, by
**Help → About** in the GUI, and by `pip show py-env-studio` (which reads the
same `2.1.0` value as `pyproject.toml` and `py_env_studio/config.ini`).

If `py-env-studio` is not found, either use the full path to the executable
(for example
`C:\Users\<you>\AppData\Local\Programs\Python\Python312\Scripts\py-env-studio.exe`)
or invoke the module form `python -m py_env_studio mcp`.

Confirm the server starts and speaks JSON-RPC. Send an `initialize` message:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | py-env-studio mcp
```

On PowerShell the same one-liner works with single quotes; if your shell mangles
the braces, save the line to a file and redirect it
(`py-env-studio mcp < request.jsonl`).

Expected response (single line):

```json
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05",
 "capabilities": {"tools": {}},
 "serverInfo": {"name": "py-env-studio", "version": "2.1.0"}}}
```

Press `Ctrl+C` to stop a manually started server.

## Step 2 — Register the server in your MCP client

### VS Code with Copilot Chat (recommended: the guided flow)

1. Open the Command Palette (`Ctrl+Shift+P`).
2. Run **MCP: Add Server**.
3. Choose **stdio** as the server type.
4. Enter the command `py-env-studio` and the argument `mcp`.
5. Save the server to **Workspace** (`.vscode/mcp.json`) or to your **User
   profile**.

### VS Code with Copilot Chat (manual `.vscode/mcp.json`)

Create `.vscode/mcp.json` in the workspace (or open your user configuration with
the **MCP: Open User Configuration** command) and add:

```json
{
  "servers": {
    "py-env-studio": {
      "type": "stdio",
      "command": "py-env-studio",
      "args": ["mcp"]
    }
  }
}
```

When the command is not on `PATH`, point `command` at the interpreter and pass
the module as the first argument:

```json
{
  "servers": {
    "py-env-studio": {
      "type": "stdio",
      "command": "C:\\Python312\\python.exe",
      "args": ["-m", "py_env_studio", "mcp"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

### Portable format (Copilot CLI, Agent Host, other clients)

Clients that use the portable format read a top-level `mcpServers` object from
`.mcp.json` at the workspace root or `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "py-env-studio": {
      "command": "py-env-studio",
      "args": ["mcp"]
    }
  }
}
```

Claude Desktop uses `claude_desktop_config.json` in the platform-specific
`%APPDATA%\Claude` (Windows), `~/Library/Application Support/Claude` (macOS), or
`~/.config/Claude` (Linux) directory with the same `mcpServers` shape, and
Cursor uses `~/.cursor/mcp.json` (global) or `<workspace>/.cursor/mcp.json`.

## Step 3 — Start and trust the server

1. In VS Code, run **MCP: List Servers** from the Command Palette.
2. Select `py-env-studio` and choose **Start** (or **Restart** after a config
   change).
3. Approve the MCP server trust prompt. Workspace servers inherit Workspace
   Trust; user-level servers show a separate trust dialog on first start or
   after their configuration changes.
4. Open Copilot Chat and use **Configure Tools** to confirm the eight
   `pyenv_*` tools are listed, and toggle off any tool you do not want the
   agent to use.

VS Code can also start configured servers automatically when you send a chat
message; the `chat.mcp.autostart` setting controls that behaviour
(`never`, `onlyNew`, `newAndOutdated`).

## Step 4 — Ask the agent something

Once the tools are available, prompts such as these resolve from PES state
instead of guesswork:

- "Which Python environments does PES manage, and which one is the current
  project using?"
- "List the packages installed in environment `<environment_id>`."
- "Analyze this project with PES and report the Python version, package
  manager, outdated packages, and any cached vulnerabilities."

To call a tool directly for debugging:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "pyenv_get_project_context", "arguments": {}}}
```

## Step 5 — (Optional) Tune the MCP settings

The server reads the `[mcp]` section of the PES `config.ini` (the packaged
default lives in `py_env_studio/config.ini`; the active copy lives in the
platform user-data directory):

```ini
[mcp]
enabled = true
server_name = py-env-studio
transport = stdio
log_level = INFO
```

| Setting | Default | Purpose |
|---|---|---|
| `enabled` | `true` | Set to `false` to refuse `py-env-studio mcp` startup |
| `server_name` | `py-env-studio` | Name reported in the `initialize` handshake |
| `transport` | `stdio` | Reserved for future transports; stdio is the only supported value in beta |
| `log_level` | `INFO` | Logging verbosity for MCP diagnostics (stderr only) |

When the server is disabled, startup exits with
`MCP server is disabled (config [mcp] enabled=false).` on stderr.

## Tools (beta, read-only)

| Tool | Input | Source |
|---|---|---|
| `pyenv_list_environments` | — | `core.env_manager` environment inventory |
| `pyenv_get_environment` | `environment_id` | `core.env_manager.get_environment_info` |
| `pyenv_get_environment_status` | `environment_id` | environment + package count + runtime registry |
| `pyenv_list_packages` | `environment_id` | `core.package_manager` (pip/uv aware) |
| `pyenv_get_project_context` | `project_path?` | `core.runtime_toggle` status + metadata |
| `pyenv_get_dependency_information` | `environment_id`, `package?` | `core.dependency_preview` (`pip show`, offline) |
| `pyenv_scan_vulnerabilities` | `environment_id` | cached scan via `utils.handlers.DBHelper` |
| `pyenv_analyze_project` | `project_path?` | `core.project_intelligence.ProjectIntelligenceService` |

`pyenv_analyze_project` is the aggregate tool: one call returns the PES project
configuration, resolved environment, Python runtime, package manager,
dependencies, outdated packages, cached vulnerabilities, and runtime state.

### Response envelope

Successful calls return the payload inside `structuredContent` (and the same
JSON as text content):

```json
{"success": true, "data": {"..." : "..."},
 "metadata": {"source": "pes", "cached": true, "timestamp": "2026-09-23T12:00:00+00:00"}}
```

Failures use a structured error and set `isError` on the MCP content envelope:

```json
{"success": false,
 "error": {"code": "ENVIRONMENT_NOT_FOUND", "message": "...", "details": {}}}
```

Error codes: `ENVIRONMENT_NOT_FOUND`, `PROJECT_NOT_FOUND`, `AMBIGUOUS_PROJECT`,
`INVALID_INPUT`, `SERVICE_UNAVAILABLE`, `SCAN_UNAVAILABLE`.

An environment with no cached scan returns `success: true` with
`"scan_available": false` and `"findings": []` — PES never performs a network
lookup on behalf of MCP.

## Security and privacy

- The transport is local stdio: nothing is exposed on a port and no MCP tool
  makes a network request.
- Vulnerability data is read from the cache PES already produced; use
  **Tools → Scan Now** in the GUI (or refresh the dashboard) to update it.
- MCP returns environment, package, dependency, and project *metadata*. A
  project analysis can include installed package names and versions, so treat
  tool output like any other repository metadata.
- Like every MCP server, `py-env-studio mcp` is a local process started by your
  client: only register it from configuration you control.

## Troubleshooting

| Symptom | Resolution |
|---|---|
| Server missing in **MCP: List Servers** | Re-check `.vscode/mcp.json` (top-level `servers`) or the portable `.mcp.json` (top-level `mcpServers`); run **MCP: Open Workspace Folder MCP Configuration** to edit the right file |
| `command not found` / server exits immediately | `py-env-studio` is not on the client's `PATH`; use the full executable path or the `python -m py_env_studio mcp` form |
| Tools list is empty | Start/restart the server, then run **MCP: Reset Cached Tools** and reload the chat |
| Tools return `INVALID_INPUT` | Call `pyenv_list_environments` first and pass the returned `environment_id` |
| `PROJECT_NOT_FOUND` / `AMBIGUOUS_PROJECT` | Pass an explicit `project_path`, or run `pes init` in the project so PES has `pes.config` metadata |
| `scan_available: false` | Run a PES vulnerability scan for that environment first; MCP only reads cached results |
| Output shows nothing but chat cannot reach the server | Read the server log via **MCP: List Servers → Show Output**; PES writes diagnostics to stderr only |
| Startup says the server is disabled | Set `enabled = true` in the `[mcp]` section of `config.ini` |

## Disable or remove

- Add `enabled = false` to the `[mcp]` section of `config.ini` to refuse startup
  for every client.
- Or remove the `py-env-studio` entry from `.vscode/mcp.json`,
  `~/.copilot/mcp-config.json`, or the equivalent client configuration.

## Related topics

- [Features & current implementation](current-implementation.md) — section 25
- [Architecture](architecture.md)
- [CLI reference](../getting-started/cli.md)
- [v2.1.0 release notes](../releases/v2.1.0.md)
