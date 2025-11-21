@echo off
setlocal enabledelayedexpansion

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

color 0C
title MewChat Uninstaller

echo ============================================
echo    MewChat Uninstallation Script
echo ============================================
echo.
echo WARNING: This will remove MewChat from your system
echo.
set /p confirm="Are you sure you want to uninstall? (Y/N): "
if /I not "!confirm!"=="Y" (
    echo.
    echo Uninstallation cancelled.
    echo.
    set /p dummy="Press Enter to exit..."
    exit /b 0
)
echo.

set "FILES_FOUND=0"
set "FILES_REMOVED=0"
set "ERRORS=0"

echo [Step 1] Scanning system PATH for FudChat files...
echo.

for %%i in ("%PATH:;=";"%") do (
    set "dir=%%~i"
    set "dir=!dir:"=!"
    
    if exist "!dir!" (
        if exist "!dir!\mewchat.py" (
            set /a FILES_FOUND+=1
            echo [FOUND] fudmewf.py in: !dir!
            del /F /Q "!dir!\mewchat.py" >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Removed mewchat.py
                set /a FILES_REMOVED+=1
            ) else (
                echo [ERROR] Failed to remove mewchat.py
                set /a ERRORS+=1
            )
            echo.
        )
        
        if exist "!dir!\mewchat.bat" (
            set /a FILES_FOUND+=1
            echo [FOUND] mewchat.bat in: !dir!
            del /F /Q "!dir!\mewchat.bat" >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Removed mewchat.bat
                set /a FILES_REMOVED+=1
            ) else (
                echo [ERROR] Failed to remove mewchat.bat
                set /a ERRORS+=1
            )
            echo.
        )
    )
)

echo ============================================
echo    Uninstallation Summary
echo ============================================
echo.

if !FILES_FOUND! equ 0 (
    echo [INFO] No MewChat files found in system PATH
    echo MewChat may not be installed or was already removed
) else (
    echo Files found: !FILES_FOUND!
    echo Files removed: !FILES_REMOVED!
    
    if !ERRORS! gtr 0 (
        echo Errors encountered: !ERRORS!
        echo.
        echo [WARNING] Some files could not be removed.
    ) else (
        echo.
        echo [✓] All MewChat files removed successfully!
        echo [✓] mewchat.py removed from PATH
        echo [✓] mewchat.bat launcher removed
        echo [✓] 'mewchat' command is no longer available
    )
)

echo.
echo ============================================
echo    Uninstallation Complete
echo ============================================
echo.

if !ERRORS! equ 0 (
    echo MewChat has been completely removed from your system.
    echo Python and packages remain untouched.
) else (
    echo Some errors occurred during uninstallation.
)

echo.
set /p dummy="Press Enter to exit..."
exit /b 0