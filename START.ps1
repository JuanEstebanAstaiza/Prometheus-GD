# SGDI - Script de inicio completo (PowerShell)
# Levanta toda la aplicacion con Docker Compose

Write-Host "Iniciando SGDI - Sistema de Gestion Documental Institucional" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que Docker esta corriendo
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker esta corriendo" -ForegroundColor Blue
    } else {
        throw
    }
} catch {
    Write-Host "Error: Docker no esta corriendo" -ForegroundColor Red
    Write-Host "Por favor inicia Docker Desktop y vuelve a intentar"
    exit 1
}

Write-Host ""

# Ir al directorio del backend
Set-Location sgdi-backend

Write-Host "Limpiando contenedores antiguos..." -ForegroundColor Yellow
docker-compose down 2>$null

Write-Host ""
Write-Host "Construyendo imagenes..." -ForegroundColor Yellow
Write-Host "Esto puede tardar unos minutos la primera vez"
Write-Host ""

# Build de las imagenes
docker-compose build

Write-Host ""
Write-Host "Levantando servicios..." -ForegroundColor Yellow
Write-Host ""

# Levantar servicios
docker-compose up -d

Write-Host ""
Write-Host "Servicios levantados" -ForegroundColor Green
Write-Host ""

# Esperar a que los servicios esten listos
Write-Host "Esperando a que los servicios esten listos..." -ForegroundColor Yellow

# Esperar por la base de datos
Write-Host -NoNewline "   Database... "
$dbReady = $false
for ($i = 1; $i -le 30; $i++) {
    $result = docker exec sgdi-postgres pg_isready -U sgdi_user -d sgdi_db 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK" -ForegroundColor Green
        $dbReady = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $dbReady) {
    Write-Host "TIMEOUT" -ForegroundColor Red
}

# Esperar por la API
Write-Host -NoNewline "   API... "
$apiReady = $false
for ($i = 1; $i -le 60; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 1 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "OK" -ForegroundColor Green
            $apiReady = $true
            break
        }
    } catch {
        # Ignorar errores
    }
    Start-Sleep -Seconds 1
}
if (-not $apiReady) {
    Write-Host "TIMEOUT" -ForegroundColor Red
}

# Esperar por el frontend
Write-Host -NoNewline "   Frontend... "
$frontendReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/health" -TimeoutSec 1 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "OK" -ForegroundColor Green
            $frontendReady = $true
            break
        }
    } catch {
        # Ignorar errores
    }
    Start-Sleep -Seconds 1
}
if (-not $frontendReady) {
    Write-Host "TIMEOUT" -ForegroundColor Red
}

Write-Host ""
Write-Host "SGDI esta listo!" -ForegroundColor Green
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "URLs de la aplicacion:" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend:      http://localhost:3000" -ForegroundColor White
Write-Host "  API:           http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:      http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Database:      localhost:5432" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Credenciales de prueba:" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Email:     admin@sgdi.test" -ForegroundColor Yellow
Write-Host "  Password:  Admin123!" -ForegroundColor Yellow
Write-Host "  Rol:       SUPER_ADMIN" -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Comandos utiles:" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Ver logs:              cd sgdi-backend; docker-compose logs -f"
Write-Host "  Ver logs (frontend):   cd sgdi-backend; docker-compose logs -f frontend"
Write-Host "  Ver logs (api):        cd sgdi-backend; docker-compose logs -f api"
Write-Host "  Ver logs (db):         cd sgdi-backend; docker-compose logs -f db"
Write-Host ""
Write-Host "  Detener aplicacion:    cd sgdi-backend; docker-compose down"
Write-Host "  Reiniciar:             cd sgdi-backend; docker-compose restart"
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Abre tu navegador en: " -NoNewline -ForegroundColor Green
Write-Host "http://localhost:3000/login.html" -ForegroundColor Blue
Write-Host ""

# Preguntar si desea abrir el navegador
$response = Read-Host "Deseas abrir el navegador ahora? (s/n)"
if ($response -eq "s" -or $response -eq "S") {
    Start-Process "http://localhost:3000/login.html"
}
