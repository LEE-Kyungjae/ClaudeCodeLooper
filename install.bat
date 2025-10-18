@echo off
REM ClaudeCodeLooper Installation Script for Windows

echo ================================================
echo   ClaudeCodeLooper Installation
echo ================================================
echo.

REM Check Python version
echo Checking Python version...
python --version > temp_version.txt 2>&1
set /p PYTHON_VERSION=<temp_version.txt
del temp_version.txt

echo %PYTHON_VERSION% | findstr /R "Python 3\.1[1-9]" > nul
if errorlevel 1 (
    echo Error: Python 3.11 or higher is required
    echo Current version: %PYTHON_VERSION%
    echo Please upgrade Python and try again
    pause
    exit /b 1
)

echo Python version OK: %PYTHON_VERSION%
echo.

REM Installation options
echo Installation Options:
echo   1^) User installation ^(recommended^)
echo   2^) Development installation
echo.
set /p INSTALL_TYPE="Select option [1-2]: "

if "%INSTALL_TYPE%"=="1" (
    echo.
    echo Installing ClaudeCodeLooper ^(user mode^)...
    pip install --user -e .
) else if "%INSTALL_TYPE%"=="2" (
    echo.
    echo Installing ClaudeCodeLooper ^(development mode^)...
    pip install -e .[dev]
) else (
    echo Invalid option. Exiting.
    pause
    exit /b 1
)

echo.
echo Installation complete!
echo.

REM Verify installation
echo Verifying installation...
where claude-looper > nul 2>&1
if errorlevel 1 (
    echo Warning: claude-looper command not found in PATH
    echo You may need to add Python Scripts directory to your PATH
    echo Typical location: C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python3XX\Scripts
) else (
    echo claude-looper command is available
    claude-looper --version
)

echo.
echo ================================================
echo   Quick Start
echo ================================================
echo.
echo To start using ClaudeCodeLooper:
echo.
echo   # Start monitoring
echo   claude-looper start --daemon
echo.
echo   # Check status
echo   claude-looper status
echo.
echo   # View logs
echo   claude-looper logs
echo.
echo   # Stop monitoring
echo   claude-looper stop --all
echo.
echo Or use Claude Code slash commands:
echo   /cl:on, /cl:status, /cl:logs, /cl:off
echo.
echo ================================================
echo For more information, see README.md
echo ================================================
echo.
pause
