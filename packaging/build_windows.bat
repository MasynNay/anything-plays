@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
set "VERSION=3.0.0-alpha.1"
REM Stable 3.0 production is a separate fail-closed release mode.
REM Never publish the preview identity with a stable filename.
if "%AP_V30_APPROVED_RELEASE%"=="1" (
  if not "%AP_RELEASE_BUILD%"=="1" (
    echo Production 3.0 requires AP_RELEASE_BUILD=1
    exit /b 1
  )
  if not defined AP_CORE_ARCHIVE_DIR (
    echo Production 3.0 needs immutable AP_CORE_ARCHIVE_DIR
    exit /b 1
  )
  python tools\check_v30_release.py
  if errorlevel 1 exit /b 1
  python -c "from tools.v30_release_lock import load_approved_lock; load_approved_lock()"
  if errorlevel 1 exit /b 1
  set "VERSION=3.0.0"
)
REM Build source-verified private 3.0.0 installer IDENTITIES, not an approved
REM release. No build can turn the source/redistribution review flags true.
if "%AP_V30_STABLE_CANDIDATE%"=="1" (
  if "%AP_RELEASE_BUILD%"=="1" exit /b 1
  if "%AP_V30_APPROVED_RELEASE%"=="1" exit /b 1
  if not "%AP_V30_TEST_CORES%"=="1" exit /b 1
  if not "%AP_V30_GPL_TRIAL%"=="1" exit /b 1
  if not "%AP_V30_TIA_TRIAL%"=="1" exit /b 1
  set "VERSION=3.0.0"
)
REM 3.1 Preview 1 is an isolated, owner-review test build, never a release.
if "%AP_V31_PREVIEW%"=="1" (
  if "%AP_RELEASE_BUILD%"=="1" exit /b 1
  if "%AP_V30_APPROVED_RELEASE%"=="1" exit /b 1
  if "%AP_V30_STABLE_CANDIDATE%"=="1" exit /b 1
  if not "%AP_V30_MINIMAL_CORE_BUILD%"=="1" exit /b 1
  set "VERSION=3.1.0-preview1"
)
REM Independent source-built RC1 application stage: still mGBA only,
REM never a stable installer or a replacement for the public 3.0.
if "%AP_V31_RC%"=="1" (
  if "%AP_V31_PREVIEW%"=="1" exit /b 1
  if "%AP_RELEASE_BUILD%"=="1" exit /b 1
  if "%AP_V30_APPROVED_RELEASE%"=="1" exit /b 1
  if "%AP_V30_STABLE_CANDIDATE%"=="1" exit /b 1
  if not "%AP_V30_MINIMAL_CORE_BUILD%"=="1" exit /b 1
  set "VERSION=3.1.0-rc1"
)
REM Independent RC2 owner-QA stage, never the public RC1 installer.
if "%AP_V31_RC2%"=="1" (
  if "%AP_V31_RC%"=="1" exit /b 1
  if "%AP_V31_PREVIEW%"=="1" exit /b 1
  if "%AP_RELEASE_BUILD%"=="1" exit /b 1
  if "%AP_V30_APPROVED_RELEASE%"=="1" exit /b 1
  if "%AP_V30_STABLE_CANDIDATE%"=="1" exit /b 1
  if not "%AP_V30_MINIMAL_CORE_BUILD%"=="1" exit /b 1
  set "VERSION=3.1.0-rc2"
)
REM Both CI preview and fully approved 3.0 builds include all 11 cores.
REM A 3.0 approval flag is rejected by fetch_mgba_core.py until its lock passes.
set "AP_FULL_CORE_BUILD=0"
if "%AP_V30_TEST_CORES%"=="1" set "AP_FULL_CORE_BUILD=1"
if "%AP_V30_APPROVED_RELEASE%"=="1" set "AP_FULL_CORE_BUILD=1"
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
REM The corrected 3.0 preview icon is built independently from stable 2.0 artwork.
.build-venv\Scripts\python.exe tools\render_v21_icon.py
if errorlevel 1 exit /b 1
set "V31_IDENTITY_ARG="
if "%AP_V31_PREVIEW%"=="1" set "V31_IDENTITY_ARG=--add-data build\v31_build_identity.json;assets"
if "%AP_V31_RC%"=="1" set "V31_IDENTITY_ARG=--add-data build\v31_build_identity.json;assets"
if "%AP_V31_RC2%"=="1" set "V31_IDENTITY_ARG=--add-data build\v31_build_identity.json;assets"
if defined V31_IDENTITY_ARG (
  .build-venv\Scripts\python.exe -m tools.write_v31_identity build\v31_build_identity.json
  if errorlevel 1 exit /b 1
)
if errorlevel 1 exit /b 1
.build-venv\Scripts\python.exe -m PyInstaller --collect-all pygame --collect-all glcontext --noconfirm --clean --onedir --windowed --name AnythingPlays %V31_IDENTITY_ARG% --icon build\v21-icon\anything_plays.ico --add-data "assets\anything_plays.png;assets" --add-data "assets\anything_plays_v21.webp;assets" --collect-all cv2 --collect-all PIL app.py
if errorlevel 1 exit /b 1
if not exist dist\AnythingPlays\cores mkdir dist\AnythingPlays\cores
set "CORE_LIST=mgba snes9x"
if "%AP_V30_MINIMAL_CORE_BUILD%"=="1" (
  set "CORE_LIST=mgba"
) else (
  if "%AP_FULL_CORE_BUILD%"=="1" set "CORE_LIST=mgba snes9x fceumm genesis_plus_gx parallel_n64 dolphin stella2014 prosystem mednafen_pce_fast mednafen_ngp mednafen_wswan"
)
REM The only alternate 3.0 test lane is explicitly unapproved and
REM preserves all 11 native core slots with source-authentic core names.
if "%AP_V30_GPL_TRIAL%"=="1" (
  if not "%AP_V30_TEST_CORES%"=="1" exit /b 1
  if "%AP_RELEASE_BUILD%"=="1" exit /b 1
  if "%AP_V30_APPROVED_RELEASE%"=="1" exit /b 1
  set "CORE_LIST=mgba mednafen_supafaust fceumm blastem parallel_n64 dolphin stella2014 prosystem mednafen_pce_fast mednafen_ngp mednafen_wswan"
  if "%AP_V30_TIA_TRIAL%"=="1" set "CORE_LIST=mgba mednafen_supafaust fceumm blastem parallel_n64 dolphin tia prosystem mednafen_pce_fast mednafen_ngp mednafen_wswan"
)
REM An ACTUALLY APPROVED production build must take its names from the
REM independently reviewed 11-core lock, not the original NC hardcoded list.
if "%AP_V30_APPROVED_RELEASE%"=="1" (
  set "CORE_LIST="
  for /f "usebackq delims=" %%L in (`python -m tools.v30_release_lock --print-approved-core-names`) do set "CORE_LIST=%%L"
  if not defined CORE_LIST exit /b 1
)
for %%C in (%CORE_LIST%) do (
  if not exist "cores\%%C_libretro.dll" (echo Missing required core %%C & exit /b 1)
  copy /Y "cores\%%C_libretro.dll" "dist\AnythingPlays\cores\" >nul
  if errorlevel 1 exit /b 1
)
copy /Y "cores\CORE_PROVENANCE.json" "dist\AnythingPlays\cores\" >nul
if errorlevel 1 exit /b 1
if "%AP_V30_APPROVED_RELEASE%"=="1" if exist "cores\V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json" (
  copy /Y "cores\V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json" "dist\AnythingPlays\cores\" >nul
  if errorlevel 1 exit /b 1
  copy /Y "cores\libwinpthread-1.dll" "dist\AnythingPlays\cores\" >nul
  if errorlevel 1 exit /b 1
)
if "%AP_V30_GPL_TRIAL%"=="1" (
  copy /Y "cores\V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json" "dist\AnythingPlays\cores\" >nul
  if errorlevel 1 exit /b 1
  REM The source-built Windows research cores link libwinpthread; bundle the
  REM exact original SHA-verified DLL rather than assuming MSYS2 is installed.
  copy /Y "cores\libwinpthread-1.dll" "dist\AnythingPlays\cores\" >nul
  if errorlevel 1 exit /b 1
)
if "%AP_FULL_CORE_BUILD%"=="1" (
  if not exist "cores\dolphin-emu\Sys\codehandler.bin" (
    echo Missing bundled Dolphin Sys resources
    exit /b 1
  )
  xcopy /E /I /Y "cores\dolphin-emu" "dist\AnythingPlays\cores\dolphin-emu" >nul
  if errorlevel 1 exit /b 1
  copy /Y "cores\DOLPHIN_SYS_PROVENANCE.json" "dist\AnythingPlays\cores\" >nul
  if errorlevel 1 exit /b 1
)
REM Include project and third-party licensing documentation.
if not exist dist\AnythingPlays\licenses mkdir dist\AnythingPlays\licenses
copy /Y LICENSE dist\AnythingPlays\licenses\AnythingPlays-MIT.txt >nul
if errorlevel 1 exit /b 1
copy /Y .github\CODE_OF_CONDUCT.md dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
copy /Y docs\THIRD_PARTY_NOTICES.md dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
copy /Y docs\THIRD_PARTY_COMPONENTS.md dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
copy /Y licenses\*.txt dist\AnythingPlays\licenses\ >nul
if errorlevel 1 exit /b 1
if defined AP_CORE_ARCHIVE_DIR if exist "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-DOLPHIN-ORIGINAL-COPYING.txt" (
  for %%N in (COPYING GPL2-OR-LATER BSD3 CC0 MIT) do (
    copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-DOLPHIN-ORIGINAL-%%N.txt" "dist\AnythingPlays\licenses\" >nul
    if errorlevel 1 exit /b 1
  )
)
if "%AP_V30_GPL_TRIAL%"=="1" (
  copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-Supafaust-COPYING.txt" "dist\AnythingPlays\licenses\" >nul
  if errorlevel 1 exit /b 1
  copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-BlastEm-COPYING.txt" "dist\AnythingPlays\licenses\" >nul
  if errorlevel 1 exit /b 1
  if "%AP_V30_PINNED_PCE%"=="1" (
    copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-PCE-COPYING.txt" "dist\AnythingPlays\licenses\" >nul
    if errorlevel 1 exit /b 1
  )
  if "%AP_V30_PINNED_N64%"=="1" (
    for %%I in (01 02 03 04 05 06 07 08 09 10 11) do (
      copy /Y "%AP_CORE_ARCHIVE_DIR%\\GPL-TRIAL-N64-NOTICE-%%I.txt" "dist\\AnythingPlays\\licenses\\" >nul
      if errorlevel 1 exit /b 1
    )
  )
  if "%AP_V30_PINNED_MGBA%"=="1" (
    copy /Y "%AP_CORE_ARCHIVE_DIR%\\MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt" "dist\\AnythingPlays\\licenses\\" >nul
    if errorlevel 1 exit /b 1
  )
  if "%AP_V30_PINNED_FIVE%"=="1" (
    if "%AP_V30_TIA_TRIAL%"=="1" (
      for %%C in (fceumm tia prosystem mednafen_ngp mednafen_wswan) do (
        copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-%%C-ORIGINAL-COPYING.txt" "dist\AnythingPlays\licenses\" >nul
        if errorlevel 1 exit /b 1
      )
      copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-tia-ORIGINAL-SPDX.txt" "dist\AnythingPlays\licenses\" >nul
      if errorlevel 1 exit /b 1
    ) else (
    for %%C in (fceumm stella2014 prosystem mednafen_ngp mednafen_wswan) do (
      copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-%%C-ORIGINAL-COPYING.txt" "dist\AnythingPlays\licenses\" >nul
      if errorlevel 1 exit /b 1
    )
    )
  )
)
if "%AP_V30_APPROVED_RELEASE%"=="1" if exist "cores\V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json" (
  copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-Supafaust-COPYING.txt" "dist\AnythingPlays\licenses\Supafaust-COPYING.txt" >nul
  if errorlevel 1 exit /b 1
  copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-BlastEm-COPYING.txt" "dist\AnythingPlays\licenses\BlastEm-COPYING.txt" >nul
  if errorlevel 1 exit /b 1
  copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-PCE-COPYING.txt" "dist\AnythingPlays\licenses\PCE-COPYING.txt" >nul
  if errorlevel 1 exit /b 1
  if "%AP_V30_APPROVED_EIGHT%"=="1" (
    for %%C in (fceumm prosystem mednafen_ngp mednafen_wswan) do (
      copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-%%C-ORIGINAL-COPYING.txt" "dist\AnythingPlays\licenses\" >nul
      if errorlevel 1 exit /b 1
    )
    REM The immutable approved core map selects Tia in the one Atari2600 slot.
    if exist "cores\tia_libretro.dll" (
      copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-tia-ORIGINAL-COPYING.txt" "dist\AnythingPlays\licenses\" >nul
      if errorlevel 1 exit /b 1
      copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-tia-ORIGINAL-SPDX.txt" "dist\AnythingPlays\licenses\" >nul
      if errorlevel 1 exit /b 1
    ) else (
      copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-stella2014-ORIGINAL-COPYING.txt" "dist\AnythingPlays\licenses\" >nul
      if errorlevel 1 exit /b 1
    )
  )
  if "%AP_V30_APPROVED_TEN%"=="1" (
    copy /Y "%AP_CORE_ARCHIVE_DIR%\MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt" "dist\AnythingPlays\licenses\" >nul
    if errorlevel 1 exit /b 1
    for %%I in (01 02 03 04 05 06 07 08 09 10 11) do (
      copy /Y "%AP_CORE_ARCHIVE_DIR%\GPL-TRIAL-N64-NOTICE-%%I.txt" "dist\AnythingPlays\licenses\" >nul
      if errorlevel 1 exit /b 1
    )
  )
)
.build-venv\Scripts\python.exe tools\collect_python_notices.py dist\AnythingPlays\licenses
if errorlevel 1 exit /b 1

python verify_bundle.py --check-native windows dist\AnythingPlays
if errorlevel 1 exit /b 1
if "%AP_FULL_CORE_BUILD%"=="1" (
  .build-venv\Scripts\python.exe tools\probe_embedded_3d.py windows dist\AnythingPlays
  if errorlevel 1 exit /b 1
)
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
if "%AP_V31_RC2%"=="1" (
  "%ISCC%" /DV31RC2Build=1 /DAppVersion=%VERSION% packaging\installer.iss
) else if "%AP_V31_RC%"=="1" (
  "%ISCC%" /DV31RCBuild=1 /DAppVersion=%VERSION% packaging\installer.iss
) else if "%AP_V31_PREVIEW%"=="1" (
  "%ISCC%" /DV31PreviewBuild=1 /DAppVersion=%VERSION% packaging\installer.iss
) else if "%AP_V30_APPROVED_RELEASE%"=="1" (
  "%ISCC%" /DProductionBuild=1 /DAppVersion=%VERSION% packaging\installer.iss
) else if "%AP_V30_STABLE_CANDIDATE%"=="1" (
  "%ISCC%" /DProductionBuild=1 /DAppVersion=%VERSION% packaging\installer.iss
) else (
  "%ISCC%" /DAppVersion=%VERSION% packaging\installer.iss
)
if errorlevel 1 exit /b 1
echo.
echo SUCCESS: release\AnythingPlaysSetup-%VERSION%.exe
exit /b 0
