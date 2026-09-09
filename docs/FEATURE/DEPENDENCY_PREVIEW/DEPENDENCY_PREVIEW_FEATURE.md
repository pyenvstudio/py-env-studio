# Dependency Impact Preview Feature

## Overview

The **Dependency Impact Preview** feature in the PES VS Code Extension allows developers to see exactly what will change before installing a package. It shows:

- 📥 **New packages** that will be added
- 📈 **Package upgrades** (with old → new version)
- 📤 **Package removals** (if any)
- ⚠️ **Potential breaking changes** that might affect your code

## User Guide

### Quick Start

1. Open the VS Code Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
2. Search for "**PES: Preview Package Install**"
3. Select your Python environment
4. Enter the package name (e.g., `pandas`, `django==4.2`, `numpy>=1.20`)
5. Review the dependency changes in the preview panel
6. If satisfied, proceed with installation

### Understanding the Preview

The preview shows you four types of changes:

#### 📥 New Packages
These packages will be added to your environment because they're dependencies of the package you're installing.

```
numpy          v1.26.4
scipy          v1.11.0
```

#### 📈 Upgrades
These packages are already installed but will be upgraded to new versions to satisfy dependencies.

```
python-dateutil  2.8.2 → 2.9.0
setuptools       65.5.0 → 69.0.0
```

#### 📤 Removals (if any)
If pip determines that some packages are no longer needed, they may be removed.

```
deprecated-lib   v1.0.0
```

#### ⚠️ Potential Breaking Changes
Some packages have known breaking changes that might affect your code:

```
numpy: May break code using deprecated numpy.dtype constructors
   Severity: high
```

## Examples

### Example 1: Installing pandas

**Command:** `pip install pandas`

**Preview:**
```
Installing: pandas
Environment: my-env

Summary:
+ 12 new packages
↑ 3 upgrades
- 0 removals

New Packages:
  📥 numpy         v1.26.4
  📥 scipy         v1.11.0
  📥 pytz          v2023.3
  ... (9 more)

Upgrades:
  📈 python-dateutil  2.8.2 → 2.9.0
  📈 setuptools      65.5.0 → 69.0.0
  📈 pip             24.0 → 24.1

Potential Breaking Changes:
  ⚠️ numpy: May break code using deprecated numpy.dtype constructors
     Severity: high
```

### Example 2: Upgrading Django

**Command:** `pip install "django>=5.0"`

**Preview:**
```
Installing: django>=5.0
Environment: my-env

Summary:
+ 0 new packages
↑ 1 upgrade
- 0 removals

Upgrades:
  📈 django  4.2.8 → 5.0.0

Potential Breaking Changes:
  ⚠️ django: ORM query API changes between major versions
     Severity: high
```

## Architecture

### Components

1. **Python Backend** (`dependency_preview.py`)
   - Analyzes package dependencies using pip metadata
   - Simulates installation using pip's `--dry-run` capability
   - Detects known breaking changes

2. **gRPC API** (`grpc_server.py`)
   - Exposes `PreviewInstall` RPC method
   - Communicates between TypeScript and Python

3. **TypeScript UI** (`extension.ts`, `previewInstall.ts`)
   - Provides command interface
   - Renders preview in VS Code webview
   - Handles user interactions

### Data Flow

```
User Input (Command Palette)
    ↓
previewInstallCommand() (TypeScript)
    ↓
pesClient.previewInstall() (gRPC)
    ↓
PESServicer.PreviewInstall() (Python gRPC)
    ↓
dependency_preview.preview_install() (Python)
    ↓
simulate_dependency_resolution() (Python)
    ↓
PreviewResult (structured data)
    ↓
showPreviewWebview() (renders in VS Code)
```

## Implementation Details

### Dependency Analysis Algorithm

1. **Get Current State**: Fetch all currently installed packages in the environment
2. **Simulate Installation**: Use `pip install --dry-run <package>` to see what pip would do
3. **Parse Output**: Extract added/upgraded/removed packages from pip's output
4. **Detect Breaking Changes**: Check against known breaking changes database
5. **Format Results**: Return structured PreviewResult with all details

### Dry-Run Simulation

The feature uses pip's `--dry-run` flag (available in pip >= 24.0) to simulate the installation without actually modifying the environment. This is safe and fast.

If `--dry-run` is not available, the feature falls back to:
- Fetching package metadata from PyPI
- Building a dependency tree
- Comparing with current environment

### Breaking Changes Detection

The system maintains a database of known breaking changes:

```python
breaking_changes_db = {
    "numpy": {
        "reason": "May break code using deprecated numpy.dtype constructors",
        "severity": "high"
    },
    "pandas": {
        "reason": "Index behavior changes in newer versions",
        "severity": "medium"
    },
    ...
}
```

This can be extended with:
- External databases (e.g., Advisory Database)
- Machine learning-based change detection
- Community reports

## API Reference

### gRPC Interface

#### PreviewInstall RPC

**Request:**
```protobuf
message PreviewInstallRequest {
  string environment_name = 1;
  string package_spec = 2;
}
```

**Response:**
```protobuf
message PreviewInstallResponse {
  repeated PackageChange additions = 1;
  repeated PackageChange upgrades = 2;
  repeated PackageChange removals = 3;
  repeated BreakingChange potential_breaks = 4;
  InstallSummary summary = 5;
}

message PackageChange {
  string name = 1;
  string version = 2;
  optional string old_version = 3;
}

message BreakingChange {
  string package = 1;
  string reason = 2;
  string severity = 3;  // high, medium, low
}
```

## Configuration

### Environment Variables

- `ENABLE_DEPENDENCY_PREVIEW=1` - Enable/disable preview feature (default: enabled)
- `PIP_PREVIEW_TIMEOUT=60` - Timeout for pip dry-run in seconds (default: 60)

### Settings (VS Code)

Add to your `.vscode/settings.json`:

```json
{
  "pes.preview.checkBreakingChanges": true,
  "pes.preview.showSeverity": ["high", "medium"],
  "pes.preview.timeout": 30
}
```

## Limitations

1. **pip Dry-Run**: Requires pip >= 24.0 for optimal performance
2. **Breaking Changes**: Limited to packages with known issues
3. **Large Dependency Trees**: May take 30+ seconds for complex packages
4. **Network**: Requires PyPI access for metadata lookup

## Future Enhancements

- [ ] Integration with vulnerability databases (CVE, Advisory DB)
- [ ] Machine learning-based incompatibility detection
- [ ] Integration with `pipdeptree` for detailed dependency graphs
- [ ] Commit-based change tracking
- [ ] IDE inspection of affected code
- [ ] Automatic conflict resolution suggestions

## Troubleshooting

### Preview takes too long

- Increase timeout in settings
- Check your network connection
- Try with a simpler package first

### "Package not found" error

- Verify the package name is correct
- Check PyPI availability
- Make sure pip is up to date (`pip install --upgrade pip`)

### Preview shows empty results

- The package may have no dependencies
- Try installing a popular package like `requests` or `pandas` as a test

## See Also

- [Dependency Impact Preview PR](https://github.com/your-repo/pulls)
- [pip Documentation](https://pip.pypa.io/)
- [PyPI Package Index](https://pypi.org/)
