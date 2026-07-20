@echo off
chcp 65001 > nul
title KATARA - Systeme d'Alerte Precoce Inondations
color 0B

echo.
echo  ====================================================
echo    KATARA v6 - Systeme d Alerte Precoce Inondations
echo    Lome, Togo  --  http://localhost:5000
echo  ====================================================
echo.

cd /d "%~dp0"

REM ---- Localiser Python ----
SET PYEXE=
where python >nul 2>&1 && SET PYEXE=python
if "%PYEXE%"=="" where python3 >nul 2>&1 && SET PYEXE=python3
if "%PYEXE%"=="" if exist "C:\Program Files\Python310\python.exe" SET PYEXE="C:\Program Files\Python310\python.exe"
if "%PYEXE%"=="" if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe" SET PYEXE="C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe"

if "%PYEXE%"=="" (
    echo  [ERREUR] Python introuvable.
    echo  Installez Python 3.10+ depuis https://python.org
    pause
    exit /b 1
)

echo  [1/2] Python trouve : %PYEXE%
echo  [1/2] Installation des dependances...
%PYEXE% -m pip install -q -r requirements.txt

echo  [2/2] Demarrage de l'API KATARA + Interface Web...
echo.
echo  Interface  : http://localhost:5000
echo  API Status : http://localhost:5000/api/status
echo.

REM Ouvrir le navigateur apres 2 secondes
start "" cmd /c "timeout /t 2 /nobreak > nul && start http://localhost:5000"

REM Lancer l'API (bloquant)
%PYEXE% katara_api.py
pause
