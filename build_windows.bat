@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "VERSION=2.0.0"
REM Use one explicit interpreter for the downloader, build venv and bundle
REM verification. The unqualified Windows 'py' launcher may select a different
REM installation than actions/setup-python (observed Python 3.15 vs 3.13).
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH. Install Python 3.12 or 3.13.
  exit /b 1
)
python -c "import sys; assert (3, 12) <= sys.version_info[:2] < (3, 14), 'Use Python 3.12 or 3.13'"
if errorlevel 1 exit /b 1
python fetch_mgba_core.py
if errorlevel 1 exit /b 1
python -m venv .build-venv
if errorlevel 1 exit /b 1
.build-venv\Scripts\python.exe -m pip install --upgrade pip==26.3
if errorlevel 1 exit /b 1
.build-venv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
REM Optional, hash-locked custom camera-only OpenCV wheel with FFmpeg disabled.
if defined AP_CUSTOM_OPENCV_WHEEL (
  if not defined AP_CUSTOM_OPENCV_SHA256 (
    echo AP_CUSTOM_OPENCV_SHA256 must be set with the custom wheel
    exit /b 1
  )
  python tools\verify_custom_opencv_wheel.py "%AP_CUSTOM_OPENCV_WHEEL%" "%AP_CUSTOM_OPENCV_SHA256%" windows-x86_64
  if errorlevel 1 exit /b 1
  .build-venv\Scripts\python.exe -m pip install --force-reinstall --no-deps "%AP_CUSTOM_OPENCV_WHEEL%"
  if errorlevel 1 exit /b 1
  set "AP_REQUIRE_OPENCV_FFMPEG_OFF=1"
)
.build-venv\Scripts\python.exe tools/check_opencv_build.py
if errorlevel 1 exit /b 1
.build-venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name AnythingPlays --icon assets\anything_plays.ico --add-data "assets\anything_plays.png;assets" --collect-all cv2 --collect-all PIL app.py
if errorlevel 1 exit /b 1
if not exist dist\AnythingPlays\cores mkdir dist\AnythingPlays\cores
for %%C in (mgba snes9x) do (
  if not exist "cores\%%C_libretro.dll" (echo Missing required core %%C & exit /b 1)
  copy /Y "cores\%%C_libretro.dll" "dist\AnythingPlays\cores\" >nul
  if errorlevel 1 exit /b 1
)
copy /Y "cores\CORE_PROVENANCE.json" "dist\AnythingPlays\cores\" >nul
if errorlevel 1 exit /b 1
REM Include project and third-party licensing documentation.
if not exist dist\AnythingPlays\licenses mkdir dist\AnythingPlays\licenses
copy /Y LICENSE dist\AnythingPlays\licenses\AnythingPlays-MIT.txt >nul
if errorlevel 1 exit /b 1
copy /Y CODE_OF_CONDUCT.md dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
copy /Y docs\THIRD_PARTY_NOTICES.md dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
copy /Y docs\THIRD_PARTY_COMPONENTS.md dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
copy /Y licenses\*.txt dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
.build-venv\Scripts\python.exe tools\collect_python_notices.py dist\AnythingPlays\licenses
if errorlevel 1 exit /b 1

python verify_bundle.py --check-native windows dist\AnythingPlays
if errorlevel 1 exit /b 1
if not exist release mkdir release
set "ISCC="
for %%P in ("%ProgramFiles%\Inno Setup 7\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do if exist "%%~P" set "ISCC=%%~P"
if not defined ISCC (
  where ISCC.exe >nul 2>nul
  if not errorlevel 1 set "ISCC=ISCC.exe"
)
if not defined ISCC (
  echo.
  echo The application was built, but a setup EXE requires Inno Setup 6 or 7.
  echo Install Inno Setup from https://jrsoftware.org/isinfo.php
  echo Then run build_windows.bat again.
  echo App folder: dist\AnythingPlays
  exit /b 2
)
"%ISCC%" /DAppVersion=%VERSION% installer.iss
if errorlevel 1 exit /b 1
echo.
echo SUCCESS: release\AnythingPlaysSetup-%VERSION%.exe
exit /b 0
