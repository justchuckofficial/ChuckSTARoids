#!/bin/bash

echo "============================================"
echo "Building ChuckSTARoids v5 for macOS"
echo "============================================"
echo

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "ERROR: This script must be run on macOS!"
    echo "For cross-platform building, see the documentation."
    exit 1
fi

# Check if chuckstaroidsv5.py exists
if [ ! -f "chuckstaroidsv5.py" ]; then
    echo "ERROR: chuckstaroidsv5.py not found!"
    echo "Please make sure you're running this script from the correct directory."
    exit 1
fi

# Check if music.py exists
if [ ! -f "music.py" ]; then
    echo "ERROR: music.py not found!"
    echo "Please make sure music.py is in the same directory."
    exit 1
fi

# Check if xwing.icns exists, if not try to create it from xwing.ico
if [ ! -f "xwing.icns" ]; then
    if [ -f "xwing.ico" ]; then
        echo "Converting xwing.ico to xwing.icns..."
        # Try to convert using sips (built into macOS)
        sips -s format icns xwing.ico --out xwing.icns
        if [ $? -eq 0 ]; then
            echo "Icon converted successfully!"
        else
            echo "WARNING: Could not convert icon. The app will build without a custom icon."
            echo "To create a proper .icns file, use Icon Composer or online converters."
        fi
    else
        echo "WARNING: No icon file found. The app will build without a custom icon."
    fi
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build
rm -rf dist
rm -rf temp_build

# Install required packages
echo "Installing required packages..."
pip3 install pygame numpy pyinstaller requests psutil mido

echo
echo "============================================"
echo "Building macOS app bundle..."
echo "============================================"

# Build using the Mac spec file
python3 -m PyInstaller chuckstaroidsv5_mac.spec

# Check if build was successful
if [ -d "dist/ChuckSTARoids_v5.app" ]; then
    echo
    echo "============================================"
    echo "BUILD SUCCESSFUL!"
    echo "============================================"
    echo
    echo "The macOS app has been created at: dist/ChuckSTARoids_v5.app"
    echo
    echo "This app bundle:"
    echo "- Contains all game assets embedded within it"
    echo "- Can be moved to any folder and still work"
    echo "- Does not require Python or any other dependencies"
    echo "- Will display proper graphics on any macOS computer"
    echo "- Includes enhanced music system"
    echo "- Has proper macOS app bundle structure"
    echo
    
    # Copy to a more convenient location
    cp -r "dist/ChuckSTARoids_v5.app" "ChuckSTARoids_v5.app"
    echo "Also copied to: ChuckSTARoids_v5.app"
    echo
    
    # Show app size
    APP_SIZE=$(du -sh "dist/ChuckSTARoids_v5.app" | cut -f1)
    echo "App bundle size: $APP_SIZE"
    echo
    
    echo "============================================"
    echo "TESTING INSTRUCTIONS"
    echo "============================================"
    echo
    echo "To test the app:"
    echo "1. Double-click ChuckSTARoids_v5.app to run"
    echo "2. Try moving it to a different folder and running again"
    echo "3. Try renaming it and running again"
    echo "4. The game should display all graphics properly"
    echo "5. Enhanced music system should work"
    echo
    echo "If you get a security warning:"
    echo "1. Right-click the app and select 'Open'"
    echo "2. Or go to System Preferences > Security & Privacy"
    echo "3. Click 'Open Anyway' for the blocked app"
    echo
    
    echo "Press Enter to test the app now..."
    read
    
    echo "Testing app..."
    open "ChuckSTARoids_v5.app"
    
else
    echo
    echo "============================================"
    echo "BUILD FAILED!"
    echo "============================================"
    echo
    echo "The app bundle was not created successfully."
    echo "Check the output above for error messages."
    echo
    echo "Common issues:"
    echo "- Missing dependencies (run: pip3 install -r requirements.txt)"
    echo "- Missing image files (ensure all .gif files are present)"
    echo "- Missing music.py file"
    echo "- PyInstaller not installed (run: pip3 install pyinstaller)"
    echo "- Missing xwing.icns file (try converting from xwing.ico)"
    echo
fi

echo
echo "Press Enter to exit..."
read
