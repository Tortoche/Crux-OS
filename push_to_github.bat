@echo off
title Crux OS - Synchronisation GitHub
color 0b
echo ========================================================
echo        CRUX OS - PUSH VERS GITHUB TORTOCHETV
echo ========================================================
echo.
cd /d "%~dp0"

echo [1/3] Verification des commits locaux...
git branch -M main

echo [2/3] Verification de l'adresse du depot...
git remote set-url origin https://github.com/Tortoche/Crux-OS.git

echo [3/3] Envoi vers https://github.com/Tortoche/Crux-OS...
echo.
echo Si Git vous demande une connexion, validez la page GitHub dans votre navigateur.
echo.
git push -u origin main

echo.
if %ERRORLEVEL% EQU 0 (
    color 0a
    echo ========================================================
    echo   SUCCES : Le projet Crux OS est en ligne sur GitHub !
    echo ========================================================
) else (
    color 0c
    echo ========================================================
    echo   ECHEC : Verifiez vos acces ou votre connexion GitHub.
    echo ========================================================
)
echo.
pause
