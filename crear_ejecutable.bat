@echo off
chcp 65001 > nul
setlocal

echo ================================================================
echo         GENERADOR DE EJECUTABLE (.EXE) - LIMPIADOR PDF
echo ================================================================
echo.

:: 1. Verificar si Python está disponible
python --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python no se encuentra instalado o no esta en el PATH.
    pause
    exit /b 1
)

:: 2. Instalar o verificar PyInstaller y requerimientos
echo [1/4] Verificando e instalando PyInstaller y dependencias...
python -m pip install --upgrade pip > nul 2>&1
python -m pip install pyinstaller pymupdf pillow
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Ocurrió un error al instalar las dependencias requeridas.
    pause
    exit /b 1
)

:: 3. Limpiar compilaciones anteriores si existen
echo.
echo [2/4] Preparando entorno de compilacion...
if exist "build" rmdir /s /q "build" > nul 2>&1
if exist "dist\LimpiadorPDF.exe" del /f /q "dist\LimpiadorPDF.exe" > nul 2>&1
if exist "LimpiadorPDF.spec" del /f /q "LimpiadorPDF.spec" > nul 2>&1

:: 4. Compilar a un único ejecutable (.exe)
echo.
echo [3/4] Compilando con PyInstaller (empaquetando PyMuPDF y motor C/C++)...
python -m PyInstaller --noconfirm --clean --onefile --collect-all pymupdf --name "LimpiadorPDF" clean_pdf.py

:: 5. Verificar resultado
echo.
echo [4/4] Verificando resultado...
if exist "dist\LimpiadorPDF.exe" (
    echo.
    echo ================================================================
    echo   [EXITO] Ejecutable generado correctamente!
    echo ================================================================
    echo.
    echo Ubicación: %~dp0dist\LimpiadorPDF.exe
    echo.
    echo Copiando acceso directo del ejecutable a la carpeta principal...
    copy /y "dist\LimpiadorPDF.exe" "%~dp0LimpiadorPDF.exe" > nul
    echo.
    echo Puedes ejecutar 'LimpiadorPDF.exe' directamente o arrastrar
    echo un archivo PDF encima de el para limpiarlo al instante.
    echo ================================================================
) else (
    echo.
    echo ================================================================
    echo   [ERROR] No se pudo generar el archivo ejecutable.
    echo   Revisa los mensajes anteriores para mas detalles.
    echo ================================================================
)

echo.
pause
