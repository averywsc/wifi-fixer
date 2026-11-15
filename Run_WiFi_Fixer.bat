@echo off
cd /d "%~dp0"
py -m pip install -q psutil
start "" pyw wifi_fixer.py
