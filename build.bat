@echo off
set "PROJECT_DIR=%~dp0"

echo Limpando pastas de build e dist...
if exist "%PROJECT_DIR%build" rmdir /s /q "%PROJECT_DIR%build"
if %errorlevel% neq 0 (
    echo Erro ao limpar a pasta build.
    pause
    exit /b %errorlevel%
)
if exist "%PROJECT_DIR%dist" rmdir /s /q "%PROJECT_DIR%dist"
if %errorlevel% neq 0 (
    echo Erro ao limpar a pasta dist.
    pause
    exit /b %errorlevel%
)

echo Criando a pasta dist...
mkdir "%PROJECT_DIR%dist"
if %errorlevel% neq 0 (
    echo Erro ao criar a pasta dist.
    pause
    exit /b %errorlevel%
)

echo Gerando o executável SSHGitHubConfigurator.exe...
call pyinstaller --onefile --name "SSHGitHubConfigurator" --distpath "%PROJECT_DIR%dist" "%PROJECT_DIR%app.py"

if %errorlevel% equ 0 (
    echo Build concluído com sucesso!
) else (
    echo Ocorreu um erro durante o build.
    pause
    exit /b %errorlevel%
)

pause