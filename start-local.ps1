# Local Development Launcher for Tachelhit Drills
# This script starts the backend and frontend servers in separate windows.
# Run from the root directory of the project.

$backendDir = "backend"
$frontendDir = "frontend"

Write-Host "Starting Tachelhit Drills local environment..." -ForegroundColor Green

# Check if backend .env file exists, copy from example if not
if (-not (Test-Path "$backendDir/.env")) {
    Write-Host "Backend .env not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item "$backendDir/.env.example" "$backendDir/.env"
}

# Check if frontend .env file exists, copy from example if not
if (-not (Test-Path "$frontendDir/.env")) {
    Write-Host "Frontend .env not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item "$frontendDir/.env.example" "$frontendDir/.env"
}

# Install frontend dependencies if node_modules missing
if (-not (Test-Path "$frontendDir/node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Set-Location $frontendDir
    npm install
    Set-Location ..
}

# Check if Python is available
Write-Host "Checking Python installation..." -ForegroundColor Gray
try {
    $pythonVersion = (python --version 2>&1) | Out-String
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found or not in PATH. Please install Python 3.8 or later." -ForegroundColor Red
    exit 1
}

# Check if port 8000 is already in use
Write-Host "Checking port 8000..." -ForegroundColor Gray
try {
    $portTest = Test-NetConnection -ComputerName localhost -Port 8000 -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($portTest -eq $true) {
        Write-Host "⚠️  Port 8000 is already in use. If a previous backend is running, please stop it first." -ForegroundColor Yellow
        Write-Host "   You can run: Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force" -ForegroundColor Gray
    }
} catch {
    # Ignore errors, continue
}

# Install backend dependencies
Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
Set-Location $backendDir
python -m venv venv 2>$null
.\venv\Scripts\Activate.ps1
pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install backend dependencies. Check requirements.txt." -ForegroundColor Red
    exit 1
}
Set-Location ..

# Start backend in a new PowerShell window
Write-Host "Starting backend server..." -ForegroundColor Cyan
$backendScript = @"
cd `"$PWD\$backendDir`"
.\venv\Scripts\Activate.ps1
python main.py
"@
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", $backendScript

# Wait for backend to start and verify health
Write-Host "Waiting for backend to start (this may take up to 2 minutes)..." -ForegroundColor Gray
$maxAttempts = 60
$attempt = 0
$backendUp = $false
while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($response.status -eq "healthy") {
            $backendUp = $true
            break
        }
    } catch {
        # Do nothing, just wait
    }
    $attempt++
    Write-Progress -Activity "Waiting for backend" -Status "Attempt $attempt of $maxAttempts" -PercentComplete (($attempt/$maxAttempts)*100)
    Start-Sleep -Seconds 2
}
Write-Progress -Activity "Waiting for backend" -Completed

if (-not $backendUp) {
    Write-Host "❌ Backend failed to start within 120 seconds. Please check the backend window for errors." -ForegroundColor Red
    Write-Host "   Ensure all dependencies are installed (pip install -r requirements.txt)." -ForegroundColor Yellow
    Write-Host "   You can also try to start the backend manually:" -ForegroundColor Yellow
    Write-Host "   cd backend; python main.py" -ForegroundColor White
    Write-Host "   Then open a new terminal and run: cd frontend; npm run dev" -ForegroundColor White
} else {
    Write-Host "✅ Backend is up and running." -ForegroundColor Green
}

# Start frontend in a new PowerShell window
Write-Host "Starting frontend dev server..." -ForegroundColor Cyan
$frontendScript = @"
cd `"$PWD\$frontendDir`"
npm run dev
"@
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", $frontendScript

Write-Host "Both servers started in separate windows." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop this script (servers will continue running)." -ForegroundColor Gray
Write-Host ""
