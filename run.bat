@echo off
setlocal
cd /d "%~dp0"
where pythonw >nul 2>nul
if not errorlevel 1 (
  start "" pythonw "%~dp0NTE_RT_KR_SafeInstaller.py"
  exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
  start "" python "%~dp0NTE_RT_KR_SafeInstaller.py"
  exit /b
)
where pyw >nul 2>nul
if not errorlevel 1 (
  start "" pyw -3 "%~dp0NTE_RT_KR_SafeInstaller.py"
  exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
  start "" py -3 "%~dp0NTE_RT_KR_SafeInstaller.py"
  exit /b
)
echo Python 3 was not found.
echo Please install Python 3 from https://www.python.org/downloads/windows/
echo During installation, enable "Add python.exe to PATH".
pause
