# ============================================================================
# SmartParser Setup and Run Script
# ============================================================================
# 
# Functions:
#   1. Check Python version
#   2. Create virtual environment
#   3. Install all dependencies
#   4. Create necessary folders
#   5. Start the program
#
# Usage:
#   Run in PowerShell: .\setup_and_run.ps1
#
# ============================================================================

# Error handling
$ErrorActionPreference = "Stop"

# Color output functions
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Step {
    param([string]$Message)
    Write-ColorOutput "`n[Step] $Message" "Cyan"
    Write-ColorOutput ("=" * 60) "DarkGray"
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "[OK] $Message" "Green"
}

function Write-Err {
    param([string]$Message)
    Write-ColorOutput "[X] $Message" "Red"
}

function Write-Warn {
    param([string]$Message)
    Write-ColorOutput "[!] $Message" "Yellow"
}

# ============================================================================
# Welcome message
# ============================================================================
Clear-Host
Write-ColorOutput "" "Blue"
Write-ColorOutput "============================================================" "Blue"
Write-ColorOutput "           SmartParser - Setup and Configure                " "Blue"
Write-ColorOutput "============================================================" "Blue"
Write-ColorOutput ""
Write-ColorOutput "  This script will:"
Write-ColorOutput "    1. Check Python environment"
Write-ColorOutput "    2. Create virtual environment"
Write-ColorOutput "    3. Install all dependencies"
Write-ColorOutput "    4. Start SmartParser program"
Write-ColorOutput ""
Write-ColorOutput "============================================================" "Blue"
Write-ColorOutput ""

# ============================================================================
# Step 1: Check Python version
# ============================================================================
Write-Step "Checking Python environment"

$pythonCmd = $null
$pythonCmds = @("python", "python3", "py")

foreach ($cmd in $pythonCmds) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 9) {
                $pythonCmd = $cmd
                Write-Success "Found Python: $version"
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $pythonCmd) {
    Write-Err "Python 3.9+ not found"
    Write-ColorOutput ""
    Write-ColorOutput "Please install Python 3.9 or higher:" "Yellow"
    Write-ColorOutput "  1. Visit https://www.python.org/downloads/"
    Write-ColorOutput "  2. Download and install Python 3.9+"
    Write-ColorOutput "  3. Make sure to check 'Add Python to PATH'"
    Write-ColorOutput "  4. Re-run this script"
    Write-ColorOutput ""
    Read-Host "Press Enter to exit"
    exit 1
}

# ============================================================================
# Step 2: Change to script directory
# ============================================================================
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
Write-Success "Working directory: $scriptDir"

# ============================================================================
# Step 3: Create virtual environment
# ============================================================================
Write-Step "Creating virtual environment"

$venvPath = Join-Path $scriptDir "venv"

if (Test-Path $venvPath) {
    Write-Warn "Virtual environment already exists, skipping creation"
} else {
    Write-ColorOutput "Creating virtual environment..." "Gray"
    & $pythonCmd -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to create virtual environment"
        exit 1
    }
    Write-Success "Virtual environment created"
}

# ============================================================================
# Step 4: Activate virtual environment
# ============================================================================
Write-Step "Activating virtual environment"

$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-Err "Activation script not found: $activateScript"
    exit 1
}

# Activate
. $activateScript
Write-Success "Virtual environment activated"

# ============================================================================
# Step 5: Upgrade pip
# ============================================================================
Write-Step "Upgrading pip"

Write-ColorOutput "Upgrading pip..." "Gray"
& python -m pip install --upgrade pip --quiet
Write-Success "pip upgraded"

# ============================================================================
# Step 6: Install dependencies
# ============================================================================
Write-Step "Installing dependencies (this may take several minutes)"

$requirementsPath = Join-Path $scriptDir "requirements.txt"

if (-not (Test-Path $requirementsPath)) {
    Write-Err "requirements.txt not found"
    exit 1
}

Write-ColorOutput "Installing dependencies, please wait..." "Gray"
Write-ColorOutput "(docling and faster-whisper are large packages, first install takes longer)" "DarkGray"

& pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Warn "Some dependencies may have failed, program will try to continue"
} else {
    Write-Success "All dependencies installed"
}

# ============================================================================
# Step 7: Create necessary folders
# ============================================================================
Write-Step "Creating necessary folders"

$inputDir = Join-Path $scriptDir "input_materials"
$outputDir = Join-Path $scriptDir "output_markdown"
$logsDir = Join-Path $scriptDir "logs"

foreach ($dir in @($inputDir, $outputDir, $logsDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Created folder: $(Split-Path $dir -Leaf)"
    } else {
        Write-Warn "Folder already exists: $(Split-Path $dir -Leaf)"
    }
}

# ============================================================================
# Step 8: Start program
# ============================================================================
Write-Step "Starting SmartParser"

Write-ColorOutput ""
Write-ColorOutput "============================================================" "Yellow"
Write-ColorOutput "  Instructions:"
Write-ColorOutput "    1. Put files into input_materials folder"
Write-ColorOutput "    2. Program will auto-process and output to output_markdown"
Write-ColorOutput "    3. Press Ctrl+C to stop"
Write-ColorOutput "============================================================" "Yellow"
Write-ColorOutput ""

# Run main program
& python main_parser.py
