@echo off
cd /d "%~dp0"
py -m pip install PySide6 ttkbootstrap pyinstaller
if errorlevel 1 (
    echo PySide6/Qt gereksinimleri kurulamadi.
    pause
    exit /b 1
)
py -m PyInstaller --noconfirm --clean --onefile --windowed --icon deporiaq_icon.ico --add-data "deporiaq_icon.svg;." --collect-all PySide6 --collect-all shiboken6 --collect-all ttkbootstrap --name DeporiaQ deporiaq_qt.py
if errorlevel 1 (
    echo EXE olusturulamadi.
    pause
    exit /b 1
)
py -m PyInstaller --noconfirm --clean --onefile --windowed --name DeporiaQUpdate deporiaq_guncelleme_bildirici.py
if errorlevel 1 (
    echo Guncelleme bildiricisi olusturulamadi.
    pause
    exit /b 1
)
echo EXE dosyalari basariyla olusturuldu:
echo dist\DeporiaQ.exe
echo dist\DeporiaQUpdate.exe
pause
