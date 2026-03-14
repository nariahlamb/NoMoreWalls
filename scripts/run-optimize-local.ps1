param(
    [string]$Python = "python",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$OptimizeArgs
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
    & $Python "optimize_local.py" @OptimizeArgs
} finally {
    Pop-Location
}

Write-Host "Optimize finished. Key artifacts:"
Write-Host "  $localDir/list.local.txt"
Write-Host "  $localDir/list.local.yml"
Write-Host "  $localDir/list.local.meta.yml"
Write-Host "  $localDir/snippets/nodes.local.yml"
Write-Host "  $localDir/snippets/nodes.local.meta.yml"
Write-Host "  $qualityDir/summary.md"
Write-Host "  $qualityDir/top_nodes.csv"
Write-Host "  $qualityDir/filter_reasons.csv"
Write-Host "  $qualityDir/source_reputation.csv"
