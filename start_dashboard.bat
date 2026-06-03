@echo off
title ITUB4 Dashboard Server

cd /d "%~dp0"

echo ==============================================
echo    ITUB4 QUANTUM - INICIANDO SISTEMA
echo ==============================================
echo.
echo Limpando servidores fantasmas antigos...
wmic process where "name='python.exe' and (commandline like '%%http.server%%' or commandline like '%%servidor.py%%')" call terminate >nul 2>&1

echo.
echo Iniciando servidor inteligente na porta 8000...
echo O navegador abrira automaticamente.
echo (Esta janela se fechara automaticamente ao encerrar o sistema)
echo.

:: Inicia o servidor -- ao encerrar o Python, sai imediatamente
python servidor.py

:: Sai e fecha a janela automaticamente apos o servidor encerrar
exit
