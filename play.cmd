@echo off
rem Start the game on Windows: play.cmd, or play.cmd landing-zone to go straight into a map.
where py >nul 2>&1 && (py -3 -X utf8 "%~dp0mod\play.py" %* & exit /b)
python -X utf8 "%~dp0mod\play.py" %*
