@echo off
cd /d "%~dp0"
set "KURULUM=kurulum\DeporiaQ_Setup_0.17.0.exe"
if not exist "%KURULUM%" (
    echo Kurulum bulunamadi. Once EXE_OLUSTUR.bat ve KURULUM_OLUSTUR.bat calistirin.
    pause
    exit /b 1
)
set "INDIRME_URL=https://github.com/DeporiaQ/DeporiaQ-Updates/releases/download/v0.17.0/DeporiaQ_Setup_0.17.0.exe"
py GUNCELLEME_YAYINA_HAZIRLA.py "%KURULUM%" "0.17.0" "%INDIRME_URL%"
pause
