# SGDI File Management API - Ejemplos

Documentación completa de operaciones de archivos con ejemplos curl.

## 📤 Upload de Archivos

### Upload de Archivo Principal (sin anexos)

```bash
curl -X POST "http://localhost:8000/files/upload" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -F "file=@/path/to/Contrato.pdf" \
  -F "folder_id=<folder-uuid>" \
  -F 'metadata={"doc_number":"CN-123","tags":["contrato","proveedor"],"has_annexes":false}'
```

**Respuesta (201):**
```json
{
  "main_file": {
    "id": "file-uuid",
    "original_name": "Contrato.pdf",
    "stored_name": "uuid.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 245760,
    "checksum_sha256": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
    "folder_id": "folder-uuid",
    "dependency_id": "dep-uuid",
    "uploaded_by": "user-uuid",
    "version": 1,
    "is_deleted": false,
    "main_file_id": null,
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-01T10:00:00Z"
  },
  "annex_files": null,
  "annex_folder": null
}
```

### Upload con Anexos (crea carpeta automática)

```bash
curl -X POST "http://localhost:8000/files/upload" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -F "file=@/path/to/Contrato.pdf" \
  -F "anexos=@/path/to/AnexoA.pdf" \
  -F "anexos=@/path/to/AnexoB.xlsx" \
  -F "anexos=@/path/to/Fotos.zip" \
  -F "folder_id=<folder-uuid>" \
  -F 'metadata={"doc_number":"CN-123","tags":["contrato","proveedor"],"has_annexes":true}' \
  -F "create_annex_folder=true"
```

**Respuesta (201):**
```json
{
  "main_file": {
    "id": "main-file-uuid",
    "original_name": "Contrato.pdf",
    "stored_name": "uuid.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 245760,
    "checksum_sha256": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
    "folder_id": "folder-uuid",
    "dependency_id": "dep-uuid",
    "uploaded_by": "user-uuid",
    "version": 1,
    "is_deleted": false,
    "main_file_id": null,
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-01T10:00:00Z"
  },
  "annex_folder": {
    "id": "annex-folder-uuid",
    "name": "Anexos-Contrato-20241201",
    "path": "Contracts/Anexos-Contrato-20241201"
  },
  "annex_files": [
    {
      "id": "annex1-uuid",
      "original_name": "AnexoA.pdf",
      "stored_name": "uuid.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 102400,
      "checksum_sha256": "b665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae4",
      "folder_id": "annex-folder-uuid",
      "dependency_id": "dep-uuid",
      "uploaded_by": "user-uuid",
      "version": 1,
      "is_deleted": false,
      "main_file_id": "main-file-uuid",
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T10:00:00Z"
    },
    {
      "id": "annex2-uuid",
      "original_name": "AnexoB.xlsx",
      "stored_name": "uuid.xlsx",
      "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "size_bytes": 51200,
      "checksum_sha256": "c665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae5",
      "folder_id": "annex-folder-uuid",
      "dependency_id": "dep-uuid",
      "uploaded_by": "user-uuid",
      "version": 1,
      "is_deleted": false,
      "main_file_id": "main-file-uuid",
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T10:00:00Z"
    }
  ]
}
```

### Upload sin Crear Carpeta de Anexos

```bash
curl -X POST "http://localhost:8000/files/upload" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -F "file=@/path/to/Documento.pdf" \
  -F "anexos=@/path/to/Anexo.pdf" \
  -F "folder_id=<folder-uuid>" \
  -F "create_annex_folder=false"
```

---

## 📥 Download de Archivos

### Download de Archivo

```bash
curl -X GET "http://localhost:8000/files/<file-uuid>/download" \
  -H "Authorization: Bearer <your-jwt-token>" \
  --output downloaded_file.pdf
```

**Headers de Respuesta:**
```
Content-Disposition: attachment; filename="Contrato.pdf"
Content-Type: application/pdf
Content-Length: 245760
X-Checksum-Sha256: a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3
```

### Verificar Integridad del Download

```bash
# Calcular checksum del archivo descargado
shasum -a 256 downloaded_file.pdf

# Comparar con el header X-Checksum-Sha256
# Deben coincidir para confirmar integridad
```

---

## ✏️ Update de Archivos (Versionado)

### Actualizar Contenido de Archivo

```bash
curl -X PUT "http://localhost:8000/files/<file-uuid>" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -F "file=@/path/to/Contrato_Actualizado.pdf" \
  -F 'metadata={"doc_number":"CN-123-v2","tags":["contrato","proveedor","actualizado"]}'
```

**Respuesta (200):**
```json
{
  "id": "file-uuid",
  "original_name": "Contrato_Actualizado.pdf",
  "stored_name": "new-uuid.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 278432,
  "checksum_sha256": "d665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae6",
  "folder_id": "folder-uuid",
  "dependency_id": "dep-uuid",
  "uploaded_by": "user-uuid",
  "version": 2,
  "is_deleted": false,
  "main_file_id": null,
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-01T11:30:00Z"
}
```

### Ver Versiones de un Archivo

```bash
curl -X GET "http://localhost:8000/files/<file-uuid>/versions" \
  -H "Authorization: Bearer <your-jwt-token>"
```

**Respuesta (200):**
```json
{
  "file_id": "file-uuid",
  "current_version": 2,
  "versions": [
    {
      "version": 1,
      "filename": "file-uuid_v1_20241201_100000.pdf",
      "created_at": "2025-01-01T10:00:00Z",
      "size_bytes": 245760,
      "checksum": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
    },
    {
      "version": 2,
      "filename": "file-uuid_v2_20241201_113000.pdf",
      "created_at": "2025-01-01T11:30:00Z",
      "size_bytes": 278432,
      "checksum": "d665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae6"
    }
  ]
}
```

---

## 🗑️ Delete de Archivos

### Soft Delete (Marcar como Eliminado)

```bash
curl -X DELETE "http://localhost:8000/files/<file-uuid>" \
  -H "Authorization: Bearer <your-jwt-token>"
```

**Respuesta (200):**
```json
{
  "deleted": true,
  "deleted_files": ["file-uuid"],
  "message": "File marked as deleted. 1 files affected."
}
```

### Hard Delete (Eliminar Permanentemente)

```bash
curl -X DELETE "http://localhost:8000/files/<file-uuid>?hard=true" \
  -H "Authorization: Bearer <your-jwt-token>"
```

**Respuesta (200):**
```json
{
  "deleted": true,
  "deleted_files": ["file-uuid"],
  "message": "File hard deleted successfully. Deleted 1 files."
}
```

### Eliminar Archivo con Anexos (Requiere confirmación)

```bash
# Intentar eliminar sin cascade (bloqueará)
curl -X DELETE "http://localhost:8000/files/<main-file-uuid>?hard=true" \
  -H "Authorization: Bearer <your-jwt-token>"
```

**Respuesta (409):**
```json
{
  "deleted": false,
  "deleted_files": ["annex1-uuid", "annex2-uuid"],
  "message": "File has 2 annexes. Use cascade=true to delete them too."
}
```

```bash
# Eliminar con cascade
curl -X DELETE "http://localhost:8000/files/<main-file-uuid>?hard=true&cascade=true" \
  -H "Authorization: Bearer <your-jwt-token>"
```

**Respuesta (200):**
```json
{
  "deleted": true,
  "deleted_files": ["main-file-uuid", "annex1-uuid", "annex2-uuid"],
  "message": "File hard deleted successfully. Deleted 3 files."
}
```

---

## 📋 Gestión de Anexos

### Listar Anexos de un Archivo

```bash
curl -X GET "http://localhost:8000/files/<main-file-uuid>/anexos" \
  -H "Authorization: Bearer <your-jwt-token>"
```

**Respuesta (200):**
```json
[
  {
    "id": "annex1-uuid",
    "original_name": "AnexoA.pdf",
    "stored_name": "uuid.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 102400,
    "checksum_sha256": "b665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae4",
    "folder_id": "annex-folder-uuid",
    "dependency_id": "dep-uuid",
    "uploaded_by": "user-uuid",
    "version": 1,
    "is_deleted": false,
    "main_file_id": "main-file-uuid",
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-01T10:00:00Z"
  }
]
```

---

## 📊 Listado de Archivos

### Listar Archivos con Filtros

```bash
# Todos los archivos en una carpeta
curl -X GET "http://localhost:8000/files?folder_id=<folder-uuid>" \
  -H "Authorization: Bearer <your-jwt-token>"

# Filtrar por tipo MIME
curl -X GET "http://localhost:8000/files?mime_type=application/pdf" \
  -H "Authorization: Bearer <your-jwt-token>"

# Filtrar por usuario que subió
curl -X GET "http://localhost:8000/files?uploaded_by=<user-uuid>" \
  -H "Authorization: Bearer <your-jwt-token>"

# Incluir archivos eliminados
curl -X GET "http://localhost:8000/files?is_deleted=true" \
  -H "Authorization: Bearer <your-jwt-token>"

# Paginación
curl -X GET "http://localhost:8000/files?skip=0&limit=50" \
  -H "Authorization: Bearer <your-jwt-token>"
```

**Respuesta (200):**
```json
{
  "items": [
    {
      "id": "file-uuid",
      "original_name": "Contrato.pdf",
      "stored_name": "uuid.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 245760,
      "checksum_sha256": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
      "folder_id": "folder-uuid",
      "dependency_id": "dep-uuid",
      "uploaded_by": "user-uuid",
      "version": 1,
      "is_deleted": false,
      "main_file_id": null,
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

## ❌ Códigos de Error

### 400 Bad Request
```json
{
  "detail": "Invalid metadata JSON: Expecting ',' delimiter: line 1 column 25 (char 24)",
  "code": "VALIDATION_ERROR"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied. You can only upload to folders in your dependency.",
  "code": "PERMISSION_DENIED"
}
```

### 404 Not Found
```json
{
  "detail": "File not found",
  "code": "NOT_FOUND",
  "resource_type": "file",
  "resource_id": "file-uuid"
}
```

### 409 Conflict
```json
{
  "detail": "File has 2 annexes. Use cascade=true to delete them too.",
  "code": "CONFLICT"
}
```

### 413 Payload Too Large
```json
{
  "detail": "File too large. Maximum size: 50MB",
  "code": "PAYLOAD_TOO_LARGE"
}
```

### 415 Unsupported Media Type
```json
{
  "detail": "Unsupported file type: application/x-msdownload",
  "code": "UNSUPPORTED_MEDIA_TYPE"
}
```

---

## 🔐 Permisos por Rol

| Operación | SUPER_ADMIN | ADMIN_DEP | WORKER | READER |
|-----------|-------------|-----------|--------|--------|
| Upload | ✅ | ✅ (dep propia) | ✅ (dep propia) | ❌ |
| Download | ✅ | ✅ (dep propia) | ✅ (dep propia) | ✅ (dep propia) |
| Update | ✅ | ✅ (dep propia) | ✅ (solo propios) | ❌ |
| Delete | ✅ | ✅ (dep propia) | ❌ | ❌ |
| List | ✅ | ✅ (dep propia) | ✅ (dep propia) | ✅ (dep propia) |

---

## 📁 Estructura de Almacenamiento

```
STORAGE_PATH/
├── dependencies/
│   └── <dependency_code>/
│       └── <folder_path>/
│           ├── files/
│           │   ├── <stored_name>  # Archivos actuales
│           └── versions/
│               └── <file_id>_v<version>_<timestamp>.<ext>  # Versiones anteriores
├── temp/
│   └── <uuid>.<ext>  # Archivos temporales durante upload
└── trash/
    └── <timestamp>_deleted_<stored_name>  # Archivos eliminados permanentemente
```

---

## ⚡ Características Avanzadas

1. **Atomicidad**: Uploads con anexos son transaccionales
2. **Versionado**: Mantiene historial completo de versiones
3. **Checksums**: SHA-256 para verificar integridad
4. **Safe Storage**: Archivos temporales y moves atómicos
5. **Annex Management**: Carpetas automáticas para anexos
6. **Audit Logging**: Registro completo de todas las operaciones
7. **Permission Checks**: Validación granular por rol y dependencia
8. **File Validation**: Tamaño y tipo MIME validados
