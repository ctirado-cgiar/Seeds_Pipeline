@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo ================================================
echo   Seeds Pipeline - Crear estructura de ensayo
echo   Alliance Bioversity International and CIAT
echo ================================================
echo.

:: ── Solicitar nombre del ensayo ──────────────────────────────────────────────
set /p ENSAYO="Ingrese el nombre del ensayo o poblacion (sin espacios): "

if "%ENSAYO%"=="" (
    echo [ERROR] Debe ingresar un nombre para el ensayo.
    pause
    exit /b 1
)

:: ── Definir ruta base (carpeta donde se ejecuta el .bat) ────────────────────
set BASE=%~dp0%ENSAYO%

:: Verificar si ya existe
if exist "%BASE%" (
    echo.
    echo [AVISO] La carpeta "%ENSAYO%" ya existe en este directorio.
    set /p CONTINUAR="Desea continuar de todas formas? (s/n): "
    if /i "!CONTINUAR!" neq "s" (
        echo Operacion cancelada.
        pause
        exit /b 0
    )
)

echo.
echo Creando estructura en: %BASE%
echo.

:: ── Carpetas de entrada ──────────────────────────────────────────────────────
mkdir "%BASE%\all"                                      2>nul
mkdir "%BASE%\calibracionCamara\ajedrez"                2>nul
mkdir "%BASE%\calibracionCamara\colorCard"              2>nul
mkdir "%BASE%\calibracionCamara\factorEscala"           2>nul
mkdir "%BASE%\calibracionCamara\parametrosCorreccion"   2>nul
mkdir "%BASE%\libroCampo"                               2>nul

:: ── Carpetas de salida del pipeline ─────────────────────────────────────────
mkdir "%BASE%\noDistorsion"                             2>nul
mkdir "%BASE%\colorCorrejidas"                          2>nul
mkdir "%BASE%\areaInteres"                              2>nul
mkdir "%BASE%\Binarizadas"                              2>nul
mkdir "%BASE%\Segmentadas"                              2>nul
mkdir "%BASE%\Morfometria"                              2>nul
mkdir "%BASE%\Colorimetria"                             2>nul
mkdir "%BASE%\colorDistance"                            2>nul
mkdir "%BASE%\binarizadasFiltradas"                     2>nul
mkdir "%BASE%\binarizadasAlineadas"                     2>nul
mkdir "%BASE%\formaPromedio"                            2>nul
mkdir "%BASE%\formasDistance"                           2>nul
mkdir "%BASE%\analisisFormasIntegrado"                  2>nul
mkdir "%BASE%\conteo\reports"                           2>nul
mkdir "%BASE%\resultadosUnidos"                         2>nul

:: ── Crear archivo .env con RUTA prellenada ───────────────────────────────────
set RUTA_ENV=%BASE%
:: Eliminar barra final si existe
if "%RUTA_ENV:~-1%"=="\" set RUTA_ENV=%RUTA_ENV:~0,-1%

(
    echo RUTA=%RUTA_ENV%
) > "%BASE%\.env"

:: ── Crear README de referencia rápida ────────────────────────────────────────
(
    echo # Ensayo: %ENSAYO%
    echo # Estructura creada por crear_ensayo_seedPipeline.bat
    echo # Seeds Pipeline - Alliance Bioversity International and CIAT
    echo.
    echo ## Carpetas de entrada ^(llenar antes de ejecutar el pipeline^)
    echo.
    echo   all/                              ^<-- Imagenes originales ^(JPG, PNG, JPEG^)
    echo   calibracionCamara/ajedrez/        ^<-- Min. 8 imagenes del tablero de ajedrez
    echo   calibracionCamara/colorCard/      ^<-- 1 imagen con tarjeta de color visible ^(0.jpg^)
    echo   calibracionCamara/factorEscala/   ^<-- 1 imagen con objeto de referencia metrica
    echo   libroCampo/                       ^<-- libroCampo.csv con datos del ensayo
    echo.
    echo ## Archivo de configuracion
    echo.
    echo   .env                              ^<-- Variable RUTA ya configurada automaticamente
    echo.
    echo ## Carpetas de salida ^(generadas por el pipeline^)
    echo.
    echo   noDistorsion/                     ^<-- Script 02
    echo   colorCorrejidas/                  ^<-- Script 04
    echo   areaInteres/                      ^<-- Script 06
    echo   Binarizadas/                      ^<-- Script 08
    echo   Segmentadas/                      ^<-- Script 08
    echo   Morfometria/                      ^<-- Script 08 y 09
    echo   Colorimetria/                     ^<-- Script 10_0
    echo   colorDistance/                    ^<-- Script 10_1 y 13
    echo   binarizadasFiltradas/             ^<-- Script 11_0
    echo   binarizadasAlineadas/             ^<-- Script 11_1
    echo   formaPromedio/                    ^<-- Script 11_2
    echo   formasDistance/                   ^<-- Script 12 y 13
    echo   analisisFormasIntegrado/          ^<-- Script 14
    echo   conteo/                           ^<-- Script 15
    echo   resultadosUnidos/                 ^<-- Script 16
) > "%BASE%\README_estructura.txt"

:: ── Resumen final ─────────────────────────────────────────────────────────────
echo [OK] all\
echo [OK] calibracionCamara\ajedrez\
echo [OK] calibracionCamara\colorCard\
echo [OK] calibracionCamara\factorEscala\
echo [OK] calibracionCamara\parametrosCorreccion\
echo [OK] libroCampo\
echo [OK] noDistorsion\
echo [OK] colorCorrejidas\
echo [OK] areaInteres\
echo [OK] Binarizadas\
echo [OK] Segmentadas\
echo [OK] Morfometria\
echo [OK] Colorimetria\
echo [OK] colorDistance\
echo [OK] binarizadasFiltradas\
echo [OK] binarizadasAlineadas\
echo [OK] formaPromedio\
echo [OK] formasDistance\
echo [OK] analisisFormasIntegrado\
echo [OK] conteo\reports\
echo [OK] resultadosUnidos\
echo [OK] .env  ^(RUTA=%RUTA_ENV%^)
echo [OK] README_estructura.txt
echo.
echo ================================================
echo   Listo. Estructura creada para: %ENSAYO%
echo.
echo   Proximos pasos:
echo   1. Copie sus imagenes en all\
echo   2. Copie las imagenes del tablero en calibracionCamara\ajedrez\
echo   3. Copie la imagen de la tarjeta de color en calibracionCamara\colorCard\
echo   4. Copie su libro de campo en libroCampo\
echo   5. Abra el editor de codigo y ejecute los scripts en orden
echo ================================================
echo.

pause
endlocal
