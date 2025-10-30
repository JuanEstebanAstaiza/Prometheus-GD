#!/bin/bash

# SGDI - Script de inicio completo
# Levanta toda la aplicación con Docker Compose

echo "🚀 Iniciando SGDI - Sistema de Gestión Documental Institucional"
echo "================================================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker no está corriendo${NC}"
    echo "Por favor inicia Docker Desktop y vuelve a intentar"
    exit 1
fi

echo -e "${BLUE}📦 Docker está corriendo${NC}"
echo ""

# Ir al directorio del backend
cd sgdi-backend

echo -e "${YELLOW}🧹 Limpiando contenedores antiguos...${NC}"
docker-compose down 2>/dev/null

echo ""
echo -e "${YELLOW}🏗️  Construyendo imágenes...${NC}"
echo "Esto puede tardar unos minutos la primera vez"
echo ""

# Build de las imágenes
docker-compose build

echo ""
echo -e "${YELLOW}🚀 Levantando servicios...${NC}"
echo ""

# Levantar servicios
docker-compose up -d

echo ""
echo -e "${GREEN}✅ Servicios levantados${NC}"
echo ""

# Esperar a que los servicios estén listos
echo -e "${YELLOW}⏳ Esperando a que los servicios estén listos...${NC}"

# Esperar por la base de datos
echo -n "   Database... "
for i in {1..30}; do
    if docker exec sgdi-postgres pg_isready -U sgdi_user -d sgdi_db > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ (timeout)${NC}"
    fi
done

# Esperar por la API
echo -n "   API... "
for i in {1..60}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 60 ]; then
        echo -e "${RED}✗ (timeout)${NC}"
    fi
done

# Esperar por el frontend
echo -n "   Frontend... "
for i in {1..30}; do
    if curl -s http://localhost:3000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ (timeout)${NC}"
    fi
done

echo ""
echo -e "${GREEN}🎉 ¡SGDI está listo!${NC}"
echo ""
echo "================================================================"
echo "📍 URLs de la aplicación:"
echo "================================================================"
echo ""
echo -e "  ${BLUE}🌐 Frontend:${NC}      http://localhost:3000"
echo -e "  ${BLUE}🔧 API:${NC}           http://localhost:8000"
echo -e "  ${BLUE}📖 API Docs:${NC}      http://localhost:8000/docs"
echo -e "  ${BLUE}🗄️  Database:${NC}      localhost:5432"
echo ""
echo "================================================================"
echo "🔑 Credenciales de prueba:"
echo "================================================================"
echo ""
echo -e "  ${YELLOW}Email:${NC}     admin@sgdi.local"
echo -e "  ${YELLOW}Password:${NC}  Admin123!"
echo -e "  ${YELLOW}Rol:${NC}       SUPER_ADMIN"
echo ""
echo "================================================================"
echo "📚 Comandos útiles:"
echo "================================================================"
echo ""
echo "  Ver logs:              cd sgdi-backend && docker-compose logs -f"
echo "  Ver logs (frontend):   cd sgdi-backend && docker-compose logs -f frontend"
echo "  Ver logs (api):        cd sgdi-backend && docker-compose logs -f api"
echo "  Ver logs (db):         cd sgdi-backend && docker-compose logs -f db"
echo ""
echo "  Detener aplicación:    cd sgdi-backend && docker-compose down"
echo "  Reiniciar:             cd sgdi-backend && docker-compose restart"
echo ""
echo "  Abrir shell en API:    docker exec -it sgdi-api sh"
echo "  Abrir psql:            docker exec -it sgdi-postgres psql -U sgdi_user -d sgdi_db"
echo ""
echo "================================================================"
echo ""
echo -e "${GREEN}✨ Abre tu navegador en: ${BLUE}http://localhost:3000${NC}"
echo ""

