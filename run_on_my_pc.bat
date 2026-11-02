@echo off
rem Runs the AI on this PC instead of online: opens its world and lets him wake whenever he chooses.
cd /d "%~dp0"
start "AI World page" python serve.py
start "" http://localhost:8765
python -m brain loop --every 10
