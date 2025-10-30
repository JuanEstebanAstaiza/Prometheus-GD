/**
 * SGDI - Router Module
 * Ruteo ligero basado en hash con guards de autenticación
 */

import { auth } from './auth.js';

class Router {
  constructor() {
    this.routes = [];
    this.currentRoute = null;
    this.guards = [];
    this.notFoundHandler = null;
  }

  /**
   * Registra una ruta con su loader
   * @param {string|RegExp} pattern - Patrón de ruta (puede ser regex)
   * @param {Function} loaderFunction - Función que carga la vista
   * @param {Object} options - Opciones adicionales (requireAuth, requiredRole, etc.)
   */
  registerRoute(pattern, loaderFunction, options = {}) {
    const route = {
      pattern: typeof pattern === 'string' ? this.patternToRegex(pattern) : pattern,
      originalPattern: pattern,
      loader: loaderFunction,
      options
    };
    
    this.routes.push(route);
  }

  /**
   * Convierte patrón de ruta a regex
   * Ej: "/folders/:depId/:folderId" → /^\/folders\/([^/]+)\/([^/]+)$/
   */
  patternToRegex(pattern) {
    // Escapar caracteres especiales excepto :
    const escaped = pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
    
    // Convertir :param a grupos de captura
    const regex = escaped.replace(/:([a-zA-Z_][a-zA-Z0-9_]*)/g, '([^/]+)');
    
    return new RegExp(`^${regex}$`);
  }

  /**
   * Extrae parámetros de la ruta
   */
  extractParams(pattern, path) {
    if (typeof pattern === 'string') {
      const paramNames = [];
      const regex = pattern.replace(/:([a-zA-Z_][a-zA-Z0-9_]*)/g, (_, name) => {
        paramNames.push(name);
        return '([^/]+)';
      });
      
      const match = path.match(new RegExp(`^${regex}$`));
      if (!match) return null;
      
      const params = {};
      paramNames.forEach((name, i) => {
        params[name] = decodeURIComponent(match[i + 1]);
      });
      
      return params;
    }
    
    return null;
  }

  /**
   * Registra un guard global
   * @param {Function} guardFunction - Función que retorna true/false
   */
  addGuard(guardFunction) {
    this.guards.push(guardFunction);
  }

  /**
   * Guard de autenticación
   */
  requireAuth() {
    return async (route, params) => {
      const isAuth = await auth.isAuthenticated();

      if (!isAuth) {
        console.log('Navigation blocked: not authenticated');
        // Como manejamos autenticación a nivel de página, esto no debería suceder
        // Pero por si acaso, redirigir al login
        return false;
      }

      return true;
    };
  }

  /**
   * Guard de rol
   */
  requireRole(role) {
    return async (route, params) => {
      if (!auth.hasRole(role)) {
        console.log(`Navigation blocked: requires role ${role}`);
        alert(`No tienes permisos para acceder a esta página. Se requiere rol: ${auth.getRoleName(role)}`);
        this.navigateTo('/dashboard');
        return false;
      }
      
      return true;
    };
  }

  /**
   * Guard para super admin
   */
  requireSuperAdmin() {
    return this.requireRole('SUPER_ADMIN');
  }

  /**
   * Guard para admin (super admin o admin dep)
   */
  requireAdmin() {
    return async (route, params) => {
      if (!auth.isSuperAdmin() && !auth.isAdminDep()) {
        console.log('Navigation blocked: requires admin role');
        alert('No tienes permisos para acceder a esta página. Se requiere rol de administrador.');
        this.navigateTo('/dashboard');
        return false;
      }
      
      return true;
    };
  }

  /**
   * Navega a una ruta
   * @param {string} hashPath - Ruta con hash (ej: "/dashboard" o "#/dashboard")
   * @param {boolean} replace - Si true, usa replaceState en lugar de pushState
   */
  navigateTo(hashPath, replace = false) {
    // Normalizar path (remover # si existe)
    const path = hashPath.startsWith('#') ? hashPath.substring(1) : hashPath;
    
    // Actualizar hash
    if (replace) {
      window.location.replace(`#${path}`);
    } else {
      window.location.hash = path;
    }
  }

  /**
   * Obtiene la ruta actual (sin #)
   */
  getCurrentPath() {
    return window.location.hash.slice(1) || '/';
  }

  /**
   * Busca la ruta que coincide con el path
   */
  findRoute(path) {
    for (const route of this.routes) {
      const match = path.match(route.pattern);
      if (match) {
        // Extraer parámetros si es un patrón con :params
        const params = this.extractParams(route.originalPattern, path);
        return { route, match, params: params || {} };
      }
    }
    
    return null;
  }

  /**
   * Ejecuta guards de una ruta
   */
  async executeGuards(route, params) {
    // Guards globales
    for (const guard of this.guards) {
      const result = await guard(route, params);
      if (!result) return false;
    }
    
    // Guards específicos de la ruta
    if (route.options.guards) {
      for (const guard of route.options.guards) {
        const result = await guard(route, params);
        if (!result) return false;
      }
    }
    
    // Guard requireAuth
    if (route.options.requireAuth) {
      const authGuard = this.requireAuth();
      const result = await authGuard(route, params);
      if (!result) return false;
    }
    
    // Guard requireRole
    if (route.options.requireRole) {
      const roleGuard = this.requireRole(route.options.requireRole);
      const result = await roleGuard(route, params);
      if (!result) return false;
    }
    
    // Guard requireSuperAdmin
    if (route.options.requireSuperAdmin) {
      const superAdminGuard = this.requireSuperAdmin();
      const result = await superAdminGuard(route, params);
      if (!result) return false;
    }
    
    // Guard requireAdmin
    if (route.options.requireAdmin) {
      const adminGuard = this.requireAdmin();
      const result = await adminGuard(route, params);
      if (!result) return false;
    }
    
    return true;
  }

  /**
   * Maneja cambios en el hash
   */
  async onHashChange() {
    const path = this.getCurrentPath();
    console.log('Route changed to:', path);
    
    // Buscar ruta
    const found = this.findRoute(path);
    
    if (found) {
      const { route, params } = found;
      
      // Ejecutar guards
      const guardsPassed = await this.executeGuards(route, params);
      if (!guardsPassed) {
        console.log('Guards blocked navigation');
        return;
      }
      
      // Actualizar ruta actual
      this.currentRoute = { route, params };
      
      // Ejecutar loader
      try {
        await route.loader(params);
      } catch (error) {
        console.error('Error loading route:', error);
        this.handleError(error);
      }
    } else {
      console.warn('Route not found:', path);
      if (this.notFoundHandler) {
        this.notFoundHandler(path);
      } else {
        // Redirigir a dashboard por defecto
        this.navigateTo('/dashboard', true);
      }
    }
  }

  /**
   * Registra handler para rutas no encontradas
   */
  onNotFound(handler) {
    this.notFoundHandler = handler;
  }

  /**
   * Maneja errores de carga
   */
  handleError(error) {
    console.error('Router error:', error);
    
    // Mostrar mensaje de error al usuario
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
      mainContent.innerHTML = `
        <div style="padding: 2rem; text-align: center;">
          <h2 style="color: var(--color-danger);">Error al cargar la página</h2>
          <p>${error.message || 'Error desconocido'}</p>
          <button onclick="window.location.reload()" class="btn btn-primary">
            Recargar página
          </button>
        </div>
      `;
    }
  }

  /**
   * Inicializa el router
   */
  init() {
    // Escuchar cambios en el hash
    window.addEventListener('hashchange', () => this.onHashChange());
    
    // Manejar ruta inicial
    this.onHashChange();
    
    console.log('Router initialized');
  }

  /**
   * Obtiene parámetros de query string
   */
  getQueryParams() {
    const params = {};
    const queryString = window.location.search.substring(1);
    
    if (!queryString) return params;
    
    const pairs = queryString.split('&');
    pairs.forEach(pair => {
      const [key, value] = pair.split('=');
      if (key) {
        params[decodeURIComponent(key)] = decodeURIComponent(value || '');
      }
    });
    
    return params;
  }

  /**
   * Construye query string desde objeto
   */
  buildQueryString(params) {
    return Object.entries(params)
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      .join('&');
  }

  /**
   * Actualiza el título de la página
   */
  setPageTitle(title) {
    document.title = `${title} - SGDI`;
  }

  /**
   * Marca link activo en el sidebar
   */
  updateActiveLink(path) {
    // Remover active de todos los links
    document.querySelectorAll('.sidebar-link').forEach(link => {
      link.classList.remove('active');
    });
    
    // Agregar active al link actual
    const activeLink = document.querySelector(`.sidebar-link[href="#${path}"]`);
    if (activeLink) {
      activeLink.classList.add('active');
    }
  }
}

// Exportar instancia singleton
export const router = new Router();
