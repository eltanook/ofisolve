@echo off
setlocal enabledelayedexpansion

REM Si el script recibe el argumento --ollama, ejecuta solo Ollama
if "%1"=="--ollama" (
    TITLE OfiSolve - Ollama
    echo Iniciando Motor de IA ^(Ollama^)...
    ollama serve
    echo.
    echo Ollama se cerro.
    pause
    exit /b
)

REM Si el script recibe el argumento --backend, ejecuta solo el Backend
if "%1"=="--backend" (
    TITLE OfiSolve - Backend
    echo Esperando a que la IA ^(Ollama^) este disponible...
    set RETRIES=0
    :loop_ia
    curl -s http://localhost:11434 > NUL 2>&1
    if !ERRORLEVEL! NEQ 0 (
        set /a RETRIES+=1
        if !RETRIES! GEQ 15 (
            echo [ERROR] La IA no responde en el puerto 11434. Abortando Backend.
            pause
            exit /b 1
        )
        ping 127.0.0.1 -n 3 > nul
        goto loop_ia
    )
    echo [OK] IA disponible! Iniciando Backend...
    cd backend
    call .venv\Scripts\activate.bat
    python -m uvicorn main:app --reload --port 8080
    echo.
    echo Backend se cerro.
    pause
    exit /b
)

REM Si el script recibe el argumento --frontend, ejecuta solo el Frontend
if "%1"=="--frontend" (
    TITLE OfiSolve - Frontend
    echo Esperando a que el Backend este disponible...
    set RETRIES=0
    :loop_be
    curl -s http://127.0.0.1:8080/health > NUL 2>&1
    if !ERRORLEVEL! NEQ 0 (
        set /a RETRIES+=1
        if !RETRIES! GEQ 15 (
            echo [ERROR] El Backend no responde en el puerto 8080. Abortando Frontend.
            pause
            exit /b 1
        )
        ping 127.0.0.1 -n 3 > nul
        goto loop_be
    )
    echo [OK] Backend disponible! Iniciando Frontend...
    cd frontend\ui
    npm run dev
    echo.
    echo Frontend se cerro.
    pause
    exit /b
)

REM =========================================================================
REM Lógica Principal: Abrir Windows Terminal con 3 pestañas
REM =========================================================================

echo Iniciando OfiSolve en multiples ventanas (CMD)...
start "OfiSolve - Ollama" cmd /k "%~f0" --ollama
start "OfiSolve - Backend" cmd /k "%~f0" --backend
start "OfiSolve - Frontend" cmd /k "%~f0" --frontend

echo.
echo =========================================
echo OfiSolve se esta iniciando en nuevas
echo ventanas de CMD.
echo =========================================
echo.
echo Abriendo el navegador en 45 segundos...
ping 127.0.0.1 -n 46 > nul
start http://localhost:3000
exit
