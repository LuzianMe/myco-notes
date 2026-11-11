@echo off
REM capture: Windows launcher for capture.py
where python >nul 2>nul
if %errorlevel%==0 (python -B "%~dp0capture.py" %*) else (py -3 -B "%~dp0capture.py" %*)
exit /b %errorlevel%
