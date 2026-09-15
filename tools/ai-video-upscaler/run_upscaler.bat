@echo off
setlocal
cd /d "%~dp0"
py -3 video_upscaler.py
if errorlevel 1 (
  echo.
  echo Python 3 was not found. Install Python 3.11 or newer, then run this file again.
  pause
)
