"""Tests for dependency preview feature."""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from py_env_studio.core import dependency_preview


class TestDependencyChange(unittest.TestCase):
    """Test DependencyChange class."""
    
    def test_creation(self):
        """Test creating a dependency change."""
        change = dependency_preview.DependencyChange("numpy", "1.26.4")
        self.assertEqual(change.name, "numpy")
        self.assertEqual(change.version, "1.26.4")
        self.assertIsNone(change.old_version)
    
    def test_with_old_version(self):
        """Test creating a change with old version."""
        change = dependency_preview.DependencyChange("pandas", "2.0.0", "1.5.0")
        self.assertEqual(change.name, "pandas")
        self.assertEqual(change.version, "2.0.0")
        self.assertEqual(change.old_version, "1.5.0")
    
    def test_to_dict(self):
        """Test converting to dict."""
        change = dependency_preview.DependencyChange("django", "4.2", "4.0")
        result = change.to_dict()
        self.assertEqual(result["name"], "django")
        self.assertEqual(result["version"], "4.2")
        self.assertEqual(result["old_version"], "4.0")


class TestBreakingChange(unittest.TestCase):
    """Test BreakingChange class."""
    
    def test_creation(self):
        """Test creating a breaking change."""
        change = dependency_preview.BreakingChange(
            "numpy",
            "May break deprecated numpy.dtype",
            "high"
        )
        self.assertEqual(change.package, "numpy")
        self.assertEqual(change.reason, "May break deprecated numpy.dtype")
        self.assertEqual(change.severity, "high")
    
    def test_to_dict(self):
        """Test converting to dict."""
        change = dependency_preview.BreakingChange(
            "pandas",
            "Index behavior changed",
            "medium"
        )
        result = change.to_dict()
        self.assertEqual(result["package"], "pandas")
        self.assertEqual(result["reason"], "Index behavior changed")
        self.assertEqual(result["severity"], "medium")


class TestPreviewResult(unittest.TestCase):
    """Test PreviewResult class."""
    
    def test_creation(self):
        """Test creating a preview result."""
        result = dependency_preview.PreviewResult()
        self.assertEqual(len(result.additions), 0)
        self.assertEqual(len(result.upgrades), 0)
        self.assertEqual(len(result.removals), 0)
        self.assertEqual(len(result.breaking_changes), 0)
    
    def test_to_dict_empty(self):
        """Test converting empty result to dict."""
        result = dependency_preview.PreviewResult()
        data = result.to_dict()
        
        self.assertEqual(len(data["additions"]), 0)
        self.assertEqual(data["summary"]["will_add"], 0)
        self.assertEqual(data["summary"]["will_upgrade"], 0)
        self.assertEqual(data["summary"]["will_remove"], 0)
    
    def test_to_dict_with_changes(self):
        """Test converting result with changes to dict."""
        result = dependency_preview.PreviewResult()
        result.additions.append(dependency_preview.DependencyChange("numpy", "1.26.4"))
        result.upgrades.append(dependency_preview.DependencyChange("pandas", "2.0.0", "1.5.0"))
        
        data = result.to_dict()
        self.assertEqual(data["summary"]["will_add"], 1)
        self.assertEqual(data["summary"]["will_upgrade"], 1)
        self.assertEqual(len(data["additions"]), 1)
        self.assertEqual(len(data["upgrades"]), 1)


class TestParsePackageSpec(unittest.TestCase):
    """Test parse_package_spec function."""
    
    def test_simple_name(self):
        """Test parsing simple package name."""
        name, version = dependency_preview.parse_package_spec("numpy")
        self.assertEqual(name, "numpy")
        self.assertIsNone(version)
    
    def test_exact_version(self):
        """Test parsing exact version."""
        name, version = dependency_preview.parse_package_spec("django==4.2")
        self.assertEqual(name, "django")
        self.assertEqual(version, "==4.2")
    
    def test_minimum_version(self):
        """Test parsing minimum version."""
        name, version = dependency_preview.parse_package_spec("requests>=2.25")
        self.assertEqual(name, "requests")
        self.assertEqual(version, ">=2.25")
    
    def test_complex_version(self):
        """Test parsing complex version."""
        name, version = dependency_preview.parse_package_spec("numpy>=1.20,<2.0")
        self.assertEqual(name, "numpy")
        self.assertEqual(version, ">=1.20,<2.0")
    
    def test_case_insensitive(self):
        """Test that package names are lowercase."""
        name, version = dependency_preview.parse_package_spec("NumPy")
        self.assertEqual(name, "numpy")


class TestExtractNameAndVersion(unittest.TestCase):
    """Test _extract_name_and_version function."""
    
    def test_equals_format(self):
        """Test extracting from == format."""
        name, version = dependency_preview._extract_name_and_version("numpy==1.26.4")
        self.assertEqual(name, "numpy")
        self.assertEqual(version, "1.26.4")
    
    def test_dash_format(self):
        """Test extracting from dash format."""
        name, version = dependency_preview._extract_name_and_version("numpy-1.26.4")
        self.assertEqual(name, "numpy")
        self.assertEqual(version, "1.26.4")
    
    def test_parentheses_format(self):
        """Test extracting from parentheses format."""
        name, version = dependency_preview._extract_name_and_version("numpy (1.26.4)")
        self.assertEqual(name, "numpy")
        self.assertEqual(version, "1.26.4")


class TestCheckBreakingChanges(unittest.TestCase):
    """Test _check_breaking_changes function."""
    
    def test_numpy_breaking_changes(self):
        """Test numpy breaking changes detection."""
        result = dependency_preview.PreviewResult()
        dependency_preview._check_breaking_changes("numpy", result)
        
        self.assertEqual(len(result.breaking_changes), 1)
        self.assertEqual(result.breaking_changes[0].package, "numpy")
        self.assertEqual(result.breaking_changes[0].severity, "high")
    
    def test_unknown_package(self):
        """Test unknown package doesn't add breaking changes."""
        result = dependency_preview.PreviewResult()
        dependency_preview._check_breaking_changes("some-obscure-package", result)
        
        self.assertEqual(len(result.breaking_changes), 0)


class TestParsePipDryRunOutput(unittest.TestCase):
    """Test _parse_pip_dry_run_output function."""
    
    def test_parse_simple_output(self):
        """Test parsing simple pip output."""
        output = """
Collecting pandas==2.0.0
Collecting numpy==1.26.4 (from pandas)
        """
        installed = {"pandas": "1.5.0"}
        result = dependency_preview.PreviewResult()
        
        result = dependency_preview._parse_pip_dry_run_output(
            output, "pandas", installed, result
        )
        
        # Should have detected an upgrade for pandas
        self.assertGreater(len(result.upgrades) + len(result.additions), 0)


    def test_parse_package_spec_known_and_unknown(self):
        """parse_package_spec resolves name + version for known and unknown packages."""
        self.assertEqual(dependency_preview.parse_package_spec("requests==2.31.0"), ("requests", "==2.31.0"))
        self.assertEqual(dependency_preview.parse_package_spec("django>=4.2"), ("django", ">=4.2"))
        self.assertEqual(dependency_preview.parse_package_spec("pytest"), ("pytest", None))
        self.assertEqual(dependency_preview.parse_package_spec("unknown-pkg-x"), ("unknown-pkg-x", None))
        self.assertEqual(dependency_preview.parse_package_spec("NumPy>=1.20"), ("numpy", ">=1.20"))

    def test_parse_pip_dry_run_output_removes_upgrades_and_breaking(self):
        """Upgrades and additions are classified correctly for the parsed output;
        'Would uninstall' removal lines are NOT parsed by the current implementation
        (documented GAP, not a false 'covered')."""
        output = """
Collecting pandas==2.0.0
Would uninstall pandas
Collecting numpy==1.26.4 (from pandas)
"""
        installed = {"pandas": "1.5.0", "numpy": "1.24.0"}
        result = dependency_preview.PreviewResult()
        result = dependency_preview._parse_pip_dry_run_output(output, "pandas", installed, result)

        # pandas (1.5.0 -> 2.0.0) and numpy (1.24.0 -> 1.26.4) are both installed
        # packages whose collected version differs -> both are upgrades, not additions.
        self.assertEqual(len(result.additions), 0, "both packages are already installed -> no additions")
        self.assertEqual(len(result.removals), 0, "Would-Uninstall lines are not parsed by this implementation (GAP)")
        self.assertGreater(len(result.upgrades), 0, "installed packages with a different collected version are upgrades")
        self.assertTrue(
            any(c.name == "pandas" for c in result.upgrades),
            "pandas 1.5.0 -> 2.0.0 should be an upgrade"
        )
        self.assertTrue(
            any(c.name == "numpy" for c in result.upgrades),
            "numpy 1.24.0 -> 1.26.4 should be an upgrade"
        )

        breaking = dependency_preview.PreviewResult()
        dependency_preview._check_breaking_changes("django", breaking)
        self.assertEqual(len(breaking.breaking_changes), 1)
        self.assertEqual(breaking.breaking_changes[0].package, "django")
        self.assertEqual(breaking.breaking_changes[0].severity, "high")

        unknown = dependency_preview.PreviewResult()
        dependency_preview._check_breaking_changes("unknown-pkg-x", unknown)
        self.assertEqual(len(unknown.breaking_changes), 0)


class TestGetInstalledPackages(unittest.TestCase):
    """Test get_installed_packages function."""
    
    @patch('py_env_studio.core.dependency_preview.list_packages')
    def test_get_installed_packages(self, mock_list):
        """Test getting installed packages."""
        mock_list.return_value = [
            ("numpy", "1.26.4"),
            ("pandas", "2.0.0"),
            ("requests", "2.31.0")
        ]
        
        packages = dependency_preview.get_installed_packages("test-env")
        
        self.assertEqual(packages["numpy"], "1.26.4")
        self.assertEqual(packages["pandas"], "2.0.0")
        self.assertEqual(packages["requests"], "2.31.0")
    
    @patch('py_env_studio.core.dependency_preview.list_packages')
    def test_case_insensitive(self, mock_list):
        """Test that package names are case insensitive."""
        mock_list.return_value = [
            ("NumPy", "1.26.4"),
        ]
        
        packages = dependency_preview.get_installed_packages("test-env")
        
        self.assertIn("numpy", packages)
        self.assertEqual(packages["numpy"], "1.26.4")


# Integration tests (require actual environment)
@unittest.skip("Requires actual environment")
class TestIntegration(unittest.TestCase):
    """Integration tests with real environment."""
    
    def test_preview_install_requests(self):
        """Test previewing requests installation."""
        # This test requires a real environment
        result = dependency_preview.preview_install("test-env", "requests")
        
        self.assertIsNotNone(result)
        self.assertTrue(len(result.additions) >= 0)


if __name__ == '__main__':
    unittest.main()
