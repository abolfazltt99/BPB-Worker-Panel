[CmdletBinding()]
param(
    [string]$BinDirectory = (Join-Path $PSScriptRoot "bin")
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Expand-ZipToDirectory([string]$url, [string]$destination) {
    $archive = Join-Path $env:TEMP ([IO.Path]::GetRandomFileName() + ".zip")
    try {
        Write-Host "Downloading $url"
        Invoke-WebRequest -Uri $url -OutFile $archive
        Expand-Archive -Path $archive -DestinationPath $destination -Force
    }
    finally {
        Remove-Item $archive -Force -ErrorAction SilentlyContinue
    }
}

New-Item -ItemType Directory -Path $BinDirectory -Force | Out-Null
$scratch = Join-Path $env:TEMP ("ai-video-upscaler-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
try {
    # Official project release. NCNN Vulkan avoids requiring a current CUDA/PyTorch build.
    Expand-ZipToDirectory "https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/download/0.2.0/realesrgan-ncnn-vulkan-0.2.0-windows.zip" $scratch
    $esrgan = Get-ChildItem $scratch -Recurse -Filter "realesrgan-ncnn-vulkan.exe" | Select-Object -First 1
    if (-not $esrgan) { throw "Real-ESRGAN executable was not found in the downloaded archive." }
    Copy-Item $esrgan.FullName (Join-Path $BinDirectory "realesrgan-ncnn-vulkan.exe") -Force
    Copy-Item (Join-Path $esrgan.DirectoryName "models") (Join-Path $BinDirectory "models") -Recurse -Force

    Remove-Item $scratch -Recurse -Force
    New-Item -ItemType Directory -Path $scratch | Out-Null
    # gyan.dev is a well-known Windows FFmpeg build distributor.
    Expand-ZipToDirectory "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" $scratch
    $ffmpeg = Get-ChildItem $scratch -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
    $ffprobe = Get-ChildItem $scratch -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
    if (-not $ffmpeg -or -not $ffprobe) { throw "FFmpeg executables were not found in the downloaded archive." }
    Copy-Item $ffmpeg.FullName (Join-Path $BinDirectory "ffmpeg.exe") -Force
    Copy-Item $ffprobe.FullName (Join-Path $BinDirectory "ffprobe.exe") -Force
    Write-Host "Runtime is ready in $BinDirectory"
}
finally {
    Remove-Item $scratch -Recurse -Force -ErrorAction SilentlyContinue
}
