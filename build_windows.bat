@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "VERSION=2.0.0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher 'py' was not found. Install Python for Windows first.
  exit /b 1
)
py fetch_mgba_core.py
if errorlevel 1 exit /b 1
py -m venv .build-venv
if errorlevel 1 exit /b 1
.build-venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1
.build-venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1
.build-venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name AnythingPlays --icon assets\anything_plays.ico --add-data "assets\anything_plays.png;assets" --collect-all cv2 --collect-all PIL app.py
if errorlevel 1 exit /b 1
if not exist dist\AnythingPlays\cores mkdir dist\AnythingPlays\cores
for %%C in (gambatte mgba snes9x) do (
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
copy /Y THIRD_PARTY_NOTICES.md dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
copy /Y THIRD_PARTY_COMPONENTS.md dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
copy /Y licenses\*.txt dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1

py verify_bundle.py windows dist\AnythingPlays
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
