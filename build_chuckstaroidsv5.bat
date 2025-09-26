@echo off
echo ============================================
echo Building ChuckSTARoids v5 Standalone Executable
echo ============================================
echo.

REM Check if chuckstaroidsv5.py exists
if not exist "chuckstaroidsv5.py" (
    echo ERROR: chuckstaroidsv5.py not found!
    echo Please make sure you're running this script from the correct directory.
    pause
    exit /b 1
)

REM Check if music.py exists
if not exist "music.py" (
    echo ERROR: music.py not found!
    echo Please make sure music.py is in the same directory.
    pause
    exit /b 1
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "temp_build" rmdir /s /q "temp_build"

REM Install required packages
echo Installing required packages...
python -m pip install pygame numpy pyinstaller requests psutil --user

echo.
echo ============================================
echo Building executable...
echo ============================================

REM Build using the spec file
python -m PyInstaller chuckstaroidsv5.spec

REM Check if build was successful
if exist "dist\ChuckSTARoids_v5.exe" (
    echo.
    echo ============================================
    echo BUILD SUCCESSFUL!
    echo ============================================
    echo.
    echo The executable has been created at: dist\ChuckSTARoids_v5.exe
    echo.
    echo This executable:
    echo - Contains all game assets embedded within it
    echo - Can be renamed to anything you want
    echo - Can be moved to any folder and still work
    echo - Does not require Python or any other dependencies
    echo - Will display proper graphics on any Windows computer
    echo - Includes enhanced music system
    echo.
    
    REM Copy to a more convenient location with a better name
    copy "dist\ChuckSTARoids_v5.exe" "ChuckSTARoids_v5.exe"
    echo Also copied to: ChuckSTARoids_v5.exe
    echo.
    
    REM Show file size
    for %%I in ("dist\ChuckSTARoids_v5.exe") do echo File size: %%~zI bytes
    echo.
    
    echo ============================================
    echo TESTING INSTRUCTIONS
    echo ============================================
    echo.
    echo To test the executable:
    echo 1. Double-click ChuckSTARoids_v5.exe to run
    echo 2. Try moving it to a different folder and running again
    echo 3. Try renaming it and running again
    echo 4. The game should display all graphics properly
    echo 5. Enhanced music system should work
    echo.
    
    echo Press any key to test the executable now...
    pause >nul
    
    echo Testing executable...
    start "" "ChuckSTARoids_v5.exe"
    
) else (
    echo.
    echo ============================================
    echo BUILD FAILED!
    echo ============================================
    echo.
    echo The executable was not created successfully.
    echo Check the output above for error messages.
    echo.
    echo Common issues:
    echo - Missing dependencies (run: pip install -r requirements.txt)
    echo - Missing image files (ensure all .gif files are present)
    echo - Missing music.py file
    echo - PyInstaller not installed (run: pip install pyinstaller)
    echo.
)

echo.
echo Press any key to exit...
pause >nul

