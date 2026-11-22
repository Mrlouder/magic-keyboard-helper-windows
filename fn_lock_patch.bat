@echo off
rem Magic Keyboard Fn + Lock key patch. Parameter: -Restore = restore the original
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0fn_lock_patch.ps1" %*
