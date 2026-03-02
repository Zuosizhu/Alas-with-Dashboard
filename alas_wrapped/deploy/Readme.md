# Deploy

This directory holds the Alas installer.

Install Alas by running `python -m deploy.installer` in Alas root folder.



# Launcher

Launcher `Alas.exe` is a `.bat` file converted to `.exe` file by [Bat To Exe Converter](https://f2ko.de/programme/bat-to-exe-converter/).

If you have warnings from your anti-virus software, replace `alas.exe` with `deploy/launcher/Alas.bat`.

In this monorepo, `deploy/launcher/Alas.bat` is a compatibility wrapper that delegates to repository-root `start_alas.bat` (canonical launcher).

