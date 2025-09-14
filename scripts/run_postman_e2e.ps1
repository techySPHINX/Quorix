# Run this script in PowerShell to execute the Postman collection using Newman
# Prerequisites: Install newman (npm i -g newman) and have Node.js available.

$collection = "$(Resolve-Path ..\docs\postman\evently.postman_collection.json)"
$env = "$(Resolve-Path ..\docs\postman\evently.postman_environment.json)"

if (-not (Get-Command newman -ErrorAction SilentlyContinue)) {
    Write-Error "newman is not installed. Install with: npm i -g newman"
    exit 1
}

Write-Host "Running Postman collection with Newman..."
newman run $collection -e $env --delay-request 200

if ($LASTEXITCODE -ne 0) {
    Write-Error "Newman returned non-zero exit code: $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "Newman run completed."
