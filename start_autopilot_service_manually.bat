@echo off
REM Manually start Autopilot Service for testing
REM This runs the service in the foreground (not as Windows service)

echo ========================================
echo Starting Autopilot Service Manually
echo ========================================
echo.
echo Press Ctrl+C to stop
echo.

REM Navigate to script directory
cd /d %~dp0

REM Use system Python
python autopilot_service.py
