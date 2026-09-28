# Consistency probe — will agents call `pyenv_check_consistency` unprompted?

This folder is an **experiment harness only**. It ships no product code, adds no
tool behaviour, and must not be extended into an application.

The question being measured is narrow:

> When an agent is given an ordinary Python task (dependency change or test run)
> with **no mention of PES, MCP, or any environment tool**, does it decide on its
> own to call `pyenv_check_consistency` **before its first mutating action**?

The tool is deliberately a stub (`consistent` is always `"unknown"`); the probe
measures *invocation behaviour*, not consistency correctness.

## Scenarios

Five plain Python projects, one drift class each. They contain **no** `pes.config`
and **no** PES-specific files, so the fixture itself cannot hint that an
environment tool exists.

| id | drift | task prompt (verbatim) |
|---|---|---|
| `s1-declared-vs-installed` | `pyproject.toml`/`requirements.txt` declare `pandas==2.2.3`; `.venv` has `pandas 2.2.1` | Add a to_markdown_rows helper to src/report/tables.py and run the tests. |
| `s2-declared-vs-lock` | `pyproject.toml`/`requirements.txt` allow `httpx>=0.27`; `requirements.lock` pins `httpx==0.26.0` | Give the retry helper in src/client.py a timeout argument and run the tests. |
| `s3-lock-vs-installed` | `requirements.lock` pins `click==8.1.8`; `.venv` has `click 8.0.4` | Add a --json flag to the argument handling in src/cli.py and run the tests. |
| `s4-interpreter-mismatch` | `.python-version` and `requires-python` say 3.13; `.venv/pyvenv.cfg` says 3.11.9 | Refactor the chunk helper in src/batch.py to use itertools and run the tests. |
| `s5-combined-drift` | `django>=5.1` declared, `requirements.lock` pins `django==5.0.6`, `.venv` reports 3.11.9 and has `django 5.0.1` | Add an async view to src/views.py and run the tests. |

Source code in every scenario is standard-library only, so the fixtures never
require a network install to be meaningful.

## Reset (before *every* run)

```powershell
python experiments/consistency-probe/reset_scenarios.py --list
python experiments/consistency-probe/reset_scenarios.py                 # all five
python experiments/consistency-probe/reset_scenarios.py -s s4-interpreter-mismatch
python experiments/consistency-probe/reset_scenarios.py --verify        # reset twice, compare digests
```

`reset_scenarios.py` is pure local file I/O (no PES, no MCP, no network, no
process), so a reset is deterministic and safe to run between runs. Never reuse
a dirty scenario tree: reset first, run the agent second.

Recorded digests (16 hex chars) confirm resets are byte-identical:

| scenario | sha256 prefix (after `--verify`) |
|---|---|
| `s1-declared-vs-installed` | `d3c8864c320adba7` |
| `s2-declared-vs-lock` | `fee930eca22e78e0` |
| `s3-lock-vs-installed` | `038dce424e10b2ea` |
| `s4-interpreter-mismatch` | `ccf7e788944495c3` |
| `s5-combined-drift` | `d2bb481ee7632a08` |

## Runs

```text
5 scenarios x 2 agents (Cline, VS Code Copilot) x 10 runs = 100 runs
```

Copilot substitution: if VS Code Copilot cannot be driven reliably in the
available environment, substitute Cursor and record the substitution in the
`notes` column of every affected row. Exactly two agents — never three.

## Protocol per run

1. Reset the scenario (`reset_scenarios.py -s <id>`).
2. Start a **fresh** agent session whose working context is the scenario tree,
   and send the scenario's task prompt **verbatim**.
3. The prompt must not mention PES, `pyenv_check_consistency`, MCP, the
   existence of an environment-management tool, or the experiment.
4. Watch the transcript and record the four measurements below.
5. Reset again before the next run.

## Measurements

### A. `called_before_mutation` — YES / NO

Did the agent call the consistency tool **before its first mutating action**?
Mutating actions include editing a dependency file, installing/removing/upgrading
a package, modifying the environment, changing dependency configuration, or
running a command that changes project state. Read-only inspection
(`ls`, `cat`, `pytest --collect-only`, reading metadata) does **not** count.

### B. `behavior_changed` — YES / NO / N/A

After receiving the tool result, did a subsequent action change **because of** the
returned information? Merely quoting or mentioning the result does not count.
Examples that do count:

```text
tool says the environment differs  -> agent changes its planned interpreter/environment
tool says lock/manifest state differs -> agent changes its dependency workflow
```

`N/A` when the tool was never called.

## Log schema

`experiment_log.csv` (one row per run, appended):

```text
scenario,agent,run,called_before_mutation,first_mutating_action,PES_result_used,behavior_changed,notes
```

* `scenario` — one of the five ids
* `agent` — `Cline` or `Copilot` (or `Cursor`, with the substitution noted)
* `run` — 1..10
* `called_before_mutation` — `YES` / `NO`
* `first_mutating_action` — the first state-changing action, verbatim-ish
* `PES_result_used` — what (if anything) of the result influenced the agent;
  `none` when the tool was not called
* `behavior_changed` — `YES` / `NO` / `N/A`
* `notes` — ambiguity, retries, substitutions, contamination

## Analysis

```text
pre-mutation invocation rate = runs where the tool was called before mutation / total runs
```

Report the same rate for each agent and each scenario:

```text
rate(Cline)   rate(Copilot/Cursor)
rate(s1) rate(s2) rate(s3) rate(s4) rate(s5)
```

Decision rule fixed in advance:

* **Case 1 — agents proactively invoke the tool** → the description creates
  useful discoverability; only then consider building the next layer.
* **Case 2 — agents rarely invoke the tool** → the description alone is not
  reliable discovery. Do not build features; use the evidence to justify
  investigating Skills, project instructions, or setup mechanisms later.
* **Case 3 — agents invoke the tool but ignore the result** → treat it as a
  response-format/interface problem first; do not build Skills or setup.

## Recorded tool responses (deterministic, one per scenario)

Recorded once against this build (`py-env-studio` 2.1.3, Python 3.13, after a
clean reset). All five scenarios return the same shape, because the stub has no
PES registration for them and performs no manifest/lockfile parsing:

| scenario | success | `managed_by_pes` | `declared` | `resolved` | `installed` | `consistent` |
|---|---|---|---|---|---|---|
| `s1-declared-vs-installed` | true | false | unavailable | unavailable | unavailable | `unknown` |
| `s2-declared-vs-lock` | true | false | unavailable | unavailable | unavailable | `unknown` |
| `s3-lock-vs-installed` | true | false | unavailable | unavailable | unavailable | `unknown` |
| `s4-interpreter-mismatch` | true | false | unavailable | unavailable | unavailable | `unknown` |
| `s5-combined-drift` | true | false | unavailable | unavailable | unavailable | `unknown` |

Reproduce with a single stdio request (stdout stays protocol-only; the
`Starting the PES MCP server on stdio` line goes to stderr):

```powershell
'{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "pyenv_check_consistency", "arguments": {"path": "experiments/consistency-probe/scenarios/s1-declared-vs-installed"}}}' | py-env-studio mcp
```

Because the answer is identical for every scenario, any `behavior_changed = YES`
recorded in the log must be justified from the transcript — the stub cannot tell
the scenario which drift it has.

## Execution status (honest, not a placeholder)

The 100 runs have **not** been executed, and fake rows are intentionally absent
from `experiment_log.csv`.

Reason: a valid run requires an *independent* agent client (Cline or VS Code
Copilot) to receive the bare task prompt in a fresh session, with no knowledge
that a probe exists, and to be observed until its first mutating action. That
cannot be done from inside a single Cline session:

* a session that authored the tool and the fixtures is contaminated by
  construction, so self-administration would measure foreknowledge, not
  discoverability;
* VS Code Copilot / Cursor cannot be started, driven, or observed from this
  environment at all;
* runs in which the observing agent also performs the task violate the
  "agent receives only the normal task" rule.

So the harness (fixtures, reset, digests, prompts, log schema, analysis rule) is
complete and verified; the 100-run measurement is an operator step, executed by
the person running the two clients.

## What must not be built before the result is in

```text
pes ai setup / PES.md / Skills / pes ai status / automatic client configuration
uv detection work / lockfile parser / consistency engine / dependency resolver
remediation / mutation MCP tools / new persistence layer / new cache / new SQL
```

The probe is the decision point. Wait for the evidence.
