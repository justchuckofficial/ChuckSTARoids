@echo off
echo ============================================
echo Building Chucksteroids v4 Standalone Executable
echo ============================================
echo.

REM Check if chuckstaroidsv4.py exists
if not exist "chuckstaroidsv4.py" (
    echo ERROR: chuckstaroidsv4.py not found!
    echo Please make sure you're running this script from the correct directory.
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
python -m pip install pygame numpy pyinstaller --user

echo.
echo ============================================
echo Building executable...
echo ============================================

REM Build using the spec file
python -m PyInstaller chuckstaroidsv4.spec

REM Check if build was successful
if exist "dist\Chucksteroids_v4.exe" (
    echo.
    echo ============================================
    echo BUILD SUCCESSFUL!
    echo ============================================
    echo.
    echo The executable has been created at: dist\Chucksteroids_v4.exe
    echo.
    echo This executable:
    echo - Contains all game assets embedded within it
    echo - Can be renamed to anything you want
    echo - Can be moved to any folder and still work
    echo - Does not require Python or any other dependencies
    echo - Will display proper graphics on any Windows computer
    echo.
    
    REM Copy to a more convenient location with a better name
    copy "dist\Chucksteroids_v4.exe" "Chucksteroids_v4_Standalone.exe"
    echo Also copied to: Chucksteroids_v4_Standalone.exe
    echo.
    
    REM Show file size
    for %%I in ("dist\Chucksteroids_v4.exe") do echo File size: %%~zI bytes
    echo.
    
    echo ============================================
    echo TESTING INSTRUCTIONS
    echo ============================================
    echo.
    echo To test the executable:
    echo 1. Double-click Chucksteroids_v4_Standalone.exe to run
    echo 2. Try moving it to a different folder and running again
    echo 3. Try renaming it and running again
    echo 4. The game should display all graphics properly
    echo.
    
    echo Press any key to test the executable now...
    pause >nul
    
    echo Testing executable...
    start "" "Chucksteroids_v4_Standalone.exe"
    
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
    echo - PyInstaller not installed (run: pip install pyinstaller)
    echo.
)

echo.
echo Press any key to exit...
pause >nul
