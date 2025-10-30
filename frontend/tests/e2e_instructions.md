# SGDI Frontend - Testing E2E

## Cuentas de Prueba

### Seed SuperAdmin (Requerido)

Ejecutar en el backend antes de las pruebas:

```bash
cd sgdi-backend

# Configurar variables de entorno
export SUPERADMIN_EMAIL="admin@sgdi.test"
export SUPERADMIN_PASSWORD="Admin123!"
export SUPERADMIN_FULL_NAME="Super Administrador"

# Ejecutar script de seed
python scripts/seed_superadmin.py
```

**Credenciales de prueba:**
- **Email:** `admin@sgdi.test`
- **Password:** `Admin123!`
- **Rol:** SUPER_ADMIN

### Cuentas Adicionales (Opcional)

Crear mediante UI después del login con superadmin:

- **Admin Dep:** `admin.dep@sgdi.local` / `AdminDep123!` (ADMIN_DEP)
- **Worker:** `worker@sgdi.local` / `Worker123!` (WORKER)
- **Reader:** `reader@sgdi.local` / `Reader123!` (READER)

## Testing Manual

### Paso 1: Autenticación (Login)

**Objetivo:** Verificar que el sistema de autenticación funciona correctamente.

1. Abrir `http://localhost:8080/login.html`
2. Ingresar credenciales:
   - Email: `admin@sgdi.test`
   - Password: `Admin123!`
3. Click en "Iniciar Sesión"
4. **Verificar:**
   - ✓ Redirección a `/dashboard.html`
   - ✓ Nombre de usuario en navbar: "Super Administrador"
   - ✓ Avatar con inicial "S"
   - ✓ Rol visible: "Super Administrador"
   - ✓ Menú sidebar con todas las opciones (Super Admin tiene acceso total)

### Paso 2: Crear Dependencia de Prueba

**Objetivo:** Crear estructura organizacional para las pruebas.

1. Click en "Dependencias" en el sidebar
2. Click en botón "Nueva Dependencia"
3. Completar formulario:
   - Nombre: `PRUEBA`
   - Código: `DEP-PRUEBA`
   - Descripción: `Dependencia para testing E2E`
4. Click en "Crear"
5. **Verificar:**
   - ✓ Toast de éxito: "Dependencia PRUEBA creada correctamente"
   - ✓ Dependencia aparece en lista (si hay vista de dependencias)

### Paso 3: Crear Carpeta "Contratos"

**Objetivo:** Verificar gestión de carpetas y árbol de navegación.

1. Click en "Carpetas" en el sidebar
2. Seleccionar dependencia "PRUEBA" en el selector
3. Click en botón "Nueva Carpeta"
4. Completar formulario:
   - Nombre: `Contratos`
5. Click en "Crear"
6. **Verificar:**
   - ✓ Toast de éxito
   - ✓ Carpeta "Contratos" aparece en árbol
   - ✓ Icono de carpeta 📁 visible
   - ✓ Puede expandirse/contraerse con click

### Paso 4: Subir Archivo con Anexos

**Objetivo:** Probar upload con anexos y generación automática de carpeta.

**Preparación:**
- Crear archivos de prueba:
  - `Contrato.pdf` (archivo principal)
  - `AnexoA.pdf` (anexo 1)
  - `AnexoB.pdf` (anexo 2)

**Proceso:**
1. Seleccionar carpeta "Contratos" en el árbol
2. Click en botón "Subir Archivo"
3. Drag & drop o seleccionar `Contrato.pdf` como archivo principal
4. **Verificar preview:**
   - ✓ Nombre del archivo visible
   - ✓ Tamaño mostrado
   - ✓ Botón "Cambiar" disponible
5. Marcar checkbox "¿Tiene anexos?"
6. Seleccionar `AnexoA.pdf` y `AnexoB.pdf` en el input de anexos
7. **Verificar preview de anexos:**
   - ✓ Lista muestra 2 anexos
   - ✓ Tamaños individuales visibles
   - ✓ Nombre de carpeta auto-generado: `Anexos-Contrato-YYYYMMDD`
8. Completar metadata (opcional):
   - Número de documento: `2025-001`
   - Etiquetas: `prueba, e2e, contrato`
   - Observaciones: `Prueba de upload con anexos`
9. Click en "Subir"
10. **Verificar progreso:**
    - ✓ Barra de progreso visible (0% → 100%)
    - ✓ Mensaje: "Subiendo archivos..."
11. **Verificar éxito:**
    - ✓ Modal de éxito muestra:
      - Archivo principal: Contrato.pdf
      - Carpeta de anexos: Anexos-Contrato-YYYYMMDD
      - Anexos incluidos: AnexoA.pdf, AnexoB.pdf
    - ✓ Toast: "Archivo y 2 anexo(s) subidos correctamente"

### Paso 5: Verificar Carpeta de Anexos

**Objetivo:** Confirmar que la carpeta de anexos se creó correctamente.

1. En el árbol de carpetas, expandir carpeta "Contratos"
2. **Verificar:**
   - ✓ Subcarpeta `Anexos-Contrato-YYYYMMDD` visible
   - ✓ Formato de fecha correcto (YYYYMMDD = año-mes-día actual)
   - ✓ Nombre sanitizado (sin caracteres especiales)
3. Click en la carpeta de anexos
4. **Verificar contenido:**
   - ✓ Panel derecho muestra archivos
   - ✓ AnexoA.pdf listado
   - ✓ AnexoB.pdf listado
   - ✓ Botones de descarga disponibles

### Paso 6: Descargar y Validar Checksum

**Objetivo:** Verificar integridad de archivos descargados.

1. Seleccionar carpeta "Contratos" (archivo principal)
2. Click en botón "Descargar" del archivo Contrato.pdf
3. **Verificar descarga:**
   - ✓ Archivo se descarga con nombre original
   - ✓ Toast: "Archivo descargado correctamente"

**Validación de checksum (manual):**

```bash
# En terminal, navegar a carpeta de descargas
cd ~/Downloads

# Calcular SHA256 del archivo descargado
sha256sum Contrato.pdf
# o en Windows PowerShell:
# Get-FileHash Contrato.pdf -Algorithm SHA256

# Comparar con checksum del backend:
# 1. Inspeccionar Network en DevTools
# 2. Buscar request GET /files/{id}/download
# 3. Ver header X-Checksum-Sha256
# 4. Verificar que coincidan
```

**Resultado esperado:**
- ✓ Checksums coinciden (integridad verificada)

### Paso 7: Generar Backup

**Objetivo:** Probar creación de backup completo del sistema.

1. Click en "Backups" en el sidebar
2. Click en botón "Backup Completo"
3. Leer advertencias en el modal
4. Click en "Crear Backup"
5. **Verificar progreso:**
   - ✓ Loading: "Generando backup... Esto puede tardar varios minutos"
   - ✓ Esperar completación (puede tardar 30s - 2min)
6. **Verificar éxito:**
   - ✓ Modal muestra:
     - Archivo: backup-YYYYMMDD-HHMMSS.tar.gz
     - Tamaño en MB
     - ID del backup
     - Checksum (primeros 16 caracteres)
   - ✓ Botón "Descargar Ahora" disponible
7. Click en "Cerrar"
8. **Verificar tabla:**
   - ✓ Backup aparece en lista
   - ✓ Tipo: "Completo" (badge azul)
   - ✓ Fecha actual
   - ✓ Tamaño visible

### Paso 8: Simular Restauración

**Objetivo:** Probar modo simulate del restore sin afectar datos.

1. En tabla de backups, click en botón "Restaurar" del backup recién creado
2. Leer **todas** las advertencias (crítico)
3. **Verificar configuración por defecto:**
   - ✓ Checkbox "Solo simular" está marcado (✓)
   - ✓ Estrategia: "Crear Nuevos IDs" seleccionada
4. Click en "Continuar"
5. **Verificar simulación:**
   - ✓ Loading: "Simulando restauración..."
   - ✓ Esperar completación
6. **Verificar reporte:**
   - ✓ Modal: "📊 Reporte de Simulación"
   - ✓ Mensaje: "Esta es una simulación. No se han aplicado cambios"
   - ✓ Resumen muestra:
     - Dependencias a crear: 1 (PRUEBA)
     - Carpetas a crear: 2 (Contratos + Anexos-Contrato-...)
     - Archivos a restaurar: 3 (Contrato.pdf + 2 anexos)
   - ✓ Conflictos: 0 o lista si existen
   - ✓ Request ID visible
7. Click en "Cancelar" (no ejecutar restore real en prueba)

**Nota:** Para probar restore real, seguir instrucciones en modal de confirmación final (3 checkboxes).

### Paso 9: Revisar Logs de Auditoría

**Objetivo:** Verificar que todas las acciones se registraron.

1. Click en "Auditoría" en el sidebar
2. **Verificar filtros por defecto:**
   - ✓ Fecha desde: hace 30 días
   - ✓ Fecha hasta: hoy
3. **Buscar acciones específicas:**
   - Usar filtro "Tipo de Acción": `CREATE_FOLDER`
   - Click en "Aplicar Filtros"
4. **Verificar logs de carpetas:**
   - ✓ Log de creación de "Contratos"
   - ✓ Log de creación de "Anexos-Contrato-..."
   - ✓ Usuario: Super Administrador
   - ✓ Resumen legible
   - ✓ IP address visible
5. Cambiar filtro a `UPLOAD_FILE`
6. **Verificar logs de archivos:**
   - ✓ Log de upload de Contrato.pdf
   - ✓ Menciona anexos en resumen
   - ✓ Fecha/hora correcta
7. Limpiar filtros
8. Usar búsqueda: escribir "Contrato"
9. **Verificar búsqueda:**
   - ✓ Resultados filtrados en tiempo real (debounce 500ms)
   - ✓ Muestra logs relacionados con "Contrato"

### Paso 10: Exportar Audit CSV

**Objetivo:** Verificar exportación de logs.

1. Con filtros aplicados o sin filtros
2. Click en botón "Exportar CSV"
3. **Verificar:**
   - ✓ Loading: "Generando CSV..."
   - ✓ Archivo `audit-logs.csv` se descarga
   - ✓ Toast: "CSV exportado correctamente"
4. Abrir CSV en editor de texto o Excel
5. **Verificar contenido:**
   - ✓ Headers: timestamp, user_id, user_full_name, user_role, action_type, target_type, target_id, summary, details, ip_address
   - ✓ Datos corresponden a los filtros aplicados
   - ✓ Formato CSV válido

---

## Testing con Playwright (Automatizado - Opcional)

### Setup

```bash
# Instalar Playwright (solo para testing, no afecta el frontend en producción)
npm init playwright@latest

# O con pnpm
pnpm create playwright
```

### Script de prueba completo

```javascript
// tests/e2e.spec.js
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8080';
const CREDENTIALS = {
  email: 'admin@sgdi.local',
  password: 'Admin123!'
};

test.describe('SGDI E2E Flow', () => {
  
  test('Complete workflow: Login → Create → Upload → Backup → Audit', async ({ page }) => {
    
    // 1. Login
    await page.goto(`${BASE_URL}/login.html`);
    await page.fill('input[name="email"]', CREDENTIALS.email);
    await page.fill('input[name="password"]', CREDENTIALS.password);
    await page.click('button[type="submit"]');
    
    // Verificar redirección
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.locator('.user-name')).toContainText('Super Administrador');
    
    // 2. Crear Dependencia
    await page.click('a[href="#/dependencies"]');
    await page.click('button:has-text("Nueva Dependencia")');
    await page.fill('input[name="name"]', 'PRUEBA');
    await page.fill('input[name="code"]', 'DEP-PRUEBA');
    await page.click('button:has-text("Crear")');
    
    // Verificar toast
    await expect(page.locator('.toast-success')).toBeVisible();
    
    // 3. Crear Carpeta
    await page.click('a[href="#/folders"]');
    await page.selectOption('select[name="dependency"]', { label: 'PRUEBA' });
    await page.click('button:has-text("Nueva Carpeta")');
    await page.fill('input[name="folder-name"]', 'Contratos');
    await page.click('button:has-text("Crear")');
    
    // Verificar en árbol
    await expect(page.locator('.tree-item:has-text("Contratos")')).toBeVisible();
    
    // 4. Upload con Anexos
    await page.click('.tree-item:has-text("Contratos")');
    await page.click('button:has-text("Subir Archivo")');
    
    // Upload archivo principal
    await page.setInputFiles('input[name="main-file"]', './test-files/Contrato.pdf');
    
    // Marcar anexos
    await page.check('input[name="has-annexes"]');
    await page.setInputFiles('input[name="annexes"]', [
      './test-files/AnexoA.pdf',
      './test-files/AnexoB.pdf'
    ]);
    
    // Metadata
    await page.fill('input[name="doc_number"]', '2025-001');
    await page.fill('input[name="tags"]', 'prueba, e2e');
    
    // Submit
    await page.click('button:has-text("Subir")');
    
    // Esperar progreso
    await expect(page.locator('.progress-bar')).toBeVisible();
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 30000 });
    
    // Verificar carpeta anexos
    await expect(page.locator('.tree-item:has-text("Anexos-Contrato-")')).toBeVisible();
    
    // 5. Generar Backup
    await page.click('a[href="#/backups"]');
    await page.click('button:has-text("Backup Completo")');
    await page.click('button:has-text("Crear Backup")');
    
    // Esperar completación
    await expect(page.locator('.modal:has-text("Backup creado exitosamente")')).toBeVisible({ timeout: 120000 });
    
    // 6. Simular Restore
    await page.click('button:has-text("Restaurar")');
    await expect(page.locator('input[name="simulate"]:checked')).toBeVisible();
    await page.click('button:has-text("Continuar")');
    
    // Verificar reporte
    await expect(page.locator('.modal:has-text("Reporte de Simulación")')).toBeVisible({ timeout: 60000 });
    await expect(page.locator('text=/Dependencias a crear: 1/')).toBeVisible();
    
    // 7. Auditoría
    await page.click('button:has-text("Cancelar")');
    await page.click('a[href="#/audit"]');
    
    // Filtrar por CREATE_FOLDER
    await page.selectOption('select[name="action_type"]', 'CREATE_FOLDER');
    await page.click('button:has-text("Aplicar Filtros")');
    
    // Verificar logs
    await expect(page.locator('table tbody tr')).toHaveCount(2); // Contratos + Anexos folder
    
    // Exportar CSV
    await page.click('button:has-text("Exportar CSV")');
    
    // Verificar descarga
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('button:has-text("Exportar CSV")')
    ]);
    expect(download.suggestedFilename()).toBe('audit-logs.csv');
  });
  
  test('Keyboard navigation', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard.html`);
    
    // Tab navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter'); // Should activate focused element
    
    // Tree navigation
    await page.click('a[href="#/folders"]');
    await page.locator('.tree-item').first().focus();
    await page.keyboard.press('Enter'); // Expand/collapse
    await page.keyboard.press('ArrowDown'); // Next item
    await page.keyboard.press('ArrowUp'); // Previous item
  });
  
  test('Accessibility checks', async ({ page }) => {
    await page.goto(`${BASE_URL}/login.html`);
    
    // Check for proper labels
    await expect(page.locator('label[for="email"]')).toBeVisible();
    await expect(page.locator('label[for="password"]')).toBeVisible();
    
    // Check ARIA attributes
    await page.goto(`${BASE_URL}/dashboard.html`);
    await page.click('a[href="#/folders"]');
    await expect(page.locator('[role="tree"]')).toBeVisible();
    await expect(page.locator('[role="treeitem"]')).toHaveCount.greaterThan(0);
  });
});
```

### Ejecutar tests

```bash
# Run all tests
npx playwright test

# Run with UI
npx playwright test --ui

# Run specific test
npx playwright test tests/e2e.spec.js

# Generate report
npx playwright show-report
```

---

## Checklist de Validación

### ✅ Funcionalidad

- [ ] Login con credenciales correctas funciona
- [ ] Login con credenciales incorrectas muestra error
- [ ] Refresh token funciona (dejar tab abierto > 30 min)
- [ ] Logout limpia sesión y redirige
- [ ] Anti-brute force bloquea después de 5 intentos
- [ ] Crear carpeta actualiza árbol sin reload
- [ ] Renombrar carpeta actualiza path
- [ ] Eliminar carpeta pide confirmación
- [ ] Upload con progress bar funciona
- [ ] Upload con anexos crea carpeta automática
- [ ] Download devuelve archivo original
- [ ] Backup completo se genera
- [ ] Simulate restore muestra reporte
- [ ] Audit logs muestra todas las acciones
- [ ] CSV export descarga archivo válido
- [ ] Permisos se respetan (worker no ve admin endpoints)

### ✅ Accesibilidad (WCAG AA)

- [ ] Todas las imágenes/iconos tienen `alt` o `aria-label`
- [ ] Navegación por teclado funciona en todos los componentes
- [ ] Tab order es lógico y secuencial
- [ ] Focus visible en todos los elementos interactivos
- [ ] Contraste de texto cumple WCAG AA (4.5:1 para texto normal)
- [ ] `aria-expanded` en tree nodes
- [ ] `role="tree"` y `role="treeitem"` en árbol de carpetas
- [ ] `role="dialog"` en modales con `aria-labelledby`
- [ ] `role="alert"` en toasts/notificaciones
- [ ] Skip links para navegación rápida (opcional)
- [ ] Screen reader puede leer todo el contenido

### ✅ Responsividad

- [ ] Layout funciona en 320px (mobile small)
- [ ] Layout funciona en 768px (tablet)
- [ ] Layout funciona en 1920px (desktop)
- [ ] Sidebar colapsa en móvil
- [ ] Tablas se convierten en cards en móvil
- [ ] Touch targets mínimo 44x44px
- [ ] No scroll horizontal en ningún tamaño

### ✅ Performance

- [ ] Página carga en < 3s (primera vez)
- [ ] Navegación entre rutas < 500ms
- [ ] Búsqueda tiene debounce (no busca en cada tecla)
- [ ] Upload muestra progreso en tiempo real
- [ ] Árbol de carpetas con lazy loading (si >100 folders)
- [ ] No memory leaks (dejar tab abierto 1 hora)

### ✅ Seguridad

- [ ] No hay `eval()` en código
- [ ] No se exponen tokens en console
- [ ] CSP headers configurados
- [ ] XSS prevention (escaping HTML)
- [ ] CSRF tokens en requests (si aplica)
- [ ] HTTPS en producción (documentado)

### ✅ Sin Node/NPM

- [ ] No existe `node_modules/` en repositorio
- [ ] No existe `package.json` en repositorio
- [ ] No hay scripts npm en documentación
- [ ] Todos los assets son locales (no CDN de terceros)
- [ ] Se puede servir con cualquier HTTP server simple

---

## Troubleshooting

### Problema: CORS errors

**Síntoma:** `Access-Control-Allow-Origin` error en console

**Solución:**
1. Verificar que backend tiene CORS configurado
2. Agregar en `sgdi-backend/app/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Problema: Token expired demasiado rápido

**Síntoma:** Se cierra sesión cada pocos minutos

**Solución:**
1. Verificar `ACCESS_TOKEN_EXPIRE_MINUTES` en backend `.env`
2. Aumentar a 60 minutos: `ACCESS_TOKEN_EXPIRE_MINUTES=60`
3. Verificar que refresh token funciona en `fetch-wrapper.js`

### Problema: Upload falla con archivos grandes

**Síntoma:** Timeout o error 413

**Solución:**
1. Aumentar límite en NGINX:
```nginx
client_max_body_size 200M;
```
2. Aumentar timeout en backend:
```python
# uvicorn --timeout-keep-alive 300
```
3. Verificar timeout en `fetch-wrapper.js` (actual: 60s, aumentar si necesario)

### Problema: Árbol de carpetas no carga

**Síntoma:** Spinner infinito o error

**Solución:**
1. Abrir DevTools → Network → buscar request fallido
2. Verificar X-Request-Id en error message
3. Buscar ese Request ID en logs del backend
4. Revisar que endpoint `/dependencies/{id}/folders` existe y responde

### Problema: Backup no descarga

**Síntoma:** Click en descargar no hace nada

**Solución:**
1. Verificar en DevTools → Network que request se envía
2. Verificar que response tiene `Content-Disposition` header
3. Verificar que browser no bloqueó descarga (permisos)
4. Usar método alternativo:
```javascript
// En console del browser
const url = '/admin/backups/{id}/download';
const a = document.createElement('a');
a.href = `http://localhost:8000${url}`;
a.download = 'backup.tar.gz';
a.click();
```

### Problema: localStorage quota exceeded

**Síntoma:** Error al guardar sesión

**Solución:**
1. Limpiar localStorage: `localStorage.clear()`
2. Reducir tamaño de datos guardados
3. Considerar IndexedDB para datos grandes (mejora futura)

---

## Conclusión

Este documento provee una guía completa para testing manual y automatizado del frontend SGDI. Todos los flujos críticos están cubiertos y se han documentado las soluciones a problemas comunes.

**Duración estimada del E2E manual completo:** 30-45 minutos

**Cuentas necesarias:**
- Super Admin: `admin@sgdi.com` / `supersecret123` (seed con script)

**Archivos de prueba necesarios:**
- `Contrato.pdf` (cualquier PDF)
- `AnexoA.pdf` (cualquier PDF)
- `AnexoB.pdf` (cualquier PDF)

**Backend debe estar corriendo en:** `http://localhost:8000`
**Frontend debe estar corriendo en:** `http://localhost:8080`
1. Verificar que el menú lateral muestre solo las opciones según el rol
2. Hacer click en cada opción y verificar navegación

### 4. Logout
1. Click en botón "Salir"
2. Confirmar en el diálogo
3. Verificar redirección a login
4. Verificar que localStorage se limpió

## Testing E2E con Playwright

### Instalación

```bash
npm init -y
npm install -D @playwright/test
npx playwright install
```

### Crear archivo de test

Crear `tests/e2e/login.spec.js`:

```javascript
const { test, expect } = require('@playwright/test');

test.describe('Login', () => {
  test('should login successfully', async ({ page }) => {
    await page.goto('http://localhost:8080/login.html');
    
    await page.fill('#email', 'admin@sgdi.local');
    await page.fill('#password', 'Admin123!');
    await page.click('#loginButton');
    
    await page.waitForURL('**/dashboard.html');
    
    const userName = await page.textContent('#userName');
    expect(userName).toBeTruthy();
  });

  test('should show error with wrong credentials', async ({ page }) => {
    await page.goto('http://localhost:8080/login.html');
    
    await page.fill('#email', 'wrong@email.com');
    await page.fill('#password', 'wrongpassword');
    await page.click('#loginButton');
    
    const alert = await page.locator('#loginAlert');
    await expect(alert).toBeVisible();
  });
});

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login primero
    await page.goto('http://localhost:8080/login.html');
    await page.fill('#email', 'admin@sgdi.local');
    await page.fill('#password', 'Admin123!');
    await page.click('#loginButton');
    await page.waitForURL('**/dashboard.html');
  });

  test('should display stats', async ({ page }) => {
    const statsContainer = await page.locator('#statsContainer');
    await expect(statsContainer).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    await page.click('#logoutButton');
    await page.waitForURL('**/login.html');
  });
});
```

### Ejecutar tests

```bash
npx playwright test
npx playwright test --headed  # Ver navegador
npx playwright test --debug   # Modo debug
```

### Configuración playwright.config.js

```javascript
module.exports = {
  testDir: './tests/e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:8080',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
    {
      name: 'firefox',
      use: { browserName: 'firefox' },
    },
  ],
};
```

## Testing de Carga con Artillery

### Instalación

```bash
npm install -D artillery
```

### Crear escenario de carga

Crear `tests/load/scenario.yml`:

```yaml
config:
  target: "http://localhost:8080"
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Sustained load"

scenarios:
  - name: "Login and navigate"
    flow:
      - get:
          url: "/login.html"
      - think: 2
      - post:
          url: "/auth/login"
          json:
            email: "admin@sgdi.local"
            password: "Admin123!"
      - get:
          url: "/dashboard.html"
```

### Ejecutar test de carga

```bash
npx artillery run tests/load/scenario.yml
```

## Checklist de Testing

### Funcionalidad
- [ ] Login con credenciales correctas
- [ ] Login con credenciales incorrectas
- [ ] Refresh de token automático
- [ ] Logout
- [ ] Navegación entre páginas
- [ ] Protección de rutas
- [ ] Verificación de roles

### UI/UX
- [ ] Responsive design (móvil, tablet, desktop)
- [ ] Toasts de notificación
- [ ] Modales
- [ ] Loading states
- [ ] Error states
- [ ] Empty states

### Performance
- [ ] Tiempo de carga < 3s
- [ ] Assets comprimidos (gzip)
- [ ] Assets cacheados
- [ ] No memory leaks

### Seguridad
- [ ] Tokens almacenados de forma segura
- [ ] Headers de seguridad configurados
- [ ] XSS prevention
- [ ] CSRF protection

### Compatibilidad
- [ ] Chrome 90+
- [ ] Firefox 88+
- [ ] Safari 14+
- [ ] Edge 90+

