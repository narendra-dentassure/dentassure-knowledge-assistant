# Pack a shareable ZIP. Run from anywhere:
#   powershell -File scripts/pack_submission.ps1
# Does NOT include .env, venv, storage, logs, or caches.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "DentAssure_Knowledge_Assistant.zip"
$stage = Join-Path $env:TEMP "dentassure_pack"

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null

$copy = @(
    "app.py",
    "requirements.txt",
    ".env.example",
    "README.md",
    "pytest.ini",
    ".gitignore",
    ".streamlit",
    "src",
    "tests",
    "data",
    "scripts",
    "project_flow_images"
)

foreach ($item in $copy) {
    $src = Join-Path $root $item
    $dst = Join-Path $stage $item
    if (-not (Test-Path $src)) { throw "Missing $item" }
    $parent = Split-Path $dst -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    Copy-Item $src $dst -Recurse -Force
}

Get-ChildItem $stage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem $stage -Recurse -File -Include ".env", "*.pyc", "*.zip" | Remove-Item -Force -ErrorAction SilentlyContinue
if (Test-Path (Join-Path $stage "storage")) { Remove-Item (Join-Path $stage "storage") -Recurse -Force }
if (Test-Path (Join-Path $stage "logs")) { Remove-Item (Join-Path $stage "logs") -Recurse -Force }
if (Test-Path $out) { Remove-Item $out -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $out -Force
Remove-Item $stage -Recurse -Force
Write-Output "Wrote $out"
