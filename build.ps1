param(
    [string]$VenvPython = ".\.venv\Scripts\python.exe",
    [string]$ExeName = "mediacutter"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ffmpegPath = Join-Path $projectRoot "tools\ffmpeg\ffmpeg.exe"
$entryScript = Join-Path $projectRoot "src\mediacutter\cli.py"

if (-not (Test-Path $VenvPython)) {
    throw "Python executable not found at '$VenvPython'. Create the virtual environment first."
}

if (-not (Test-Path $ffmpegPath)) {
    throw "Bundled ffmpeg not found at '$ffmpegPath'."
}

Write-Host "Using FFmpeg: $ffmpegPath"

& $VenvPython -m pip install --upgrade pyinstaller | Out-Null

& $VenvPython -m PyInstaller `
    --onefile `
    --name $ExeName `
    --add-binary "${ffmpegPath};." `
    "$entryScript"

Write-Host "Build complete: dist\$ExeName.exe"
