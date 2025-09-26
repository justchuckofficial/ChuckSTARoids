# 🚀 Automated Mac Builds with GitHub Actions

## What This Does
GitHub Actions will automatically build your Mac version whenever you push code changes. You'll get a downloadable `.app` file without needing a Mac!

## Setup Instructions

### 1. Create GitHub Repository
```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit with Mac build support"

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
git commit -m "Add Mac build support"
git push
```

### 4. Download Your Mac App
- Go to "Actions" tab in GitHub
- Click on the latest workflow run
- Download the "ChuckSTARoids-macOS" artifact
- Extract the `.app` file

## What Happens Automatically

### On Every Push:
1. **Triggers build** on macOS runner
2. **Installs dependencies** (Python, PyInstaller, etc.)
3. **Converts icon** from `.ico` to `.icns`
4. **Builds the app** using your spec file
5. **Tests the app** to ensure it works
6. **Uploads artifact** for download

### Build Time:
- **~5-10 minutes** per build
- **Free** for public repositories
- **2000 minutes/month** for private repos

## Files You Need

Make sure these files are in your repository:
- ✅ `chuckstaroidsv5.py` (main game)
- ✅ `music.py` (music module)
- ✅ `xwing.ico` (Windows icon)
- ✅ `chuckstaroidsv5_mac.spec` (Mac build config)
- ✅ `create_mac_icon.py` (icon converter)
- ✅ `.github/workflows/build-mac.yml` (GitHub Actions config)
- ✅ All `.gif` and `.jpg` game assets

## Benefits

### ✅ No Mac Required
- Builds happen in the cloud
- You get the final `.app` file
- Works from any computer

### ✅ Automatic Updates
- Every code change triggers new build
- Always have latest Mac version
- Version control integration

### ✅ Professional Distribution
- Downloadable from GitHub
- Version history
- Release management

## Troubleshooting

### Build Fails
1. Check the "Actions" tab for error logs
2. Ensure all game assets are committed
3. Verify Python dependencies in workflow

### App Won't Run
1. Right-click app and select "Open"
2. Check System Preferences > Security & Privacy
3. Allow the app to run

### Missing Files
1. Ensure all `.gif` files are in repository
2. Check that `music.py` is present
3. Verify `xwing.ico` exists

## Alternative: Manual Mac Build

If you prefer to build manually on a Mac:

1. **Copy files to Mac**:
   - All game files
   - `chuckstaroidsv5_mac.spec`
   - `build_chuckstaroidsv5_mac.sh`

2. **Run on Mac**:
   ```bash
   chmod +x build_chuckstaroidsv5_mac.sh
   ./build_chuckstaroidsv5_mac.sh
   ```

3. **Get the app**:
   - `dist/ChuckSTARoids_v5.app`

## Next Steps

1. **Set up GitHub repository** (if not already done)
2. **Push your code** with the new files
3. **Check Actions tab** for build status
4. **Download the Mac app** when ready
5. **Test on Mac** (borrow one if needed)

---

**This gives you a perfect Mac copy without needing a Mac!** 🎮🍎
