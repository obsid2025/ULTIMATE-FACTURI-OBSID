@echo off
REM Ultimate FACTURI - Launcher
REM Acest script pornește aplicația Ultimate FACTURI

echo.
echo ====================================
echo    ULTIMATE FACTURI - PORNIRE
echo ====================================
echo.

REM Schimbă directorul curent la locația scriptului
cd /d "%~dp0"

REM Verifică dacă există mediul virtual Python
if exist ".venv\Scripts\activate.bat" (
    echo Activez mediul virtual Python...
    call .venv\Scripts\activate.bat
    echo Mediu virtual activat.
    echo.
) else (
    echo Mediul virtual nu a fost găsit. Se încearcă rularea cu Python global...
    echo.
)

REM Verifică dacă fișierul principal există
if not exist "grupare facturi.py" (
    echo EROARE: Fișierul "grupare facturi.py" nu a fost găsit!
    echo Verifică că toate fișierele sunt în locația corectă.
    pause
    exit /b 1
)

echo Pornesc Ultimate FACTURI...
echo.

REM Rulează aplicația Python
python "grupare facturi.py"

REM Verifică codul de ieșire
if %ERRORLEVEL% neq 0 (
    echo.
    echo EROARE: Aplicația s-a închis cu erori (cod: %ERRORLEVEL%)
    echo.
    pause
) else (
    echo.
    echo Aplicația s-a închis normal.
    timeout /t 2 /nobreak >nul
)

REM Dezactivează mediul virtual dacă a fost activat
if exist ".venv\Scripts\activate.bat" (
    echo Dezactivez mediul virtual...
    deactivate 2>nul
)

echo.
echo Apasă orice tastă pentru a închide...
pause >nul
