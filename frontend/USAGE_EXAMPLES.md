# SGDI Frontend - Ejemplos de Uso

## 📚 Tabla de Contenido

1. [Fetch Wrapper](#fetch-wrapper)
2. [Autenticación](#autenticación)
3. [Validadores](#validadores)
4. [UI Components](#ui-components)
5. [Integración Completa](#integración-completa)

---

## Fetch Wrapper

### GET Request con Parámetros

```javascript
import { fetchWrapper } from './js/lib/fetch-wrapper.js';

// Simple GET
const dependencies = await fetchWrapper.get('/dependencies');

// GET con query params
const users = await fetchWrapper.get('/users', {
  role: 'WORKER',
  active: true,
  limit: 10
});
// Genera: /users?role=WORKER&active=true&limit=10
```

### POST Request

```javascript
// Crear nueva dependencia
const newDep = await fetchWrapper.post('/dependencies', {
  name: 'Departamento Legal',
  code: 'DEP-LEGAL',
  description: 'Departamento de asuntos legales'
});

// Login (sin token automático)
const response = await fetchWrapper.post('/auth/login', {
  email: 'admin@sgdi.local',
  password: 'SecurePassword123!'
});
```

### PUT/PATCH Request

```javascript
// Actualizar usuario completo (PUT)
const updated = await fetchWrapper.put('/users/user-uuid-123', {
  full_name: 'Juan Pérez Actualizado',
  email: 'juan.nuevo@email.com',
  role: 'ADMIN_DEP'
});

// Actualizar parcialmente (PATCH)
const patched = await fetchWrapper.patch('/users/user-uuid-123', {
  full_name: 'Solo cambio el nombre'
});
```

### DELETE Request

```javascript
// Eliminar usuario
await fetchWrapper.delete('/users/user-uuid-123');

// Eliminar archivo
await fetchWrapper.delete('/files/file-uuid-456');
```

### Upload con Progreso

```javascript
// Preparar FormData
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('folder_id', 'folder-uuid-789');
formData.append('description', 'Documento importante');

// Anexos opcionales
if (annexInput.files.length > 0) {
  for (let i = 0; i < annexInput.files.length; i++) {
    formData.append('annexes', annexInput.files[i]);
  }
}

// Upload con callback de progreso
try {
  const result = await fetchWrapper.upload(
    '/files/upload',
    formData,
    (percent) => {
      // Actualizar barra de progreso
      progressBar.style.width = `${percent}%`;
      progressText.textContent = `${percent}%`;
    }
  );
  
  console.log('Upload exitoso:', result);
} catch (error) {
  console.error('Error en upload:', error);
}
```

### Download de Archivos

```javascript
// Download simple
await fetchWrapper.download('/files/file-uuid-123/download', 'documento.pdf');

// Download de backup
await fetchWrapper.download('/admin/backups/backup-uuid/download', 'backup-20250129.tar.gz');

// Download con manejo de errores
try {
  await fetchWrapper.download(`/files/${fileId}/download`, filename);
  ui.success('Archivo descargado correctamente');
} catch (error) {
  ui.error('Error al descargar el archivo');
}
```

### Características Automáticas

**Retry Automático (solo GET):**
```javascript
// Si falla por timeout o network error, se reintenta 2 veces con backoff exponencial
const data = await fetchWrapper.get('/api/slow-endpoint');
// 1er intento → falla → espera 1s → 2do intento → falla → espera 2s → 3er intento
```

**Refresh Token Automático:**
```javascript
// Si recibe 401, automáticamente:
// 1. Llama a POST /auth/refresh con refresh_token
// 2. Obtiene nuevo access_token
// 3. Reintenta la petición original una sola vez
// 4. Si refresh falla, limpia tokens y redirige a login

const data = await fetchWrapper.get('/protected-resource');
// Usuario no necesita manejar refresh manualmente
```

**X-Request-Id Automático:**
```javascript
// Cada petición incluye header X-Request-Id con UUID v4
// Útil para correlacionar con logs del backend
```

---

## Autenticación

### Login

```javascript
import { auth } from './js/auth.js';

// Login básico
try {
  const response = await auth.login('admin@sgdi.local', 'Admin123!');
  console.log('Usuario autenticado:', response.user);
  
  // Redirigir a dashboard
  window.location.href = '/dashboard.html';
} catch (error) {
  if (error.status === 401) {
    alert('Credenciales inválidas');
  } else if (error.status === 429) {
    alert('Demasiadas peticiones, intenta más tarde');
  } else if (error.isLockout) {
    alert(error.message); // "Demasiados intentos, espera X segundos"
  } else {
    alert('Error al iniciar sesión');
  }
}
```

### Verificar Autenticación

```javascript
// Verificar si está autenticado (con refresh automático si expiró)
if (await auth.isAuthenticated()) {
  console.log('Usuario autenticado');
} else {
  console.log('Usuario no autenticado');
  window.location.href = '/login.html';
}

// Verificar token (sin refresh automático)
const isValid = await auth.verifyToken();
```

### Obtener Información del Usuario

```javascript
// Usuario actual (desde localStorage)
const user = auth.getCurrentUser();
console.log(user.full_name);
console.log(user.email);
console.log(user.role);
console.log(user.dependency_id);

// Obtener perfil actualizado del servidor
const profile = await auth.getProfile();
console.log(profile);

// Tokens
const accessToken = auth.getAccessToken();
const refreshToken = auth.getRefreshToken();
```

### Verificar Roles y Permisos

```javascript
// Verificar rol específico
if (auth.hasRole('SUPER_ADMIN')) {
  console.log('Es super admin');
}

// Helpers de roles
if (auth.isSuperAdmin()) {
  // Mostrar opciones de super admin
}

if (auth.isAdminDep()) {
  // Mostrar opciones de admin de dependencia
}

if (auth.isWorker()) {
  // Acceso limitado
}

if (auth.isReader()) {
  // Solo lectura
}

// Obtener nombre legible del rol
const roleName = auth.getRoleName('SUPER_ADMIN');
// → "Super Administrador"
```

### Proteger Rutas

```javascript
// En páginas que requieren autenticación
// (al inicio del script)
import { auth } from './js/auth.js';

// Proteger cualquier página
auth.requireAuth(); // Redirige a login si no autenticado

// Proteger páginas de super admin
auth.requireSuperAdmin(); // Redirige si no es super admin

// Proteger con rol específico
auth.requireRole('ADMIN_DEP'); // Redirige si no tiene el rol

// Ejemplo completo
if (!auth.requireAuth()) {
  // Ya redirigió a login, salir
  throw new Error('Not authenticated');
}

if (!auth.isSuperAdmin() && !auth.isAdminDep()) {
  alert('No tienes permisos para esta página');
  window.location.href = '/dashboard.html';
}
```

### Actualizar Perfil

```javascript
// Actualizar información del usuario
const updated = await auth.updateProfile({
  full_name: 'Nuevo Nombre',
  phone: '+56912345678'
});

// Cambiar contraseña
try {
  await auth.changePassword('oldPassword123', 'newPassword456!');
  ui.success('Contraseña cambiada correctamente');
} catch (error) {
  if (error.status === 401) {
    ui.error('Contraseña actual incorrecta');
  } else {
    ui.error('Error al cambiar contraseña');
  }
}
```

### Logout

```javascript
// Logout simple
await auth.logout();
// Limpia tokens, limpia localStorage, redirige a login

// Logout con confirmación
if (confirm('¿Seguro que deseas cerrar sesión?')) {
  await auth.logout();
}
```

### Actualizar UI con Datos del Usuario

```javascript
// Después del login o al cargar la página
auth.attachAuthToUI();

// Esto actualiza automáticamente:
// - #userName → user.full_name
// - #userRole → "Super Administrador"
// - #userAvatar → Primera letra del nombre
// - #userEmail → user.email
// - Oculta elementos según rol ([data-role], [data-permission])
```

### Anti-Brute Force (Cliente)

```javascript
// El auth module maneja automáticamente:
// - Cuenta intentos fallidos (max 5)
// - Bloquea UI por 30 segundos
// - Muestra tiempo restante

// Verificar manualmente si hay bloqueo
const lockoutSeconds = auth.isLockedOut();
if (lockoutSeconds) {
  alert(`Espera ${lockoutSeconds} segundos antes de intentar de nuevo`);
}

// Resetear intentos (automático en login exitoso)
auth.resetLoginAttempts();
```

---

## Validadores

```javascript
import { validators } from './js/lib/validators.js';

// Required
const error = validators.required(value, 'El nombre');
// → "El nombre es requerido" si vacío, null si OK

// Email
validators.email('invalid-email'); // → "Email inválido"
validators.email('user@example.com'); // → null

// Password fuerte
validators.password('weak'); // → "La contraseña debe tener..."
validators.password('Strong123!'); // → null

// Longitud
validators.minLength('ab', 3, 'El código'); // → "El código debe tener al menos 3 caracteres"
validators.maxLength('texto largo', 5, 'El código'); // → "El código no puede tener más de 5 caracteres"

// Matches (confirmar contraseña)
validators.matches('pass123', 'pass456', 'Las contraseñas'); // → "Las contraseñas no coinciden"

// Número
validators.number('abc'); // → "Este campo debe ser un número"
validators.positive(-5); // → "Este campo debe ser un número positivo"
validators.range(150, 1, 100, 'La edad'); // → "La edad debe estar entre 1 y 100"

// Fecha
validators.date('2025-13-40'); // → "La fecha no es válida"
validators.date('2025-01-29'); // → null

// URL
validators.url('not-a-url'); // → "La URL no es válida"
validators.url('https://example.com'); // → null

// Archivos
validators.fileExtension('document.txt', ['pdf', 'docx']); // → "Solo se permiten..."
validators.fileSize(file, 10); // → "El archivo no puede ser mayor a 10MB"
validators.fileMimeType(file, ['application/pdf']); // → "Tipo de archivo no permitido"

// Ejemplo de validación completa de formulario
function validateForm(formData) {
  const errors = {};
  
  errors.email = validators.required(formData.email, 'El email') 
    || validators.email(formData.email);
  
  errors.password = validators.required(formData.password, 'La contraseña')
    || validators.minLength(formData.password, 8, 'La contraseña');
  
  errors.confirmPassword = validators.required(formData.confirmPassword)
    || validators.matches(formData.password, formData.confirmPassword, 'Las contraseñas');
  
  // Filtrar errores null
  return Object.fromEntries(
    Object.entries(errors).filter(([_, v]) => v !== null)
  );
}
```

---

## UI Components

### Toasts

```javascript
import { ui } from './js/ui.js';

// Toasts simples
ui.success('Operación exitosa');
ui.error('Ocurrió un error');
ui.warning('Atención: verifica los datos');
ui.info('Información importante');

// Toast con duración personalizada (milisegundos)
ui.success('Guardado correctamente', 3000);
ui.error('Error crítico', 0); // No se cierra automáticamente

// Toast genérico
ui.showToast('Mensaje personalizado', 'info', 5000);
```

### Modales

```javascript
// Modal simple
ui.showModal('Título del Modal', '<p>Contenido HTML aquí</p>');

// Modal con botones
ui.showModal('Confirmar Acción', '<p>¿Estás seguro?</p>', {
  buttons: [
    {
      text: 'Cancelar',
      class: 'btn btn-secondary'
    },
    {
      text: 'Confirmar',
      class: 'btn btn-primary',
      onClick: async () => {
        // Acción al confirmar
        await deleteUser(userId);
        ui.success('Usuario eliminado');
      }
    }
  ]
});

// Modal de confirmación (helper)
ui.confirm(
  'Eliminar Usuario',
  '¿Estás seguro de que deseas eliminar este usuario?',
  async () => {
    await deleteUser(userId);
    ui.success('Usuario eliminado');
  }
);

// Modal con contenido dinámico
const content = document.createElement('div');
content.innerHTML = `
  <form id="editForm">
    <input type="text" name="name" value="${user.name}">
    <button type="submit">Guardar</button>
  </form>
`;
ui.showModal('Editar Usuario', content);
```

### Loading

```javascript
// Mostrar loading
const loading = ui.showLoading('Cargando datos...');

// Hacer operación
await fetchData();

// Ocultar loading
ui.hideLoading();

// Uso con async/await
async function loadData() {
  ui.showLoading('Cargando...');
  try {
    const data = await fetchWrapper.get('/data');
    processData(data);
  } finally {
    ui.hideLoading();
  }
}
```

### Helpers de Formato

```javascript
// Formatear fecha
ui.formatDate('2025-01-29T10:30:00Z');
// → "Hace 2 horas" o "29 ene 2025, 10:30"

// Formatear bytes
ui.formatBytes(1024); // → "1 KB"
ui.formatBytes(1048576); // → "1 MB"
ui.formatBytes(1073741824, 2); // → "1.00 GB"
```

---

## Integración Completa

### Ejemplo: Página de Upload de Archivos

```javascript
import { auth } from './js/auth.js';
import { fetchWrapper } from './js/lib/fetch-wrapper.js';
import { validators } from './js/lib/validators.js';
import { ui } from './js/ui.js';

// Proteger página
auth.requireAuth();

// Cargar folders
async function loadFolders() {
  try {
    const folders = await fetchWrapper.get('/folders');
    const select = document.getElementById('folderSelect');
    
    folders.forEach(folder => {
      const option = document.createElement('option');
      option.value = folder.id;
      option.textContent = folder.name;
      select.appendChild(option);
    });
  } catch (error) {
    ui.error('Error al cargar carpetas');
  }
}

// Upload de archivo
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const fileInput = document.getElementById('file');
  const folderSelect = document.getElementById('folderSelect');
  const descInput = document.getElementById('description');
  
  // Validar
  if (!fileInput.files[0]) {
    ui.error('Selecciona un archivo');
    return;
  }
  
  const sizeError = validators.fileSize(fileInput.files[0], 50);
  if (sizeError) {
    ui.error(sizeError);
    return;
  }
  
  // Preparar FormData
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('folder_id', folderSelect.value);
  formData.append('description', descInput.value);
  
  // Upload con progreso
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  
  try {
    const result = await fetchWrapper.upload('/files/upload', formData, (percent) => {
      progressBar.style.width = `${percent}%`;
      progressText.textContent = `${percent}%`;
    });
    
    ui.success('Archivo subido correctamente');
    fileInput.value = '';
    descInput.value = '';
    progressBar.style.width = '0%';
  } catch (error) {
    ui.error(error.message || 'Error al subir archivo');
  }
});

// Inicializar
loadFolders();
auth.attachAuthToUI();
```

### Ejemplo: Página de Auditoría

```javascript
import { auth } from './js/auth.js';
import { fetchWrapper } from './js/lib/fetch-wrapper.js';
import { ui } from './js/ui.js';

// Solo admin y super admin
if (!auth.isSuperAdmin() && !auth.isAdminDep()) {
  alert('No tienes permisos');
  window.location.href = '/dashboard.html';
}

// Cargar logs
async function loadLogs(filters = {}) {
  ui.showLoading('Cargando logs...');
  
  try {
    const logs = await fetchWrapper.get('/audit/logs', filters);
    renderLogs(logs);
  } catch (error) {
    ui.error('Error al cargar logs');
  } finally {
    ui.hideLoading();
  }
}

// Renderizar logs
function renderLogs(logs) {
  const container = document.getElementById('logsContainer');
  
  container.innerHTML = logs.map(log => `
    <div class="log-item">
      <div class="log-header">
        <strong>${log.user_full_name}</strong>
        <span class="badge">${log.action_type}</span>
      </div>
      <div class="log-body">
        ${log.summary}
      </div>
      <div class="log-footer">
        ${ui.formatDate(log.timestamp)} • IP: ${log.ip_address}
      </div>
    </div>
  `).join('');
}

// Exportar CSV
document.getElementById('exportBtn').addEventListener('click', async () => {
  try {
    await fetchWrapper.download('/audit/logs?format=csv', 'audit-logs.csv');
    ui.success('Logs exportados correctamente');
  } catch (error) {
    ui.error('Error al exportar logs');
  }
});

// Inicializar
loadLogs();
```

---

## Notas de Seguridad

### ⚠️ localStorage vs httpOnly Cookies

**Estado actual:**
```javascript
// Tokens en localStorage (desarrollo)
localStorage.setItem('access_token', token);
localStorage.setItem('refresh_token', refreshToken);
```

**Recomendación para producción:**
```javascript
// Backend debe setear httpOnly cookies
// Frontend no accede directamente a los tokens
// fetch-wrapper automáticamente incluye cookies
```

### 🔐 Mejores Prácticas

1. **Nunca almacenar contraseñas:**
```javascript
// ❌ MAL
localStorage.setItem('password', password);

// ✅ BIEN
await auth.login(email, password);
// password se descarta inmediatamente
```

2. **Validar en cliente Y servidor:**
```javascript
// Cliente
const error = validators.email(email);
if (error) {
  ui.error(error);
  return;
}

// Servidor también valida (no confiar solo en cliente)
```

3. **Usar HTTPS en producción:**
```javascript
// config.js
export const config = {
  FRONTEND_API_URL: 'https://api.sgdi.local', // No HTTP
  // ...
};
```

4. **Limpiar datos sensibles:**
```javascript
// Después de login
passwordInput.value = '';

// Después de operación
sensitiveData = null;
```

---

**¿Preguntas? Consulta la [documentación del backend](../sgdi-backend/README.md) para endpoints disponibles.**

