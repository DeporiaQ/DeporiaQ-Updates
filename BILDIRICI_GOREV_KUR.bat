@echo off
schtasks /Create /F /SC MINUTE /MO 30 /TN "DeporiaQ Update Check" /TR "\"%~dp0DeporiaQUpdate.exe\"" /RL LIMITED >nul 2>&1
exit /b 0
