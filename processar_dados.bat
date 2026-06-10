@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title B3 Quantum - Atualizador de Dados (Orquestrador)

cd /d "%~dp0"

echo ==============================================
echo    B3 QUANTUM - PROCESSAMENTO DE DADOS
echo ==============================================
echo.
echo Iniciando o Orquestrador para buscar os dados de todos os ativos...
echo Isso pode levar alguns minutos (Aguarde a finalizacao).
echo.

python orquestrador.py

echo.
echo Processamento concluido com sucesso!
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
