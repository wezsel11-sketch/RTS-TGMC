@echo off
rem One-command setup on Windows: fetches OpenRA and the TGMC art, builds the mod. Run mod\windows-prereqs.ps1 first if git, Python or ffmpeg are missing.
where py >nul 2>&1 && (py -3 -X utf8 "%~dp0mod\bootstrap.py" %* & exit /b)
python -X utf8 "%~dp0mod\bootstrap.py" %*
