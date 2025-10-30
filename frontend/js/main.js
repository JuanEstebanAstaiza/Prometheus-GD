/**
 * SGDI - Main Entry Point
 * Inicialización de la aplicación, registro de rutas y listeners globales
 */

import { auth } from './auth.js';
import { router } from './router.js';
import { ui } from './ui.js';
import { loadStats, loadRecentActivity } from './dashboard.js';

/**
 * Carga el navbar con información del usuario
 */
function loadNavbar() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;

  const user = auth.getCurrentUser();
  if (!user) return;

  // Actualizar información del usuario
  auth.attachAuthToUI();

  // Configurar botón de logout
  const logoutButton = document.getElementById('logoutButton');
  if (logoutButton) {
    logoutButton.addEventListener('click', async (e) => {
      e.preventDefault();
      
      if (confirm('¿Estás seguro que deseas cerrar sesión?')) {
        ui.showLoading('Cerrando sesión...');
        await auth.logout();
      }
    });
  }

  // Configurar menú de usuario (dropdown)
  const userMenuButton = document.getElementById('userMenuButton');
  const userMenuDropdown = document.getElementById('userMenuDropdown');
  
  if (userMenuButton && userMenuDropdown) {
    userMenuButton.addEventListener('click', (e) => {
      e.stopPropagation();
      userMenuDropdown.classList.toggle('hidden');
    });

    // Cerrar dropdown al hacer click fuera
    document.addEventListener('click', () => {
      userMenuDropdown.classList.add('hidden');
    });
  }
}

/**
 * Carga el sidebar con navegación
 */
function loadSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;

  const user = auth.getCurrentUser();
  if (!user) return;

  // Definir items del menú según el rol
  const menuItems = getMenuItems(user.role);

  sidebar.innerHTML = `
    <nav class="sidebar-nav">
      ${menuItems.map(item => renderSidebarLink(item)).join('')}
    </nav>
  `;

  // Actualizar link activo
  const currentPath = router.getCurrentPath();
  router.updateActiveLink(currentPath);
}

/**
 * Obtiene los items del menú según el rol
 */
function getMenuItems(role) {
  const allItems = [
    {
      label: 'Dashboard',
      path: '/dashboard',
      icon: 'home',
      roles: ['SUPER_ADMIN', 'ADMIN_DEP', 'WORKER', 'READER'],
      description: 'Panel principal'
    },
    {
      label: 'Carpetas',
      path: '/folders',
      icon: 'folder',
      roles: ['SUPER_ADMIN', 'ADMIN_DEP', 'WORKER'],
      description: 'Gestión de carpetas'
    },
    {
      label: 'Archivos',
      path: '/archivos',
      icon: 'file-text',
      roles: ['SUPER_ADMIN', 'ADMIN_DEP', 'WORKER', 'READER'],
      description: 'Búsqueda y gestión de documentos'
    },
    {
      label: 'Usuarios',
      path: '/users',
      icon: 'users',
      roles: ['SUPER_ADMIN', 'ADMIN_DEP'],
      description: 'Administración de usuarios',
      tooltip: role === 'WORKER' || role === 'READER' 
        ? 'Solo administradores pueden gestionar usuarios' 
        : null
    },
    {
      label: 'Dependencias',
      path: '/dependencies',
      icon: 'building',
      roles: ['SUPER_ADMIN'],
      description: 'Administración de dependencias',
      tooltip: role !== 'SUPER_ADMIN' 
        ? 'Solo super administradores pueden gestionar dependencias' 
        : null
    },
    {
      label: 'Backups',
      path: '/backups',
      icon: 'database',
      roles: ['SUPER_ADMIN'],
      description: 'Gestión de respaldos',
      tooltip: role !== 'SUPER_ADMIN' 
        ? 'Solo super administradores pueden gestionar backups' 
        : null
    }
  ];

  // Filtrar por rol (mostrar todos pero deshabilitar los no permitidos)
  return allItems;
}

/**
 * Renderiza un link del sidebar
 */
function renderSidebarLink(item) {
  const user = auth.getCurrentUser();
  const hasAccess = item.roles.includes(user.role);
  const isDisabled = !hasAccess;
  const tooltip = isDisabled && item.tooltip ? `title="${item.tooltip}"` : '';

  return `
    <a 
      href="${hasAccess ? '#' + item.path : 'javascript:void(0)'}" 
      class="sidebar-link ${isDisabled ? 'disabled' : ''}" 
      ${tooltip}
      ${isDisabled ? 'data-disabled="true"' : ''}
    >
      ${getSvgIcon(item.icon)}
      <span>${item.label}</span>
      ${isDisabled ? '<span class="lock-icon">🔒</span>' : ''}
    </a>
  `;
}

/**
 * Obtiene SVG icon (inline, se puede reemplazar con sprite)
 */
function getSvgIcon(name) {
  const icons = {
    home: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/></svg>',
    
    file: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>',
    
    folder: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/></svg>',
    
    users: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/></svg>',
    
    building: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 110 2h-3a1 1 0 01-1-1v-2a1 1 0 00-1-1H9a1 1 0 00-1 1v2a1 1 0 01-1 1H4a1 1 0 110-2V4zm3 1h2v2H7V5zm2 4H7v2h2V9zm2-4h2v2h-2V5zm2 4h-2v2h2V9z" clip-rule="evenodd"/></svg>',
    
    chart: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 0l-2 2a1 1 0 101.414 1.414L8 10.414l1.293 1.293a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
    
    database: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z"/><path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z"/><path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z"/></svg>'
  };

  return icons[name] || icons.file;
}

/**
 * Configura listeners globales
 */
function setupGlobalListeners() {
  // Toggle sidebar en móvil
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  
  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    // Cerrar sidebar al hacer click en overlay o link (móvil)
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
    });
    document.body.appendChild(overlay);

    // Cerrar al navegar
    sidebar.addEventListener('click', (e) => {
      if (e.target.classList.contains('sidebar-link') && !e.target.dataset.disabled) {
        sidebar.classList.remove('open');
      }
    });
  }

  // Tooltips para elementos deshabilitados
  document.addEventListener('click', (e) => {
    const disabledLink = e.target.closest('.sidebar-link[data-disabled="true"]');
    if (disabledLink) {
      e.preventDefault();
      const tooltip = disabledLink.getAttribute('title');
      if (tooltip) {
        ui.warning(tooltip);
      }
    }
  });

  // Manejar teclas de navegación
  document.addEventListener('keydown', (e) => {
    // Esc para cerrar sidebar en móvil
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
      sidebar.classList.remove('open');
    }
  });
}

/**
 * Precarga sprite de iconos SVG (si existe)
 */
async function preloadIconSprite() {
  try {
    const response = await fetch('/assets/icons/sprite.svg');
    if (response.ok) {
      const svgText = await response.text();
      const div = document.createElement('div');
      div.style.display = 'none';
      div.innerHTML = svgText;
      document.body.insertBefore(div, document.body.firstChild);
      console.log('Icon sprite loaded');
    }
  } catch (error) {
    console.log('No icon sprite found, using inline SVGs');
  }
}

/**
 * Registra todas las rutas de la aplicación
 */
function registerRoutes() {
  // Dashboard (todos los roles)
  router.registerRoute('/dashboard', async (params) => {
    router.setPageTitle('Dashboard');
    router.updateActiveLink('/dashboard');
    
    // Mostrar contenido del dashboard
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      mainContent.innerHTML = `
        <div class="page-header">
          <h1 class="page-title">Dashboard</h1>
          <p class="page-subtitle">Bienvenido al Sistema de Gestión Documental Institucional</p>
        </div>
        <div id="statsContainer" class="stats-grid"></div>
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">Actividad Reciente</h2>
          </div>
          <div class="card-body" id="recentActivityContainer">
            <p class="text-muted">Cargando...</p>
          </div>
        </div>
      `;
      
      // Cargar datos
      await loadStats();
      await loadRecentActivity();
    }
  });

  // Folders (super admin, admin dep, worker)
  router.registerRoute('/folders', async (params) => {
    router.setPageTitle('Carpetas');
    router.updateActiveLink('/folders');
    
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      const canWrite = !auth.isReader();
      const isSuperAdmin = auth.isSuperAdmin();
      
      mainContent.innerHTML = `
        <div class="page-header">
          <div>
            <h1 class="page-title">Gestión de Carpetas</h1>
            <p class="page-subtitle">Explorador de carpetas en árbol</p>
          </div>
          <div style="display: flex; gap: var(--space-3);">
            ${canWrite ? `
              <button class="btn btn-primary" id="createRootFolderBtn">
                ${getSvgIcon('folder')} Nueva Carpeta
              </button>
            ` : ''}
            ${isSuperAdmin ? `
              <button class="btn btn-secondary" id="createMonthlyFoldersBtn" style="display: none;">
                ${getSvgIcon('chart')} Carpetas Mensuales
              </button>
            ` : ''}
          </div>
        </div>

        <div class="folders-container">
          <!-- Panel izquierdo: Árbol de carpetas -->
          <div class="folders-panel">
            <div class="folders-panel-header">
              <h3 class="folders-panel-title">Carpetas</h3>
              <select id="dependencySelector" class="form-input" style="margin: 0;">
                <option value="">Cargando...</option>
              </select>
            </div>
            <div class="folders-panel-body" id="foldersTree">
              <div class="loading-state" style="padding: 2rem;">
                <div class="spinner"></div>
                <p>Cargando...</p>
              </div>
            </div>
          </div>

          <!-- Panel derecho: Contenido de carpeta -->
          <div class="files-panel">
            <div class="files-panel-header">
              <h3 class="files-panel-title">Contenido</h3>
              ${canWrite ? `
                <button class="btn btn-sm btn-primary">
                  ${getSvgIcon('file')} Subir Archivo
                </button>
              ` : ''}
            </div>
            <div class="files-panel-body" id="folderFiles">
              <div class="empty-state">
                <div class="empty-state-icon">📂</div>
                <h3 class="empty-state-title">Selecciona una carpeta</h3>
                <p class="empty-state-description">Haz clic en una carpeta para ver su contenido</p>
              </div>
            </div>
          </div>
        </div>
      `;
      
      // Cargar módulo de carpetas
      const { foldersManager } = await import('./folders.js');
      await foldersManager.init();
    }
  }, { 
    requireAuth: true,
    guards: [async () => {
      if (auth.isReader()) {
        ui.warning('No tienes permisos para gestionar carpetas');
        router.navigateTo('/dashboard');
        return false;
      }
      return true;
    }]
  });

  // Folders con parámetros
  router.registerRoute('/folders/:depId/:folderId', async (params) => {
    router.setPageTitle('Carpeta');
    router.updateActiveLink('/folders');
    
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      mainContent.innerHTML = `
        <div class="page-header">
          <h1 class="page-title">Carpeta: ${params.folderId}</h1>
          <p class="text-muted">Dependencia: ${params.depId}</p>
        </div>
        <div class="card">
          <div class="card-body">
            <p>Módulo de carpetas en desarrollo...</p>
          </div>
        </div>
      `;
    }
  }, { requireAuth: true });

  // Redirect de /files a /archivos para compatibilidad
  router.registerRoute('/files', async (params) => {
    router.navigateTo('/archivos');
  }, { requireAuth: true });

  // Archivos (módulo independiente con buscador)
  router.registerRoute('/archivos', async (params) => {
    router.setPageTitle('Archivos');
    router.updateActiveLink('/archivos');
    
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      mainContent.innerHTML = `
        <div class="page-header">
          <div class="page-header-content">
            <h1 class="page-title">Gestión de Archivos</h1>
            <p class="page-description">Búsqueda y gestión centralizada de documentos</p>
          </div>
          <div class="page-actions">
            <button class="btn btn-primary" id="uploadFileBtn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              Subir Archivo
            </button>
          </div>
        </div>

        <!-- Buscador y filtros -->
        <div class="card" style="margin-bottom: 1.5rem;">
          <div class="card-body">
            <div class="search-filters">
              <div class="search-box" style="flex: 1;">
                <input 
                  type="text" 
                  id="fileSearch" 
                  class="form-input" 
                  placeholder="Buscar archivos por nombre, tipo, o contenido..."
                  autocomplete="off"
                >
                <div class="autocomplete-results" id="autocompleteResults"></div>
              </div>
              
              <button class="btn btn-secondary" id="toggleFiltersBtn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
                </svg>
                Filtros
              </button>
            </div>

            <!-- Filtros avanzados (colapsables) -->
            <div class="advanced-filters hidden" id="advancedFilters">
              <div class="filters-grid">
                <div class="form-group">
                  <label class="form-label">Dependencia</label>
                  <select id="filterDependency" class="form-input">
                    <option value="">Todas</option>
                  </select>
                </div>

                <div class="form-group">
                  <label class="form-label">Carpeta</label>
                  <select id="filterFolder" class="form-input">
                    <option value="">Todas</option>
                  </select>
                </div>

                <div class="form-group">
                  <label class="form-label">Tipo de archivo</label>
                  <select id="filterMimeType" class="form-input">
                    <option value="">Todos</option>
                    <option value="application/pdf">PDF</option>
                    <option value="application/msword">Word</option>
                    <option value="application/vnd.ms-excel">Excel</option>
                    <option value="image/">Imágenes</option>
                  </select>
                </div>

                <div class="form-group">
                  <label class="form-label">Subido por</label>
                  <select id="filterUploadedBy" class="form-input">
                    <option value="">Todos</option>
                  </select>
                </div>

                <div class="form-group">
                  <label class="form-label">Incluir eliminados</label>
                  <label class="checkbox-label">
                    <input type="checkbox" id="filterIncludeDeleted">
                    <span>Mostrar archivos eliminados</span>
                  </label>
                </div>

                <div class="form-group" style="display: flex; align-items: flex-end; gap: 0.5rem;">
                  <button class="btn btn-primary" id="applyFiltersBtn">Aplicar Filtros</button>
                  <button class="btn btn-secondary" id="clearFiltersBtn">Limpiar</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Tabla de archivos -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Archivos</h3>
            <div class="card-actions">
              <span class="text-muted" id="filesCount">0 archivos</span>
            </div>
          </div>
          <div class="card-body" style="padding: 0;">
            <div id="filesTableContainer">
              <div class="loading-state">
                <div class="spinner"></div>
                <p>Cargando archivos...</p>
              </div>
            </div>
          </div>
          <div class="card-footer">
            <div class="pagination" id="filesPagination"></div>
          </div>
        </div>
      `;
      
      // Cargar módulo de archivos
      const { filesManager } = await import('./files.js');
      await filesManager.init();
    }
  }, { requireAuth: true });

  // Users (super admin y admin dep)
  router.registerRoute('/users', async (params) => {
    router.setPageTitle('Usuarios');
    router.updateActiveLink('/users');
    
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      const isSuperAdmin = auth.isSuperAdmin();
      
      mainContent.innerHTML = `
        <div class="page-header">
          <div>
            <h1 class="page-title">Gestión de Usuarios</h1>
            <p class="page-subtitle">Administración de usuarios y permisos</p>
          </div>
          <div style="display: flex; gap: var(--space-3);">
            <button class="btn btn-primary" id="createUserBtn">
              ${getSvgIcon('users')} Nuevo Usuario
            </button>
            ${isSuperAdmin ? `
              <button class="btn btn-secondary" id="createDependencyBtn" style="display: none;">
                ${getSvgIcon('building')} Nueva Dependencia
              </button>
            ` : ''}
          </div>
        </div>

        <!-- Filtros y búsqueda -->
        <div class="card" style="margin-bottom: var(--space-6);">
          <div class="card-body">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-4);">
              <div class="form-group" style="margin: 0;">
                <label for="userSearch" class="form-label">Buscar</label>
                <input 
                  type="text" 
                  id="userSearch" 
                  class="form-input" 
                  placeholder="Nombre o email..."
                >
              </div>

              <div class="form-group" style="margin: 0;">
                <label for="roleFilter" class="form-label">Rol</label>
                <select id="roleFilter" class="form-input">
                  <option value="">Todos</option>
                  ${isSuperAdmin ? '<option value="SUPER_ADMIN">Super Admin</option>' : ''}
                  <option value="ADMIN_DEP">Admin Dep</option>
                  <option value="WORKER">Trabajador</option>
                  <option value="READER">Lector</option>
                </select>
              </div>

              <div class="form-group" style="margin: 0;">
                <label for="dependencyFilter" class="form-label">Dependencia</label>
                <select id="dependencyFilter" class="form-input">
                  <option value="">Todas</option>
                  <!-- Se llenarán dinámicamente -->
                </select>
              </div>

              <div class="form-group" style="margin: 0;">
                <label for="statusFilter" class="form-label">Estado</label>
                <select id="statusFilter" class="form-input">
                  <option value="">Todos</option>
                  <option value="active">Activo</option>
                  <option value="inactive">Inactivo</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Tabla de usuarios -->
        <div class="card">
          <div class="card-body" style="overflow-x: auto;">
            <table class="table">
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Rol</th>
                  <th>Dependencia</th>
                  <th>Estado</th>
                  <th>Creado</th>
                  <th style="width: 150px;">Acciones</th>
                </tr>
              </thead>
              <tbody id="usersTableBody">
                <tr>
                  <td colspan="6" class="loading-state" style="text-align: center; padding: 3rem;">
                    <div class="spinner"></div>
                    <p style="margin-top: 1rem;">Cargando usuarios...</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      `;
      
      // Cargar módulo de usuarios
      const { usersManager } = await import('./users.js');
      await usersManager.init();
      
      // Llenar filtro de dependencias
      const depFilter = document.getElementById('dependencyFilter');
      if (depFilter && usersManager.dependencies) {
        usersManager.dependencies.forEach(dep => {
          const option = document.createElement('option');
          option.value = dep.id;
          option.textContent = dep.name;
          depFilter.appendChild(option);
        });
      }
    }
  }, { requireAuth: true, requireAdmin: true });

  // Dependencies (solo super admin) - INTEGRADO CON users.js
  router.registerRoute('/dependencies', async (params) => {
    router.setPageTitle('Dependencias');
    router.updateActiveLink('/dependencies');
    
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      mainContent.innerHTML = `
        <div class="page-header">
          <div>
            <h1 class="page-title">Gestión de Dependencias</h1>
            <p class="page-subtitle">Administración de dependencias institucionales</p>
          </div>
          <button class="btn btn-primary" id="createDependencyBtn">
            ${getSvgIcon('building')} Nueva Dependencia
          </button>
        </div>

        <!-- Tabla de dependencias -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Dependencias Registradas</h3>
          </div>
          <div class="card-body" style="overflow-x: auto;">
            <table class="table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Nombre</th>
                  <th>Usuarios</th>
                  <th>Carpetas</th>
                  <th>Archivos</th>
                  <th>Creado</th>
                  <th style="width: 150px;">Acciones</th>
                </tr>
              </thead>
              <tbody id="dependenciesTableBody">
                <tr>
                  <td colspan="7" class="loading-state" style="text-align: center; padding: 3rem;">
                    <div class="spinner"></div>
                    <p style="margin-top: 1rem;">Cargando dependencias...</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      `;
      
      // Cargar módulo de usuarios (incluye gestión de dependencias)
      const { usersManager } = await import('./users.js');
      // Cargar solo dependencias sin usuarios completos
      await usersManager.loadDependencies();
      
      // Renderizar tabla de dependencias
      const tbody = document.getElementById('dependenciesTableBody');
      if (tbody && usersManager.dependencies && usersManager.dependencies.length > 0) {
        tbody.innerHTML = usersManager.dependencies.map(dep => `
          <tr>
            <td><strong>${dep.code || 'N/A'}</strong></td>
            <td>${dep.name}</td>
            <td>${dep.user_count || 0}</td>
            <td>${dep.folder_count || 0}</td>
            <td>${dep.file_count || 0}</td>
            <td>${new Date(dep.created_at || Date.now()).toLocaleDateString()}</td>
            <td>
              <button class="btn btn-sm btn-secondary" onclick="editDependency('${dep.id}')">
                Editar
              </button>
            </td>
          </tr>
        `).join('');
      } else if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" class="empty-state" style="text-align: center; padding: 3rem;">
              <p>No hay dependencias registradas</p>
            </td>
          </tr>
        `;
      }
      
      // Configurar botón crear
      const createBtn = document.getElementById('createDependencyBtn');
      if (createBtn) {
        createBtn.addEventListener('click', () => {
          usersManager.showCreateDependencyModal();
        });
      }

      // Hacer función global para botones onclick
      window.editDependency = (depId) => {
        usersManager.showEditDependencyModal(depId);
      };
    }
  }, { requireAuth: true, requireSuperAdmin: true });

  // Backups (solo super admin)
  router.registerRoute('/backups', async (params) => {
    router.setPageTitle('Backups');
    router.updateActiveLink('/backups');
    
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      mainContent.innerHTML = `
        <div class="page-header">
          <div>
            <h1 class="page-title">Gestión de Backups</h1>
            <p class="page-subtitle">Respaldo y restauración del sistema</p>
          </div>
          <div style="display: flex; gap: var(--space-3);">
            <button class="btn btn-primary" id="createFullBackupBtn">
              ${getSvgIcon('database')} Backup Completo
            </button>
            <button class="btn btn-secondary" id="createPartialBackupBtn">
              ${getSvgIcon('folder')} Backup Parcial
            </button>
          </div>
        </div>

        <!-- Información y advertencias -->
        <div class="card" style="margin-bottom: var(--space-6);">
          <div class="card-body">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: var(--space-4);">
              <div style="padding: 1rem; background: var(--color-info-50); border-left: 4px solid var(--color-info); border-radius: var(--radius-md);">
                <strong>ℹ️ Backup Completo</strong>
                <p style="margin-top: 0.5rem; margin-bottom: 0; font-size: 0.875rem;">
                  Incluye todas las dependencias, carpetas, archivos y logs del sistema.
                </p>
              </div>

              <div style="padding: 1rem; background: var(--color-warning-50); border-left: 4px solid var(--color-warning); border-radius: var(--radius-md);">
                <strong>📁 Backup Parcial</strong>
                <p style="margin-top: 0.5rem; margin-bottom: 0; font-size: 0.875rem;">
                  Respalda solo una dependencia específica con sus carpetas y archivos.
                </p>
              </div>

              <div style="padding: 1rem; background: var(--color-danger-50); border-left: 4px solid var(--color-danger); border-radius: var(--radius-md);">
                <strong>⚠️ Importante</strong>
                <p style="margin-top: 0.5rem; margin-bottom: 0; font-size: 0.875rem;">
                  Siempre ejecuta pg_dump antes de restaurar un backup.
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Tabla de backups -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Backups Disponibles</h3>
          </div>
          <div class="card-body" style="overflow-x: auto;">
            <table class="table">
              <thead>
                <tr>
                  <th>Archivo</th>
                  <th>Tipo</th>
                  <th>Fecha</th>
                  <th>Tamaño</th>
                  <th style="width: 200px;">Acciones</th>
                </tr>
              </thead>
              <tbody id="backupsTableBody">
                <tr>
                  <td colspan="5" class="loading-state" style="text-align: center; padding: 3rem;">
                    <div class="spinner"></div>
                    <p style="margin-top: 1rem;">Cargando backups...</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      `;
      
      // Cargar módulo de backups
      const { backupsManager } = await import('./backups.js');
      await backupsManager.init();
    }
  }, { requireAuth: true, requireSuperAdmin: true });

  // Ruta por defecto
  router.registerRoute('/', async (params) => {
    router.navigateTo('/dashboard');
  });

  // 404
  router.onNotFound((path) => {
    router.setPageTitle('Página no encontrada');
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      mainContent.innerHTML = `
        <div style="padding: 4rem 2rem; text-align: center;">
          <h1 style="font-size: 4rem; color: var(--color-gray-400);">404</h1>
          <h2>Página no encontrada</h2>
          <p class="text-muted">La ruta "${path}" no existe</p>
          <button onclick="location.hash='/dashboard'" class="btn btn-primary" style="margin-top: 2rem;">
            Ir al Dashboard
          </button>
        </div>
      `;
    }
  });
}

/**
 * Inicializa la aplicación
 */
async function initializeApp() {
  console.log('Initializing SGDI app...');

  // Verificar autenticación básica (sin refresh automático)
  const token = localStorage.getItem('access_token');
  const expiry = localStorage.getItem('access_expiry_ts');
  const user = localStorage.getItem('current_user');

  console.log('Session check - Token:', !!token, 'Expiry:', !!expiry, 'User:', !!user);

  if (!token || !expiry || !user) {
    console.log('Missing session data, redirecting to login');
    window.location.href = '/login.html';
    return;
  }

  // Verificar expiración
  const now = Date.now();
  const expiryTime = parseInt(expiry);

  if (now >= expiryTime) {
    console.log('Token expired, redirecting to login');
    localStorage.clear();
    window.location.href = '/login.html';
    return;
  }

  console.log('Session valid, proceeding with app initialization');

  // Precargar sprite de iconos
  await preloadIconSprite();

  // Cargar componentes del layout
  loadNavbar();
  loadSidebar();

  // Configurar listeners globales
  setupGlobalListeners();

  // Registrar rutas
  registerRoutes();

  // Inicializar router
  router.init();

  console.log('SGDI app initialized successfully');
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

// Exportar funciones útiles
export { loadNavbar, loadSidebar, getSvgIcon };
