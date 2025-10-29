# SGDI Backup and Restore System - Documentación Completa

Sistema completo de backup y restore con empaquetado tar.gz, metadata.json y estrategias de restauración seguras.

## 📦 Arquitectura del Backup

### Estructura del Archivo de Backup

```
backup-YYYYMMDD_HHMMSS.tar.gz
└── backup-YYYYMMDD_HHMMSS/
    ├── metadata.json          # Todos los metadatos del sistema
    └── files/                 # Archivos físicos
        ├── uuid1.pdf
        ├── uuid2.docx
        └── ...
```

### Contenido de metadata.json

```json
{
  "backup_version": "1.0",
  "created_at": "2024-12-01T10:30:00Z",
  "dependency_id": null,  // null = backup completo
  "include_logs": true,
  "dependencies": [
    {
      "id": "dep-uuid",
      "name": "Legal Department",
      "code": "LEGAL",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-12-01T09:00:00Z"
    }
  ],
  "folders": [...],
  "files": [
    {
      "id": "file-uuid",
      "original_name": "contrato.pdf",
      "stored_name": "uuid.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 245760,
      "checksum_sha256": "a665a459...",
      "folder_id": "folder-uuid",
      "dependency_id": "dep-uuid",
      "uploaded_by": "user-uuid",
      "version": 1,
      "is_deleted": false,
      "main_file_id": null,
      "file_metadata": {"doc_number": "CN-123"}
    }
  ],
  "action_logs": [...]  // Últimos 90 días si include_logs=true
}
```

---

## 🚀 API de Backup

### Crear Backup - POST /admin/backup/create

**Permisos:** Super Admin únicamente

**Parámetros (Form Data):**
- `dependency_id` (opcional): ID de dependencia para backup parcial
- `include_logs` (opcional, default=true): Incluir logs de auditoría

**Ejemplo - Backup Completo:**
```bash
curl -X POST "http://localhost:8000/admin/backup/create" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "include_logs=true"
```

**Ejemplo - Backup Parcial:**
```bash
curl -X POST "http://localhost:8000/admin/backup/create" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "dependency_id=<dep-uuid>" \
  -F "include_logs=false"
```

**Respuesta (200):**
```json
{
  "success": true,
  "message": "Backup created successfully: backup-20241201_143000",
  "backup": {
    "id": "backup-record-uuid",
    "name": "backup-20241201_143000",
    "filename": "backup-20241201_143000.tar.gz",
    "type": "comprehensive",
    "dependency_id": null,
    "total_files": 42,
    "total_size_bytes": 15728640,
    "checksum_sha256": "a665a459...",
    "created_at": "2024-12-01T14:30:15Z"
  },
  "download_url": "/admin/backups/backup-record-uuid/download"
}
```

---

## 📋 Gestión de Backups

### Listar Backups - GET /admin/backups

**Parámetros de Query:**
- `dependency_id` (opcional): Filtrar por dependencia

**Ejemplo:**
```bash
# Todos los backups
curl -X GET "http://localhost:8000/admin/backups" \
  -H "Authorization: Bearer <super-admin-token>"

# Backups de una dependencia específica
curl -X GET "http://localhost:8000/admin/backups?dependency_id=<dep-uuid>" \
  -H "Authorization: Bearer <super-admin-token>"
```

**Respuesta (200):**
```json
[
  {
    "id": "backup-uuid-1",
    "filename": "backup-20241201_143000.tar.gz",
    "backup_type": "comprehensive",
    "dependency_id": null,
    "total_files": 42,
    "total_size_bytes": 15728640,
    "checksum_sha256": "a665a459...",
    "created_at": "2024-12-01T14:30:15Z",
    "created_by": "admin-uuid",
    "download_url": "/admin/backups/backup-uuid-1/download"
  }
]
```

### Detalles de Backup - GET /admin/backups/{backup_id}

**Ejemplo:**
```bash
curl -X GET "http://localhost:8000/admin/backups/<backup-uuid>" \
  -H "Authorization: Bearer <super-admin-token>"
```

**Respuesta (200):**
```json
{
  "id": "backup-uuid",
  "filename": "backup-20241201_143000.tar.gz",
  "backup_type": "comprehensive",
  "dependency_id": null,
  "total_files": 42,
  "total_size_bytes": 15728640,
  "checksum_sha256": "a665a459...",
  "metadata": {
    "backup_version": "1.0",
    "created_at": "2024-12-01T14:30:00Z",
    "dependencies": [...],
    "folders": [...],
    "files": [...]
  },
  "created_at": "2024-12-01T14:30:15Z",
  "created_by": "admin-uuid",
  "download_url": "/admin/backups/backup-uuid/download"
}
```

### Descargar Backup - GET /admin/backups/{backup_id}/download

**Ejemplo:**
```bash
curl -X GET "http://localhost:8000/admin/backups/<backup-uuid>/download" \
  -H "Authorization: Bearer <super-admin-token>" \
  --output backup-20241201_143000.tar.gz
```

**Headers de Respuesta:**
```
Content-Disposition: attachment; filename="backup-20241201_143000.tar.gz"
Content-Type: application/gzip
Content-Length: 15728640
X-Checksum-Sha256: a665a459...
```

---

## 🔄 API de Restore

### Simular Restore - POST /admin/backup/restore

**Parámetros (Form Data):**
- `backup_file`: Archivo de backup (UploadFile)
- `strategy`: `"simulate"`
- `preserve_existing`: `true` (no aplica en simulación)
- `confirm`: `false` (no aplica en simulación)

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "backup_file=@/path/to/backup-20241201_143000.tar.gz" \
  -F "strategy=simulate" \
  -F "preserve_existing=true" \
  -F "confirm=false"
```

**Respuesta (200):**
```json
{
  "simulation": true,
  "strategy": "simulate",
  "restore_id": "restore-sim-uuid",
  "backup_info": {
    "filename": "backup-20241201_143000.tar.gz",
    "metadata_version": "1.0",
    "created_at": "2024-12-01T14:30:00Z",
    "dependency_id": null,
    "include_logs": true
  },
  "impact_report": {
    "dependencies": {
      "to_create": [
        {
          "id": "dep-uuid-1",
          "name": "Legal Department",
          "code": "LEGAL"
        }
      ],
      "conflicts": []
    },
    "folders": {
      "to_create": [
        {
          "id": "folder-uuid-1",
          "name": "2024-12",
          "path": "Legal/2024-12"
        }
      ],
      "conflicts": [
        {
          "id": "folder-uuid-2",
          "name": "2024-11",
          "path": "Legal/2024-11",
          "existing_path": "Legal/2024-11"
        }
      ]
    },
    "files": {
      "to_create": [
        {
          "id": "file-uuid-1",
          "original_name": "contrato.pdf",
          "size_bytes": 245760
        }
      ],
      "conflicts": []
    },
    "action_logs": {
      "to_create": 156
    }
  },
  "message": "Simulation completed. Review the impact report before proceeding with actual restore."
}
```

### Ejecutar Restore - POST /admin/backup/restore

**Estrategias de Restore:**

1. **`create_new_ids`** (Recomendado)
   - Crea nuevos IDs para evitar conflictos
   - Archivos se renombran con nuevos UUID
   - Datos existentes se preservan
   - Seguro para restores incrementales

2. **`overwrite`** (Peligroso)
   - Requiere `confirm=true`
   - Sobreescribe datos existentes
   - Solo para restores a sistemas limpios

**Ejemplo - Create New IDs:**
```bash
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "backup_file=@/path/to/backup-20241201_143000.tar.gz" \
  -F "strategy=create_new_ids" \
  -F "preserve_existing=true" \
  -F "confirm=false"
```

**Ejemplo - Overwrite (Peligroso):**
```bash
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -H "Authorization: Bearer <super-admin-token>" \
  -F "backup_file=@/path/to/backup-20241201_143000.tar.gz" \
  -F "strategy=overwrite" \
  -F "preserve_existing=false" \
  -F "confirm=true"
```

**Respuesta de Restore Exitoso (200):**
```json
{
  "success": true,
  "simulation": false,
  "strategy": "create_new_ids",
  "restore_id": "restore-uuid",
  "status": "completed",
  "started_at": "2024-12-01T15:00:00Z",
  "completed_at": "2024-12-01T15:02:30Z",
  "summary": {
    "dependencies_created": 1,
    "folders_created": 5,
    "files_restored": 42
  },
  "message": "Restore completed successfully using create_new_ids strategy"
}
```

---

## 🔒 Seguridad y Validaciones

### Confirmación Requerida
- **Overwrite strategy** requiere `confirm=true`
- Validación de checksum del archivo de backup
- Verificación de integridad del archivo tar.gz

### Transacciones Database
- **Rollback automático** en caso de error
- **Staging seguro** para archivos antes del commit final
- **Auditoría completa** de operaciones de restore

### Validaciones de Seguridad
- Solo **Super Admin** puede crear/listar/descargar backups
- Solo **Super Admin** puede ejecutar restores
- Validación de tipos MIME permitidos
- Límites de tamaño de archivo

---

## 📊 Monitoreo y Logs

### Logs de Operaciones
Cada operación registra eventos de auditoría:

```json
{
  "action_type": "BACKUP_CREATE",
  "target_type": "SYSTEM",
  "target_id": "backup-uuid",
  "details": {
    "filename": "backup-20241201_143000.tar.gz",
    "total_files": 42,
    "total_size_bytes": 15728640
  }
}
```

```json
{
  "action_type": "RESTORE",
  "target_type": "SYSTEM",
  "target_id": "restore-uuid",
  "details": {
    "strategy": "create_new_ids",
    "files_restored": 42,
    "dependencies_created": 1
  }
}
```

---

## 🚨 Procedimientos de Emergencia

### Antes de Restore
```bash
# 1. Crear backup de la base actual
pg_dump -h localhost -U user -d sgdi_db > emergency_backup.sql

# 2. Simular el restore
curl -X POST "http://localhost:8000/admin/backup/restore" \
  -F "backup_file=@backup.tar.gz" \
  -F "strategy=simulate"

# 3. Revisar impact_report
# 4. Ejecutar restore solo si es seguro
```

### Recuperación de Errores
- **Rollback automático** si hay errores durante restore
- **Staging cleanup** automático en caso de falla
- **Logs detallados** para diagnóstico de problemas

---

## ⚙️ Configuración

### Variables de Entorno
```bash
# Backup Configuration
BACKUP_PATH=/app/backups          # Directorio para backups
MAX_BACKUP_SIZE_MB=1000          # Tamaño máximo de backup
BACKUP_RETENTION_DAYS=30         # Días para retener backups
```

### Estructura de Directorios
```
/app/storage/                    # Archivos del sistema
├── dependencies/
│   └── <dep_code>/
│       └── <folders>/
└── temp/                        # Archivos temporales

/app/backups/                    # Backups del sistema
├── backup-20241201_143000.tar.gz
├── backup-20241130_120000.tar.gz
└── staging/                     # Área de staging para restores
    └── restore_uuid/
        ├── extracted/
        └── staged_files/
```

---

## ✅ Criterios de Aceptación Completados

✅ **Backup Creation**: POST /admin/backup/create crea tar.gz con metadata.json y archivos físicos  
✅ **Metadata Gathering**: Incluye dependencies, folders, files, action_logs (opcional)  
✅ **Physical Files**: Copia archivos usando stored_name, mantiene mapping en metadata  
✅ **Backup Records**: Almacena filename, size, checksum, created_by en DB  

✅ **Backup Listing**: GET /admin/backups retorna records con download URLs  
✅ **Backup Download**: GET /admin/backups/{id}/download stream con headers correctos  

✅ **Simulate Mode**: Retorna impact_report detallado sin cambios en DB  
✅ **Create New IDs**: Restaura con nuevos UUIDs, renombra archivos para evitar conflictos  
✅ **Overwrite Strategy**: Sobreescribe datos existentes (con confirm=true requerido)  
✅ **Transaction Safety**: Rollback automático, staging seguro, auditoría completa  

✅ **Super Admin Only**: Todas las operaciones requieren permisos de super admin  
✅ **Checksum Validation**: SHA-256 para verificar integridad de backups  
✅ **Detailed Reporting**: Impact reports, summaries, error messages específicos  

---

## 🎯 Mejores Prácticas

### Para Backups
1. **Backups regulares** usando el scheduler automático
2. **Backups parciales** por dependencia para restores selectivos
3. **Excluir logs** en backups grandes para reducir tamaño
4. **Verificar checksums** después de crear backups

### Para Restores
1. **Siempre simular primero** para ver el impact report
2. **Usar create_new_ids** para restores seguros
3. **Hacer pg_dump** antes de restores peligrosos
4. **Probar en staging** antes de producción

### Para Monitoreo
1. **Revisar logs** después de cada operación
2. **Monitorear espacio en disco** para backups
3. **Verificar integridad** periódicamente
4. **Mantener retención** apropiada de backups antiguos
