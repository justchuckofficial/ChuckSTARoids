Write-Host "Activating Chucksteroids Python 3.13 Virtual Environment..." -ForegroundColor Green
& ".\chucksteroids_env\Scripts\Activate.ps1"
Write-Host "Virtual environment activated! Python version:" -ForegroundColor Green
python --version
Write-Host ""
Write-Host "You can now run your Chucksteroids game with:" -ForegroundColor Yellow
Write-Host "python chuckstaroidsv5.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "To deactivate the virtual environment later, just type: deactivate" -ForegroundColor Yellow
