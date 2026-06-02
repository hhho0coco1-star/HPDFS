@echo off
chcp 65001 > nul
title HPDFS Launcher

cd /d "%~dp0"

echo ==========================================
echo HPDFS - Streamlit Launcher
echo ==========================================

if not exist "app_pdfs_mockup_v3.py" (
    echo [ERROR] app_pdfs_mockup_v3.py 파일이 없습니다.
    pause
    exit /b 1
)

if not exist "models\storage_best_model.pkl" (
    echo [ERROR] models\storage_best_model.pkl 파일이 없습니다.
    pause
    exit /b 1
)

py --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher(py)를 찾지 못했습니다. Python 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

echo [CHECK] 필요한 Python 패키지 확인...
py -c "import streamlit, pandas, numpy, sklearn, joblib" >nul 2>nul
if errorlevel 1 (
    echo [INFO] 필요한 패키지가 부족합니다. 자동 설치를 시작합니다.
    py -m pip install -r requirements_pdfs.txt

    py -c "import streamlit, pandas, numpy, sklearn, joblib" >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] 패키지 설치 후에도 import에 실패했습니다.
        pause
        exit /b 1
    )
)

echo.
echo [INFO] HPDFS를 실행합니다.
echo 브라우저가 자동으로 열리지 않으면 아래 주소를 직접 여세요.
echo http://localhost:8501
echo 종료하려면 이 창에서 Ctrl + C를 누르세요.
echo ==========================================

py -m streamlit run app_pdfs_mockup_v3.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false --theme.base dark --theme.primaryColor "#58a6ff" --theme.backgroundColor "#0d1117" --theme.secondaryBackgroundColor "#161b22" --theme.textColor "#e6edf3"

pause
