@echo off
REM Start Action Plan Service manually (foreground mode for testing)

echo ========================================
echo Action Plan Service - Manual Start
echo ========================================
echo.
echo Running service in foreground mode...
echo Press Ctrl+C to stop
echo.
echo ========================================
echo.

REM Use system Python
python action_plan_service.py

echo.
echo Service stopped.
pause
