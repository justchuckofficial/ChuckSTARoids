@echo off
echo Building Chucksteroids executable...
echo.

REM Clean previous builds
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM Install PyInstaller if not already installed
pip install pyinstaller

REM Build the executable
pyinstaller chucksteroids.spec

echo.
echo Build complete! Check the 'dist' folder for Chucksteroids.exe
echo.
pause


















