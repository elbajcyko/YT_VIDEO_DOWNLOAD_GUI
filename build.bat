@echo off
setlocal
set APP_NAME=YT_VIDEO_DOWNLOAD_GUI
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

REM Ensure local FFmpeg (download if missing)
if not exist bin\ffmpeg.exe (
  echo FFmpeg not found. Downloading...
  if not exist bin mkdir bin
  powershell -NoProfile -Command ^
    "$url='https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip';" ^
    "$zip='ffmpeg.zip';" ^
    "Invoke-WebRequest -Uri $url -OutFile $zip;" ^
    "Expand-Archive -Path $zip -DestinationPath ffmpeg_tmp -Force;" ^
    "$exe=Get-ChildItem -Recurse -Path ffmpeg_tmp -Filter ffmpeg.exe | Select-Object -First 1;" ^
    "Copy-Item $exe.FullName -Destination 'bin\\ffmpeg.exe' -Force;"
)

REM Build onedir EXE, include ffmpeg.exe and settings.json if present
set ADDDATA=
if exist bin\ffmpeg.exe set ADDDATA=--add-data "bin\ffmpeg.exe;bin"
if exist settings.json set ADDDATA=%ADDDATA% --add-data "settings.json;."

%PYTHON% -m PyInstaller --noconfirm --clean --windowed --name "%APP_NAME%" %ADDDATA% %MAIN% || exit /b 1

REM Create default videos folder in output
if not exist dist\%APP_NAME%\videos mkdir dist\%APP_NAME%\videos

echo.
echo Build finished. EXE is in dist\%APP_NAME%\%APP_NAME%.exe
endlocal
