# 🚀 Automated Builds for Chucksteroids v5

## Overview
This project now has **fully automated builds** for both Windows and macOS! Every time you push code changes, GitHub Actions will automatically build both versions and make them available for download.

## 🎯 What You Get

### Automatic Builds
- ✅ **Windows .exe** - Built on Windows runners
- ✅ **macOS .app** - Built on macOS runners  
- ✅ **Both platforms** - Every code change triggers both builds
- ✅ **Downloadable artifacts** - Get the files directly from GitHub
- ✅ **Automatic releases** - Tagged versions create proper releases

### Professional Distribution
- 📦 **Standalone executables** - No dependencies required
- 🎮 **All assets embedded** - Graphics, sounds, everything included
- 🔒 **Code signing ready** - Professional distribution ready
- 📱 **Cross-platform** - Works on Windows 10+ and macOS 10.13+

## 🚀 Quick Start

### 1. Set Up GitHub Repository
```bash
# Add all files to Git
git add .
git commit -m "Add automated build system for Windows and Mac"

# Create repository on GitHub, then:
git remote add origin https://github.com/yourusername/chucksteroids.git
git push -u origin main
```

### 2. Enable GitHub Actions
- Go to your GitHub repository
- Click "Actions" tab
- Click "I understand my workflows, go ahead and enable them"

### 3. Push Your Code
```bash
git add .
git commit -m "Update game code"
git push
```

### 4. Download Your Builds
- Go to "Actions" tab in GitHub
- Click on the latest workflow run
- Download both:
  - **ChuckSTARoids-Windows** (Windows .exe)
  - **ChuckSTARoids-macOS** (macOS .app)

## 📁 File Structure

### Build Files Created
```
.github/workflows/
├── build-windows.yml    # Windows build workflow
├── build-mac.yml        # macOS build workflow
└── release.yml          # Combined release workflow

# Build configuration
chuckstaroidsv5.spec         # Windows PyInstaller config
chuckstaroidsv5_mac.spec     # macOS PyInstaller config
create_mac_icon.py           # Icon converter utility
.gitignore                   # Git ignore rules
```

### Output Files
```
# Windows
dist/ChuckSTARoids_v5.exe    # Windows executable

# macOS  
dist/ChuckSTARoids_v5.app    # macOS application bundle
```

## 🔧 How It Works

### Build Process
1. **You push code** to GitHub
2. **GitHub Actions triggers** both Windows and Mac builds
3. **Windows runner** builds the .exe file
4. **macOS runner** builds the .app bundle
5. **Artifacts uploaded** for download
6. **You download** both versions

### Build Triggers
- **Every push** to main/master branch
- **Pull requests** (for testing)
- **Manual trigger** (workflow_dispatch)
- **Version tags** (creates releases)

## 📊 Build Information

### Windows Build
- **Runner**: Windows Server 2022
- **Python**: 3.11
- **Output**: `ChuckSTARoids_v5.exe`
- **Size**: ~40-50MB
- **Dependencies**: All embedded

### macOS Build
- **Runner**: macOS 12 (Monterey)
- **Python**: 3.11
- **Output**: `ChuckSTARoids_v5.app`
- **Size**: ~40-50MB
- **Dependencies**: All embedded

## 🎮 Testing Your Builds

### Windows Testing
1. Download `ChuckSTARoids_v5.exe`
2. Double-click to run
3. Test all game features
4. Try moving to different folders

### macOS Testing
1. Download `ChuckSTARoids_v5.app`
2. Right-click and select "Open"
3. If security warning appears, click "Open"
4. Test all game features
5. Try moving to Applications folder

## 🏷️ Creating Releases

### Automatic Releases
When you create a version tag, both builds are automatically packaged into a release:

```bash
# Create a version tag
git tag v1.0.0
git push origin v1.0.0
```

This will:
- Build both Windows and Mac versions
- Create a GitHub release
- Include both executables
- Generate release notes

### Manual Releases
- Go to "Actions" tab
- Click "Build and Release All Platforms"
- Click "Run workflow"
- Download artifacts when complete

## 🔍 Monitoring Builds

### Check Build Status
1. Go to "Actions" tab in GitHub
2. See all workflow runs
3. Click on any run to see details
4. Download artifacts when complete

### Build Logs
- **Real-time logs** during builds
- **Error messages** if builds fail
- **Asset verification** before building
- **File size information** after building

## 🛠️ Troubleshooting

### Common Issues

#### Build Fails
1. **Check logs** in Actions tab
2. **Verify all assets** are committed
3. **Ensure dependencies** are in requirements.txt
4. **Check file paths** in spec files

#### Missing Assets
1. **Add missing files** to repository
2. **Update .gitignore** if needed
3. **Commit and push** changes
4. **Trigger new build**

#### Download Issues
1. **Wait for build** to complete
2. **Check artifact** expiration (30 days)
3. **Try manual trigger** if needed
4. **Contact support** if persistent

### Build Optimization
- **Parallel builds** - Windows and Mac build simultaneously
- **Caching** - Dependencies cached between builds
- **Asset verification** - Checks files before building
- **Error handling** - Clear error messages

## 📈 Benefits

### For Development
- ✅ **No local builds** needed
- ✅ **Consistent environment** every time
- ✅ **Both platforms** automatically
- ✅ **Version control** integration

### For Distribution
- ✅ **Professional packaging** ready
- ✅ **Cross-platform** support
- ✅ **Easy sharing** via GitHub
- ✅ **Automatic updates** possible

### For Users
- ✅ **No dependencies** required
- ✅ **Native performance** on both platforms
- ✅ **Easy installation** process
- ✅ **Professional appearance**

## 🎯 Next Steps

### Immediate
1. **Set up GitHub repository**
2. **Push your code**
3. **Download first builds**
4. **Test on both platforms**

### Advanced
1. **Set up code signing** for distribution
2. **Create installer packages** (MSI, DMG)
3. **Set up automated testing**
4. **Add performance benchmarks**

### Distribution
1. **Share GitHub repository** with users
2. **Create release notes** for each version
3. **Set up download tracking**
4. **Consider app stores** for wider reach

## 📞 Support

### Getting Help
1. **Check build logs** first
2. **Verify all files** are committed
3. **Test locally** before pushing
4. **Check GitHub Actions** documentation

### Common Commands
```bash
# Check Git status
git status

# Add all files
git add .

# Commit changes
git commit -m "Your message"

# Push to GitHub
git push

# Create version tag
git tag v1.0.0
git push origin v1.0.0
```

---

**You now have professional, automated builds for both Windows and Mac!** 🎮🚀

Every code change automatically creates both versions, ready for distribution to your players.
