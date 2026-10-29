# Start the AZ-BOQ demo from the shipped caches. No network is needed.
# Usage: .\run-demo.ps1            (serve and open the browser)
#        .\run-demo.ps1 -Rebuild   (re-run the pipeline stages that read caches, the exports and the frontend build first)
param([switch]$Rebuild, [int]$Port = 8780)
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
Set-Location "$PSScriptRoot\backend"
if ($Rebuild) {
    py -3 -m azboq run
    py -3 -m azboq tiles
    py -3 -m azboq export
    py -3 -m azboq hardcoded-report
    Push-Location "$PSScriptRoot\frontend"; npm run build; Pop-Location
}
if (-not (Test-Path "$PSScriptRoot\frontend\dist\index.html")) { throw "frontend/dist is missing: run .\run-demo.ps1 -Rebuild" }
Start-Job -ScriptBlock { param($p) Start-Sleep 4; Start-Process "http://127.0.0.1:$p/#/home" } -ArgumentList $Port | Out-Null
py -3 -m azboq serve --port $Port
