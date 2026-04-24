# Download and install FFmpeg locally (no admin required)
$ErrorActionPreference = "Stop"

Write-Host "Downloading FFmpeg..." -ForegroundColor Cyan

# FFmpeg download URL (essentials build)
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$downloadPath = "$PSScriptRoot\ffmpeg.zip"
$extractPath = "$PSScriptRoot\ffmpeg"

try {
    # Download
    Write-Host "Downloading from: $ffmpegUrl" -ForegroundColor Yellow
    Write-Host "This may take a few minutes..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $downloadPath -UseBasicParsing
    Write-Host "Download complete!" -ForegroundColor Green

    # Extract
    Write-Host "Extracting..." -ForegroundColor Yellow
    if (Test-Path $extractPath) {
        Remove-Item $extractPath -Recurse -Force
    }
    Expand-Archive -Path $downloadPath -DestinationPath $extractPath -Force

    # Find bin folder
    $binFolder = Get-ChildItem -Path $extractPath -Filter "bin" -Recurse -Directory | Select-Object -First 1

    if ($binFolder) {
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "FFmpeg installed successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "Location: $($binFolder.FullName)" -ForegroundColor Yellow
        Write-Host "`nFFmpeg binaries:" -ForegroundColor Yellow
        Get-ChildItem $binFolder.FullName -Filter "*.exe" | ForEach-Object {
            Write-Host "  - $($_.Name)" -ForegroundColor White
        }

        # Test ffmpeg
        Write-Host "`nTesting ffmpeg..." -ForegroundColor Yellow
        & "$($binFolder.FullName)\ffmpeg.exe" -version | Select-Object -First 1

        Write-Host "`nFFmpeg is ready to use!" -ForegroundColor Green
    } else {
        throw "Could not find bin folder in extracted files"
    }

    # Cleanup
    Remove-Item $downloadPath -Force

} catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
