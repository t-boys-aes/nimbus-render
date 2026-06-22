@echo off
cd /d "%~dp0"
echo ================================================== >> pipeline_run.log
echo STARTING PIPELINE RUN: %date% %time% >> pipeline_run.log
echo ================================================== >> pipeline_run.log

:: Activate virtual environment and run orchestrator
call .\venv\Scripts\activate.bat
python main.py >> pipeline_run.log 2>&1

echo COMPLETED PIPELINE RUN: %date% %time% >> pipeline_run.log
echo ================================================== >> pipeline_run.log
