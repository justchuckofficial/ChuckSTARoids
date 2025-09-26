# ChuckSTARoids v5

A Star Wars-themed Asteroids game with advanced AI and scoring systems.

🚀 **Download**: [Windows](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions) | [macOS](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions)

---

## 🎮 Controls

![Controls](controls.gif)

---

## 🎯 Points & Scoring

### **Asteroid Points** (Based on Size)
- **Size 1 (XXS)**: 11 points
- **Size 2 (XXS)**: 22 points  
- **Size 3 (XS)**: 33 points
- **Size 4 (S)**: 44 points
- **Size 5 (M)**: 55 points
- **Size 6 (L)**: 66 points
- **Size 7 (XL)**: 77 points
- **Size 8 (XXL)**: 88 points
- **Size 9 (XXXL)**: 99 points

### **Enemy Points**
- **UFO Shot**: 500 points
- **UFO Collision**: 200-250 points
- **UFO Spinout**: 200-250 points
- **Ability Asteroid**: 100 points
- **Ability UFO**: 200 points

### **Score Multipliers**
- **Chain destructions** to build multipliers
- **Decay delay**: 0.5 seconds before decay starts
- **Decay duration**: 5 seconds to return to 1.0x
- **Visual pulse effect** when multiplier increases

### **Milestone Rewards**
- **25,000 points** → Shield recharge
- **100,000 points** → Shield + ability recharge
- **250,000 points** → Extra life + full recharges
- **Every 250k** → Additional life (max 5 lives)

---

## 🛡️ Shield System

- **3 shield layers** - Take 3 hits before ship destruction
- **Auto-recharge** - 3 seconds per shield layer
- **Visual feedback** - Color-coded shield status
- **Damage effects** - Screen shake and visual indicators

---

## 🔧 Technical Details

### **File Statistics**
- **Main game file**: `chuckstaroidsv5.py` (13,596 lines)
- **Music system**: `music.py` (enhanced audio)
- **Dependencies**: pygame, numpy, requests, psutil, mido
- **Build system**: PyInstaller with automated CI/CD

### **Code Architecture**
- **Image caching system** - Rotated sprites cached for performance
- **Particle management** - 2,500+ particle limit with dynamic scaling
- **Memory optimization** - Garbage collection and resource management
- **Multi-threading** - Background audio and networking systems

### **Performance Features**
- **FPS**: 60 FPS target
- **Screen size**: 1000x600 (resizable)
- **Particle limit**: 2,500 particles max
- **Asteroid limit**: 300 asteroids max
- **Memory management**: Automatic cleanup and optimization

### **Build System**
- **Windows**: Single .exe file (~45MB)
- **macOS**: .app bundle (~45MB)
- **Automated builds** on every code push
- **Cross-platform** CI/CD with GitHub Actions

---

## 📁 Project Files

```
├── chuckstaroidsv5.py          # Main game (13,596 lines)
├── music.py                    # Audio system
├── requirements.txt            # Dependencies
├── xwing.ico                   # Windows icon
├── *.gif, *.jpg, *.png        # Game assets
├── chuckstaroidsv5.spec       # Windows build config
├── chuckstaroidsv5_mac.spec   # macOS build config
└── .github/workflows/         # Automated builds
```

---

## 🚀 Quick Start

1. **Download** the executable for your platform
2. **Run** the game (no installation needed)
3. **Use arrow keys** to move and spacebar to shoot
4. **Build multipliers** by chaining kills
5. **Survive** as long as possible!

**System Requirements**: Windows 10+ or macOS 10.13+