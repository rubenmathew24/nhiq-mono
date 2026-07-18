#Requires -Version 5.1
<#
.SYNOPSIS
  Run continuous national ingest from the laptop (orchestrator loop locally).

.DESCRIPTION
  Loads .env (DATABASE_URL + AZURE_* for ACA job control), then repeatedly runs
  `python -m ingest.orchestrate.run` with ORCH_CONTINUOUS=1 until exit 0
  (nation complete) or exit 1 (hard failure). Exit 2 (more work / time budget)
  restarts the loop — same contract as the GitHub Action chain.

  Actual data pulls still run on Azure Container Apps jobs; this script only
  hosts the coordinating loop (needs Postgres inventory + Azure SP).

.PARAMETER AllowMyIp
  Create/update a Postgres Flexible Server firewall rule for the caller's
  current public IP so inventory queries succeed from this machine.

.PARAMETER ResourceGroup
  Azure resource group (default from AZURE_RESOURCE_GROUP or .env).

.PARAMETER PostgresServer
  Flexible Server name (default from AZURE_POSTGRES_SERVER or niq-pg).
#>
param(
    [switch]$AllowMyIp,
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$PostgresServer = $(if ($env:AZURE_POSTGRES_SERVER) { $env:AZURE_POSTGRES_SERVER } else { "niq-pg" })
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }
        $name = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1).Trim().Trim("'").Trim('"')
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

Import-DotEnv (Join-Path $RepoRoot ".env")

if (-not $ResourceGroup) {
    $ResourceGroup = $env:AZURE_RESOURCE_GROUP
}
if (-not $env:DATABASE_URL) {
    throw "DATABASE_URL is required (set in .env)."
}

if ($AllowMyIp) {
    if (-not $ResourceGroup) {
        throw "AZURE_RESOURCE_GROUP / -ResourceGroup required with -AllowMyIp"
    }
    Write-Host "Resolving public IP…"
    $ip = (Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 30).Trim()
    $ruleName = "niq-local-$(Get-Date -Format 'yyyyMMddHHmm')"
    Write-Host "Allowing $ip on $PostgresServer (rule $ruleName)…"
    az postgres flexible-server firewall-rule create `
        --resource-group $ResourceGroup `
        --name $PostgresServer `
        --rule-name $ruleName `
        --start-ip-address $ip `
        --end-ip-address $ip `
        -o none
}

$env:ORCH_CONTINUOUS = "1"
if (-not $env:ORCH_BATCH_STATES) { $env:ORCH_BATCH_STATES = "10" }
if (-not $env:ORCH_TIME_BUDGET_SECONDS) { $env:ORCH_TIME_BUDGET_SECONDS = "20700" }
if (-not $env:INGEST_SCOPE) { $env:INGEST_SCOPE = "national" }

$WorkersDir = Join-Path $RepoRoot "workers"
if (-not (Test-Path $WorkersDir)) {
    throw "workers/ not found at $WorkersDir"
}

Write-Host "Starting continuous national ingest (Ctrl+C to cancel)…"
Write-Host "  ORCH_BATCH_STATES=$($env:ORCH_BATCH_STATES)"
Write-Host "  ORCH_TIME_BUDGET_SECONDS=$($env:ORCH_TIME_BUDGET_SECONDS)"

Push-Location $WorkersDir
try {
    while ($true) {
        Write-Host "`n=== orchestrator cycle $(Get-Date -Format o) ==="
        & python -m ingest.orchestrate.run
        $code = $LASTEXITCODE
        if ($code -eq 0) {
            Write-Host "Nation complete (exit 0)."
            exit 0
        }
        if ($code -eq 2) {
            Write-Host "More work remains (exit 2) — restarting cycle…"
            continue
        }
        Write-Host "Hard failure (exit $code)."
        exit $code
    }
}
finally {
    Pop-Location
}
