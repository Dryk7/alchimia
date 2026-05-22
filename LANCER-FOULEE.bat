@echo off
title FOULEE - Serveur local
echo.
echo ====================================
echo   FOULEE - Lancement du serveur
echo ====================================
echo.

REM Verifier que Python est dispo
where python >nul 2>nul
if errorlevel 1 (
  echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
  echo Installe Python depuis https://www.python.org/ et reessaie.
  echo.
  pause
  exit /b 1
)

REM Trouver un port libre (8765 par defaut)
set PORT=8765

REM Lancer le serveur en arriere-plan + ouvrir le navigateur
echo Serveur demarre sur http://localhost:%PORT%
echo.
echo Pour acceder depuis ton telephone (meme WiFi) :
ipconfig | findstr /C:"IPv4" | findstr /v "169.254"
echo   -> ouvrir http://[ton-ip]:%PORT% sur le tel
echo.
echo Appuie sur Ctrl+C pour arreter le serveur.
echo ====================================
echo.

REM Ouvre Chrome direct
start "" "http://localhost:%PORT%"

REM Lance le serveur (bloque la fenetre, Ctrl+C pour arreter)
cd /d "%~dp0"
python -m http.server %PORT%
