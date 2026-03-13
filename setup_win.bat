@echo off
REM === SwiGi — Setup ===
REM Spust z Downloads slozky kde mas vsechno.

echo === SwiGi Setup ===
echo.

REM Vytvor slozku
mkdir "%USERPROFILE%\SwiGi" 2>nul

REM Zkopiruj Python
if exist "%~dp0python-3\python.exe" (
    xcopy /E /I /Y "%~dp0python-3" "%USERPROFILE%\SwiGi\python"
    echo [OK] Python zkopirovan
) else (
    echo [CHYBA] Slozka python-3 s python.exe nenalezena v %~dp0
    pause
    exit /b 1
)

REM Zkopiruj hidapi.dll
if exist "%~dp0hidapi.dll" (
    copy /Y "%~dp0hidapi.dll" "%USERPROFILE%\SwiGi\"
    copy /Y "%~dp0hidapi.dll" "%USERPROFILE%\SwiGi\python\"
    echo [OK] hidapi.dll zkopirovan
) else if exist "%~dp0x64\hidapi.dll" (
    copy /Y "%~dp0x64\hidapi.dll" "%USERPROFILE%\SwiGi\"
    copy /Y "%~dp0x64\hidapi.dll" "%USERPROFILE%\SwiGi\python\"
    echo [OK] hidapi.dll zkopirovan z x64\
) else (
    echo [CHYBA] hidapi.dll nenalezen v %~dp0
    pause
    exit /b 1
)

REM Zkopiruj daemon
if exist "%~dp0swigi.py" (
    copy /Y "%~dp0swigi.py" "%USERPROFILE%\SwiGi\"
    echo [OK] swigi.py zkopirovan
) else (
    echo [CHYBA] swigi.py nenalezen v %~dp0
    pause
    exit /b 1
)

REM Vytvor start.bat
(
echo @echo off
echo echo === SwiGi ===
echo echo Cekam na Easy-Switch...
echo echo Ctrl+C pro ukonceni.
echo echo.
echo "%%~dp0python\python.exe" "%%~dp0swigi.py"
echo pause
) > "%USERPROFILE%\SwiGi\start.bat"
echo [OK] start.bat vytvoren

REM Vytvor start_verbose.bat
(
echo @echo off
echo echo === SwiGi [verbose] ===
echo echo.
echo "%%~dp0python\python.exe" "%%~dp0swigi.py" -v
echo pause
) > "%USERPROFILE%\SwiGi\start_verbose.bat"
echo [OK] start_verbose.bat vytvoren

echo.
echo === HOTOVO ===
echo.
echo Slozka: %USERPROFILE%\SwiGi\
echo.
echo Spusteni: otevri %USERPROFILE%\SwiGi\ a dvojklikni start.bat
echo.
echo Autostart: ve Startup slozce vytvor zastupce na:
echo   %USERPROFILE%\SwiGi\python\pythonw.exe %USERPROFILE%\SwiGi\swigi.py
echo.
echo Otviram slozku...
explorer "%USERPROFILE%\SwiGi"
pause
