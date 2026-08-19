@echo off
REM ============================================================
REM  Mandala Stakeholder Dashboard - one-click launcher
REM  Double-click this file to start the dashboard. It will
REM  open in your web browser. Close this black window to stop.
REM ============================================================
cd /d "%~dp0"
echo Starting the Mandala Stakeholder Dashboard...
echo A browser tab will open shortly. Keep this window open while you use it.
echo To stop the dashboard, close this window.
echo.
".venv\Scripts\streamlit.exe" run app.py
pause
