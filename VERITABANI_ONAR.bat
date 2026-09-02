@echo off
cd /d "%~dp0"
title DeporiaQ Veritabani Onarimi
echo ONEMLI: Once eski ve yeni tum DeporiaQ pencerelerini kapatin.
echo.
pause
py VERITABANI_ONAR.py
echo.
if errorlevel 1 (
    echo Onarim tamamlanamadi. Bu ekranin goruntusunu ChatGPT'ye gonderin.
) else (
    echo Islem tamamlandi. Simdi dist klasorundeki DeporiaQ.exe dosyasini acin.
)
pause
