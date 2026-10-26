@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PY=
where python >nul 2>nul && set PY=python
if not defined PY where py >nul 2>nul && set PY=py
if not defined PY (
  echo Python nao encontrado.
  pause
  exit /b 1
)

%PY% -m pip install --quiet --disable-pip-version-check -r requirements.txt
%PY% patcher\dune_ptbr.py --restore
echo.
pause
