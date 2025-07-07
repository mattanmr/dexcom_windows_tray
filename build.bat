@echo off
pip install pyinstaller
pyinstaller --noconsole --onefile dexcom_tray_secure.py
pause