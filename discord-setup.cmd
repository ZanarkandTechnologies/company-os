@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Company OS Discord Setup
set "HERMES_ROOT=%LOCALAPPDATA%\hermes"
if not exist "%HERMES_ROOT%\hermes-agent\venv\Scripts\python.exe" set "HERMES_ROOT=%USERPROFILE%\.hermes"
set "COMPANY_OS_PROFILE_HOME=%HERMES_ROOT%\profiles\company-os"
set "HERMES_PYTHON=%HERMES_ROOT%\hermes-agent\venv\Scripts\python.exe"
set "PATH=%HERMES_ROOT%\hermes-agent\venv\Scripts;%PATH%"

if not exist "%HERMES_PYTHON%" (
  echo Hermes' bundled Python runtime was not found.
  echo Install Hermes first, then run this file again.
  pause
  exit /b 2
)

if not exist "%COMPANY_OS_PROFILE_HOME%\distribution.yaml" (
  echo Company OS has not been installed into its own Hermes profile yet.
  echo Run setup.cmd in this folder first and complete the Company OS setup.
  echo Your existing Hermes profile will not be changed.
  pause
  exit /b 2
)

set "HERMES_HOME=%COMPANY_OS_PROFILE_HOME%"
"%HERMES_PYTHON%" "%~dp0setup.py" discord configure --profile-home "%COMPANY_OS_PROFILE_HOME%"
set "COMPANY_OS_EXIT=%ERRORLEVEL%"
pause
exit /b %COMPANY_OS_EXIT%
