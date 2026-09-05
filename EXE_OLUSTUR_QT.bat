@echo off
cd /d "%~dp0"
py -m pip install PySide6 ttkbootstrap pyinstaller
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all PySide6 --collect-all shiboken6 --collect-all ttkbootstrap --name DeporiaQ deporiaq_qt.py
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --windowed --name DeporiaQUpdate deporiaq_guncelleme_bildirici.py
if errorlevel 1 exit /b 1
echo PySide6/Qt EXE hazir: dist\DeporiaQ.exe
pause
