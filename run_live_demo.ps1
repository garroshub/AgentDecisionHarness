param(
    [ValidateSet("codex", "claude")]
    [string]$Provider = "codex"
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\src"

if ($Provider -eq "codex") {
    $Scenario = "$PSScriptRoot\examples\live\sample_postearn_codex.json"
} else {
    $Scenario = "$PSScriptRoot\examples\live\sample_postearn_claude.json"
}

Write-Host "=== AgentDecisionHarness: live $Provider provider ==="
Write-Host "Three independent candidate draws -> common decision harness"
Write-Host ""

python -m agent_decision_harness.cli live $Scenario --provider $Provider --effort high
exit $LASTEXITCODE
