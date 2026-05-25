@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM ============================================================
REM run_eval.bat - one-click batch eval for Open-AutoGLM phone_agent
REM Windows cmd + conda "phone-agent" environment
REM
REM Usage:
REM     set PHONE_AGENT_API_KEY=your_zhipu_key
REM     run_eval.bat [lang] [exp] [task_ids]
REM         lang     : cn | en | all     (default cn)
REM         exp      : experiment name   (default full112_<lang>)
REM         task_ids : e.g. 99-112       (default 51-112, skip first 50 originals)
REM
REM Examples:
REM     run_eval.bat cn
REM     run_eval.bat all full112_ext
REM     run_eval.bat all full112_full 1-112
REM     run_eval.bat cn smoke 99-112
REM
REM Optional env vars: PHONE_AGENT_DEVICE_ID, MAX_STEPS (def 50), REPEATS (def 2)
REM ============================================================

set "LANG_FILTER=%~1"
if "%LANG_FILTER%"=="" set "LANG_FILTER=cn"
set "EXP=%~2"
if "%EXP%"=="" set "EXP=full112_%LANG_FILTER%"
set "TASK_IDS=%~3"
if "%TASK_IDS%"=="" set "TASK_IDS=51-112"
if "%MAX_STEPS%"=="" set "MAX_STEPS=50"
if "%REPEATS%"=="" set "REPEATS=2"

REM --- locate repo root = two levels up from this .bat ---
pushd "%~dp0..\.."
set "REPO_ROOT=%CD%"
popd
cd /d "%REPO_ROOT%"
set "RB=Mobile-Agent-E\instr_rewrite"
set "BENCH=app-data\Ins-bench\Vague-ins-full-112.json"
set "LOGROOT=app-data\Ins-bench\phoneagent_logs"

REM --- activate conda env (change name here if yours differs) ---
call conda activate phone-agent

echo ================ pre-check ================
where adb >nul 2>nul
if errorlevel 1 ( echo [X] adb not found in PATH. Install platform-tools first. & exit /b 1 )
echo [OK] adb found
adb devices
if "%PHONE_AGENT_API_KEY%"=="" ( echo [i] PHONE_AGENT_API_KEY not set - will use built-in key from main.py ) else ( echo [OK] PHONE_AGENT_API_KEY is set )
echo bench=%BENCH%  lang=%LANG_FILTER%  exp=%EXP%  task_ids=%TASK_IDS%  levels=L1,L3 x%REPEATS%  max_steps=%MAX_STEPS%

echo.
echo ================ dry-run plan ================
python "%RB%\run_phoneagent_batch.py" --bench "%BENCH%" --levels L1,L3 --repeats %REPEATS% --lang-filter %LANG_FILTER% --exp %EXP% --task-ids %TASK_IDS% --dry-run
if errorlevel 1 ( echo dry-run failed & exit /b 1 )

echo.
set /p ans=Confirm and run? [y/N]
if /i not "%ans%"=="y" ( echo cancelled. & exit /b 0 )

echo.
echo ================ running (resume: re-run same exp to continue) ================
python "%RB%\run_phoneagent_batch.py" --bench "%BENCH%" --levels L1,L3 --repeats %REPEATS% --lang-filter %LANG_FILTER% --exp %EXP% --task-ids %TASK_IDS% --max-steps %MAX_STEPS%

echo.
echo ================ metrics ================
python "%RB%\analyze_phoneagent_logs.py" --exp-dir "%LOGROOT%\%EXP%"

echo.
echo Done. Per-run detail / manual labeling: %LOGROOT%\%EXP%\runs.csv
echo After labeling manual_correct, recompute true success rate:
echo   python %RB%\analyze_phoneagent_logs.py --exp-dir %LOGROOT%\%EXP% --use-manual
endlocal
