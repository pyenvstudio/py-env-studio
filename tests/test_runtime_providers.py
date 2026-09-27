from __future__ import annotations

import subprocess

import pytest
from unittest.mock import patch

import py_env_studio.core.runtime_providers as runtime_providers
from py_env_studio.core.runtime_providers import (
    PythonInstallManagerProvider,
    PythonRuntime,
)

# The real message the legacy 'Python Launcher' prints for every command.
LEGACY_LAUNCHER_OUTPUT = (
    "WARNING: The 'list' command is unavailable because this is the legacy py.exe command.\n"
    "If you have already installed the Python install manager, open Installed Apps and "
    "remove 'Python Launcher' to enable the new py.exe command."
)


def _completed(stdout: str = "[]", stderr: str = "", code: int = 0):
    return subprocess.CompletedProcess(["probe"], code, stdout, stderr)


@pytest.fixture(autouse=True)
def _clear_manager_probe_cache():
    """Probe answers and legacy paths are process state; tests must not inherit them."""
    runtime_providers._probe_python_install_manager.cache_clear()
    runtime_providers._LEGACY_LAUNCHER_PATHS.clear()
    yield
    runtime_providers._probe_python_install_manager.cache_clear()
    runtime_providers._LEGACY_LAUNCHER_PATHS.clear()


def _provider(mock_py=None):
    return PythonInstallManagerProvider(py_executable=mock_py or "py")


class TestPythonInstallManagerProviderAvailability:
    def test_find_py_when_py_not_on_path(self):
        with patch("shutil.which", return_value=None):
            provider = PythonInstallManagerProvider()
        assert provider._py is None
        assert provider.is_available() is False

    def test_find_py_accepts_py_exe_that_behaves_like_the_manager(self):
        def which(exe):
            return {"pymanager.exe": None, "py.exe": "C:\\\\py.exe", "py": "C:\\\\py"}.get(exe)

        with patch("shutil.which", side_effect=which), patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            return_value=_completed("[]"),
        ):
            provider = PythonInstallManagerProvider()
        assert provider._py == "C:\\\\py.exe"

    def test_find_py_ignores_legacy_py_exe(self):
        """A legacy launcher must not be used as the manager (it has no 'list')."""

        def which(exe):
            return {"pymanager.exe": None, "pymanager": None, "py.exe": "C:\\\\py.exe"}.get(exe)

        with patch("shutil.which", side_effect=which), patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            return_value=_completed("", LEGACY_LAUNCHER_OUTPUT, code=1),
        ) as run_mock:
            provider = PythonInstallManagerProvider()
        assert provider._py is None
        assert provider.is_available() is False
        assert run_mock.call_args.args[0][1] == "list"

    def test_find_py_falls_back_to_py_when_py_exe_is_legacy(self):
        def which(exe):
            return {
                "pymanager.exe": None,
                "pymanager": None,
                "py.exe": "C:\\\\py.exe",
                "py": "C:\\\\py",
            }.get(exe)

        def run(cmd, **kwargs):
            if cmd[0].endswith("py.exe"):
                return _completed("", LEGACY_LAUNCHER_OUTPUT, code=1)
            return _completed("[]")

        with patch("shutil.which", side_effect=which), patch(
            "py_env_studio.core.runtime_providers.subprocess.run", side_effect=run
        ):
            provider = PythonInstallManagerProvider()
        assert provider._py == "C:\\\\py"

    def test_find_py_prefers_pymanager_exe(self):
        def which(exe):
            return {"pymanager.exe": "C:\\\\pymanager.exe", "py.exe": "C:\\\\py.exe", "py": "C:\\\\py"}.get(exe)

        with patch("shutil.which", side_effect=which):
            provider = PythonInstallManagerProvider()
        assert provider._py == "C:\\\\pymanager.exe"

    def test_is_available_false_when_py_not_found(self):
        with patch("shutil.which", return_value=None):
            assert PythonInstallManagerProvider().is_available() is False


class TestInstalledRuntimeParsing:
    def test_installed_with_paths_parse(self):
        provider = _provider()
        stdout = "\n".join([
            "-3.14.7 * Python 3.14.7 (64-bit)",
            "-3.13.7 Python 3.13.7 (64-bit)",
            "-3.12.10 Python 3.12.10 (32-bit)",
        ])
        installed = provider._parse_installed_with_paths(stdout)
        assert len(installed) == 3
        versions = {item.version for item in installed}
        assert versions == {"3.14.7", "3.13.7", "3.12.10"}
        by_version = {item.version: item for item in installed}
        assert by_version["3.14.7"].display == "Python 3.14.7 (64-bit)"
        assert by_version["3.12.10"].architecture == "32-bit"

    def test_installed_plain_parse(self):
        provider = _provider()
        stdout = "\n".join([
            "-3.13.7 * Python 3.13.7 (64-bit)",
            "-3.12.10 Python 3.12.10 (32-bit)",
        ])
        installed = provider._parse_installed_plain(stdout)
        assert {item.version for item in installed} == {"3.13.7", "3.12.10"}

    def test_installed_line_with_devmeta(self):
        provider = _provider()
        parsed = provider._parse_installed_line("-3.13.7 Python 3.13.7 (64-bit) [Dev]")
        assert parsed is not None
        assert parsed.release_status == "Dev/Preview"

    def test_installed_line_with_arm(self):
        provider = _provider()
        parsed = provider._parse_installed_line("-3.12 Python 3.12.0 (ARM)")
        assert parsed is not None
        assert parsed.architecture == "ARM"

    def test_installed_line_with_implementation(self):
        provider = _provider()
        parsed = provider._parse_installed_line("-3.11 Python 3.11.0 pypy")
        assert parsed is not None
        assert parsed.implementation == "pypy"

    def test_non_matching_installed_line_returns_none(self):
        provider = _provider()
        assert provider._parse_installed_line("some random line") is None

    def test_installed_version_dedup(self):
        provider = _provider()
        stdout = "\n".join([
            "-3.12.10 Python 3.12.10 (32-bit)",
            "-3.12 Python 3.12.10 (32-bit)",
        ])
        installed = provider._parse_installed_plain(stdout)
        assert len(installed) == 2
        assert {item.version for item in installed} == {"3.12.10", "3.12"}


class TestAvailableRuntimeParsing:
    def test_available_parse_simple(self):
        provider = _provider()
        stdout = "\n".join([
            "3.11.11",
            "3.10.16",
            "3.9.21",
        ])
        available = provider._parse_available(stdout)
        assert len(available) == 3
        assert {item.version for item in available} == {"3.11.11", "3.10.16", "3.9.21"}
        assert all(item.installed is False for item in available)

    def test_available_parse_with_status(self):
        provider = _provider()
        stdout = "3.12.10 Support\n3.11.11 Security\n3.13.0 Latest"
        available = provider._parse_available(stdout)
        by_version = {item.version: item for item in available}
        assert by_version["3.12.10"].release_status == "Supported"
        assert by_version["3.11.11"].release_status == "Security"
        assert by_version["3.13.0"].release_status == "Latest"

    def test_available_parse_with_architecture(self):
        provider = _provider()
        stdout = "3.12.10 (64-bit)"
        available = provider._parse_available(stdout)
        assert available[0].architecture == "64-bit"
        assert available[0].display == "Python 3.12.10 (64-bit)"

    def test_available_parse_with_status_in_display(self):
        provider = _provider()
        stdout = "3.12.10 Support"
        available = provider._parse_available(stdout)
        assert available[0].display == "Python 3.12.10 [Supported]"

    def test_available_line_without_version_returns_none(self):
        provider = _provider()
        assert provider._parse_available_line("no version here") is None


class TestInstalledVersionFiltering:
    def test_filtering_removes_installed_from_available(self):
        installed = [
            PythonRuntime(version="3.14.7", display="Python 3.14.7", installed=True),
            PythonRuntime(version="3.13.7", display="Python 3.13.7", installed=True),
            PythonRuntime(version="3.12.10", display="Python 3.12.10", installed=True),
        ]
        available = [
            PythonRuntime(version="3.14.7", display="Python 3.14.7", installed=False),
            PythonRuntime(version="3.13.7", display="Python 3.13.7", installed=False),
            PythonRuntime(version="3.12.10", display="Python 3.12.10", installed=False),
            PythonRuntime(version="3.11.11", display="Python 3.11.11", installed=False),
            PythonRuntime(version="3.10.16", display="Python 3.10.16", installed=False),
        ]
        installed_versions = {item.version for item in installed}
        filtered = [item for item in available if item.version not in installed_versions]
        assert [item.version for item in filtered] == ["3.11.11", "3.10.16"]

    def test_filtering_keeps_only_uninstalled_versions(self):
        installed_versions = {"3.12.0"}
        available = [
            PythonRuntime(version="3.12.0", display="Python 3.12.0", installed=False),
            PythonRuntime(version="3.11.0", display="Python 3.11.0", installed=False),
        ]
        filtered = [item for item in available if item.version not in installed_versions]
        assert [item.version for item in filtered] == ["3.11.0"]


class TestInstallationCommandConstruction:
    def test_install_uses_normalized_version(self):
        provider = _provider(mock_py="py")

        recorded = []

        def fake_run(args, log_callback=None):
            recorded.append(args)
            return ""

        with patch.object(provider, "_run", fake_run):
            result = provider.install("3.11.11")
        assert result == "3.11.11"
        assert recorded[0] == ["install", "3.11.11"]

    def test_install_falls_back_to_major_minor_when_exact_fails(self):
        provider = _provider(mock_py="py")

        def fake_run(args, log_callback=None):
            if args == ["install", "3.12.99"]:
                raise RuntimeError("More Python versions are available for download.")
            if args == ["install", "3.12"]:
                return ""
            raise AssertionError(args)

        with patch.object(provider, "_run", fake_run):
            result = provider.install("3.12.99")
        assert result == "3.12"

    def test_install_rejects_invalid_version(self):
        provider = _provider()
        with pytest.raises(ValueError, match="Unsupported Python version identifier"):
            provider.install("not-a-version")

    def test_install_reports_already_installed(self):
        provider = _provider()

        def fake_run(args, log_callback=None):
            if args == ["install", "3.12.10"]:
                raise RuntimeError("Python 3.12.10 is already installed.")
            raise AssertionError(args)

        with patch.object(provider, "_run", fake_run):
            result = provider.install("3.12.10")
        assert result == "3.12.10"

    def test_install_propagates_real_error(self):
        provider = _provider()

        def fake_run(args, log_callback=None):
            raise RuntimeError("Access denied")

        with patch.object(provider, "_run", fake_run):
            with pytest.raises(RuntimeError, match="Access denied"):
                provider.install("3.12.10", log_callback=lambda m: None)


class TestMalformedCliOutput:
    def test_installed_empty_output(self):
        provider = _provider()
        assert provider._parse_installed_with_paths("") == []
        assert provider._parse_installed_plain("") == []

    def test_installed_with_no_version_lines(self):
        provider = _provider()
        stdout = "\n".join([
            "this launcher cannot list installed pythons",
            "please use py --version",
        ])
        assert provider._parse_installed_plain(stdout) == []

    def test_available_with_no_version_lines(self):
        provider = _provider()
        stdout = "\n".join([
            "no installable versions found",
            "",
        ])
        assert provider._parse_available(stdout) == []

    def test_available_with_commentary(self):
        provider = _provider()
        stdout = "\n".join([
            "Versions available for installation:",
            "3.12.10",
            "3.11.11",
            "",
        ])
        available = provider._parse_available(stdout)
        assert {item.version for item in available} == {"3.12.10", "3.11.11"}


class TestProviderUnavailableBehavior:
    def test_list_installed_returns_empty_when_unavailable(self):
        # Construction happens inside the patch: locating py.exe must not reach
        # the real machine.
        with patch("shutil.which", return_value=None):
            provider = PythonInstallManagerProvider(py_executable=None)
            assert provider.is_available() is False
            assert provider.list_installed() == []
            assert provider.list_available() == []

    def test_install_raises_when_unavailable(self):
        with patch("shutil.which", return_value=None):
            provider = PythonInstallManagerProvider(py_executable=None)
            with pytest.raises(RuntimeError, match="not available on this system"):
                provider.install("3.12")

    def test_fallback_available_returns_empty(self):
        provider = _provider()
        assert provider._fallback_available() == []


class TestLegacyLauncherDetection:
    """``py.exe`` is shared with the legacy launcher; the probe tells them apart."""

    def test_probe_accepts_manager_json_listing(self):
        with patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            return_value=_completed("[]"),
        ):
            assert runtime_providers._probe_python_install_manager("C:\\\\py.exe") is True

    def test_probe_rejects_legacy_launcher(self):
        with patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            return_value=_completed("", LEGACY_LAUNCHER_OUTPUT, code=1),
        ):
            assert runtime_providers._probe_python_install_manager("C:\\\\py.exe") is False

    def test_probe_rejects_non_json_output(self):
        with patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            return_value=_completed("Python 3.12.10"),
        ):
            assert runtime_providers._probe_python_install_manager("C:\\\\py.exe") is False

    def test_probe_rejects_unstartable_executable(self):
        with patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            side_effect=OSError("not a real executable"),
        ):
            assert runtime_providers._probe_python_install_manager("C:\\\\py.exe") is False

    def test_probe_runs_once_per_executable(self):
        with patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            return_value=_completed("[]"),
        ) as run_mock:
            runtime_providers._probe_python_install_manager("C:\\\\py.exe")
            runtime_providers._probe_python_install_manager("C:\\\\py.exe")
        assert run_mock.call_count == 1

    def test_find_legacy_python_launcher_reports_the_path(self):
        with patch("shutil.which", return_value="C:\\\\py.exe"), patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            return_value=_completed("", LEGACY_LAUNCHER_OUTPUT, code=1),
        ):
            assert runtime_providers.find_legacy_python_launcher() == "C:\\\\py.exe"

    def test_find_legacy_python_launcher_none_when_manager_owns_py(self):
        with patch("shutil.which", return_value="C:\\\\py.exe"), patch(
            "py_env_studio.core.runtime_providers.subprocess.run",
            return_value=_completed("[]"),
        ):
            assert runtime_providers.find_legacy_python_launcher() is None

    def test_find_legacy_python_launcher_none_without_py(self):
        with patch("shutil.which", return_value=None):
            assert runtime_providers.find_legacy_python_launcher() is None
