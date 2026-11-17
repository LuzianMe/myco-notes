@echo off
REM search: Windows launcher for notes_search.py
where python >nul 2>nul
if %errorlevel%==0 (python -B "%~dp0notes_search.py" %*) else (py -3 -B "%~dp0notes_search.py" %*)
exit /b %errorlevel%
