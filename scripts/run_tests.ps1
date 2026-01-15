# Comprehensive Test Runner for Evently (PowerShell)
# Run all test categories and generate reports

param(
    [ValidateSet("all", "unit", "integration", "e2e", "security", "performance")]
    [string]$Category = "all",
    
    [switch]$Coverage,
    [switch]$Parallel,
    [switch]$Verbose,
    
    [ValidateSet("chrome", "firefox")]
    [string]$Browser = "chrome"
)

function Run-Command {
    param(
        [string]$Command,
        [string]$Description
    )
    
    Write-Host "`n$('=' * 80)" -ForegroundColor Cyan
    Write-Host "Running: $Description" -ForegroundColor Cyan
    Write-Host "$('=' * 80)`n" -ForegroundColor Cyan
    
    Invoke-Expression $Command
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ $Description passed!" -ForegroundColor Green
        return $true
    } else {
        Write-Host "`n❌ $Description failed!" -ForegroundColor Red
        return $false
    }
}

$results = @()

# Base pytest command
$pytestCmd = "pytest"

if ($Verbose) {
    $pytestCmd += " -v"
}

if ($Coverage) {
    $pytestCmd += " --cov=app --cov-report=html --cov-report=term"
}

if ($Parallel) {
    $pytestCmd += " -n auto"
}

# Type checking
if ($Category -in @("all")) {
    $results += Run-Command "mypy app/" "Type Checking"
}

# Linting
if ($Category -in @("all")) {
    $results += Run-Command "flake8 app/" "Linting"
    $results += Run-Command "black --check app/" "Code Formatting Check"
    $results += Run-Command "isort --check-only app/" "Import Sorting Check"
}

# Unit tests
if ($Category -in @("all", "unit")) {
    $cmd = "$pytestCmd tests/ -m 'unit or not (integration or e2e or security)'"
    $results += Run-Command $cmd "Unit Tests"
}

# Integration tests
if ($Category -in @("all", "integration")) {
    $cmd = "$pytestCmd tests/integration/ -m integration"
    $results += Run-Command $cmd "Integration Tests"
}

# E2E tests
if ($Category -in @("all", "e2e")) {
    $cmd = "$pytestCmd tests/e2e/ -m e2e --browser=$Browser"
    $results += Run-Command $cmd "End-to-End Tests"
}

# Security tests
if ($Category -in @("all", "security")) {
    $cmd = "$pytestCmd tests/security/ -m security"
    $results += Run-Command $cmd "Security Tests"
    
    # Additional security checks
    $results += Run-Command "safety check" "Dependency Vulnerability Check"
    $results += Run-Command "bandit -r app/" "Security Linting"
}

# Performance tests
if ($Category -eq "performance") {
    Write-Host "`n$('=' * 80)" -ForegroundColor Cyan
    Write-Host "Performance Testing with Locust" -ForegroundColor Cyan
    Write-Host "$('=' * 80)`n" -ForegroundColor Cyan
    Write-Host "To run performance tests:" -ForegroundColor Yellow
    Write-Host "  locust -f tests/performance/locustfile.py --host http://localhost:8000" -ForegroundColor Yellow
    Write-Host "  Then open http://localhost:8089 in your browser`n" -ForegroundColor Yellow
}

# Summary
Write-Host "`n$('=' * 80)" -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "$('=' * 80)`n" -ForegroundColor Cyan

$passed = ($results | Where-Object { $_ -eq $true }).Count
$total = $results.Count

Write-Host "Passed: $passed/$total" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })

if ($passed -eq $total -and $total -gt 0) {
    Write-Host "`n🎉 All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n❌ Some tests failed!" -ForegroundColor Red
    exit 1
}
