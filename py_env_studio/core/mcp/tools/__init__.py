"""MCP tool registry — Phase 1 read-only toolset only."""

from __future__ import annotations

from . import analysis, environments, packages, project, security

TOOL_DEFINITIONS = [
    {
        "name": "pyenv_list_environments",
        "description": "List Python environments known to Py Env Studio.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "handler": environments.list_environments,
    },
    {
        "name": "pyenv_get_environment",
        "description": "Return detailed information about one environment.",
        "inputSchema": {
            "type": "object",
            "properties": {"environment_id": {"type": "string"}},
            "required": ["environment_id"],
            "additionalProperties": False,
        },
        "handler": environments.get_environment,
    },
    {
        "name": "pyenv_list_packages",
        "description": "List installed packages in an environment (pip/uv aware).",
        "inputSchema": {
            "type": "object",
            "properties": {"environment_id": {"type": "string"}},
            "required": ["environment_id"],
            "additionalProperties": False,
        },
        "handler": packages.list_packages,
    },
    {
        "name": "pyenv_get_project_context",
        "description": "Authoritative project/environment/runtime context for the current project.",
        "inputSchema": {
            "type": "object",
            "properties": {"project_path": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": project.get_project_context,
    },
    {
        "name": "pyenv_get_environment_status",
        "description": "Concise machine-readable environment status.",
        "inputSchema": {
            "type": "object",
            "properties": {"environment_id": {"type": "string"}},
            "required": ["environment_id"],
            "additionalProperties": False,
        },
        "handler": environments.get_environment_status,
    },
    {
        "name": "pyenv_scan_vulnerabilities",
        "description": "Return cached vulnerability findings for an environment (no network scan).",
        "inputSchema": {
            "type": "object",
            "properties": {"environment_id": {"type": "string"}},
            "required": ["environment_id"],
            "additionalProperties": False,
        },
        "handler": security.scan_vulnerabilities,
    },
    {
        "name": "pyenv_get_dependency_information",
        "description": "Expose local dependency information (pip show based, offline).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "environment_id": {"type": "string"},
                "package": {"type": "string"},
            },
            "required": ["environment_id"],
            "additionalProperties": False,
        },
        "handler": project.get_dependency_information,
    },
    {
        "name": "pyenv_analyze_project",
        "description": "Analyze a Python project using Py Env Studio and return authoritative environment, Python runtime, package manager, dependency, outdated-package, vulnerability, runtime, and PES project configuration information. This operation is read-only and does not modify the project or environment.",
        "inputSchema": {
            "type": "object",
            "properties": {"project_path": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": analysis.analyze_project,
    },
]


def tool_schemas():
    """Return MCP tools/list entries (without handler internals)."""
    return [
        {
            "name": entry["name"],
            "description": entry["description"],
            "inputSchema": entry["inputSchema"],
        }
        for entry in TOOL_DEFINITIONS
    ]


def dispatch(tool_name, arguments):
    """Dispatch a tools/call to the registered handler (thin adapter)."""
    for entry in TOOL_DEFINITIONS:
        if entry["name"] == tool_name:
            return entry["handler"](arguments or {})
    return None
