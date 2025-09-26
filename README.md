# ChuckSTARoids v5

A Star Wars-themed Asteroids game with advanced AI and scoring systems.

🚀 **Download**: [Windows](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions) | [macOS](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions)

---

## 🎮 Controls

| Key | Action |
|-----|--------|
| **↑ Arrow** | Thrust forward |
| **← → Arrows** | Rotate ship |
| **Spacebar** | Fire weapons |
| **P** | Pause game |
| **ESC** | Return to menu |

---

## 🎯 Points & Scoring

### **Base Points**
- **Small Asteroid**: 20 points
- **Medium Asteroid**: 50 points  
- **Large Asteroid**: 100 points
- **TIE Fighter**: 500 points
- **Advanced TIE**: 1000 points
- **UFO Boss**: 2000 points
- **Massive Boss**: 5000+ points

### **Score Multipliers**
- **Chain destructions** to build multipliers (up to 10x)
- **Multiplier decay** starts after 0.5 seconds of no kills
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

## 🤖 Enemy AI Types

1. **Aggressive** - Direct attacks, high aggression
2. **Defensive** - Evasive maneuvers, calculated strikes
3. **Tactical** - Formation flying, coordinated attacks  
4. **Swarm** - Group behavior, overwhelming numbers
5. **Deadly** - Advanced targeting, lethal precision

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