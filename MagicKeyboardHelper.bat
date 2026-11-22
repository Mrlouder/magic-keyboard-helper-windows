@echo off
rem Starts Magic Keyboard Helper with AutoHotkey v2.
rem 1. AutoHotkey64.exe in this folder (portable, no install needed), or
rem 2. an installed AutoHotkey v2 (default install folder), or
rem 3. the program Windows opens .ahk files with.
set "SCRIPT=%~dp0magic_keyboard_media.ahk"

if exist "%~dp0AutoHotkey64.exe" (
    start "" "%~dp0AutoHotkey64.exe" "%SCRIPT%" %*
    goto :eof
)
if exist "%ProgramFiles%\AutoHotkey\v2\AutoHotkey64.exe" (
    start "" "%ProgramFiles%\AutoHotkey\v2\AutoHotkey64.exe" "%SCRIPT%" %*
    goto :eof
)
if exist "%LOCALAPPDATA%\Programs\AutoHotkey\v2\AutoHotkey64.exe" (
    start "" "%LOCALAPPDATA%\Programs\AutoHotkey\v2\AutoHotkey64.exe" "%SCRIPT%" %*
    goto :eof
)
assoc .ahk >nul 2>&1
if not errorlevel 1 (
    start "" "%SCRIPT%" %*
    goto :eof
)
echo AutoHotkey v2 was not found.
echo Install it from https://www.autohotkey.com/ or copy AutoHotkey64.exe into this folder.
pause
