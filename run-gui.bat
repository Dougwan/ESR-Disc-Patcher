@echo off
REM ---------------------------------------------------------------------------
REM run-gui.bat - Lancador da GUI do edp para Windows.
REM
REM Apenas encontra um Python para executar run-gui.py (que detecta Tk >= 8.6,
REM ajusta o PYTHONPATH para .\src e abre a GUI). No macOS/Linux use run-gui.sh.
REM
REM Uso:
REM   run-gui.bat            :: abre a GUI
REM   run-gui.bat --print    :: so mostra o diagnostico (nao abre janela)
REM   set EDP_PYTHON=C:\caminho\python.exe ^&^& run-gui.bat   :: interpretador preferido
REM ---------------------------------------------------------------------------
setlocal
set "HERE=%~dp0"

if defined EDP_PYTHON goto :run_env
where py >nul 2>nul && goto :run_py
where python >nul 2>nul && goto :run_python
goto :no_python

:run_env
"%EDP_PYTHON%" "%HERE%run-gui.py" %*
exit /b %errorlevel%

:run_py
py -3 "%HERE%run-gui.py" %*
exit /b %errorlevel%

:run_python
python "%HERE%run-gui.py" %*
exit /b %errorlevel%

:no_python
echo edp: Python nao encontrado no PATH. 1>&2
echo Instale o Python 3.9+ em https://www.python.org/downloads/windows/ 1>&2
exit /b 1
