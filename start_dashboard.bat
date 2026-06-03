@echo off
title ITUB4 Dashboard Server

cd /d "%~dp0"

echo ==============================================
echo 🏦 ITUB4 QUANTUM - INICIANDO SISTEMA
echo ==============================================
echo.
echo Limpando servidores fantasmas antigos...
wmic process where "name='python.exe' and (commandline like '%%http.server%%' or commandline like '%%servidor.py%%')" call terminate >nul 2>&1

echo.
echo Iniciando servidor inteligente na porta 8000...
echo O navegador abrira automaticamente.
echo.

:: Inicia o servidor e a janela será fechada automaticamente quando o Python encerrar
python servidor.py
