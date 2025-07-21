@echo off
REM Install dependencies
pip install -r requirements.txt
REM Build executable
pip install pyinstaller
python -m PyInstaller --noconsole --onefile --hidden-import win10toast --hidden-import pkg_resources --collect-all win10toast dexcom_tray_secure.py
pause
