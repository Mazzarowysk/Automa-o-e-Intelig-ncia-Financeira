@echo off
title ITUB4 Dashboard Server

cd /d "%~dp0"

echo ==============================================
echo    ITUB4 QUANTUM - INICIANDO SISTEMA
echo ==============================================
echo.
echo Limpando servidores fantasmas antigos na porta 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%a >nul 2>&1

echo.
echo Iniciando servidor inteligente na porta 8000...
echo O navegador abrira automaticamente.
echo (Esta janela se fechara automaticamente ao encerrar o sistema)
echo.

:: Inicia o servidor -- ao encerrar o Python, sai imediatamente
python servidor.py

:: Sai e fecha a janela automaticamente apos o servidor encerrar
exit
