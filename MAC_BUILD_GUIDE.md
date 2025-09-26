# 🍎 Chucksteroids v5 - macOS Build Guide

## Overview
This guide explains how to create a macOS version of Chucksteroids v5. The Mac version will be packaged as a `.app` bundle that can be distributed and run on any macOS system.

## Prerequisites

### Option 1: Build on macOS (Recommended)
- **macOS 10.13 (High Sierra) or later**
- **Python 3.8+** installed
- **Xcode Command Line Tools** (for iconutil)
- **PyInstaller** and dependencies

### Option 2: Cross-Platform Building
- **Windows/Linux** with Docker or VM
- **GitHub Actions** for automated builds
- **GitLab CI/CD** for automated builds

## Quick Start

### 1. Prepare Your Environment
```bash
# Install Python dependencies
pip3 install pygame numpy pyinstaller requests psutil mido pillow

# Make build script executable (on macOS)
chmod +x build_chuckstaroidsv5_mac.sh
```

### 2. Convert Icon (Optional but Recommended)
```bash
# Convert Windows .ico to macOS .icns
python3 create_mac_icon.py xwing.ico xwing.icns
```

### 3. Build the App
```bash
# Run the build script
./build_chuckstaroidsv5_mac.sh

# Or build manually
python3 -m PyInstaller chuckstaroidsv5_mac.spec
```

### 4. Test the App
```bash
# Open the app
open dist/ChuckSTARoids_v5.app

# Or double-click in Finder
```

## File Structure

### New Files Created
- `chuckstaroidsv5_mac.spec` - PyInstaller spec for macOS
- `build_chuckstaroidsv5_mac.sh` - Build script for macOS
- `create_mac_icon.py` - Icon converter utility
- `MAC_BUILD_GUIDE.md` - This guide

### Output Files
- `dist/ChuckSTARoids_v5.app` - macOS application bundle
- `ChuckSTARoids_v5.app` - Copy in project root

## Key Differences from Windows Version

### 1. Application Bundle Structure
```
ChuckSTARoids_v5.app/
├── Contents/
│   ├── Info.plist          # App metadata
│   ├── MacOS/              # Executable
│   │   └── ChuckSTARoids_v5
│   └── Resources/          # Game assets
│       ├── *.gif
│       ├── *.txt
│       └── music.py
```

### 2. Icon Format
- **Windows**: `.ico` files
- **macOS**: `.icns` files (converted automatically)

### 3. Executable Format
- **Windows**: `.exe` files
- **macOS**: App bundles (`.app` folders)

## Build Process Details

### PyInstaller Configuration
The `chuckstaroidsv5_mac.spec` file includes:
- **BUNDLE** configuration for macOS app structure
- **Info.plist** with proper app metadata
- **Icon handling** for macOS
- **Asset embedding** for all game files

### App Bundle Metadata
```xml
CFBundleName: ChuckSTARoids v5
CFBundleIdentifier: com.chucksteroids.game
CFBundleVersion: 5.0.0
LSMinimumSystemVersion: 10.13.0
```

## Testing Checklist

### Basic Functionality
- [ ] App launches without errors
- [ ] All graphics display correctly
- [ ] Game controls work properly
- [ ] Music system functions
- [ ] Can be moved to different folders
- [ ] Can be renamed and still works

### macOS-Specific Testing
- [ ] App appears in Applications folder
- [ ] Icon displays correctly in Finder
- [ ] Right-click context menu works
- [ ] App can be dragged to Dock
- [ ] No console window appears (windowed mode)

### Security Testing
- [ ] App runs without security warnings (for development)
- [ ] Gatekeeper accepts the app (may need to right-click "Open")
- [ ] No antivirus false positives

## Distribution Options

### 1. Direct Distribution
- Share the `.app` bundle directly
- Users can drag to Applications folder
- No installation process needed

### 2. DMG Package (Advanced)
```bash
# Create DMG installer (requires additional tools)
hdiutil create -volname "ChuckSTARoids v5" -srcfolder ChuckSTARoids_v5.app -ov -format UDZO ChuckSTARoids_v5.dmg
```

### 3. App Store Distribution
- Requires Apple Developer account ($99/year)
- Code signing and notarization required
- App Store review process

## Troubleshooting

### Common Issues

#### 1. "App is damaged and can't be opened"
**Solution**: Right-click the app and select "Open", then click "Open" in the dialog.

#### 2. Missing dependencies
**Solution**: Ensure all Python packages are installed:
```bash
pip3 install -r requirements.txt
```

#### 3. Icon not displaying
**Solution**: Convert icon properly:
```bash
python3 create_mac_icon.py xwing.ico
```

#### 4. Build fails with PyInstaller errors
**Solution**: Check that all game assets are present and try:
```bash
python3 -m PyInstaller --clean chuckstaroidsv5_mac.spec
```

### Performance Considerations
- **App size**: ~40-50MB (includes Python runtime)
- **Startup time**: 2-5 seconds (PyInstaller overhead)
- **Memory usage**: Similar to Python version
- **Graphics performance**: Native pygame performance

## Advanced Configuration

### Code Signing (Optional)
For distribution outside the App Store:
```bash
# Sign the app (requires developer certificate)
codesign --force --deep --sign "Developer ID Application: Your Name" ChuckSTARoids_v5.app
```

### Notarization (Optional)
For distribution without security warnings:
```bash
# Notarize the app (requires Apple Developer account)
xcrun notarytool submit ChuckSTARoids_v5.app --keychain-profile "notarytool-profile" --wait
```

## Comparison with Windows Version

| Feature | Windows | macOS |
|---------|---------|-------|
| File Format | .exe | .app bundle |
| Icon Format | .ico | .icns |
| Distribution | Direct | Direct or DMG |
| Code Signing | Optional | Recommended |
| File Size | ~40MB | ~40MB |
| Dependencies | None | None |

## Next Steps

1. **Test thoroughly** on different macOS versions
2. **Create installer** (DMG) for easier distribution
3. **Set up automated builds** with GitHub Actions
4. **Consider App Store** distribution for wider reach

## Support

If you encounter issues:
1. Check this guide first
2. Verify all dependencies are installed
3. Test on a clean macOS system
4. Check PyInstaller documentation for advanced issues

---

**Happy gaming on macOS!** 🎮🍎
