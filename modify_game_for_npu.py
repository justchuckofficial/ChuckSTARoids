"""
Script to modify chuckstaroidsv4.py to use NPU acceleration
This script makes minimal changes to integrate NPU acceleration
"""

import re
import os
import shutil
from datetime import datetime

def backup_original_file():
    """Create a backup of the original game file"""
    original_file = "chuckstaroidsv4.py"
    backup_file = f"chuckstaroidsv4_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    
    if os.path.exists(original_file):
        shutil.copy2(original_file, backup_file)
        print(f"Backup created: {backup_file}")
        return True
    else:
        print(f"Error: {original_file} not found")
        return False

def modify_game_file():
    """Modify the game file to include NPU acceleration"""
    original_file = "chuckstaroidsv4.py"
    
    if not os.path.exists(original_file):
        print(f"Error: {original_file} not found")
        return False
    
    # Read the original file
    with open(original_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add NPU imports at the top
    npu_imports = '''
# NPU Acceleration imports
try:
    from npu_acceleration import npu_manager
    from npu_integration import integrate_npu_with_game
    NPU_AVAILABLE = True
    print("NPU acceleration available")
except ImportError as e:
    print(f"NPU acceleration not available: {e}")
    NPU_AVAILABLE = False
'''
    
    # Find the imports section and add NPU imports
    import_pattern = r'(import gc  # For garbage collection)'
    if re.search(import_pattern, content):
        content = re.sub(import_pattern, rf'\1{npu_imports}', content)
    else:
        # Add after the last import
        last_import = content.rfind('import')
        if last_import != -1:
            next_newline = content.find('\n', last_import)
            content = content[:next_newline + 1] + npu_imports + content[next_newline + 1:]
    
    # Modify the Game class __init__ method to include NPU
    init_pattern = r'(def __init__\(self\):.*?)(self\.running = True)'
    npu_init_code = '''
        # NPU acceleration setup
        self.npu_enabled = NPU_AVAILABLE
        self.npu_game = None
        if self.npu_enabled:
            try:
                self.npu_game = integrate_npu_with_game(self)
                print("NPU acceleration initialized")
            except Exception as e:
                print(f"Failed to initialize NPU: {e}")
                self.npu_enabled = False
'''
    
    if re.search(init_pattern, content, re.DOTALL):
        content = re.sub(init_pattern, rf'\1{self.npu_enabled = NPU_AVAILABLE}\n{self.npu_game = None}\n        if self.npu_enabled:\n            try:\n                self.npu_game = integrate_npu_with_game(self)\n                print("NPU acceleration initialized")\n            except Exception as e:\n                print(f"Failed to initialize NPU: {{e}}")\n                self.npu_enabled = False\n\n        \2', content)
    
    # Add NPU key bindings to the event handling
    key_pattern = r'(elif event\.key == pygame\.K_ESCAPE:.*?self\.running = False)'
    npu_keys = '''
                        elif event.key == pygame.K_F1:
                            # Toggle NPU acceleration
                            if self.npu_enabled and hasattr(self, 'toggle_npu'):
                                self.toggle_npu()
                        elif event.key == pygame.K_F2:
                            # Show NPU performance stats
                            if self.npu_enabled and hasattr(self, 'get_npu_stats'):
                                stats = self.get_npu_stats()
                                print("=== NPU Performance Stats ===")
                                print(stats['npu_manager_stats'])
                                print(f"Average FPS: {stats['avg_fps']:.1f}")
                                print("==============================")
'''
    
    if re.search(key_pattern, content, re.DOTALL):
        content = re.sub(key_pattern, rf'\1{npu_keys}', content)
    
    # Write the modified content back
    modified_file = "chuckstaroidsv4_npu.py"
    with open(modified_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Modified game file created: {modified_file}")
    return True

def create_requirements_file():
    """Create requirements.txt for NPU dependencies"""
    requirements = """# Chucksteroids NPU Acceleration Requirements
# Core game dependencies
pygame>=2.1.0
numpy>=1.21.0

# NPU acceleration dependencies
openvino>=2023.0.0
pyopencl>=2021.2.0

# Optional: For better performance
numba>=0.56.0
"""
    
    with open("requirements_npu.txt", 'w') as f:
        f.write(requirements)
    
    print("NPU requirements file created: requirements_npu.txt")

def create_run_script():
    """Create a script to run the NPU-accelerated version"""
    run_script = """@echo off
echo Starting Chucksteroids with NPU acceleration...
echo.

REM Check if NPU files exist
if not exist "npu_acceleration.py" (
    echo Error: npu_acceleration.py not found
    echo Please run modify_game_for_npu.py first
    pause
    exit /b 1
)

if not exist "npu_integration.py" (
    echo Error: npu_integration.py not found
    echo Please run modify_game_for_npu.py first
    pause
    exit /b 1
)

if not exist "chuckstaroidsv4_npu.py" (
    echo Error: chuckstaroidsv4_npu.py not found
    echo Please run modify_game_for_npu.py first
    pause
    exit /b 1
)

echo Installing NPU dependencies...
pip install -r requirements_npu.txt

echo.
echo Starting game...
python chuckstaroidsv4_npu.py

pause
"""
    
    with open("run_npu_game.bat", 'w') as f:
        f.write(run_script)
    
    print("NPU run script created: run_npu_game.bat")

def main():
    """Main function to set up NPU acceleration"""
    print("Chucksteroids NPU Acceleration Setup")
    print("====================================")
    
    # Create backup
    if not backup_original_file():
        return
    
    # Modify the game file
    if not modify_game_file():
        return
    
    # Create requirements file
    create_requirements_file()
    
    # Create run script
    create_run_script()
    
    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Install NPU dependencies: pip install -r requirements_npu.txt")
    print("2. Run the NPU-accelerated game: python chuckstaroidsv4_npu.py")
    print("3. Or use the batch file: run_npu_game.bat")
    print("\nControls:")
    print("F1 - Toggle NPU acceleration on/off")
    print("F2 - Show NPU performance statistics")
    print("\nNote: The game will automatically fall back to CPU if NPU is not available")

if __name__ == "__main__":
    main()
