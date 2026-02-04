# Build script for Loto Ticket Maker (PowerShell)
# Chạy script này để build .exe

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

$pythonExe = Join-Path $scriptPath ".venv32\Scripts\python.exe"
$distPath = Join-Path $scriptPath "dist32"
$workPath = Join-Path $scriptPath "build32"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Khong tim thay .venv32. Vui long tao moi truong 32-bit truoc." -ForegroundColor Red
    Write-Host "Duong dan can co: $pythonExe" -ForegroundColor Yellow
    Read-Host "Nhan Enter de thoat"
    exit 1
}

Write-Host ""
Write-Host "===== Loto Ticket Maker Build Script =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "Chon option:" -ForegroundColor Yellow
Write-Host "1. Build nhanh (su dung cache cu)"
Write-Host "2. Build sach (xoa cache build lai tu dau)"
Write-Host ""

$choice = Read-Host "Nhap lua chon (1 hoac 2)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Building... (su dung cache)" -ForegroundColor Green
        & $pythonExe -m PyInstaller loto_ticket_maker.spec --distpath $distPath --workpath $workPath
    }
    "2" {
        Write-Host ""
        Write-Host "Building... (clean, xoa cache)" -ForegroundColor Green
        & $pythonExe -m PyInstaller loto_ticket_maker.spec --clean --distpath $distPath --workpath $workPath
    }
    default {
        Write-Host "Lua chon khong hop le!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "===== Build HOAN THANH =====" -ForegroundColor Green
    Write-Host ".exe nam tai: $distPath\LotoTicketMaker.exe" -ForegroundColor Cyan
} else {
    Write-Host "Build FAILED!" -ForegroundColor Red
}
Write-Host ""
Read-Host "Nhan Enter de thoat!"