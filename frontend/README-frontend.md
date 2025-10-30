# Frontend Nativo - SGDI (Sistema de Gestión Documental Institucional)

## Objetivo del Frontend

Este frontend proporciona la interfaz de usuario para el Sistema de Gestión Documental Institucional (SGDI) de FOVIS. Desarrollado completamente en **HTML, CSS y JavaScript nativo** sin frameworks, bundlers ni gestores de paquetes (Node.js/NPM).

### Funcionalidades Principales

- **Autenticación JWT**: Login, logout, refresh automático de tokens
- **Gestión de Usuarios**: CRUD completo con roles (SUPER_ADMIN, ADMIN_DEP, WORKER, READER)
- **Gestión de Dependencias**: Creación y administración de dependencias organizacionales
- **Gestión de Carpetas**: Árbol jerárquico, creación automática de carpetas mensuales
- **Gestión de Archivos**: Upload, download, versionado, anexos, soft/hard delete
- **Auditoría**: Visualización y exportación de logs de sistema
- **Backups**: Creación, descarga y restauración de backups con estrategias

## ⚠️ Nota Importante: No usar Node/NPM/React

**Este frontend es 100% nativo. NO requiere:**
- ❌ Node.js
- ❌ NPM o Yarn
- ❌ React, Vue, Angular u otros frameworks
- ❌ Webpack, Vite, Parcel u otros bundlers
- ❌ Build process
- ❌ Transpilación

**Los directorios `node_modules/`, archivos `package.json`, `package-lock.json`, etc. han sido eliminados permanentemente.**

## 🚀 Cómo Levantar Localmente

### Opción 1: Servidor HTTP Simple (Python)

```bash
cd frontend
python -m http.server 8080
```

Abre: http://localhost:8080/login.html

### Opción 2: Servidor HTTP Simple (PHP)

```bash
cd frontend
php -S localhost:8080
```

### Opción 3: Live Server (VS Code Extension)

1. Instala la extensión "Live Server" en VS Code
2. Click derecho en `login.html` → "Open with Live Server"

### Opción 4: Docker con NGINX

```bash
cd frontend/docker/nginx
docker build -t sgdi-frontend .
docker run -d -p 80:80 sgdi-frontend
```

Abre: http://localhost/login.html

## ⚙️ Configuración

### Variables de Entorno del Backend

Editar `frontend/js/config.js`:

```javascript
export const config = {
  FRONTEND_API_URL: 'http://localhost:8000',  // URL del backend FastAPI
  MAX_UPLOAD_SIZE_MB: 50,
  ALLOWED_MIME_TYPES: [
    'application/pdf',
    'text/csv',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel'
  ]
};
```

### Variables a Configurar en Servidor (Producción)

Cuando se despliega en producción, modificar `js/config.js`:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `FRONTEND_API_URL` | URL del backend API | `https://api.sgdi.fovis.gob` |
| `MAX_UPLOAD_SIZE_MB` | Tamaño máximo de archivos | `50` |
| `ALLOWED_MIME_TYPES` | MIME types permitidos | `['application/pdf', ...]` |

**Nota**: Al ser frontend estático, las "variables de entorno" son simplemente constantes JavaScript que deben editarse antes del despliegue.

## 📡 Endpoints del Backend Usados

### Autenticación (`/auth`)

#### `POST /auth/login`
Login de usuario

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@sgdi.local",
    "password": "Admin123!"
  }'
```

**Respuesta**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "admin@sgdi.local",
    "full_name": "Super Administrador",
    "role": "SUPER_ADMIN",
    "dependency_id": null,
    "is_active": true
  }
}
```

#### `POST /auth/refresh`
Refrescar token de acceso

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }'
```

#### `POST /auth/logout`
Cerrar sesión

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {access_token}" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }'
```

#### `GET /auth/verify`
Verificar token

```bash
curl -X GET http://localhost:8000/auth/verify \
  -H "Authorization: Bearer {access_token}"
```

### Usuarios (`/users`)

#### `GET /users/me`
Obtener perfil del usuario actual

```bash
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer {access_token}"
```

#### `GET /users`
Listar usuarios (Super Admin / Admin Dep)

```bash
curl -X GET "http://localhost:8000/users?skip=0&limit=100" \
  -H "Authorization: Bearer {access_token}"
```

#### `POST /users`
Crear usuario

```bash
curl -X POST http://localhost:8000/users \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo@usuario.com",
    "password": "Password123!",
    "full_name": "Nuevo Usuario",
    "role": "WORKER",
    "dependency_id": "dep-uuid",
    "is_active": true
  }'
```

#### `PUT /users/{user_id}`
Actualizar usuario

```bash
curl -X PUT http://localhost:8000/users/{user_id} \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Nombre Actualizado",
    "is_active": false
  }'
```

#### `DELETE /users/{user_id}`
Eliminar usuario

```bash
curl -X DELETE http://localhost:8000/users/{user_id} \
  -H "Authorization: Bearer {access_token}"
```

### Dependencias (`/dependencies`)

#### `GET /dependencies`
Listar dependencias

```bash
curl -X GET http://localhost:8000/dependencies \
  -H "Authorization: Bearer {access_token}"
```

#### `POST /dependencies`
Crear dependencia

```bash
curl -X POST http://localhost:8000/dependencies \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Recursos Humanos",
    "code": "RH-001"
  }'
```

#### `PUT /dependencies/{dependency_id}`
Actualizar dependencia

```bash
curl -X PUT http://localhost:8000/dependencies/{dep_id} \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RRHH Actualizado"
  }'
```

### Carpetas (`/folders`)

#### `GET /folders/{dependency_id}/tree`
Árbol de carpetas de una dependencia

```bash
curl -X GET http://localhost:8000/folders/{dep_id}/tree \
  -H "Authorization: Bearer {access_token}"
```

#### `POST /folders`
Crear carpeta

```bash
curl -X POST http://localhost:8000/folders \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "2025-01",
    "parent_id": null,
    "dependency_id": "dep-uuid"
  }'
```

#### `PUT /folders/{folder_id}/rename`
Renombrar carpeta

```bash
curl -X PUT http://localhost:8000/folders/{folder_id}/rename \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "new_name": "2025-02"
  }'
```

#### `DELETE /folders/{folder_id}`
Eliminar carpeta

```bash
curl -X DELETE "http://localhost:8000/folders/{folder_id}?force=true" \
  -H "Authorization: Bearer {access_token}"
```

### Archivos (`/files`)

#### `POST /files/upload`
Subir archivo (multipart/form-data)

```bash
curl -X POST http://localhost:8000/files/upload \
  -H "Authorization: Bearer {access_token}" \
  -F "file=@documento.pdf" \
  -F "folder_id=folder-uuid" \
  -F "dependency_id=dep-uuid"
```

#### `GET /files/{file_id}`
Obtener metadata de archivo

```bash
curl -X GET http://localhost:8000/files/{file_id} \
  -H "Authorization: Bearer {access_token}"
```

#### `GET /files/{file_id}/download`
Descargar archivo

```bash
curl -X GET http://localhost:8000/files/{file_id}/download \
  -H "Authorization: Bearer {access_token}" \
  --output archivo.pdf
```

#### `PUT /files/{file_id}`
Actualizar archivo (nueva versión)

```bash
curl -X PUT http://localhost:8000/files/{file_id} \
  -H "Authorization: Bearer {access_token}" \
  -F "file=@documento_v2.pdf"
```

#### `DELETE /files/{file_id}`
Eliminar archivo (soft delete)

```bash
curl -X DELETE http://localhost:8000/files/{file_id} \
  -H "Authorization: Bearer {access_token}"
```

#### `DELETE /files/{file_id}/permanent`
Eliminar archivo permanentemente

```bash
curl -X DELETE http://localhost:8000/files/{file_id}/permanent \
  -H "Authorization: Bearer {access_token}"
```

### Auditoría (`/audit`)

#### `GET /audit/logs`
Obtener logs de auditoría

```bash
curl -X GET "http://localhost:8000/audit/logs?limit=50&offset=0&action_type=CREATE_FILE" \
  -H "Authorization: Bearer {access_token}"
```

#### `GET /audit/logs?format=csv`
Exportar logs a CSV

```bash
curl -X GET "http://localhost:8000/audit/logs?format=csv&start_date=2025-01-01" \
  -H "Authorization: Bearer {access_token}" \
  --output logs.csv
```

#### `GET /audit/user/{user_id}`
Logs de un usuario específico

```bash
curl -X GET http://localhost:8000/audit/user/{user_id} \
  -H "Authorization: Bearer {access_token}"
```

#### `GET /audit/file/{file_id}`
Logs de un archivo específico

```bash
curl -X GET http://localhost:8000/audit/file/{file_id} \
  -H "Authorization: Bearer {access_token}"
```

### Backups (`/admin/backups`)

#### `POST /admin/backups/create`
Crear backup

```bash
curl -X POST "http://localhost:8000/admin/backups/create?dependency_id=dep-uuid" \
  -H "Authorization: Bearer {access_token}"
```

#### `GET /admin/backups`
Listar backups

```bash
curl -X GET http://localhost:8000/admin/backups \
  -H "Authorization: Bearer {access_token}"
```

#### `GET /admin/backups/{backup_id}/download`
Descargar backup

```bash
curl -X GET http://localhost:8000/admin/backups/{backup_id}/download \
  -H "Authorization: Bearer {access_token}" \
  --output backup.tar.gz
```

#### `POST /admin/backups/restore`
Restaurar backup

```bash
curl -X POST http://localhost:8000/admin/backups/restore \
  -H "Authorization: Bearer {access_token}" \
  -F "file=@backup.tar.gz" \
  -F "strategy=simulate" \
  -F "preserve_existing=true"
```

### Carpetas Mensuales (`/admin`)

#### `POST /admin/force-create-month-folders`
Forzar creación de carpetas mensuales

```bash
curl -X POST "http://localhost:8000/admin/force-create-month-folders?month=2025-01" \
  -H "Authorization: Bearer {access_token}"
```

## 🏗️ Arquitectura del Frontend

### Módulos JavaScript (ES6)

```
js/
├── lib/
│   ├── fetch-wrapper.js    # Cliente HTTP con interceptors, retry, JWT
│   └── validators.js       # Validaciones de formularios
├── auth.js                 # Gestión de autenticación y sesión
├── router.js               # Enrutamiento SPA (hash o history)
├── ui.js                   # Utilidades UI (modales, toasts, loading)
├── dashboard.js            # Lógica del dashboard
├── folders.js              # Gestión de carpetas
├── files.js                # Gestión de archivos y uploads
├── users.js                # CRUD de usuarios
├── audit.js                # Visualización de logs
├── backups.js              # Gestión de backups
└── main.js                 # Punto de entrada de la aplicación
```

### Estilos CSS

```
css/
├── base.css           # Reset, variables CSS, tipografía
├── layout.css         # Grid, sidebar, navbar, contenedores
├── components.css     # Botones, forms, cards, modales, etc.
└── responsive.css     # Media queries para móviles/tablets
```

### Uso de Módulos ES6

```html
<script type="module" src="js/main.js"></script>
```

```javascript
// En js/main.js
import { auth } from './auth.js';
import { router } from './router.js';
import { ui } from './ui.js';

// Inicializar app
auth.init();
router.init();
```

## 🧪 Testing

Ver `tests/e2e_instructions.md` para instrucciones completas de testing manual y E2E con Playwright.

### Seed de Usuario SuperAdmin (Requerido)

```bash
cd sgdi-backend

# Configurar variables de entorno
export SUPERADMIN_EMAIL="admin@sgdi.local"
export SUPERADMIN_PASSWORD="Admin123!"
export SUPERADMIN_FULL_NAME="Super Administrador"

# Ejecutar script de seed
python scripts/seed_superadmin.py
```

### Checklist de Testing Rápido

- [ ] Login funciona con credenciales correctas
- [ ] Refresh token automático funciona (dejar tab abierto > 30 min)
- [ ] Crear carpeta actualiza árbol sin reload
- [ ] Upload con anexos crea carpeta automática
- [ ] Download devuelve archivo original
- [ ] Backup completo se genera
- [ ] Simulate restore muestra reporte
- [ ] Audit logs muestra acciones
- [ ] CSV export descarga archivo
- [ ] Navegación por teclado funciona

## 🐳 Despliegue con Docker

### Build y Run (Standalone)

```bash
cd frontend/docker/nginx
docker build -t sgdi-frontend .
docker run -d -p 8080:80 --name sgdi-frontend sgdi-frontend
```

### Docker Compose (Integrado con Backend)

Agregar al `docker-compose.yml` del backend:

```yaml
services:
  # ... (postgres, api, etc.)
  
  frontend:
    build:
      context: ../frontend
      dockerfile: docker/nginx/Dockerfile
    container_name: sgdi-frontend
    ports:
      - "8080:80"
    volumes:
      # Para desarrollo (hot-reload sin rebuild)
      - ../frontend:/usr/share/nginx/html:ro
    networks:
      - sgdi-network
    depends_on:
      - api
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
```

### Ejecutar Stack Completo

```bash
# Desde raíz del proyecto
docker-compose up -d

# Ver logs
docker-compose logs -f frontend

# Acceder
# Frontend: http://localhost:8080
# API Docs: http://localhost:8000/docs
```

## 📦 Despliegue en Servidor (Sin Docker)

### Opción 1: Copiar a Webroot de NGINX

```bash
# 1. Copiar archivos
sudo mkdir -p /var/www/sgdi
sudo cp -r frontend/ /var/www/sgdi/

# 2. Configurar permisos
sudo chown -R www-data:www-data /var/www/sgdi
sudo chmod -R 755 /var/www/sgdi

# 3. Crear configuración NGINX
sudo nano /etc/nginx/sites-available/sgdi
```

**Contenido de `/etc/nginx/sites-available/sgdi`:**

```nginx
# Redirigir HTTP a HTTPS (producción)
server {
    listen 80;
    listen [::]:80;
    server_name sgdi.fovis.gob;
    
    return 301 https://$host$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name sgdi.fovis.gob;
    
    # Certificados SSL (Let's Encrypt o similar)
    ssl_certificate /etc/letsencrypt/live/sgdi.fovis.gob/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sgdi.fovis.gob/privkey.pem;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Root y index
    root /var/www/sgdi;
    index login.html index.html;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://api.sgdi.fovis.gob; frame-ancestors 'self';" always;
    
    # API Proxy (ajustar según tu backend)
    location /api/ {
        rewrite ^/api/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts para uploads grandes
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffering off para streaming
        proxy_buffering off;
        proxy_request_buffering off;
    }
    
    # Archivos estáticos con cache
    location ~* \.(jpg|jpeg|png|gif|ico|svg|webp|woff|woff2|ttf|eot|otf)$ {
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
        access_log off;
    }
    
    location ~* \.(css)$ {
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }
    
    location ~* \.(js|mjs)$ {
        expires 6h;
        add_header Cache-Control "public, max-age=21600";
    }
    
    # HTML sin cache
    location ~* \.(html)$ {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }
    
    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Negar acceso a archivos ocultos
    location ~ /\. {
        deny all;
    }
    
    # Gzip
    gzip on;
    gzip_vary on;
    gzip_types text/css application/javascript image/svg+xml;
    
    # Client upload limits
    client_max_body_size 200M;
}
```

```bash
# 4. Habilitar sitio
sudo ln -s /etc/nginx/sites-available/sgdi /etc/nginx/sites-enabled/

# 5. Test de configuración
sudo nginx -t

# 6. Reiniciar NGINX
sudo systemctl restart nginx

# 7. Verificar status
sudo systemctl status nginx
```

### Opción 2: Despliegue con Apache

```bash
# 1. Copiar archivos
sudo cp -r frontend/ /var/www/sgdi/

# 2. Crear VirtualHost
sudo nano /etc/apache2/sites-available/sgdi.conf
```

**Contenido de `/etc/apache2/sites-available/sgdi.conf`:**

```apache
<VirtualHost *:80>
    ServerName sgdi.fovis.gob
    DocumentRoot /var/www/sgdi
    
    <Directory /var/www/sgdi>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        
        # SPA fallback
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>
    
    # API Proxy
    ProxyPass /api/ http://127.0.0.1:8000/
    ProxyPassReverse /api/ http://127.0.0.1:8000/
    
    # Security Headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"
    
    ErrorLog ${APACHE_LOG_DIR}/sgdi-error.log
    CustomLog ${APACHE_LOG_DIR}/sgdi-access.log combined
</VirtualHost>
```

```bash
# 3. Habilitar módulos
sudo a2enmod rewrite proxy proxy_http headers

# 4. Habilitar sitio
sudo a2ensite sgdi

# 5. Reiniciar Apache
sudo systemctl restart apache2
```

### Configurar HTTPS con Let's Encrypt

```bash
# Instalar Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtener certificado (NGINX)
sudo certbot --nginx -d sgdi.fovis.gob

# Obtener certificado (Apache)
sudo certbot --apache -d sgdi.fovis.gob

# Auto-renewal (ya configurado por defecto)
sudo certbot renew --dry-run
```

## 🔒 Seguridad

### Notas de Seguridad Críticas

#### ⚠️ localStorage y Tokens

**Riesgo:** Los tokens se almacenan en `localStorage`, lo que los hace vulnerables a ataques XSS.

**Recomendaciones para producción:**

1. **Usar httpOnly Cookies:**
   - Modificar backend para enviar tokens en cookies con flags `httpOnly`, `secure`, `sameSite`
   - Eliminar tokens de respuesta JSON
   - Modificar `fetch-wrapper.js` para no enviar header `Authorization` manualmente

2. **Implementar CSP estricto:**
   - Ya incluido en `nginx.conf`
   - No permitir `eval()`, inline scripts (excepto necesarios)

3. **Sanitizar inputs:**
   - Ya implementado en `escapeHtml()` en todos los módulos
   - Validaciones en `validators.js`

4. **HTTPS obligatorio en producción:**
   - Redirigir todo HTTP → HTTPS
   - HSTS header

#### 🛡️ Medidas Implementadas

- ✅ **XSS Prevention:** Escape de HTML en todas las salidas
- ✅ **CSRF:** Backend debe implementar tokens CSRF si no usa SameSite cookies
- ✅ **Rate Limiting:** Backend debe limitar requests por IP
- ✅ **Anti-brute force:** Cliente bloquea UI por 30s después de 5 intentos fallidos
- ✅ **Security Headers:** CSP, X-Frame-Options, X-Content-Type-Options, etc.
- ✅ **No eval():** Cero uso de `eval()` o `Function()` constructor
- ✅ **Input Validation:** Validaciones client-side y server-side

### Checklist de Seguridad Pre-Producción

- [ ] Cambiar `FRONTEND_API_URL` a HTTPS
- [ ] Configurar CORS en backend para dominio específico (no `*`)
- [ ] Habilitar HTTPS con certificado válido
- [ ] Configurar HSTS header
- [ ] Implementar httpOnly cookies para tokens
- [ ] Rate limiting en backend activado
- [ ] Logs de auditoría habilitados
- [ ] Backups automáticos configurados
- [ ] Firewall configurado (solo puertos 80, 443)
- [ ] Deshabilitar directorio listing
- [ ] Passwords de admin cambiados de defaults

## 🐛 Troubleshooting

### Problema: CORS Errors

**Síntoma:** `Access-Control-Allow-Origin` error en console

**Solución:**

Verificar CORS en backend `sgdi-backend/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "https://sgdi.fovis.gob"],  # Específico, no "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Problema: Token Expired Rápido

**Síntoma:** Se cierra sesión cada pocos minutos

**Solución:**

1. Aumentar tiempo en backend `.env`:
```env
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
```

2. Verificar que refresh automático funciona:
```javascript
// En DevTools Console
localStorage.getItem('refresh_token')  // Debe existir
```

3. Ver logs de refresh en Network tab (debe llamar `/auth/refresh` automáticamente)

### Problema: Upload Falla con Archivos Grandes

**Síntoma:** Timeout o error 413 (Payload Too Large)

**Solución:**

1. **NGINX:** Aumentar `client_max_body_size`:
```nginx
client_max_body_size 200M;
client_body_timeout 300s;
```

2. **Backend (uvicorn):**
```bash
uvicorn app.main:app --timeout-keep-alive 300
```

3. **Frontend:** Aumentar timeout en `fetch-wrapper.js`:
```javascript
const TIMEOUT_MS = 300000;  // 5 minutos
```

### Problema: Árbol de Carpetas No Carga

**Síntoma:** Spinner infinito o error

**Pasos de debugging:**

1. Abrir DevTools → Network
2. Buscar request fallido
3. Verificar status code:
   - **401:** Token expirado → refresh manual
   - **403:** Sin permisos → verificar rol
   - **404:** Endpoint no existe → verificar URL backend
   - **500:** Error servidor → revisar logs backend
4. Ver `X-Request-Id` en response headers
5. Buscar ese ID en logs del backend:
```bash
docker logs sgdi-api | grep "request-id-aqui"
```

### Problema: Backup No Descarga

**Síntoma:** Click en descargar no hace nada

**Solución:**

1. Verificar browser no bloqueó descarga (popup blocker)
2. Verificar header `Content-Disposition` en response
3. Método alternativo en console:
```javascript
const url = 'http://localhost:8000/admin/backups/{id}/download';
const a = document.createElement('a');
a.href = url;
a.download = 'backup.tar.gz';
a.click();
```

### Problema: localStorage Quota Exceeded

**Síntoma:** `QuotaExceededError` al guardar sesión

**Solución:**

```javascript
// Limpiar localStorage
localStorage.clear();

// O selectivo
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
localStorage.removeItem('user');
```

### Problema: Módulos ES6 No Cargan

**Síntoma:** `Uncaught SyntaxError: Cannot use import statement outside a module`

**Solución:**

Verificar `<script type="module">` en HTML:

```html
<!-- ✅ Correcto -->
<script type="module" src="js/main.js"></script>

<!-- ❌ Incorrecto -->
<script src="js/main.js"></script>
```

### Problema: 404 en Rutas SPA

**Síntoma:** Refresh en `/dashboard` da 404

**Solución:**

Verificar configuración SPA fallback en NGINX:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

O usar hash routing:

```javascript
// En router.js
const path = window.location.hash.substring(1) || '/';
```

## 📚 Recursos

- **Documentación API**: http://localhost:8000/docs
- **Backend GitHub**: [sgdi-backend](../sgdi-backend)
- **FOVIS**: https://fovis.gob
- **Synera**: Desarrollador

## 📄 Licencia

Desarrollado para FOVIS - Synera © 2025

---

**Frontend nativo sin Node.js, NPM, React ni frameworks. Código 100% HTML/CSS/JavaScript estándar.**

