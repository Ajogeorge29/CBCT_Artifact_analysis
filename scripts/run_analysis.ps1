param(
    [string]$InputWorkbook = "data/private/Alginate study master chart.xlsx",
    [string]$OutputDirectory = "reports"
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepositoryRoot
try {
    python -m cbct_artifact_analysis run --input $InputWorkbook --output-dir $OutputDirectory
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python scripts/build_revised_manuscripts.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python scripts/privacy_guard.py --tracked
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
