@echo off
REM Install Autopilot Service as Windows Service using NSSM
REM
REM Prerequisites:
REM   - Download NSSM from: https://nssm.cc/download
REM   - Extract nssm.exe to this directory or add to PATH

echo ========================================
echo Autopilot Service Installer
echo ========================================
echo.

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

REM Get current directory
set SERVICE_DIR=%~dp0
REM Use venv Python from SalesAgent directory (absolute path)
set PYTHON_EXE=C:\Users\JayantVerma\AA\SSH_AGENT\SOLO_AGENTS\SalesAgent\venv\Scripts\python.exe
set SERVICE_NAME=AutopilotService

echo Service Directory: %SERVICE_DIR%
echo Python Executable: %PYTHON_EXE%
echo Service Name: %SERVICE_NAME%
echo.

REM Check if venv Python exists
if not exist "%PYTHON_EXE%" (
    echo ERROR: Virtual environment Python not found at: %PYTHON_EXE%
    echo Please ensure the venv is set up correctly
    echo.
    pause
    exit /b 1
)

REM Check if service already exists
sc query %SERVICE_NAME% >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Service '%SERVICE_NAME%' already exists!
    echo Please uninstall it first using uninstall_autopilot_service.bat
    echo.
    pause
    exit /b 1
)

echo Installing service...
echo.

REM Install service
nssm install %SERVICE_NAME% "%PYTHON_EXE%" "%SERVICE_DIR%autopilot_service.py"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install service
    pause
    exit /b 1
)

REM Configure service
echo Configuring service...

REM Set working directory
nssm set %SERVICE_NAME% AppDirectory "%SERVICE_DIR%"

REM Set startup mode to automatic
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START

REM Set description
nssm set %SERVICE_NAME% Description "Autopilot Email Processing Service - Continuously monitors and processes emails based on autopilot rules"

REM Set display name
nssm set %SERVICE_NAME% DisplayName "Autopilot Email Processing Service"

REM Configure logging
nssm set %SERVICE_NAME% AppStdout "%SERVICE_DIR%autopilot_service_stdout.log"
nssm set %SERVICE_NAME% AppStderr "%SERVICE_DIR%autopilot_service_stderr.log"

REM Set restart policy (restart on failure)
nssm set %SERVICE_NAME% AppExit Default Restart
nssm set %SERVICE_NAME% AppRestartDelay 5000

echo.
echo ========================================
echo Service installed successfully!
echo ========================================
echo.
echo Service Name: %SERVICE_NAME%
echo Status: Stopped (not started yet)
echo.
echo To start the service:
echo   net start %SERVICE_NAME%
echo   OR
echo   nssm start %SERVICE_NAME%
echo.
echo To stop the service:
echo   net stop %SERVICE_NAME%
echo   OR
echo   nssm stop %SERVICE_NAME%
echo.
echo To view service status:
echo   nssm status %SERVICE_NAME%
echo   OR
echo   sc query %SERVICE_NAME%
echo.
echo Logs will be written to:
echo   - %SERVICE_DIR%autopilot_service.log (main log)
echo   - %SERVICE_DIR%autopilot_service_stdout.log (stdout)
echo   - %SERVICE_DIR%autopilot_service_stderr.log (stderr)
echo.
pause
