# SGDI API - Ejemplos de Uso

Documentación completa de endpoints CRUD con ejemplos curl y respuestas esperadas.

## 🔐 Autenticación

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@sgdi.local",
    "password": "securepassword123"
  }'
```

**Respuesta (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "uuid-string-here",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "user-uuid",
    "email": "admin@sgdi.local",
    "full_name": "Super Admin",
    "role": "SUPER_ADMIN",
    "dependency_id": null
  }
}
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "uuid-string-here"
  }'
```

### Logout
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "refresh_token": "uuid-string-here"
  }'
```

---

## 🏢 Dependencies API

### Listar Dependencies
```bash
# Super Admin - todas las dependencies
curl -X GET http://localhost:8000/dependencies \
  -H "Authorization: Bearer eyJ..."

# Admin - solo su dependency
curl -X GET http://localhost:8000/dependencies \
  -H "Authorization: Bearer eyJ..."

# Con paginación
curl -X GET "http://localhost:8000/dependencies?skip=0&limit=10" \
  -H "Authorization: Bearer eyJ..."
```

**Respuesta (200):**
```json
{
  "items": [
    {
      "id": "dep-uuid-1",
      "name": "Legal Department",
      "code": "LEGAL",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### Crear Dependency
```bash
curl -X POST http://localhost:8000/dependencies \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "name": "IT Department",
    "code": "IT"
  }'
```

**Respuesta (201):**
```json
{
  "id": "dep-uuid",
  "name": "IT Department",
  "code": "IT",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### Actualizar Dependency
```bash
curl -X PUT http://localhost:8000/dependencies/dep-uuid \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "name": "Information Technology"
  }'
```

### Eliminar Dependency
```bash
# Verificar contenido primero
curl -X DELETE "http://localhost:8000/dependencies/dep-uuid?force=false" \
  -H "Authorization: Bearer eyJ..."

# Forzar eliminación
curl -X DELETE "http://localhost:8000/dependencies/dep-uuid?force=true" \
  -H "Authorization: Bearer eyJ..."
```

---

## 👥 Users API

### Listar Users con Filtros
```bash
# Todos los usuarios (Super Admin)
curl -X GET http://localhost:8000/users \
  -H "Authorization: Bearer eyJ..."

# Filtrar por rol
curl -X GET "http://localhost:8000/users?role=WORKER" \
  -H "Authorization: Bearer eyJ..."

# Filtrar por dependencia
curl -X GET "http://localhost:8000/users?dependency_id=dep-uuid" \
  -H "Authorization: Bearer eyJ..."

# Buscar por email
curl -X GET "http://localhost:8000/users?email=john" \
  -H "Authorization: Bearer eyJ..."
```

**Respuesta (200):**
```json
{
  "items": [
    {
      "id": "user-uuid",
      "email": "john.doe@company.com",
      "full_name": "John Doe",
      "role": "WORKER",
      "dependency_id": "dep-uuid",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### Crear User
```bash
# Super Admin creando cualquier rol
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "email": "worker@company.com",
    "password": "securepass123",
    "full_name": "Jane Worker",
    "role": "WORKER",
    "dependency_id": "dep-uuid"
  }'

# Admin creando solo WORKER/READER en su dependency
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "email": "reader@company.com",
    "password": "securepass123",
    "full_name": "Bob Reader",
    "role": "READER",
    "dependency_id": "admin-dependency-uuid"
  }'
```

### Actualizar User
```bash
curl -X PUT http://localhost:8000/users/user-uuid \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "full_name": "John Smith",
    "is_active": false
  }'
```

### Eliminar User (Soft Delete)
```bash
curl -X DELETE http://localhost:8000/users/user-uuid \
  -H "Authorization: Bearer eyJ..."
```

---

## 📁 Folders API

### Obtener Tree Structure
```bash
curl -X GET http://localhost:8000/folders/dependencies/dep-uuid/tree \
  -H "Authorization: Bearer eyJ..."
```

**Respuesta (200):**
```json
[
  {
    "id": "folder-uuid-1",
    "name": "Legal",
    "path": "Legal",
    "parent_id": null,
    "dependency_id": "dep-uuid",
    "created_by": "user-uuid",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z",
    "children": [
      {
        "id": "folder-uuid-2",
        "name": "2025-11",
        "path": "Legal/2025-11",
        "parent_id": "folder-uuid-1",
        "dependency_id": "dep-uuid",
        "created_by": "user-uuid",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "children": []
      }
    ]
  }
]
```

### Crear Folder
```bash
# Crear folder raíz
curl -X POST http://localhost:8000/folders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "name": "Contratos",
    "dependency_id": "dep-uuid"
  }'

# Crear subfolder
curl -X POST http://localhost:8000/folders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "name": "2025",
    "parent_id": "parent-folder-uuid",
    "dependency_id": "dep-uuid"
  }'
```

### Renombrar/Mover Folder
```bash
# Renombrar
curl -X PUT http://localhost:8000/folders/folder-uuid \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "name": "Nuevo Nombre"
  }'

# Mover a otro parent
curl -X PUT http://localhost:8000/folders/folder-uuid \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "parent_id": "new-parent-uuid"
  }'
```

### Eliminar Folder
```bash
# Verificar contenido
curl -X DELETE "http://localhost:8000/folders/folder-uuid?force=false" \
  -H "Authorization: Bearer eyJ..."

# Respuesta si tiene contenido:
{
  "deleted": false,
  "items_deleted": {"subfolders": 2, "files": 5},
  "message": "Folder contains 2 subfolders and 5 files. Use force=true to delete."
}

# Forzar eliminación
curl -X DELETE "http://localhost:8000/folders/folder-uuid?force=true" \
  -H "Authorization: Bearer eyJ..."

# Respuesta exitosa:
{
  "deleted": true,
  "items_deleted": {"subfolders": 2, "files": 5},
  "message": "Folder deleted successfully"
}
```

---

## 📊 Health Check

```bash
curl -X GET http://localhost:8000/health
```

**Respuesta (200):**
```json
{
  "status": "healthy",
  "database": true,
  "storage": true
}
```

---

## ❌ Códigos de Error

### 400 Bad Request
```json
{
  "detail": "Invalid role. Must be one of: SUPER_ADMIN, ADMIN_DEP, WORKER, READER",
  "code": "VALIDATION_ERROR"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired refresh token",
  "code": "UNAUTHORIZED"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied. You can only create users in your own dependency.",
  "code": "PERMISSION_DENIED"
}
```

### 404 Not Found
```json
{
  "detail": "Dependency not found",
  "code": "NOT_FOUND",
  "resource_type": "dependency",
  "resource_id": "dep-uuid"
}
```

### 409 Conflict
```json
{
  "detail": "User with this email already exists",
  "code": "CONFLICT",
  "conflicting_resource": "email"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Too many login attempts. Please try again later.",
  "retry_after": 900,
  "attempts_remaining": 0
}
```

---

## 🔐 Permisos por Rol

| Endpoint | SUPER_ADMIN | ADMIN_DEP | WORKER | READER |
|----------|-------------|-----------|--------|--------|
| GET /dependencies | ✅ Todas | ✅ Propia | ✅ Propia | ✅ Propia |
| POST /dependencies | ✅ | ❌ | ❌ | ❌ |
| PUT /dependencies | ✅ | ❌ | ❌ | ❌ |
| DELETE /dependencies | ✅ | ❌ | ❌ | ❌ |
| GET /users | ✅ Todos | ✅ Dep + Roles bajos | ❌ | ❌ |
| POST /users | ✅ Cualquier rol | ✅ WORKER/READER en dep | ❌ | ❌ |
| PUT /users | ✅ Cualquier campo | ✅ Campos limitados | ❌ | ❌ |
| DELETE /users | ✅ | ✅ WORKER/READER en dep | ❌ | ❌ |
| GET /folders/tree | ✅ | ✅ Dep propia | ✅ Dep propia | ✅ Dep propia |
| POST /folders | ✅ | ✅ Dep propia | ❌ | ❌ |
| PUT /folders | ✅ | ✅ Dep propia | ❌ | ❌ |
| DELETE /folders | ✅ | ✅ Dep propia | ❌ | ❌ |

---

## 📝 Notas Importantes

1. **Rate Limiting**: 5 intentos de login por IP cada 15 minutos
2. **Token Rotation**: Refresh tokens se renuevan automáticamente
3. **Soft Delete**: Users se desactivan, no eliminan físicamente
4. **Path Updates**: Rename/move de folders actualiza paths recursivamente
5. **Audit Logging**: Todas las operaciones se registran con detalles completos
6. **Dependency Isolation**: Users solo pueden acceder a recursos de su dependency (excepto SUPER_ADMIN)
