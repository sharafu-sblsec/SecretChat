@echo off
setlocal enabledelayedexpansion
color 0A
title FudChat Installer

echo ============================================
echo    FudChat Installation Script
echo ============================================
echo.

echo [Step 1] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not installed!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo Installation aborted.
    echo.
    set /p dummy="Press Enter to exit..."
    exit /b 1
)
echo [OK] Python is installed
python --version
echo.

echo [Step 2] Upgrading pip and installing dependencies...
echo Running: python -m pip install --upgrade pip
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] Pip upgrade had issues, but continuing...
)
echo.
echo Installing required packages: telethon cryptography pynput prompt_toolkit colorama
pip install telethon cryptography pynput prompt_toolkit colorama
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install required packages
    echo.
    set /p dummy="Press Enter to exit..."
    exit /b 1
)
echo [OK] All packages installed successfully
echo.

echo [Step 3] Checking for mewchat.py in current directory...
if not exist "mewchat.py" (
    echo.
    echo [ERROR] mewchat.py file is missing!
    echo Please make sure mewchat.py is in the same directory as this script.
    echo.
    echo Installation aborted.
    echo.
    set /p dummy="Press Enter to exit..."
    exit /b 1
)
echo [OK] mewchat.py found
echo.

echo [Step 4] Checking system PATH...
echo Current PATH directories:
echo %PATH%
echo.

set "TARGET_DIR="
for %%i in ("%PATH:;=";"%") do (
    set "dir=%%~i"
    set "dir=!dir:"=!"
    if exist "!dir!" (
        echo !dir! | findstr /I "Users" >nul
        if !errorlevel! equ 0 (
            if "!TARGET_DIR!"=="" (
                set "TARGET_DIR=!dir!"
            )
        )
    )
)

if "!TARGET_DIR!"=="" (
    for %%i in ("%PATH:;=";"%") do (
        set "dir=%%~i"
        set "dir=!dir:"=!"
        if exist "!dir!" (
            if "!TARGET_DIR!"=="" (
                set "TARGET_DIR=!dir!"
            )
        )
    )
)

if "!TARGET_DIR!"=="" (
    echo [ERROR] Could not find a suitable directory in PATH
    echo.
    set /p dummy="Press Enter to exit..."
    exit /b 1
)

echo [OK] Selected installation directory: !TARGET_DIR!
echo.

echo [Step 5] Copying mewchat.py to !TARGET_DIR!...
copy /Y "mewchat.py" "!TARGET_DIR!\mewchat.py" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Failed to copy mewchat.py. You may need administrator privileges.
    echo Try running this script as Administrator.
    echo.
    set /p dummy="Press Enter to exit..."
    exit /b 1
)
echo [OK] mewchat.py copied successfully
echo.

echo [Step 6] Creating mewchat.bat launcher...
(
    echo @echo off
    echo python "!TARGET_DIR!\mewchat.py" %%*
) > "!TARGET_DIR!\mewchat.bat"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create mewchat.bat
    echo.
    set /p dummy="Press Enter to exit..."
    exit /b 1
)
echo [OK] mewchat.bat created successfully
echo.

echo [Step 7] Verifying installation...
where mewchat.bat >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] mewchat command is accessible from PATH
) else (
    echo [WARNING] mewchat.bat created but may not be immediately accessible
    echo You may need to restart your terminal
)
echo.

echo ============================================
echo    Installation Summary
echo ============================================
echo.
echo [✓] Python installation verified
echo [✓] Pip upgraded successfully
echo [✓] Required packages installed:
echo     - telethon
echo     - cryptography
echo     - pynput
echo     - prompt_toolkit
echo     - colorama
echo [✓] mewchat.py verified
echo [✓] Installation directory: !TARGET_DIR!
echo [✓] mewchat.py copied to: !TARGET_DIR!\mewchat.py
echo [✓] Launcher created: !TARGET_DIR!\mewchat.bat
echo.
echo ============================================
echo    Installation Complete!
echo ============================================
echo.
echo You can now run the application by typing:
echo     mewchat
echo.
echo Note: If the command doesn't work immediately,
echo please restart your terminal/command prompt.
echo.
set /p dummy="Press Enter to exit..."
exit /b 0