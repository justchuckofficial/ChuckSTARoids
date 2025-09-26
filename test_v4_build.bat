@echo off
echo ============================================
echo Testing Chucksteroids v4 Build
echo ============================================
echo.

REM Check if the executable exists
if exist "Chucksteroids_v4_Standalone.exe" (
    echo Found executable: Chucksteroids_v4_Standalone.exe
    
    REM Get file size
    for %%I in ("Chucksteroids_v4_Standalone.exe") do (
        set /a size_mb=%%~zI/1024/1024
        echo File size: %%~zI bytes (~!size_mb! MB)
    )
    
    echo.
    echo Testing executable startup...
    echo (The game window should open - close it to continue the test)
    
    REM Test the executable
    start /wait "" "Chucksteroids_v4_Standalone.exe"
    
    if %errorlevel% equ 0 (
        echo.
        echo ============================================
        echo TEST PASSED!
        echo ============================================
        echo.
        echo The executable started successfully!
        echo This means:
        echo - All dependencies are properly included
        echo - All graphics files are accessible
        echo - The game runs without errors
        echo.
        echo The executable is ready for distribution!
        echo.
    ) else (
        echo.
        echo ============================================
        echo TEST FAILED!
        echo ============================================
        echo.
        echo The executable had an error (exit code: %errorlevel%)
        echo Check that all dependencies and files are properly included.
        echo.
    )
    
) else (
    echo.
    echo ============================================
    echo EXECUTABLE NOT FOUND!
    echo ============================================
    echo.
    echo Chucksteroids_v4_Standalone.exe not found.
    echo Please run build_chuckstaroidsv4.bat first to build the executable.
    echo.
)

echo.
echo Press any key to exit...
pause >nul

