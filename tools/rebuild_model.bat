@echo off
cd /d "%~dp0.."
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\compile_an8.py models\baldi_source.an8 model-data.js
) else (
  python tools\compile_an8.py models\baldi_source.an8 model-data.js
)
echo.
echo model-data.js yeniden olusturuldu.
pause
