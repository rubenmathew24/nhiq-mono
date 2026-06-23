$Root = Split-Path $PSScriptRoot -Parent
$ApiDir = Join-Path $Root "apps\api"
$Uvicorn = Join-Path $ApiDir ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $Uvicorn)) {
    Write-Error "API venv not found. Run .\scripts\start.ps1 first to bootstrap dependencies."
    exit 1
}

function Stop-PortProcess([int[]]$Ports) {
    foreach ($port in $Ports) {
        $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($connection in $connections) {
            $processId = $connection.OwningProcess
            if ($processId -and $processId -ne 0) {
                Write-Host "Stopping process $processId listening on port $port" -ForegroundColor Yellow
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

# Free port 8000 so localhost does not hit a stale API missing /api/v1/lookup.
Stop-PortProcess -Ports @(8000)

# .env uses Docker service hostnames; local dev talks to Redis on localhost.
if (-not $env:REDIS_URL -or $env:REDIS_URL -match "redis://redis") {
    $env:REDIS_URL = "redis://localhost:6379"
}

Set-Location $ApiDir
& $Uvicorn main:app --reload --host 0.0.0.0 --port 8000
