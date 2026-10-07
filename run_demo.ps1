$ErrorActionPreference = "Stop"
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"

Write-Host ""
Write-Host "=== AgentDecisionHarness: routed frozen case ==="
python -m agent_decision_harness.cli replay "$PSScriptRoot\examples\frozen\FH025_route.json"

Write-Host ""
Write-Host "=== AgentDecisionHarness: consensus frozen case ==="
python -m agent_decision_harness.cli replay "$PSScriptRoot\examples\frozen\FH002_consensus.json"
