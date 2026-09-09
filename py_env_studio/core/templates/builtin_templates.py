"""Built-in phase 1 templates for Py Env Studio."""

from __future__ import annotations

from .models import TemplateFile, TemplateSpec


def _common_gitignore() -> str:
    return """__pycache__/
*.py[cod]
.venv/
.env
.pytest_cache/
.ruff_cache/
.mypy_cache/
dist/
build/
*.egg-info/
"""


def _license_text() -> str:
    return """MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def _script_template() -> TemplateSpec:
    return TemplateSpec(
        id="python-script",
        name="Python Script",
        version="1.0.0",
        description="Simple src-layout Python application with tests and quality tooling.",
        supported_python_versions=["3.10", "3.11", "3.12", "3.13"],
        min_python="3.10",
        architecture="src-layout",
        style="application",
        included_tooling=["pytest", "ruff", "mypy"],
        runtime_dependencies=[],
        dev_dependencies=["pytest>=8.0", "ruff>=0.6", "mypy>=1.10"],
        structure_preview=[
            "src/{module_name}/__init__.py",
            "src/{module_name}/__main__.py",
            "src/{module_name}/main.py",
            "tests/test_main.py",
            "pyproject.toml",
            "README.md",
            ".gitignore",
            "LICENSE",
        ],
        files=[
            TemplateFile(
                path="src/{module_name}/__init__.py",
                content='"""{project_name} package."""\n',
            ),
            TemplateFile(
                path="src/{module_name}/main.py",
                content="""from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    LOGGER.info("{project_name} started")
    print("Hello from {project_name}!")
    return 0
""",
            ),
            TemplateFile(
                path="src/{module_name}/__main__.py",
                content="""from .main import main


if __name__ == "__main__":
    raise SystemExit(main())
""",
            ),
            TemplateFile(
                path="tests/test_main.py",
                content="""from {module_name}.main import main


def test_main_returns_zero() -> None:
    assert main() == 0
""",
            ),
            TemplateFile(path=".gitignore", content=_common_gitignore()),
            TemplateFile(path="LICENSE", content=_license_text()),
            TemplateFile(
                path="README.md",
                content="""# {project_name}

{description}

## Python Version

Requires Python >= {python_version}

## Structure

```
src/{module_name}/
tests/
```

## Setup

```bash
python -m venv .venv
```

## Run

```bash
python -m {module_name}
```

## Test

```bash
pytest
```

## Lint

```bash
ruff check .
```

## Type Check

```bash
mypy src
```
""",
            ),
            TemplateFile(
                path="pyproject.toml",
                content="""[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{distribution_name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">={python_version}"
dependencies = []

[dependency-groups]
dev = [
  "pytest>=8.0",
  "ruff>=0.6",
  "mypy>=1.10",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py{python_tag}"

[tool.mypy]
python_version = "{python_version}"
warn_return_any = true
warn_unused_configs = true

[tool.setuptools.packages.find]
where = ["src"]
""",
            ),
        ],
    )


def _cli_template() -> TemplateSpec:
    return TemplateSpec(
        id="python-cli",
        name="Python CLI",
        version="1.0.0",
        description="Production-oriented Python CLI with argparse, tests, and tooling.",
        supported_python_versions=["3.10", "3.11", "3.12", "3.13"],
        min_python="3.10",
        architecture="src-layout",
        style="cli",
        included_tooling=["pytest", "ruff", "mypy", "argparse"],
        runtime_dependencies=[],
        dev_dependencies=["pytest>=8.0", "ruff>=0.6", "mypy>=1.10"],
        structure_preview=[
            "src/{module_name}/__init__.py",
            "src/{module_name}/__main__.py",
            "src/{module_name}/cli.py",
            "src/{module_name}/config.py",
            "tests/test_cli.py",
            "pyproject.toml",
            "README.md",
            ".gitignore",
            "LICENSE",
        ],
        files=[
            TemplateFile(path="src/{module_name}/__init__.py", content='"""{project_name} CLI package."""\n'),
            TemplateFile(
                path="src/{module_name}/config.py",
                content="""from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "{project_name}"
""",
            ),
            TemplateFile(
                path="src/{module_name}/cli.py",
                content="""from __future__ import annotations

import argparse
import logging

from .config import AppConfig

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="{cli_command_name}", description="{description}")
    subparsers = parser.add_subparsers(dest="command")

    greet = subparsers.add_parser("greet", help="Print a greeting")
    greet.add_argument("name", nargs="?", default="world", help="Name to greet")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "greet":
        cfg = AppConfig()
        LOGGER.info("Running greet command")
        print(f"{{cfg.app_name}}: hello, {{args.name}}!")
        return 0

    parser.print_help()
    return 0
""",
            ),
            TemplateFile(
                path="src/{module_name}/__main__.py",
                content="""from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
""",
            ),
            TemplateFile(
                path="tests/test_cli.py",
                content="""from {module_name}.cli import main


def test_cli_help_returns_success() -> None:
    assert main(["--help"]) == 0


def test_cli_greet_returns_success() -> None:
    assert main(["greet", "dev"]) == 0
""",
            ),
            TemplateFile(path=".gitignore", content=_common_gitignore()),
            TemplateFile(path="LICENSE", content=_license_text()),
            TemplateFile(
                path="README.md",
                content="""# {project_name}

{description}

## Python Version

Requires Python >= {python_version}

## Run CLI

```bash
python -m {module_name} --help
python -m {module_name} greet team
```

## Tests

```bash
pytest
```

## Lint and Type Check

```bash
ruff check .
mypy src
```
""",
            ),
            TemplateFile(
                path="pyproject.toml",
                content="""[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{distribution_name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">={python_version}"
dependencies = []

[project.scripts]
{cli_command_name} = "{module_name}.cli:main"

[dependency-groups]
dev = [
  "pytest>=8.0",
  "ruff>=0.6",
  "mypy>=1.10",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py{python_tag}"

[tool.mypy]
python_version = "{python_version}"
warn_return_any = true
warn_unused_configs = true

[tool.setuptools.packages.find]
where = ["src"]
""",
            ),
        ],
    )


def _package_template() -> TemplateSpec:
    return TemplateSpec(
        id="python-package",
        name="Python Package",
        version="1.0.0",
        description="Reusable Python package template with src layout and tests.",
        supported_python_versions=["3.10", "3.11", "3.12", "3.13"],
        min_python="3.10",
        architecture="src-layout",
        style="library",
        included_tooling=["pytest", "ruff", "mypy"],
        runtime_dependencies=[],
        dev_dependencies=["pytest>=8.0", "ruff>=0.6", "mypy>=1.10"],
        structure_preview=[
            "src/{module_name}/__init__.py",
            "src/{module_name}/example.py",
            "tests/test_example.py",
            "pyproject.toml",
            "README.md",
            ".gitignore",
            "LICENSE",
        ],
        files=[
            TemplateFile(path="src/{module_name}/__init__.py", content="""from .example import meaning_of_life

__all__ = ["meaning_of_life"]
"""),
            TemplateFile(
                path="src/{module_name}/example.py",
                content="""from __future__ import annotations


def meaning_of_life() -> int:
    return 42
""",
            ),
            TemplateFile(
                path="tests/test_example.py",
                content="""from {module_name} import meaning_of_life


def test_meaning_of_life() -> None:
    assert meaning_of_life() == 42
""",
            ),
            TemplateFile(path=".gitignore", content=_common_gitignore()),
            TemplateFile(path="LICENSE", content=_license_text()),
            TemplateFile(
                path="README.md",
                content="""# {project_name}

{description}

## Python Version

Requires Python >= {python_version}

## Install Locally

```bash
pip install -e .
```

## Run Tests

```bash
pytest
```
""",
            ),
            TemplateFile(
                path="pyproject.toml",
                content="""[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{distribution_name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">={python_version}"
dependencies = []

[dependency-groups]
dev = [
  "pytest>=8.0",
  "ruff>=0.6",
  "mypy>=1.10",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py{python_tag}"

[tool.mypy]
python_version = "{python_version}"
warn_return_any = true
warn_unused_configs = true

[tool.setuptools.packages.find]
where = ["src"]
""",
            ),
        ],
    )


def register_builtin_templates(registry) -> None:
    registry.register(_script_template())
    registry.register(_cli_template())
    registry.register(_package_template())
