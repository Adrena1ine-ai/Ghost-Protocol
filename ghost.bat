@echo off
REM Ghost Protocol - Quick launcher
REM Usage: ghost.bat [path_to_project]
REM If no path provided, runs in current directory

if "%~1"=="" (
    REM No arguments - run in current directory
    python "%~dp0main.py"
) else (
    REM Argument provided - change to that directory and run
    pushd "%~1"
    python "%~dp0main.py"
    popd
)


