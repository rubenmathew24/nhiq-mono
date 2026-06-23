#Requires -Version 5.1
<#
.SYNOPSIS
  Start the NeighborhoodIQ monorepo (local dev or Docker).

.EXAMPLE
  .\scripts\start.ps1
  .\scripts\start.ps1 -Mode local
  .\scripts\start.ps1 -Mode docker
#>
param(
    [ValidateSet("local", "docker")]
    [string]$Mode = "local",

    [switch]$Install
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-Command([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-EnvFile {
    $envFile = Join-Path $Root ".env"
    $example = Join-Path $Root ".env.example"
    if (-not (Test-Path $envFile)) {
        if (-not (Test-Path $example)) {
            throw "Missing .env.example at repo root."
        }
        Write-Step "Creating .env from .env.example"
        Copy-Item $example $envFile
    }
}

function Ensure-ApiVenv {
    $apiDir = Join-Path $Root "apps\api"
    $venvPython = Join-Path $apiDir ".venv\Scripts\python.exe"
    $requirements = Join-Path $apiDir "requirements.txt"

    if (-not (Test-Path $venvPython)) {
        Write-Step "Creating Python virtual environment (apps/api/.venv)"
        Push-Location $apiDir
        try {
            python -m venv .venv
            if (-not (Test-Path $requirements)) {
                throw "Missing apps/api/requirements.txt - run monorepo setup first."
            }
            & ".\.venv\Scripts\pip.exe" install -r requirements.txt
        }
        finally {
            Pop-Location
        }
        return
    }

    if ($Install) {
        Write-Step "Installing/updating API dependencies"
        Push-Location $apiDir
        try {
            & ".\.venv\Scripts\pip.exe" install -r requirements.txt
        }
        finally {
            Pop-Location
        }
    }
}

function Ensure-WebDeps {
    $webDir = Join-Path $Root "apps\web"
    $nodeModules = Join-Path $webDir "node_modules"
    if (-not (Test-Path $nodeModules) -or $Install) {
        Write-Step "Installing web dependencies (apps/web)"
        Push-Location $webDir
        try {
            npm install
        }
        finally {
            Pop-Location
        }
    }
}

function Ensure-RootDeps {
    $nodeModules = Join-Path $Root "node_modules"
    if (-not (Test-Path $nodeModules) -or $Install) {
        Write-Step "Installing root dev dependencies (concurrently)"
        Push-Location $Root
        try {
            npm install
        }
        finally {
            Pop-Location
        }
    }
}

function Start-Local {
    Ensure-EnvFile
    Ensure-ApiVenv
    Ensure-WebDeps
    Ensure-RootDeps

    if (Test-Command "docker") {
        Write-Step "Starting Redis for local API cache (docker compose)"
        Push-Location $Root
        try {
            docker compose up redis -d | Out-Null
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Host "Docker not found - ensure Redis is running at redis://localhost:6379" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "NeighborhoodIQ - local dev" -ForegroundColor Green
    Write-Host "  Web:  http://localhost:3000"
    Write-Host "  API:  http://localhost:8000"
    Write-Host "  Docs: http://localhost:8000/api/docs"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop both services."
    Write-Host ""

    Push-Location $Root
    try {
        npm run dev
    }
    finally {
        Pop-Location
    }
}

function Start-Docker {
    Ensure-EnvFile

    if (-not (Test-Command "docker")) {
        throw "Docker is not installed or not on PATH. Use -Mode local or install Docker Desktop."
    }

    Write-Step "Starting Docker Compose stack"
    Push-Location $Root
    try {
        docker compose up --build
    }
    finally {
        Pop-Location
    }
}

Push-Location $Root
try {
    switch ($Mode) {
        "local" { Start-Local }
        "docker" { Start-Docker }
    }
}
finally {
    Pop-Location
}
