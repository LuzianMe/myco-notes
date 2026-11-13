@echo off
REM ingest: Windows launcher for notes_ingest.py
where python >nul 2>nul
if %errorlevel%==0 (python -B "%~dp0notes_ingest.py" %*) else (py -3 -B "%~dp0notes_ingest.py" %*)
exit /b %errorlevel%
