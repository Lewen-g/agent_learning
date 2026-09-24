@echo off
chcp 65001 >nul
cd /d D:\Study\agent-learning
call .venv\Scripts\activate.bat
python router.py
pause