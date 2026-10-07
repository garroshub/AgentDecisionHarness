$ErrorActionPreference = "Stop"
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
python -m unittest discover -s "$PSScriptRoot\tests" -v
