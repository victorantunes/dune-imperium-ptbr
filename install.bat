@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PY=
where python >nul 2>nul && set PY=python
if not defined PY where py >nul 2>nul && set PY=py
if not defined PY (
  echo Python nao encontrado.
  echo Instale em https://www.python.org/downloads/ e marque "Add Python to PATH".
  pause
  exit /b 1
)

echo Instalando dependencia (UnityPy)...
%PY% -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Falha ao instalar o UnityPy.
  pause
  exit /b 1
)

echo.
%PY% patcher\dune_ptbr.py
echo.
pause
