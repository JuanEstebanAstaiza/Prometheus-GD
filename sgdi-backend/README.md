# SGDI - Sistema de Gestión Documental Integrado

Un sistema completo de gestión documental construido con FastAPI, SQLAlchemy y PostgreSQL, diseñado para entornos de producción con alta seguridad y escalabilidad.

## 📋 Descripción

SGDI es una plataforma robusta para la gestión integral de documentos digitales, diseñada para organizaciones que requieren un control estricto sobre sus archivos y procesos documentales. El sistema proporciona funcionalidades avanzadas de organización, búsqueda, seguridad, auditoría y respaldos.

## 🏗️ Arquitectura

- **Backend**: FastAPI (Python 3.11+)
- **Base de Datos**: PostgreSQL 15+
- **ORM**: SQLAlchemy 1.4+
- **Autenticación**: JWT con refresh tokens
- **Migraciones**: Sistema SQL idempotente personalizado
- **Contenedorización**: Docker & Docker Compose

## 📁 Estructura del Proyecto

```
sgdi-backend/
├── app/
│   ├── main.py                    # Punto de entrada FastAPI
│   ├── core/
│   │   ├── config.py             # Configuración Pydantic
│   │   ├── database.py           # Conexión y sesión DB
│   │   ├── security.py           # Utilidades de seguridad
│   │   ├── auth.py               # Dependencias de autenticación
│   │   └── logging_config.py     # Configuración de logs
│   ├── models/
│   │   ├── __init__.py           # Importación de modelos
│   │   ├── user.py               # Modelo Usuario
│   │   ├── dependency.py         # Modelo Dependencia
│   │   ├── folder.py             # Modelo Carpeta
│   │   ├── file.py               # Modelo Archivo
│   │   ├── audit.py              # Modelo Auditoría
│   │   └── backup.py             # Modelo Respaldo
│   ├── schemas/
│   │   └── auth.py               # Esquemas Pydantic
│   ├── routes/
│   │   ├── auth_routes.py        # Endpoints de autenticación
│   │   ├── users_routes.py       # Endpoints de usuarios
│   │   ├── dependencies_routes.py # Endpoints de dependencias
│   │   ├── folders_routes.py     # Endpoints de carpetas
│   │   ├── files_routes.py       # Endpoints de archivos
│   │   ├── audit_routes.py       # Endpoints de auditoría
│   │   └── backups_routes.py     # Endpoints de respaldos
│   ├── services/
│   │   ├── storage_service.py    # Servicio de almacenamiento
│   │   ├── backup_service.py     # Servicio de respaldos
│   │   ├── audit_service.py      # Servicio de auditoría
│   │   └── scheduler_service.py  # Servicio de tareas programadas
│   ├── utils/
│   │   ├── names.py              # Utilidades de nombres y rutas
│   │   └── validators.py         # Validadores de entrada
│   └── tasks/
│       └── monthly_folders.py    # Tarea de carpetas mensuales
├── migrations_sql/
│   └── 0001_initial_schema.sql   # Esquema inicial
├── scripts/
│   ├── apply_migrations.py       # Script de migraciones
│   ├── seed_superadmin.py        # Script de seeding inicial
│   └── backup_db.sh             # Script de respaldo DB
├── tests/                        # Directorio de pruebas
├── Dockerfile                    # Configuración Docker
├── docker-compose.yml            # Servicios Docker Compose
├── .env.example                  # Variables de entorno ejemplo
├── requirements.txt              # Dependencias Python
└── README.md                     # Esta documentación
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- **Docker y Docker Compose** (recomendado para producción)
- **Python 3.11+** (para desarrollo local)
- **PostgreSQL 15+** (para desarrollo local)
- **Git**

### 🐳 Configuración con Docker Compose (Recomendado)

1. **Clonar el repositorio:**
   ```bash
   git clone <repository-url>
   cd sgdi-backend
   ```

2. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env con sus configuraciones específicas
   ```

3. **Configurar superadmin inicial:**
   ```bash
   # Editar .env y configurar:
   SUPERADMIN_EMAIL=admin@yourcompany.com
   SUPERADMIN_PASSWORD=your-secure-password-here
   SUPERADMIN_FULL_NAME="System Administrator"
   ```

4. **Iniciar todos los servicios:**
   ```bash
   docker-compose up --build -d
   ```

5. **Verificar el estado:**
   ```bash
   # Ver logs
   docker-compose logs -f api

   # Verificar health check
   curl http://localhost:8000/health

   # Verificar API info
   curl http://localhost:8000/info
   ```

6. **Acceder a la aplicación:**
   - **API**: http://localhost:8000
   - **Documentación Swagger**: http://localhost:8000/docs
   - **Documentación ReDoc**: http://localhost:8000/redoc
   - **pgAdmin** (opcional): http://localhost:8080

### 💻 Configuración de Desarrollo Local

1. **Instalar dependencias del sistema:**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3.11 postgresql postgresql-contrib

   # macOS con Homebrew
   brew install python@3.11 postgresql

   # Windows - usar WSL o instalar directamente
   ```

2. **Clonar y configurar:**
   ```bash
   git clone <repository-url>
   cd sgdi-backend

   # Crear entorno virtual
   python3.11 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias Python:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar PostgreSQL:**
   ```bash
   # Crear base de datos
   createdb sgdi_db

   # Opcional: crear usuario específico
   createuser sgdi_user
   psql -c "ALTER USER sgdi_user PASSWORD 'secure_password';"
   psql -c "GRANT ALL PRIVILEGES ON DATABASE sgdi_db TO sgdi_user;"
   ```

5. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env con configuración local
   ```

6. **Inicializar la base de datos:**
   ```bash
   # Aplicar migraciones
   python scripts/apply_migrations.py --apply

   # Crear superadmin
   export SUPERADMIN_EMAIL=admin@local.dev
   export SUPERADMIN_PASSWORD=devpassword123
   export SUPERADMIN_FULL_NAME="Development Admin"
   python scripts/seed_superadmin.py
   ```

7. **Iniciar el servidor de desarrollo:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

8. **Ejecutar pruebas:**
   ```bash
   pytest tests/ -v
   ```

### 🧪 Ejecución de Pruebas

```bash
# Ejecutar todas las pruebas
pytest tests/ -v

# Ejecutar pruebas específicas
pytest tests/test_auth.py -v
pytest tests/test_files.py::test_upload_main_file_only -v

# Ejecutar con cobertura
pytest --cov=app --cov-report=html tests/

# Ejecutar pruebas de integración
pytest tests/ -k "integration" -v
```

### 🔧 Scripts de Operación

#### Seeding del Superadmin

```bash
# Configurar variables de entorno
export SUPERADMIN_EMAIL=admin@yourcompany.com
export SUPERADMIN_PASSWORD=secure_password_123
export SUPERADMIN_FULL_NAME="System Administrator"

# Ejecutar seeding
python scripts/seed_superadmin.py
```

#### Backup de Base de Datos

```bash
# Configurar variables de entorno
export DATABASE_URL="postgresql://user:password@localhost:5432/sgdi_db"
export BACKUP_PATH="/path/to/backups"
export BACKUP_RETENTION_DAYS=30

# Ejecutar backup
./scripts/backup_db.sh

# Backup con nombre personalizado
./scripts/backup_db.sh "weekly_backup"
```

#### Migraciones de Base de Datos

```bash
# Verificar migraciones pendientes
python scripts/apply_migrations.py --dry-run

# Aplicar migraciones
python scripts/apply_migrations.py --apply

# Forzar aplicación (solo desarrollo)
python scripts/apply_migrations.py --apply --force
```

## ⚙️ Configuración

### Variables de Entorno

Copie `.env.example` a `.env` y configure las siguientes variables:

```bash
# Base de Datos
DATABASE_URL=postgresql://user:password@localhost:5432/sgdi_db
DB_SCHEMA=sgdi

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-here-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Almacenamiento
STORAGE_PATH=/app/storage
BACKUP_PATH=/app/backups

# Subidas
MAX_UPLOAD_SIZE_MB=50
ALLOWED_MIME_TYPES=application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel

# Sistema
SYSTEM_USER_ID=00000000-0000-0000-0000-000000000000

# Programador
SCHEDULER_ENABLED=true
SCHEDULER_CRON=0 0 1 * *

# Logging
LOG_LEVEL=INFO
```

## 🗄️ Base de Datos

### Migraciones

El sistema utiliza migraciones SQL idempotentes almacenadas en `migrations_sql/`.

**Aplicar migraciones:**
```bash
python scripts/apply_migrations.py --apply
```

**Ver qué se aplicaría (dry run):**
```bash
python scripts/apply_migrations.py --dry-run
```

**Aplicar con dry run automático:**
```bash
python scripts/apply_migrations.py --apply --dry-run-first=true
```

### Esquema de Base de Datos

#### Tablas Principales

- **users**: Usuarios del sistema
- **dependencies**: Dependencias organizacionales
- **folders**: Estructura jerárquica de carpetas
- **files**: Archivos almacenados
- **audit_logs**: Registro de auditoría
- **backups**: Información de respaldos
- **schema_migrations**: Control de migraciones aplicadas

#### Índices Optimizados

- Índices en campos de búsqueda frecuente
- Índices compuestos para consultas complejas
- Índices parciales para estados activos

## 🔐 Autenticación y Autorización

### Endpoints de Autenticación

- `POST /auth/login`: Inicio de sesión
- `POST /auth/refresh`: Refresco de token
- `POST /auth/verify`: Verificación de token

### Niveles de Usuario

- **Superusuario**: Control total del sistema
- **Usuario regular**: Acceso limitado según permisos

### Seguridad

- JWT con tokens de acceso y refresh
- Hashing de contraseñas con bcrypt
- Validación de entrada en todas las rutas
- Auditoría completa de acciones

## 📊 API Endpoints

### Health Check
- `GET /health`: Verificación de estado del sistema

### Authentication
- `POST /auth/login`: Login con JWT + refresh token
- `POST /auth/refresh`: Refresh access token
- `POST /auth/logout`: Logout con revocación de token
- `POST /auth/verify`: Verificar token actual

### Dependencies (Gestión de Dependencias)
- `GET /dependencies`: Listar dependencias con filtros de permisos
- `POST /dependencies`: Crear dependencia (SUPER_ADMIN)
- `GET /dependencies/{id}`: Obtener dependencia específica
- `PUT /dependencies/{id}`: Actualizar dependencia (SUPER_ADMIN)
- `DELETE /dependencies/{id}`: Eliminar dependencia (SUPER_ADMIN)

### Users (Gestión de Usuarios)
- `GET /users/me`: Información del usuario actual
- `PUT /users/me`: Actualizar perfil propio
- `GET /users/`: Listar usuarios con filtros (SUPER_ADMIN, ADMIN_DEP)
- `POST /users/`: Crear usuario con validaciones de rol (SUPER_ADMIN, ADMIN_DEP)
- `GET /users/{id}`: Obtener usuario específico
- `PUT /users/{id}`: Actualizar usuario con restricciones de permisos
- `DELETE /users/{id}`: Soft delete usuario (desactivar)

### Folders (Gestión de Carpetas)
- `GET /folders/dependencies/{dep_id}/tree`: Obtener estructura de árbol de carpetas
- `POST /folders`: Crear carpeta con validación de permisos
- `GET /folders/{id}`: Obtener carpeta específica
- `PUT /folders/{id}`: Renombrar/mover carpeta con actualización recursiva de paths
- `DELETE /folders/{id}`: Eliminar carpeta con validación de contenido

### Admin Endpoints
- `POST /admin/force-create-month-folders`: Crear carpetas mensuales manualmente (Super Admin)
- `POST /admin/backup/create`: Crear backup completo con archivos y metadata (Super Admin)
- `GET /admin/backups`: Listar backups disponibles (Super Admin)
- `GET /admin/backups/{id}`: Detalles de backup específico (Super Admin)
- `GET /admin/backups/{id}/download`: Descargar archivo de backup (Super Admin)
- `POST /admin/backup/restore`: Restaurar desde backup con estrategias seguras (Super Admin)

### Audit Endpoints
- `GET /audit/logs`: Consulta avanzada de logs con filtros y exportación (Admin/Super Admin)
- `GET /audit/user/{user_id}`: Logs y estadísticas de un usuario específico (Admin/Super Admin)
- `GET /audit/file/{file_id}`: Logs cronológicos de archivo y anexos (Admin/Super Admin)
- `GET /audit/`: Endpoint legacy para compatibilidad

### Additional Endpoints
- `GET /files/`: Listar archivos
- `GET /files/{id}`: Obtener archivo
- `GET /backups/`: Listar respaldos
- `GET /backups/{id}`: Obtener respaldo

## 🔄 Tareas Programadas

### Carpetas Mensuales
El sistema incluye un scheduler automático que crea carpetas mensuales para todas las dependencias activas.

**Configuración:**
- **Horario**: Configurable via `SCHEDULER_CRON` (default: "0 5 1 * *" - 5 minutos después de la medianoche del primer día del mes)
- **Job ID**: `monthly_folders`
- **Función**: `create_monthly_folders_for_month()`

**Comportamiento:**
- Crea carpetas nombradas `YYYY-MM` en la carpeta raíz de cada dependencia
- Usa `SYSTEM_USER_ID` como creador
- Implementa idempotencia (no duplica carpetas existentes)
- Maneja concurrencia con `SELECT FOR UPDATE` por dependencia
- Registra auditoría para cada carpeta creada

**Ejecución Manual:**
```bash
# Para el mes actual
curl -X POST "http://localhost:8000/admin/force-create-month-folders" \
  -H "Authorization: Bearer <super-admin-token>"

# Para un mes específico
curl -X POST "http://localhost:8000/admin/force-create-month-folders?month=2024-12" \
  -H "Authorization: Bearer <super-admin-token>"
```

**Respuesta de Ejecución Manual:**
```json
{
  "success": true,
  "message": "Monthly folders creation completed. Created 3 folders.",
  "folders_created": [
    {
      "id": "folder-uuid-1",
      "name": "2024-12",
      "path": "Legal/2024-12",
      "dependency_id": "dep-uuid-1",
      "dependency_code": "LEGAL",
      "dependency_name": "Legal Department"
    }
  ],
  "target_month": "2024-12"
}
```

### Sistema de Backup y Restore
La aplicación incluye un sistema completo de backup y restore con las siguientes características:

**Características del Backup:**
- **Backup completo**: Metadata JSON + archivos físicos en tar.gz
- **Backup parcial**: Por dependencia específica
- **Checksum SHA-256**: Verificación de integridad
- **Compresión**: Archivos comprimidos para eficiencia
- **Auditoría**: Registro completo de operaciones

**Estrategias de Restore:**
- **Simulate**: Análisis de impacto sin cambios
- **Create New IDs**: Restore seguro con nuevos identificadores
- **Overwrite**: Restore destructivo (requiere confirmación)

**Ejemplos de Uso:**
```bash
# Crear backup completo
curl -X POST "http://localhost:8000/admin/backup/create" \
  -H "Authorization: Bearer <super-admin-token>"

# Simular restore
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "backup_file=@backup.tar.gz" \
  -F "strategy=simulate"

# Ejecutar restore seguro
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "backup_file=@backup.tar.gz" \
  -F "strategy=create_new_ids"
```

### Sistema de Auditoría Avanzado
La aplicación incluye un sistema completo de auditoría con consultas avanzadas y exportación:

**Características de Auditoría:**
- **Consulta avanzada**: Filtros por usuario, dependencia, tipo de acción, fechas
- **Exportación**: JSON, CSV, XLSX con streaming para grandes volúmenes
- **Resúmenes legibles**: Templates automáticos con contexto de anexos
- **Estadísticas**: Conteos por tipo de acción por usuario
- **Historial de archivos**: Logs cronológicos de archivos y sus anexos

**Ejemplos de Uso:**
```bash
# Consultar logs con filtros avanzados
curl -X GET "http://localhost:8000/audit/logs?user_id=user-uuid&action_type=UPLOAD&start_date=2024-01-01T00:00:00" \
  -H "Authorization: Bearer <admin-token>"

# Exportar logs a CSV
curl -X GET "http://localhost:8000/audit/logs?format=csv&dependency_id=dep-uuid" \
  -H "Authorization: Bearer <super-admin-token>"

# Ver actividad de un usuario
curl -X GET "http://localhost:8000/audit/user/user-uuid" \
  -H "Authorization: Bearer <admin-token>"

# Ver historial de un archivo
curl -X GET "http://localhost:8000/audit/file/file-uuid" \
  -H "Authorization: Bearer <admin-token>"
```

### 🛡️ Procedimientos de Backup y Restore

#### Backup del Sistema

**Backup Completo (Recomendado):**
```bash
# Crear backup completo desde la API
curl -X POST "http://localhost:8000/admin/backup/create" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "include_logs=true"

# Crear backup de base de datos desde shell
export DATABASE_URL="postgresql://user:password@localhost:5432/sgdi_db"
export BACKUP_PATH="/path/to/backups"
./scripts/backup_db.sh "manual_backup"
```

**Backup Parcial (por dependencia):**
```bash
curl -X POST "http://localhost:8000/admin/backup/create" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "dependency_id=dep-uuid" \
  -F "include_logs=false"
```

#### Simulación de Restore (Siempre hacer primero)

```bash
# Simular restore para ver impacto
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "backup_file=@backup.tar.gz" \
  -F "strategy=simulate"
```

#### Restore Seguro (Create New IDs)

```bash
# Ejecutar restore creando nuevos IDs
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "backup_file=@backup.tar.gz" \
  -F "strategy=create_new_ids" \
  -F "preserve_existing=true"
```

#### Restore Destructivo (Solo en casos extremos)

```bash
# ⚠️ PELIGROSO: Solo para sistemas limpios
# Asegurarse de tener backup completo de la DB actual

# Hacer dump completo de la DB actual
pg_dump -h localhost -U user sgdi_db > emergency_backup.sql

# Ejecutar overwrite restore
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "backup_file=@backup.tar.gz" \
  -F "strategy=overwrite" \
  -F "confirm=true"
```

#### Lista y Descarga de Backups

```bash
# Listar todos los backups
curl -X GET "http://localhost:8000/admin/backups" \
  -H "Authorization: Bearer <super-admin-token>"

# Listar backups de una dependencia
curl -X GET "http://localhost:8000/admin/backups?dependency_id=dep-uuid" \
  -H "Authorization: Bearer <super-admin-token>"

# Descargar backup
curl -X GET "http://localhost:8000/admin/backups/backup-uuid/download" \
  -H "Authorization: Bearer <super-admin-token>" \
  --output backup.tar.gz
```

### 📊 Monitoreo y Health Checks

```bash
# Health check básico
curl http://localhost:8000/health

# Información del sistema
curl http://localhost:8000/info

# Verificar conectividad a DB
curl http://localhost:8000/health | jq .database

# Verificar permisos de escritura
curl http://localhost:8000/health | jq .storage_writable
```

### 🔄 Configuración de DB_SCHEMA

Si comparte la instancia de PostgreSQL con otras aplicaciones, configure un schema específico:

```bash
# En .env
DB_SCHEMA=sgdi_prod

# Aplicar migraciones con schema específico
python scripts/apply_migrations.py --apply --schema sgdi_prod
```

**Nota**: Asegúrese de que el usuario tenga permisos para crear schemas:
```sql
GRANT CREATE ON DATABASE your_db TO your_user;
```

### Respaldos Automáticos

Configurables vía variables de entorno:
- Frecuencia: `SCHEDULER_CRON`
- Tipos: Base de datos, archivos, configuración

## 💾 Respaldos

### Respaldos de Base de Datos

```bash
# Crear respaldo
./scripts/backup_db.sh

# Con opciones personalizadas
./scripts/backup_db.sh --host prod-db --user backup_user --retention 60

# Solo limpieza de respaldos antiguos
./scripts/backup_db.sh --cleanup-only
```

### Respaldos del Sistema

El sistema incluye respaldos automáticos de:
- Base de datos PostgreSQL
- Archivos almacenados
- Configuraciones del sistema

## 🧪 Pruebas

```bash
# Ejecutar pruebas
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Pruebas específicas
pytest tests/test_auth.py
```

## 📋 Monitoreo y Logs

### Logs del Sistema

- Logs rotativos en `/app/logs/`
- Niveles configurables: DEBUG, INFO, WARNING, ERROR
- Formato estructurado con timestamps

### Health Checks

- `GET /health`: Verifica conectividad DB y almacenamiento
- Estado detallado: database, storage, writability

## 🔧 Mantenimiento

### Limpieza de Archivos Antiguos

```bash
# Ejecutar limpieza manual
python -c "from app.tasks.monthly_folders import cleanup_old_folders; cleanup_old_folders()"
```

### Verificación de Integridad

```bash
# Verificar archivos
python -c "from app.services.storage_service import storage_service; print(storage_service.get_storage_info())"
```

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o preguntas:
- Crear issue en el repositorio
- Revisar la documentación en `/docs`
- Consultar logs del sistema

## 🚀 Despliegue en Producción

### Consideraciones de Seguridad

1. **Variables de entorno**:
   - Cambiar `JWT_SECRET_KEY` por valor seguro
   - Configurar credenciales de base de datos seguras
   - Usar HTTPS en producción

2. **Base de datos**:
   - Configurar conexión pooling
   - Implementar backup strategy
   - Monitorear rendimiento

3. **Almacenamiento**:
   - Configurar límites de espacio
   - Implementar rotación de archivos
   - Backup regular de archivos

### Escalado

- Implementar cache (Redis) para sesiones
- Configurar load balancer para múltiples instancias
- Usar CDN para archivos estáticos

---

**Versión**: 1.0.0
**Última actualización**: Octubre 2025
