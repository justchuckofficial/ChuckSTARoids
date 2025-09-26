# 🚀 ChuckSTARoids v5

> **A sophisticated Star Wars-themed space shooter with advanced AI, dynamic scoring, and professional game mechanics**

[![Automated Builds](https://img.shields.io/badge/builds-automated-brightgreen)](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions)
[![Cross Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue)](#-download)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](requirements.txt)

🚀 **Automated builds now active!** Download the latest Windows and macOS versions from the [Actions](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions) tab.

---

## 🎮 Game Overview

**ChuckSTARoids v5** is a modern take on the classic Asteroids arcade game, featuring **Star Wars-themed graphics**, **advanced AI enemies**, **dynamic scoring systems**, and **professional-grade game mechanics**. Pilot your X-Wing through asteroid fields while battling intelligent TIE fighters and massive boss ships in this action-packed space shooter.

---

## ✨ Key Features

### 🛡️ **Advanced Defense Systems**
- **3-Layer Shield System** - Absorb hits before taking damage
- **Shield Recharging** - Shields regenerate over time (3 seconds per layer)
- **Visual Shield Feedback** - See your protection level with dynamic effects
- **Milestone Rewards** - Earn shield recharges at score milestones

### 🎯 **Dynamic Scoring & Multipliers**
- **Score Multiplier System** - Build multipliers for massive point gains
- **Multiplier Decay** - Strategic timing required to maintain high multipliers  
- **Milestone Rewards** - Unlock bonuses at 25k, 100k, and 250k points
- **Online Leaderboard** - Submit scores and compete globally

### 🤖 **Intelligent Enemy AI**
- **5 AI Personalities**: Aggressive, Defensive, Tactical, Swarm, and Deadly
- **Adaptive Behavior** - Enemies learn and respond to your playstyle
- **Environmental Awareness** - AI considers asteroids and other threats
- **Dynamic Difficulty** - Enemy intelligence scales with game progression

### 👾 **Diverse Enemy Types**
- **TIE Fighters** - Multiple variants with unique behaviors
- **UFO Bosses** - Massive ships with complex attack patterns
- **Asteroid Fields** - Dynamic asteroid spawning and physics
- **Special Asteroids** - Ability-granting asteroids with unique properties

### 🎵 **Enhanced Audio System**
- **Dynamic Music** - Adaptive soundtrack that responds to gameplay
- **3D Positional Audio** - Immersive spatial sound effects
- **Multiple Music Styles** - Variety of tracks for different game states
- **Professional Sound Design** - High-quality Star Wars-inspired audio

### 🎨 **Visual Excellence**
- **Particle Systems** - Advanced explosion and trail effects
- **Screen Shake** - Dynamic camera effects for impacts
- **Shadow Rendering** - Realistic ship and object shadows
- **Visual Polish** - Professional-grade graphics and animations

---

## 🎯 Game Mechanics

### **Core Gameplay Loop**
1. **Navigate** asteroid fields in your X-Wing starfighter
2. **Destroy** asteroids to clear levels and earn points
3. **Battle** intelligent TIE fighter squadrons
4. **Survive** massive UFO boss encounters
5. **Progress** through increasingly challenging levels

### **Scoring System**
- **Base Points**: Asteroids (20-100), UFOs (500-2000), Bosses (5000+)
- **Multiplier Bonus**: Chain destructions for up to 10x multipliers
- **Milestone Rewards**: 
  - **25,000 pts** → Shield recharge
  - **100,000 pts** → Shield + ability recharge  
  - **250,000 pts** → Extra life + full recharges

### **Shield Mechanics**
- **3 Hit Points** - Take 3 hits before ship destruction
- **Automatic Recharge** - Shields restore after 3 seconds per layer
- **Visual Indicators** - See shield status with color-coded effects
- **Strategic Element** - Manage shield timing for survival

### **AI Behavior Profiles**
- **Aggressive** - Direct attacks, high aggression
- **Defensive** - Evasive maneuvers, calculated strikes  
- **Tactical** - Formation flying, coordinated attacks
- **Swarm** - Group behavior, overwhelming numbers
- **Deadly** - Advanced targeting, lethal precision

---

## 🚀 Download & Installation

### 📦 **Pre-built Executables (Recommended)**
| Platform | Download | Size | Requirements |
|----------|----------|------|--------------|
| **Windows** | [ChuckSTARoids_v5.exe](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions) | ~45MB | Windows 10+ |
| **macOS** | [ChuckSTARoids_v5.app](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions) | ~45MB | macOS 10.13+ |

> 💡 **No installation required!** Just download and run.

### 🛠️ **Build from Source**
```bash
# Clone the repository
git clone https://github.com/justchuckofficial/ChuckSTARoids_v5.git
cd ChuckSTARoids_v5

# Install dependencies
pip install -r requirements.txt

# Run the game
python chuckstaroidsv5.py
```

---

## 🎮 Controls & Gameplay

### **Basic Controls**
| Key | Action |
|-----|--------|
| **↑ Arrow** | Thrust forward |
| **← → Arrows** | Rotate ship |
| **Spacebar** | Fire weapons |
| **P** | Pause game |
| **ESC** | Return to menu |

### **Advanced Tips**
- **Momentum Management** - Use thrust strategically to control speed
- **Multiplier Chaining** - Destroy enemies quickly to maintain multipliers
- **Shield Conservation** - Let shields recharge between encounters
- **AI Exploitation** - Learn enemy patterns to gain tactical advantage

---

## 🏗️ Technical Architecture

### **Performance Optimizations**
- **Image Caching System** - Rotated sprites cached for smooth performance
- **Particle Management** - Dynamic particle limits prevent framerate drops
- **Memory Optimization** - Garbage collection and resource management
- **Multi-threading** - Background systems for audio and networking

### **Advanced Systems**
- **Physics Engine** - Realistic collision detection and response
- **State Management** - Professional game state architecture
- **Event Logging** - Comprehensive gameplay analytics
- **Error Handling** - Robust error recovery and user experience

### **Code Quality**
- **13,596 lines** of professionally structured Python code
- **Object-oriented design** with clean separation of concerns
- **Type hints** and comprehensive documentation
- **Automated testing** and continuous integration

---

## 🔧 Development

### **Project Structure**
```
ChuckSTARoids_v5/
├── 🎮 chuckstaroidsv5.py      # Main game engine (13K+ lines)
├── 🎵 music.py                # Enhanced audio system  
├── 📋 requirements.txt        # Python dependencies
├── 🖼️ Game Assets/            # Graphics and sounds
│   ├── xwing.gif             # Player ship sprite
│   ├── tie*.gif              # Enemy ship variants
│   ├── *.gif                 # Effects and animations
│   └── xwing.ico             # Application icon
├── ⚙️ Build System/           # Cross-platform builds
│   ├── chuckstaroidsv5.spec  # Windows build config
│   ├── chuckstaroidsv5_mac.spec # macOS build config  
│   └── create_mac_icon.py    # Icon conversion utility
└── 🤖 .github/workflows/     # Automated CI/CD
    ├── build-windows.yml     # Windows build pipeline
    ├── build-mac.yml         # macOS build pipeline
    └── release.yml           # Release automation
```

### **Dependencies**
- **pygame** ≥2.6.1 - Game engine and graphics
- **numpy** ≥2.3.3 - Mathematical operations and physics
- **requests** ≥2.32.5 - Online scoreboard integration
- **psutil** ≥7.0.0 - System monitoring and optimization
- **mido** ≥1.3.3 - MIDI support for enhanced audio

### **Automated Build System**
- **Cross-platform builds** - Windows and macOS executables
- **GitHub Actions** - Automated testing and deployment
- **Professional packaging** - Standalone executables with embedded assets
- **Continuous integration** - Every commit triggers new builds

---

## 🏆 Game Statistics

### **Content Scale**
- **13,596 lines** of game code
- **Multiple enemy types** with unique AI behaviors  
- **Advanced particle systems** with 2,500+ particles
- **Professional audio** with dynamic music system
- **Cross-platform** Windows and macOS support

### **Technical Achievements**
- **Advanced AI** - 5 distinct personality types
- **Dynamic scoring** - Multiplier system with decay mechanics
- **Shield system** - 3-layer defense with visual feedback
- **Online integration** - Global leaderboard system
- **Professional polish** - Commercial-quality game experience

---

## 📄 License & Credits

This project is **open source** and available under the terms specified in the repository.

### **Acknowledgments**
- **Star Wars universe** - Inspiration for graphics and theme
- **Classic Asteroids** - Foundation gameplay mechanics  
- **Modern game design** - Advanced features and polish

---

## 🌟 **Ready to Play?**

**Download now and experience the most advanced Asteroids game ever created!**

[![Download Windows](https://img.shields.io/badge/Download-Windows%20EXE-blue?style=for-the-badge&logo=windows)](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions)
[![Download macOS](https://img.shields.io/badge/Download-macOS%20APP-blue?style=for-the-badge&logo=apple)](https://github.com/justchuckofficial/ChuckSTARoids_v5/actions)

*May the Force be with you, pilot!* ⭐