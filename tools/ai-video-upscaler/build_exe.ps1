[CmdletBinding()]
param(
    [switch]$DownloadRuntime
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$bin = Join-Path $root "bin"
$required = @("ffmpeg.exe", "ffprobe.exe", "realesrgan-ncnn-vulkan.exe")

if ($DownloadRuntime) {
    & (Join-Path $root "download_runtime.ps1")
}

$missing = $required | Where-Object { -not (Test-Path (Join-Path $bin $_)) }
if ($missing -or -not (Test-Path (Join-Path $bin "models"))) {
    throw "Runtime files are missing. Run: .\build_exe.ps1 -DownloadRuntime"
}

py -3 -m pip install --upgrade pip
py -3 -m pip install -r (Join-Path $root "requirements-build.txt")

$dist = Join-Path $root "dist"
$work = Join-Path $root "build"
Remove-Item $dist, $work -Recurse -Force -ErrorAction SilentlyContinue

# --onefile intentionally creates one portable .exe.  The included binaries/models
# are extracted to a temporary directory automatically when the app starts.
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name "AI-Video-Upscaler" `
    --add-binary "$bin\ffmpeg.exe;bin" `
    --add-binary "$bin\ffprobe.exe;bin" `
    --add-binary "$bin\realesrgan-ncnn-vulkan.exe;bin" `
    --add-data "$bin\models;bin\models" `
    --distpath $dist --workpath $work --specpath $work `
    (Join-Path $root "video_upscaler.py")

Write-Host ""
Write-Host "EXE created: $(Join-Path $dist 'AI-Video-Upscaler.exe')"
