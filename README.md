# PikPak Text Importer

[![Release](https://img.shields.io/github/v/release/ProfessorZhi/pikpak-text-importer)](https://github.com/ProfessorZhi/pikpak-text-importer/releases)
[![License](https://img.shields.io/github/license/ProfessorZhi/pikpak-text-importer)](https://github.com/ProfessorZhi/pikpak-text-importer/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)

Desktop app for extracting PikPak share links from plain text and importing them into your own drive.

This repository contains only the application code, packaging scripts, and neutral example data. It does not include personal configs, cached sessions, or private test content.

## Features

- Desktop GUI built with PySide6
- Account validation before import actions are enabled
- Layer-by-layer PikPak folder browsing
- Share link extraction from plain text
- Batch import with progress updates
- Fast-start Windows build using `PyInstaller --onedir`
- Windows installer build with Inno Setup

## Quick Start

Run the desktop client:

```powershell
python -m pip install -r .\requirements.txt
python .\scripts\run_gui.py
```

Or double-click:

- `StartPikPakImporter.bat`

## Usage

1. Open the desktop client.
2. Enter your PikPak account and password.
3. Choose where the local session file should be stored.
4. Click `保存配置`.
5. Click `校验账号`.
6. After validation succeeds, browse to the target parent folder.
7. Paste text that contains one or more `https://mypikpak.com/s/...` links.
8. Preview or start the import.

## Project Structure

```text
pikpakdownloader/
  app/
    pikpak_importer/
      __init__.py
      __main__.py
      gui.py
      importer.py
      paths.py
  assets/
    pikpak_importer_icon.svg
  config/
    account.example.json
  packaging/
    build_release.py
    PikPakTextImporter.iss
  scripts/
    run_cli.py
    run_gui.py
  tests/
    test_pikpak_text_importer.py
  .gitignore
  BuildRelease.bat
  LICENSE
  README.md
  requirements.txt
  StartPikPakImporter.bat
  启动PikPak批量转存界面.bat
```

## Local Config

These files are local-only and are intentionally excluded from Git:

- `config/account.json`
- `.pikpak_session.json`
- `.codex/pikpak/session.json`

Example config only:

- `config/account.example.json`

Packaged builds store real config data in the user profile directory:

- `%LOCALAPPDATA%\PikPakTextImporter\config\account.json`
- `%LOCALAPPDATA%\PikPakTextImporter\session\session.json`

## Requirements

- `pikpakapi`
- `PySide6`

Install dependencies:

```powershell
python -m pip install -r .\requirements.txt
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Build

To improve startup speed, the project uses `PyInstaller --onedir` instead of `onefile`.

Build locally:

```powershell
python .\packaging\build_release.py
```

Or double-click:

- `BuildRelease.bat`

Build outputs:

- `dist\app\PikPakTextImporter\`
  Fast local app folder
- `dist\installer\PikPakTextImporter-Setup.exe`
  Windows installer

## Release

Latest public release:

- [v1.0.0](https://github.com/ProfessorZhi/pikpak-text-importer/releases/tag/v1.0.0)
