# Chucksteroids - Standalone Executable

## Overview
This is a standalone executable version of Chucksteroids that includes all necessary assets and dependencies. The executable can be renamed, moved to any location, and run without requiring Python or any additional installations.

## Files Included
- `Chucksteroids_Standalone.exe` - The main executable (33MB)
- `Chucksteroids.exe` - Alternative name for the executable

## Features
- **Fully Self-Contained**: No external dependencies required
- **Portable**: Can be renamed and moved anywhere
- **All Assets Included**: All images, sounds, and data files are embedded
- **Windows Compatible**: Built for Windows 64-bit systems

## How to Use
1. **Run the Game**: Double-click `Chucksteroids_Standalone.exe` to start the game
2. **Rename**: You can rename the executable to anything you want (e.g., `MyAsteroidsGame.exe`)
3. **Move**: Copy the executable to any folder and it will still work
4. **Share**: Send the executable to others - they don't need Python installed

## Controls
- **Arrow Keys**: Move ship
- **Spacebar**: Shoot
- **A/D**: Strafe left/right
- **S**: Reverse thrust
- **Q/E**: Rotate left/right
- **W**: Thrust forward
- **R**: Restart (when dead)
- **ESC**: Quit

## Technical Details
- **Built with**: PyInstaller 6.15.0
- **Python Version**: 3.13.6
- **Dependencies**: pygame, numpy, mido (all included)
- **Architecture**: Windows 64-bit
- **Size**: ~33MB (includes all assets and Python runtime)

## Troubleshooting
- If the game doesn't start, make sure you have Windows 10 or later
- If you get antivirus warnings, this is normal for PyInstaller executables - add an exception
- The game requires a graphics card that supports OpenGL

## Assets Included
All game assets are embedded in the executable:
- Ship sprites (xwing.gif)
- UFO sprites (tie.gif, tieb.gif, tiei.gif, tiea.gif, tiefo.gif)
- Bullet sprites (shot.gif, tieshot.gif)
- Asteroid sprites (roid.gif)
- Effect sprites (fire.gif, spinout.gif, stard.gif)
- Icon (xwing.ico)
- All text files and data

## Building from Source
If you want to rebuild the executable:
1. Install PyInstaller: `pip install pyinstaller`
2. Run: `python -m PyInstaller --onefile --windowed --name="Chucksteroids" --icon="xwing.ico" --add-data="*.gif;." --add-data="*.jpg;." --add-data="*.ico;." --add-data="*.txt;." --add-data="*.md;." chuckstaroidsv2.py`

## Version Information
- Game Version: Chucksteroids v2
- Build Date: $(Get-Date)
- Executable Size: 33,915,044 bytes


















