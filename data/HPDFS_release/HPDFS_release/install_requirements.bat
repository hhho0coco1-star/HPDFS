@echo off
chcp 65001 > nul
title HPDFS Setup

cd /d "%~dp0"

echo ==========================================
echo HPDFS Python Package Setup
echo ==========================================

py --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher(py)를 찾지 못했습니다. Python 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

py -m pip install --upgrade pip
py -m pip install -r requirements_pdfs.txt

echo.
echo [DONE] 설치 완료
pause
