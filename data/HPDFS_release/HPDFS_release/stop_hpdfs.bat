@echo off
chcp 65001 > nul
title HPDFS Stop

echo ==========================================
echo HPDFS 종료
echo ==========================================
echo Streamlit 실행 창에서 Ctrl + C로 종료하는 것을 권장합니다.
echo 그래도 종료가 안 되면 이 스크립트가 Python/Streamlit 프로세스를 강제 종료합니다.
echo ==========================================

taskkill /F /IM streamlit.exe >nul 2>nul
taskkill /F /IM python.exe >nul 2>nul
taskkill /F /IM py.exe >nul 2>nul

echo 완료.
pause
