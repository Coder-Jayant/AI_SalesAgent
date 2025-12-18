@echo off
REM Uninstall Action Plan Service from Windows

echo ========================================
echo Action Plan Service Uninstaller
echo ========================================
echo.

set SERVICE_NAME=ActionPlanService

REM Check if NSSM is available
where nssm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: NSSM not found in PATH
    echo.
    echo Please download NSSM from: https://nssm.cc/download
    echo Extract nssm.exe to this directory or add to your PATH
    echo.
    pause
    exit /b 1
)

REM Check if service exists
sc query %SERVICE_NAME% >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Service '%SERVICE_NAME%' does not exist.
    echo Nothing to uninstall.
    echo.
    pause
    exit /b 0
)

echo Stopping service if running...
nssm stop %SERVICE_NAME%
timeout /t 2 /nobreak >nul

echo Removing service...
nssm remove %SERVICE_NAME% confirm

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Service uninstalled successfully!
    echo ========================================
) else (
    echo.
    echo ERROR: Failed to uninstall service
)

echo.
pause
