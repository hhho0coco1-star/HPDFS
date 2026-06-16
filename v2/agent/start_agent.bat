@echo off

chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

title PDFS Agent
echo ============================================================
echo  PDFS 에이전트 시작
echo  종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.
echo ============================================================
echo.

cd /d "%~dp0"
python agent.py

pause

 




