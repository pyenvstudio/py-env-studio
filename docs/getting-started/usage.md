# Usage Manual: Py Env Studio

This manual provides a comprehensive guide for using the Py Env Studio (PES) application, a Python environment and package management tool with an intuitive graphical interface.

---

## Main Screen Overview

The main screen consists:
- **Side Bar** - Customize UI of PES tool 
- **Environment Tab** - Manage Python virtual environments
- **Package Tab** - Handle package installation and management

---
## Side Bar - UI Customization
### Appearance Mode
Customize the theme mode with Light mode, Dark mode, or System mode.

### UI Scaling
As per your screen size and your needs you can modify the font and view size. 

## Environment Tab

### Creating a New Environment

To create a new Python virtual environment:

1. Navigate to the **Environment Tab**
2. Locate the **Create Environment** section
3. **New Environment Name:** Enter a name for your environment in the input field
4. **Python Path:** Optionally select a Python installation from the dropdown (automatically detects all available Python installations on your system) or manually specify a Python path
5. **Upgrade pip during creation:** Check this option to automatically upgrade pip to the latest version when creating the environment
6. Click the **Create Environment** button to initialize the new environment

---

### Configuring and Activating an Environment

**Configuration and Activation**

1. **Open at:** Enter the directory path where you want to activate the environment, or click **Browse** to select a folder from the file manager
2. **Open with:** Select a tool to open alongside the activated environment (e.g., VSCode). You can add new tools to this list
3. Now you can Actovates the environment using  **Activate Environment** button or using described other options below.
4. **Shortcuts for Activating Environemnts using the Available Environments Table**
Double-click on any of these columns row to activate the environment:
**ENVIRONMENT | PYTHON VERSION | SIZE | LAST SCANNED**


---

### Searching for Environments

Use the **Search Environment** input field to filter and quickly locate specific environments from your list by typing the environment name or related keywords.

---

### Managing Environments - Available Environments Table

All created environments are displayed in an interactive table with the following columns and actions:

| Column | Description | Action |
|--------|-------------|--------|
| **ENVIRONMENT** | Environment name | Double-click to activate the environment |
| **PYTHON VERSION** | Python version used | Double-click to activate the environment |
| **RECENT LOCATION** | Last used directory path | Click to copy the path to clipboard |
| **SIZE** | Environment folder size | Double-click to activate the environment |
| **RENAME** | Rename option | Click to rename the environment |
| **DELETE** | Delete option | Click to delete the environment |
| **LAST SCANNED** | Last vulnerability scan date | Double-click to activate the environment |
| **MORE** | Additional actions | Click to access vulnerability report and scan now options |

---

## Package Tab

The Package Tab provides comprehensive package management capabilities for selected environments.

**📌 Important Note:**
><span style="color: red;">All package operations require selecting an environment from the environment table first.<span>

### Installing Packages

**Single Package Installation:**

1. Go to **Packages Tab → Install Package Section**
2. Enter the package name in the Package name field
3. Click **Install Package** to install the package

**Multiple Packages Installation (Requirements File):**

1. Go to **Packages Tab → Install Package Section**
2. Click **Install Requirements**
3. Browse and select a text file containing package names (e.g., `requirements.txt`)
4. The application reads the file and installs all listed packages automatically

---

### Exporting Packages

To export installed packages to a requirements file:

1. Go to **Packages Tab → Export Packages**
2. Provide a filename in text format (e.g., `requirements.txt`).
3. The application automatically exports all installed packages of selected environments.

---

### Managing Installed Packages

To view and manage packages in an environment:

1. Click the **Manage Packages** button
2. A table view displays all installed packages with options to:
   - **Delete** individual packages
   - **Update** packages to their latest version

---

## Menu Options

**📌 Important Note:**
><span style="color: red;">All menu operations require selecting an environment from the environment table first.<span>

### File Menu

The File menu provides package installation and export operations:

- **Install Packages** - Install a single package by name
- **Install Requirements** - Install multiple packages from a requirements file
- **Export Packages** - Export installed packages to a requirements file


---

### View Menu

**Refresh Environments:**
1. Go to **Menu → View → Refresh Environments**
2. This refreshes the environment list and updates status if any changes were made outside the PES tool

---

### Tools Menu

The Tools menu provides advanced features for environment analysis and maintenance. 

#### Scan Now

Generates a comprehensive dependency and vulnerability report for the selected environment's packages.

1. Go to **Menu → Tools → Scan Now**
2. The tool analyzes dependencies and security vulnerabilities

---

#### Vulnerability Report

Displays detailed vulnerability and dependency information for packages:

1. Go to **Menu → Tools → Vulnerability Report**
2. Select a package from the list
3. View information across three tabs:
   - **Dependencies** - Shows the dependency tree and relationships
   - **Basic Details** - Displays package metadata and basic information
   - **Scan Details** - *(enterprise level external tool integration option [Compliance/ Training/ Incident Response]Currently not implemented)*
5. An interactive graph visualizes dependencies and vulnerabilities

---

#### Check for Package Updates

Identifies outdated packages and enables batch updating:

1. Go to **Menu → Tools → Check for Package Updates**
2. A popup table displays:
   - Package name
   - Current version
   - New version available
3. Select packages to update:
   - **Ctrl + Click** to select multiple specific packages
   - **Ctrl + A** to select all packages
4. Click **Update Selected** to upgrade the chosen packages to their latest versions.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl + Click** | Select multiple packages in the update table |
| **Ctrl + A** | Select all packages in the update table |
| **Double-click** (table columns) | Activate environment or copy path (context-dependent) |

---

## Quick Reference Workflow Guide

### Common Workflows

**Setting Up a New Project Environment:**
1. Create Environment (Environment Tab)
2. Install Requirements (File → Install Requirements)
3. Scan Now (Tools → Scan Now)

**Daily Development Work:**
1. Search Environment (locate your project)
2. Activate Environment (double-click or use Activate section)
3. Manage Packages as needed

**Maintenance and Updates:**
1. Refresh Environments (View → Refresh Environments)
2. Check for Package Updates (Tools → Check for Package Updates)
3. Review Vulnerability Report (Tools → Vulnerability Report)

**Sharing Environment Configuration:**
1. Select environment
2. Export Packages (File → Export Packages)
3. Share the generated requirements.txt file

---

## Summary

Py Env Studio streamlines Python environment management by consolidating creation, activation, package management, and security scanning into a unified interface. The combination of table-based environment selection, menu-driven operations, and interactive reporting makes it efficient for both beginners and advanced Python developers to maintain clean, secure, and well-documented development environments.