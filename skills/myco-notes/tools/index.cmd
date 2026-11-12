@echo off
REM index: Windows launcher for notes_index.py
where python >nul 2>nul
if %errorlevel%==0 (python -B "%~dp0notes_index.py" %*) else (py -3 -B "%~dp0notes_index.py" %*)
exit /b %errorlevel%
