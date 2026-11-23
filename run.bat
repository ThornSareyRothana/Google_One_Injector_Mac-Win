@echo off
setlocal enabledelayedexpansion
title Google One Subscription Injector
cd /d "%~dp0"

echo ======================================================================
echo             Google One Subscription Injector (Final)
echo ======================================================================
echo.

:: 1. Check Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [*] Python not detected in system PATH.
    echo [*] Searching common installation directories...
    
    set "PY_EXE="
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    if not defined PY_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    if not defined PY_EXE if exist "%ProgramFiles%\Python312\python.exe" set "PY_EXE=%ProgramFiles%\Python312\python.exe"
    if not defined PY_EXE if exist "%ProgramFiles%\Python311\python.exe" set "PY_EXE=%ProgramFiles%\Python311\python.exe"

    if defined PY_EXE (
        echo [+] Found Python at: "!PY_EXE!"
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;!PATH!"
    ) else (
        echo [!] Python is not installed.
        echo [*] Attempting automated installation via winget...
        winget install Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
        if %ERRORLEVEL% NEQ 0 (
            echo [x] Automated install failed. Please install Python from https://www.python.org/downloads/
            echo [x] Be sure to check the box "Add Python to PATH" during installation.
            pause
            exit /b 1
        )
        echo [+] Python installed. Refreshing environment...
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;!PATH!"
    )
)

:: 2. Check and Install Pip Dependencies (frida 17.9.1, frida-tools 14.8.1)
echo [*] Checking dependencies (frida, frida-tools)...
python -c "import frida; assert frida.__version__ == '17.9.1'" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing / aligning dependencies to match frida-server 17.9.1...
    python -m pip install --quiet --upgrade pip
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Retrying pip install...
        python -m pip install frida==17.9.1 frida-tools==14.8.1
    )
)
echo [+] Environment dependencies verified.
echo.

:: 3. Launch the injector
python main.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Injector exited with error code: %ERRORLEVEL%
    pause
)
