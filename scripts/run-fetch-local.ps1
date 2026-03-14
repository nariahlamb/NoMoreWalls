param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$qualityDir = Join-Path $repoRoot "artifacts/quality"
$localDir = Join-Path $repoRoot "artifacts/local"

New-Item -ItemType Directory -Path $qualityDir -Force | Out-Null
New-Item -ItemType Directory -Path $localDir -Force | Out-Null

Push-Location $repoRoot
try {
    & $Python "fetch.py"
} finally {
    Pop-Location
}

Write-Host "Fetch finished. Key artifacts:"
Write-Host "  $repoRoot/list.txt"
Write-Host "  $repoRoot/list.yml"
Write-Host "  $repoRoot/list.meta.yml"
Write-Host "  $qualityDir/node_snapshot.jsonl"
Write-Host "  $qualityDir/source_summary.csv"
Write-Host "  $qualityDir/merge_stats.json"
Write-Host "  $qualityDir/unknown_nodes.txt"
