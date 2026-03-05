param(
    [string]$VenvPython = ".\.venv\Scripts\python.exe",
    [string]$ExeName = "mediacutter"
)

$ErrorActionPreference = "Stop"

function Resolve-FfmpegPath {
    $chocoFull = "C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin\ffmpeg.exe"
    if (Test-Path $chocoFull) {
        return $chocoFull
    }

    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "ffmpeg.exe not found. Install FFmpeg or add it to PATH."
    }

    $candidate = $cmd.Source
    if (-not (Test-Path $candidate)) {
        throw "Resolved ffmpeg path does not exist: $candidate"
    }
    return $candidate
}

if (-not (Test-Path $VenvPython)) {
    throw "Python executable not found at '$VenvPython'. Create the virtual environment first."
}

$ffmpegPath = Resolve-FfmpegPath
Write-Host "Using FFmpeg: $ffmpegPath"

& $VenvPython -m pip install --upgrade pyinstaller | Out-Null

& $VenvPython -m PyInstaller `
    --onefile `
    --name $ExeName `
    --add-binary "${ffmpegPath};." `
    "src\mediacutter\cli.py"

Write-Host "Build complete: dist\$ExeName.exe"
