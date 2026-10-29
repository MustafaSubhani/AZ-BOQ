# Headless Edge screenshot of the running demo: .\shot.ps1 <hash-route> <name> [width] [height] [waitMs]
param([string]$route = "home", [string]$name = "shot", [int]$w = 1440, [int]$h = 900, [int]$wait = 6000)
$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
$out = Join-Path (Resolve-Path "$PSScriptRoot\..\..\cache") "shots\$name.png"
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
if (Test-Path $out) { Remove-Item $out }
$profile = Join-Path $env:TEMP "azboq-edge-shot-$name"
$args = @("--headless=new", "--disable-gpu", "--hide-scrollbars", "--user-data-dir=`"$profile`"", "--window-size=$w,$h",
          "--virtual-time-budget=$wait", "--screenshot=`"$out`"", "http://127.0.0.1:5173/#/$route")
$p = Start-Process -FilePath $edge -ArgumentList $args -PassThru -WindowStyle Hidden
if (-not $p.WaitForExit(90000)) { $p.Kill(); Write-Output "timed out" }
Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Where-Object { $_.CommandLine -like "*azboq-edge-shot-$name*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Output $out
