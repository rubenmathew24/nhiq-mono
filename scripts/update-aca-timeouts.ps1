# Apply ACA replica timeouts for continuous national ingest (007).
# Usage: .\scripts\update-aca-timeouts.ps1 [-ResourceGroup neighborhoodiq-rg]

param(
    [string]$ResourceGroup = $(if ($env:AZURE_RESOURCE_GROUP) { $env:AZURE_RESOURCE_GROUP } else { "neighborhoodiq-rg" })
)

$ErrorActionPreference = "Stop"

Write-Host "Updating niq-worker-orchestrate replica-timeout=21600 in $ResourceGroup"
az containerapp job update `
    --name niq-worker-orchestrate `
    --resource-group $ResourceGroup `
    --replica-timeout 21600 `
    -o none

$jobs = @(
    "niq-worker-census",
    "niq-worker-epa",
    "niq-worker-cms",
    "niq-worker-fbi",
    "niq-worker-nces",
    "niq-worker-urban",
    "niq-worker-acs",
    "niq-worker-bls",
    "niq-worker-fema",
    "niq-worker-cms-timely",
    "niq-worker-scoring"
)

foreach ($job in $jobs) {
    Write-Host "Updating $job replica-timeout=10800"
    az containerapp job update `
        --name $job `
        --resource-group $ResourceGroup `
        --replica-timeout 10800 `
        -o none
}

Write-Host "Done."
