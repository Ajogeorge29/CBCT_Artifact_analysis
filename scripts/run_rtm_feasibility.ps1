$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repository = Split-Path -Parent $PSScriptRoot
$workbook = Join-Path $repository "data\private\Alginate study master chart.xlsx"
$reports = Join-Path $repository "reports"
$dockerfile = Join-Path $repository "docker\rtm\Dockerfile"
$dockerContext = Split-Path -Parent $dockerfile
$image = "cbct-rtm:0.6.6"

if (-not (Test-Path -LiteralPath $workbook -PathType Leaf)) {
    throw "Private workbook not found at $workbook"
}

docker info --format '{{.ServerVersion}}' | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not running."
}

# The build context contains only the Dockerfile, never the private workbook.
docker build --tag $image --file $dockerfile $dockerContext
if ($LASTEXITCODE -ne 0) {
    throw "RTM container build failed."
}

New-Item -ItemType Directory -Force -Path $reports | Out-Null
$repositoryMount = "type=bind,source=$repository,target=/workspace,readonly"
$reportsMount = "type=bind,source=$reports,target=/output"

# Network access is disabled before the private workbook is mounted.
docker run --rm `
    --network none `
    --read-only `
    --security-opt no-new-privileges `
    --tmpfs /tmp:rw,noexec,nosuid,size=256m `
    --mount $repositoryMount `
    --mount $reportsMount `
    $image `
    --input "/workspace/data/private/Alginate study master chart.xlsx" `
    --output-dir /output

if ($LASTEXITCODE -ne 0) {
    throw "RTM feasibility analysis failed."
}
