@echo off
cd /d "%~dp0"
py -m pip install PySide6==6.11.2 ttkbootstrap==2.2.3 "pyinstaller>=6.9,<7"
if errorlevel 1 (
    echo PySide6/Qt gereksinimleri kurulamadi.
    pause
    exit /b 1
)
py -m PyInstaller --noconfirm --clean --onefile --windowed --icon deporiaq_icon.ico --add-data "deporiaq_icon.svg;." --add-data "youtube_icon.svg;." --add-data "instagram_icon.svg;." --add-data "dashboard_background.jpg;." --add-data "deporiaq_cloud.json;." --collect-all ttkbootstrap --name DeporiaQ deporiaq_qt.py
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
