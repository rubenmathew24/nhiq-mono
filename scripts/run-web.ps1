$Root = Split-Path $PSScriptRoot -Parent
$WebDir = Join-Path $Root "apps\web"

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

Stop-PortProcess -Ports @(3000, 3001)

Set-Location $WebDir
npm run dev
