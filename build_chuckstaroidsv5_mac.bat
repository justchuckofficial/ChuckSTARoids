@echo off
echo ============================================
echo ChuckSTARoids v5 - macOS Build Helper
echo ============================================
echo.
echo This script helps prepare files for macOS building.
echo Note: You need a Mac to actually build the macOS version.
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

echo Preparing files for macOS build...
echo.

REM Try to convert icon if possible
if exist "xwing.ico" (
    echo Converting icon for macOS...
    python create_mac_icon.py xwing.ico xwing.icns
    if exist "xwing.icns" (
        echo Icon converted successfully!
    ) else (
        echo Icon conversion failed, but build will continue.
        echo You may need to create xwing.icns manually on macOS.
    )
) else (
    echo WARNING: xwing.ico not found. You'll need to create xwing.icns on macOS.
)

echo.
echo ============================================
echo FILES READY FOR MACOS BUILD
echo ============================================
echo.
echo Created/verified files:
echo - chuckstaroidsv5_mac.spec (PyInstaller config)
echo - build_chuckstaroidsv5_mac.sh (build script)
echo - create_mac_icon.py (icon converter)
echo - MAC_BUILD_GUIDE.md (detailed guide)
echo.

if exist "xwing.icns" (
    echo - xwing.icns (macOS icon) ✓
) else (
    echo - xwing.icns (macOS icon) ✗ - Create this on macOS
)

echo.
echo ============================================
echo NEXT STEPS
echo ============================================
echo.
echo To build the macOS version:
echo.
echo 1. Copy these files to a Mac:
echo    - chuckstaroidsv5.py
echo    - music.py
echo    - All .gif and .jpg files
echo    - chuckstaroidsv5_mac.spec
echo    - build_chuckstaroidsv5_mac.sh
echo    - xwing.icns (if created)
echo.
echo 2. On the Mac, run:
echo    chmod +x build_chuckstaroidsv5_mac.sh
echo    ./build_chuckstaroidsv5_mac.sh
echo.
echo 3. The app will be created as:
echo    dist/ChuckSTARoids_v5.app
echo.
echo For detailed instructions, see MAC_BUILD_GUIDE.md
echo.

echo Press any key to exit...
pause >nul
