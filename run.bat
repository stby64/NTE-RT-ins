@echo off
setlocal
cd /d "%~dp0"
where pyw >nul 2>nul
if not errorlevel 1 (
  start "" pyw -3 "%~dp0NTE_RT_KR_SafeInstaller.py"
  exit /b
)
where pythonw >nul 2>nul
if not errorlevel 1 (
  start "" pythonw "%~dp0NTE_RT_KR_SafeInstaller.py"
  exit /b
)
start "" py -3 "%~dp0NTE_RT_KR_SafeInstaller.py"
