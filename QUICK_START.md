# 🚀 SGDI - Quick Start Guide

## ¡La aplicación ya está corriendo!

### 📍 URLs Disponibles

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Frontend** | http://localhost:3000 | Interfaz de usuario principal |
| **API** | http://localhost:8000 | Backend API REST |
| **API Docs** | http://localhost:8000/docs | Documentación Swagger interactiva |
| **Database** | localhost:5432 | PostgreSQL (acceso directo) |

---

## 🔑 Credenciales de Acceso

### Usuario SuperAdmin (Pre-configurado)

```
Email:    admin@sgdi.com
Password: supersecret123
Rol:      SUPER_ADMIN
```

Este usuario se crea automáticamente al iniciar la aplicación.

---

## 🎯 Primeros Pasos

### 1. Acceder al Frontend

Abre tu navegador en: **http://localhost:3000/login.html**

### 2. Iniciar Sesión

- Ingresa el email: `admin@sgdi.com`
- Ingresa la contraseña: `supersecret123`
- Click en "Iniciar Sesión"

### 3. Explorar la Aplicación

Una vez dentro, podrás:

- ✅ **Dashboard**: Ver resumen de actividad
- ✅ **Dependencias**: Gestionar dependencias organizacionales
- ✅ **Carpetas**: Navegar por el árbol de carpetas
- ✅ **Archivos**: Subir, descargar, gestionar archivos y anexos
- ✅ **Usuarios**: Crear y administrar usuarios (CRUD completo)
- ✅ **Auditoría**: Ver logs del sistema y exportar a CSV
- ✅ **Backups**: Crear backups, simular y restaurar

---

## 🧪 Testing E2E

Sigue el flujo completo de prueba documentado en:

**`frontend/tests/e2e_instructions.md`**

Resumen rápido:
1. Login ✓
2. Crear dependencia "PRUEBA" ✓
3. Crear carpeta "Contratos" ✓
4. Subir archivo con anexos ✓
5. Verificar carpeta de anexos auto-generada ✓
6. Descargar archivo ✓
7. Generar backup ✓
8. Simular restauración ✓
9. Revisar logs de auditoría ✓
10. Exportar CSV ✓

---

## 📚 Comandos Útiles

### Ver Logs en Tiempo Real

```bash
# Todos los servicios
cd sgdi-backend
docker-compose logs -f

# Solo frontend
docker-compose logs -f frontend

# Solo API
docker-compose logs -f api

# Solo base de datos
docker-compose logs -f db
```

### Gestión de Contenedores

```bash
cd sgdi-backend

# Ver estado de contenedores
docker-compose ps

# Reiniciar un servicio
docker-compose restart frontend
docker-compose restart api

# Detener todo
docker-compose down

# Reiniciar todo (desde raíz del proyecto)
cd ..
powershell -ExecutionPolicy Bypass -File START.ps1
```

### Acceso a Contenedores

```bash
# Shell en el contenedor de API
docker exec -it sgdi-api sh

# PostgreSQL CLI
docker exec -it sgdi-postgres psql -U sgdi_user -d sgdi_db

# Ver archivos en el frontend
docker exec -it sgdi-frontend ls -la /usr/share/nginx/html
```

---

## 🔧 Resolución de Problemas

### El frontend no carga (página en blanco)

1. Verifica que el contenedor esté corriendo:
   ```bash
   docker ps | grep sgdi-frontend
   ```

2. Verifica los logs:
   ```bash
   cd sgdi-backend
   docker-compose logs frontend
   ```

3. Abre la consola del navegador (F12) y busca errores

### Error de CORS

Si ves errores de CORS en la consola:

1. Verifica que el backend esté corriendo:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verifica la configuración de CORS en el backend (ya debería estar configurada)

### Token expirado rápidamente

El token dura 30 minutos por defecto. El refresh automático debería funcionar.
Si tienes problemas:

1. Limpia localStorage: F12 → Application → Local Storage → Clear
2. Vuelve a iniciar sesión

### No puedo subir archivos grandes

Por defecto, el límite es 200MB. Si necesitas más:

1. Edita `sgdi-backend/docker-compose.yml`:
   ```yaml
   - MAX_UPLOAD_SIZE_MB=500  # Aumentar límite
   ```

2. Edita `frontend/docker/nginx/nginx.conf`:
   ```nginx
   client_max_body_size 500M;
   ```

3. Reinicia los contenedores:
   ```bash
   cd sgdi-backend
   docker-compose restart
   ```

---

## 📖 Documentación Completa

### Frontend
- **`frontend/README-frontend.md`**: Guía completa del frontend
- **`frontend/tests/e2e_instructions.md`**: Testing E2E paso a paso
- **`frontend/FINAL_DELIVERY.md`**: Resumen ejecutivo de la entrega

### Backend
- **`sgdi-backend/README.md`**: Guía del backend (si existe)
- **API Docs**: http://localhost:8000/docs (Swagger interactivo)

---

## 🛑 Detener la Aplicación

```bash
cd sgdi-backend
docker-compose down
```

Esto detiene todos los contenedores pero **mantiene los datos** (base de datos, archivos, backups).

### Para eliminar TODO (incluyendo datos)

```bash
cd sgdi-backend
docker-compose down -v
```

⚠️ **Cuidado**: Esto eliminará la base de datos y todos los archivos subidos.

---

## 🔄 Reiniciar desde Cero

```bash
# Desde la raíz del proyecto
powershell -ExecutionPolicy Bypass -File START.ps1
```

Esto:
1. ✅ Limpia contenedores antiguos
2. ✅ Reconstruye imágenes si hay cambios
3. ✅ Levanta todos los servicios
4. ✅ Aplica migraciones de base de datos
5. ✅ Crea el usuario superadmin
6. ✅ Espera a que todo esté listo
7. ✅ Muestra las URLs de acceso

---

## 📊 Estado de los Servicios

### Verificar que todo está OK

```bash
# Health check del API
curl http://localhost:8000/health

# Health check del frontend
curl http://localhost:3000/health

# Estado de PostgreSQL
docker exec sgdi-postgres pg_isready -U sgdi_user -d sgdi_db
```

### Respuestas esperadas

- **API**: `{"status":"ok","db":true,"storage_writable":true}`
- **Frontend**: `healthy`
- **PostgreSQL**: `sgdi_postgres:5432 - accepting connections`

---

## 🎨 Características Implementadas

### ✅ Frontend (100% Nativo - HTML/CSS/JS)
- Login con JWT y refresh automático
- Router SPA con hash-based routing
- Gestión de usuarios (CRUD + roles)
- Gestión de dependencias
- Árbol de carpetas (expand/collapse, CRUD)
- Upload de archivos con anexos automáticos
- Download con validación de checksum
- Auditoría con filtros y export CSV
- Backups con simulate y restore
- Responsive (mobile-first)
- Accessible (WCAG AA)
- Sin Node.js/NPM/React

### ✅ Backend (FastAPI + PostgreSQL)
- API REST completa
- Autenticación JWT con refresh
- RBAC (4 roles)
- Auditoría completa
- Backups tar.gz con estrategias
- Scheduler APScheduler (carpetas mensuales)
- File versioning
- Soft/hard delete
- Health endpoints
- Swagger docs

---

## 🚀 ¡Todo listo para empezar a probar!

**Abre tu navegador en: http://localhost:3000/login.html**

**Credenciales:** `admin@sgdi.com` / `supersecret123`

---

**¿Dudas?** Consulta la documentación completa en:
- `frontend/README-frontend.md`
- `frontend/tests/e2e_instructions.md`
- http://localhost:8000/docs

---

**Synera © 2025 - FOVIS**

