@echo off
setlocal
set APP_NAME=4K-Video-Converter
set MAIN=main.py

REM Ensure venv Python is used if available
if exist .venv\Scripts\python.exe (
  set PYTHON=.venv\Scripts\python.exe
) else (
  set PYTHON=python
)

%PYTHON% -m pip install --upgrade pip >nul 2>&1
%PYTHON% -m pip install -r requirements.txt || exit /b 1
%PYTHON% -m pip install pyinstaller || exit /b 1

REM Clean previous build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build one-file exe, include ffmpeg.exe and settings.json if present
set ADDDATA=
if exist bin\ffmpeg.exe set ADDDATA=--add-data "bin\ffmpeg.exe;bin"
if exist settings.json set ADDDATA=%ADDDATA% --add-data "settings.json;."

%PYTHON% -m PyInstaller --noconfirm --clean --windowed --name "%APP_NAME%" %ADDDATA% %MAIN% || exit /b 1

echo.
echo Build finished. EXE is in dist\%APP_NAME%\%APP_NAME%.exe
endlocal
