$ErrorActionPreference = 'Stop'
$traceRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Push-Location $traceRoot
try {
    python -m compileall -q trace tests
    if ($LASTEXITCODE -ne 0) { throw 'Python compilation failed.' }
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }
    node --test tests/client.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Client tests failed.' }
    node --check web/app.js
    if ($LASTEXITCODE -ne 0) { throw 'JavaScript syntax failed.' }
    git diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Whitespace checks failed.' }
    Write-Output 'All Trace checks passed.'
} finally {
    Pop-Location
}
