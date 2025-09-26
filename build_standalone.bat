@echo off
echo Building Chucksteroids standalone executable...
echo.

REM Clean previous builds
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM Install PyInstaller if not already installed
pip install pyinstaller

REM Create a temporary directory for the build
mkdir temp_build

REM Copy all necessary files to temp directory
copy "chuckstaroidsv2.py" "temp_build\"
copy "*.gif" "temp_build\"
copy "*.jpg" "temp_build\"
copy "*.ico" "temp_build\"
copy "*.txt" "temp_build\"
copy "*.md" "temp_build\"

REM Change to temp directory
cd temp_build

REM Build with PyInstaller using onefile option
pyinstaller --onefile --windowed --name="Chucksteroids" --icon="xwing.ico" --add-data="*.gif;." --add-data="*.jpg;." --add-data="*.ico;." --add-data="*.txt;." --add-data="*.md;." chuckstaroidsv2.py

REM Copy the executable back to the main directory
copy "dist\Chucksteroids.exe" "..\Chucksteroids_Standalone.exe"

REM Clean up temp directory
cd ..
rmdir /s /q "temp_build"

echo.
echo Build complete! Chucksteroids_Standalone.exe is ready!
echo This executable can be renamed and moved anywhere.
echo.
pause


















