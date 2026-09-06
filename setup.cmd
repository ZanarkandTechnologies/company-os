@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Company OS Setup
set "HERMES_ROOT=%LOCALAPPDATA%\hermes"
if not exist "%HERMES_ROOT%\hermes-agent\venv\Scripts\python.exe" set "HERMES_ROOT=%USERPROFILE%\.hermes"
set "COMPANY_OS_PROFILE_HOME=%HERMES_ROOT%\profiles\company-os"
set "HERMES_PYTHON=%HERMES_ROOT%\hermes-agent\venv\Scripts\python.exe"
set "HERMES_CLI=%HERMES_ROOT%\hermes-agent\venv\Scripts\hermes.exe"
set "PATH=%HERMES_ROOT%\hermes-agent\venv\Scripts;%PATH%"

:preflight
cls
echo Company OS Setup
echo Checking host Hermes and Docker Desktop...
if not exist "%HERMES_CLI%" goto hermes_missing
if not exist "%HERMES_PYTHON%" goto hermes_python_missing
where docker >nul 2>nul
if errorlevel 1 goto docker_missing
docker info >nul 2>nul
if errorlevel 1 goto docker_stopped
docker compose version >nul 2>nul
if errorlevel 1 goto compose_missing

echo Opening the guided setup in your Windows Hermes profile...
call :run_setup launch
set "COMPANY_OS_ACTION=%ERRORLEVEL%"
if "%COMPANY_OS_ACTION%"=="0" exit /b 0
if "%COMPANY_OS_ACTION%"=="10" goto full_proof
if "%COMPANY_OS_ACTION%"=="11" goto static_verify
if "%COMPANY_OS_ACTION%"=="12" goto live_verify
if "%COMPANY_OS_ACTION%"=="13" goto dashboard
if "%COMPANY_OS_ACTION%"=="14" goto certify
if "%COMPANY_OS_ACTION%"=="15" goto preflight_check
if "%COMPANY_OS_ACTION%"=="16" goto eval_check
if "%COMPANY_OS_ACTION%"=="17" goto dossier
if "%COMPANY_OS_ACTION%"=="130" goto cancelled
goto failed

:run_setup
set "HERMES_HOME=%COMPANY_OS_PROFILE_HOME%"
"%HERMES_PYTHON%" "%~dp0setup.py" %*
exit /b %ERRORLEVEL%

:start_runtime
echo Starting the host Hermes gateway...
set "HERMES_HOME=%COMPANY_OS_PROFILE_HOME%"
call :selected_gateway_running
if not errorlevel 1 exit /b 0
start "Company OS Hermes Gateway" /min cmd /c "set HERMES_HOME=%COMPANY_OS_PROFILE_HOME%&& hermes gateway run"
timeout /t 3 /nobreak >nul
call :selected_gateway_running
if not errorlevel 1 exit /b 0
echo The selected Hermes profile gateway did not become ready:
echo %COMPANY_OS_PROFILE_HOME%
echo A gateway running for another profile is not accepted.
exit /b 1

:selected_gateway_running
hermes gateway status 2>&1 | findstr /c:"Gateway is running (PID:" >nul
exit /b %ERRORLEVEL%

:start_webhook_if_enabled
call :run_setup webhook-enabled >nul 2>nul
if errorlevel 1 exit /b 0
echo Starting secure webhook ingress...
docker compose --profile webhook up -d --force-recreate ngrok
if errorlevel 1 goto webhook_rollback
call :run_setup webhook-ingress-ready --wait 30
if errorlevel 1 (
  echo The assigned endpoint did not become reachable from the public internet.
  docker compose --profile webhook logs --no-color --tail 20 ngrok
  goto webhook_rollback
)
docker compose --profile webhook ps --status running --services ngrok | findstr /x /c:"ngrok" >nul
if errorlevel 1 goto webhook_rollback
call :run_setup webhook-commit
if errorlevel 1 goto webhook_rollback
exit /b 0

:webhook_rollback
call :run_setup webhook-rollback
docker compose --profile webhook stop ngrok >nul 2>nul
exit /b 1

:live_verify
call :start_runtime
if errorlevel 1 goto failed
call :start_webhook_if_enabled
if errorlevel 1 goto failed
echo Running the full health and webhook check...
call :run_setup verify --live
set "VERIFY_EXIT=%ERRORLEVEL%"
goto verification_result

:full_proof
call :start_runtime
if errorlevel 1 goto failed
call :start_webhook_if_enabled
if errorlevel 1 goto failed
echo Running the installation and webhook check...
call :run_setup verify --live
if errorlevel 1 goto failed
echo Checking whether configured company data is ready...
call :run_setup doctor preflight
if errorlevel 1 goto failed
echo Running the complete isolated PM evaluation...
call :run_setup doctor eval --open
if errorlevel 1 goto failed
echo Activating the verified Daily and Weekly schedules...
call :run_setup doctor activate
set "VERIFY_EXIT=%ERRORLEVEL%"
goto verification_result

:static_verify
call :start_runtime
if errorlevel 1 goto failed
call :run_setup verify
set "VERIFY_EXIT=%ERRORLEVEL%"
goto verification_result

:dashboard
call :start_runtime
if errorlevel 1 goto failed
set "HERMES_HOME=%COMPANY_OS_PROFILE_HOME%"
start "Company OS Dashboard" /min "%HERMES_PYTHON%" "%COMPANY_OS_PROFILE_HOME%\apps\installer\dashboard.py"
start "" "http://localhost:9119"
exit /b 0

:certify
call :run_setup certify
exit /b %ERRORLEVEL%

:preflight_check
call :run_setup doctor preflight
exit /b %ERRORLEVEL%

:eval_check
call :run_setup doctor eval --open
exit /b %ERRORLEVEL%

:dossier
call :run_setup doctor open
exit /b %ERRORLEVEL%

:verification_result
if "%VERIFY_EXIT%"=="0" (
  echo Company OS is ready. Dashboard: http://localhost:9119
) else (
  echo Company OS needs attention. Complete the failed check and rerun setup.cmd.
)
pause
exit /b %VERIFY_EXIT%

:hermes_missing
echo Hermes must be installed on Windows before Company OS setup.
pause
exit /b 2
:hermes_python_missing
echo Hermes was found, but its bundled Python runtime is missing at:
echo %HERMES_PYTHON%
pause
exit /b 2
:docker_missing
echo Docker Desktop is required for the Hermes terminal backend and ngrok.
pause
exit /b 2
:docker_stopped
echo Docker Desktop is installed but is not ready. Start it and retry.
pause
exit /b 2
:compose_missing
echo Docker Compose is unavailable. Update Docker Desktop and retry.
pause
exit /b 2
:cancelled
echo Setup stopped safely. Existing host Hermes configuration was preserved.
pause
exit /b 0
:failed
echo Setup stopped safely. Existing host Hermes profile data was preserved.
pause
exit /b 2
