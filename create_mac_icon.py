#!/usr/bin/env python3
"""
Icon converter for creating macOS .icns files from Windows .ico files.
This script helps prepare the icon for Mac builds.
"""

import os
import sys
from PIL import Image
import subprocess

def convert_ico_to_icns(ico_path, icns_path=None):
    """
    Convert Windows .ico file to macOS .icns file.
    
    Args:
        ico_path (str): Path to the input .ico file
        icns_path (str): Path for the output .icns file (optional)
    
    Returns:
        bool: True if conversion successful, False otherwise
    """
    if not os.path.exists(ico_path):
        print(f"ERROR: Input file '{ico_path}' not found!")
        return False
    
    if icns_path is None:
        icns_path = ico_path.replace('.ico', '.icns')
    
    try:
        # Open the ICO file
        with Image.open(ico_path) as img:
            print(f"Opened ICO file: {ico_path}")
            print(f"Image size: {img.size}")
            print(f"Image mode: {img.mode}")
            
            # Convert to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Create different sizes for the ICNS file
            sizes = [16, 32, 64, 128, 256, 512, 1024]
            icons = []
            
            for size in sizes:
                # Resize image to the required size
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                icons.append(resized)
                print(f"Created {size}x{size} icon")
            
            # Save as PNG first (temporary)
            temp_png = "temp_icon.png"
            icons[-1].save(temp_png)  # Save the largest size as PNG
            
            # Try to use iconutil (macOS built-in tool) if available
            if sys.platform == "darwin":
                try:
                    # Create iconset directory
                    iconset_dir = "temp_icon.iconset"
                    os.makedirs(iconset_dir, exist_ok=True)
                    
                    # Save different sizes with proper naming
                    size_mapping = {
                        16: "icon_16x16.png",
                        32: "icon_16x16@2x.png",
                        32: "icon_32x32.png",
                        64: "icon_32x32@2x.png",
                        128: "icon_128x128.png",
                        256: "icon_128x128@2x.png",
                        256: "icon_256x256.png",
                        512: "icon_256x256@2x.png",
                        512: "icon_512x512.png",
                        1024: "icon_512x512@2x.png"
                    }
                    
                    for i, size in enumerate(sizes):
                        if size in size_mapping:
                            icons[i].save(os.path.join(iconset_dir, size_mapping[size]))
                    
                    # Convert iconset to icns using iconutil
                    result = subprocess.run([
                        "iconutil", "-c", "icns", iconset_dir, "-o", icns_path
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"Successfully created ICNS file: {icns_path}")
                        # Clean up
                        os.remove(temp_png)
                        import shutil
                        shutil.rmtree(iconset_dir, ignore_errors=True)
                        return True
                    else:
                        print(f"iconutil failed: {result.stderr}")
                        
                except FileNotFoundError:
                    print("iconutil not found, trying alternative method...")
            
            # Fallback: Just save the largest size as PNG and provide instructions
            print(f"Saved largest icon as PNG: {temp_png}")
            print(f"To create ICNS file on macOS:")
            print(f"1. Copy {temp_png} to a Mac")
            print(f"2. Use Icon Composer or online converter")
            print(f"3. Or use: iconutil -c icns temp_icon.iconset -o {icns_path}")
            
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to convert icon: {e}")
        return False

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python create_mac_icon.py <input.ico> [output.icns]")
        print("Example: python create_mac_icon.py xwing.ico xwing.icns")
        sys.exit(1)
    
    ico_file = sys.argv[1]
    icns_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("============================================")
    print("Converting ICO to ICNS for macOS")
    print("============================================")
    print()
    
    success = convert_ico_to_icns(ico_file, icns_file)
    
    if success:
        print()
        print("✅ Icon conversion completed successfully!")
        print(f"ICNS file ready for macOS build: {icns_file or ico_file.replace('.ico', '.icns')}")
    else:
        print()
        print("⚠️  Icon conversion completed with limitations.")
        print("The build will work, but you may want to create a proper ICNS file on macOS.")
    
    print()
    print("Next steps:")
    print("1. Run the Mac build script: ./build_chuckstaroidsv5_mac.sh")
    print("2. Or manually: python3 -m PyInstaller chuckstaroidsv5_mac.spec")

if __name__ == "__main__":
    main()
