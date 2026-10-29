@echo off
cd /d "%~dp0"
set "YOLO_CONFIG_DIR=outputs\ultralytics-config"
set "PYTHONIOENCODING=utf-8"
".venv\Scripts\python.exe" start_ipad.py
pause
