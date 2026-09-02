@echo off
cd /d "%~dp0"
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Inno Setup 6 bulunamadi. Once Inno Setup 6 kurun.
    pause
    exit /b 1
)
"%ISCC%" DeporiaQ.iss
if errorlevel 1 (
    echo Kurulum dosyasi olusturulamadi.
    pause
    exit /b 1
)
echo Kurulum hazir: kurulum\DeporiaQ_Setup_0.17.0.exe
pause
