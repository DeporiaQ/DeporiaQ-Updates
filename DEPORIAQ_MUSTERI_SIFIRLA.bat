@echo off
cd /d "%~dp0"
title DeporiaQ Yeni Musteri Sifirlama
tasklist /FI "IMAGENAME eq DeporiaQ.exe" | find /I "DeporiaQ.exe" >nul
if not errorlevel 1 (
    echo HATA: DeporiaQ halen acik. Programi kapatip tekrar deneyin.
    pause
    exit /b 1
)
py DEPORIAQ_MUSTERI_SIFIRLA.py
echo.
if errorlevel 1 (
    echo Sifirlama tamamlanmadi. Yukaridaki mesaji kontrol edin.
) else (
    echo Islem basarili. Simdi kurulu DeporiaQ 0.14.0 uygulamasini acin.
)
pause
