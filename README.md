# Toga Hello World

A minimal, cross-platform GUI application written in Python using [BeeWare/Toga](https://beeware.org/).

[![Release](https://github.com/Foadsf/helloworld-toga/actions/workflows/release.yml/badge.svg)](https://github.com/Foadsf/helloworld-toga/actions/workflows/release.yml)

## Project Structure


```

toga-hello/
├── .github/
│   └── workflows/
│       └── release.yml      # CI/CD for cross-platform builds
├── icons/
│   └── README.md            # Icon requirements
├── src/
│   └── helloworld/
│       ├── **init**.py      # Package marker
│       ├── **main**.py      # Execution entry point
│       └── app.py           # Main application logic
├── tests/
│   └── **init**.py
├── https://www.google.com/search?q=LICENSE
├── pyproject.toml           # Briefcase configuration
└── README.md

```

## Prerequisites (Local Development)

### Linux (Ubuntu 24.04+ / Linux Mint 22)

This project relies on GTK bindings. **Note:** Ubuntu 24.04 and Linux Mint 22 have moved to `girepository-2.0`. You must install the correct development headers for local testing:

```bash
sudo apt update
sudo apt install -y git python3-dev python3-venv \
    libgirepository-2.0-dev \
    libcairo2-dev gir1.2-gtk-3.0 pkg-config

```

> **Legacy Systems:** If you are on Ubuntu 22.04 or older, use `libgirepository1.0-dev` instead.

### macOS / Windows

See [BeeWare documentation](https://docs.beeware.org/) for platform-specific requirements.

## Installation

1. **Create and activate a virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

```


2. **Install Briefcase (The packaging tool):**
```bash
pip install briefcase

```


3. **Install the project in editable mode:**
This ensures `briefcase` can find your code logic in `src/`.
```bash
pip install -e .

```



## Usage

### Run with Briefcase (Recommended)

This emulates the full packaging environment.

```bash
briefcase dev

```

### Run directly (Quick Testing)

Since this is a standard Python package, you can run it as a module:

```bash
python -m helloworld

```

## Packaging (Local Builds)

To bundle this application for distribution locally, use `briefcase`.

```bash
# Linux AppImage (Portable single-file executable)
# Note: Uses manylinux_2_34 (AlmaLinux 9) Docker image
briefcase create linux appimage
briefcase build linux appimage
briefcase package linux appimage

# Windows (Must run on Windows)
briefcase create windows app
briefcase build windows app
briefcase package windows app

# macOS (Must run on macOS)
briefcase create macOS app
briefcase build macOS app
# For ad-hoc signing (runs locally only):
briefcase package macOS app --adhoc-sign
# For distribution (requires Developer ID):
# briefcase package macOS app --identity "Developer ID Application: ..."

# Android (Requires Android SDK - Briefcase handles this)
briefcase create android
briefcase build android
briefcase package android

# iOS (Requires macOS + Xcode)
briefcase create iOS
briefcase build iOS
briefcase package iOS

```

## Automated Releases (CI/CD)

This repository includes a GitHub Action (`.github/workflows/release.yml`) that automatically builds binaries whenever you push a version tag.

1. **Commit your changes:**
```bash
git add .
git commit -m "Your commit message"
git push origin main

```


2. **Trigger a release:**
```bash
git tag -f v0.1.0
git push -f origin v0.1.0

```



The workflow builds and uploads the following artifacts:

* **Linux:** `.AppImage` (portable)
* **Windows:** `.msi` installer
* **macOS:** `.dmg` disk image (Signed if secrets are present, otherwise ad-hoc)
* **Android:** Debug `.apk`
* **iOS:** `.ipa` (if signed) or Xcode archive `.tar.gz` (unsigned)

## ⚠️ Important: Linux AppImage Configuration

Creating a portable AppImage for GTK apps requires a specific balance between the Build OS version and the Python Library versions.

The working configuration in `pyproject.toml` uses **manylinux_2_34** (AlmaLinux 9) to provide modern GLib (2.68+), while strictly pinning `pygobject` to avoid the bleeding-edge `girepository-2.0` requirement.

**Do not change these versions unless you verify compatibility:**

```toml
[tool.briefcase.app.helloworld.linux]
requires = [
    "toga-gtk>=0.4.0,<0.4.5",       # Stable Toga series
    "pygobject>=3.46.0,<3.48.0",    # Pinned to support GLib 2.68 but avoid girepository-2.0
]

[tool.briefcase.app.helloworld.linux.appimage]
manylinux = "manylinux_2_34"        # AlmaLinux 9 build environment
system_requires = [
    "fuse-libs",                    # Red Hat package name (not libfuse2)
    "cairo-devel",
    "cairo-gobject-devel",
    "gobject-introspection-devel",
]

```

## Code Signing & Secrets

To enable production-grade signing in GitHub Actions, configure the following secrets in **Settings > Secrets and variables > Actions**:

| Secret Name | Description |
| --- | --- |
| `APPLE_DEVELOPER_ID_CERTIFICATE` | Base64-encoded `.p12` certificate file. |
| `APPLE_DEVELOPER_ID_CERTIFICATE_PASSWORD` | Password for the `.p12` file. |
| `APPLE_DEVELOPER_ID` | Your Apple Developer ID (e.g., `Developer ID Application: Name (ID)`). |
| `KEYCHAIN_PASSWORD` | A random string used to secure the temporary CI keychain. |
| `APPLE_TEAM_ID` | Your 10-character Apple Team ID (required for iOS). |

*Without these secrets, macOS builds will be ad-hoc signed (requiring manual Gatekeeper override) and iOS builds will produce an unsigned Xcode archive.*

## License

MIT License - see [LICENSE](LICENSE) for details.
