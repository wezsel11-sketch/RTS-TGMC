@echo off
title TGMC Marines vs Xenos
cd /d "%~dp0game"
if not exist Support mkdir Support
OpenRA.exe Game.Mod=tgmc %*
if %errorlevel% neq 0 goto crashdialog
exit /b

:crashdialog
echo ----------------------------------------
echo The game exited with an error.
echo   * Log files are in %cd%\Support\Logs
echo ----------------------------------------
pause
