/**
 * SGDI - Auth Module
 * Gestión de autenticación, JWT, refresh y sesión
 * 
 * NOTA DE SEGURIDAD:
 * En producción considerar usar httpOnly cookies en lugar de localStorage
 * para almacenar tokens y prevenir ataques XSS.
 */

import { fetchWrapper } from './lib/fetch-wrapper.js';

class Auth {
  constructor() {
    this.currentUser = null;
    this.loginAttempts = 0;
    this.lockoutUntil = null;
    this.maxLoginAttempts = 5;
    this.lockoutDuration = 30000; // 30 segundos
    this.loadSession();
  }

  /**
   * Carga la sesión del localStorage
   */
  loadSession() {
    const userStr = localStorage.getItem('current_user');
    if (userStr) {
      try {
        this.currentUser = JSON.parse(userStr);
      } catch (error) {
        console.error('Error parsing user data:', error);
        this.currentUser = null;
      }
    }

    // Cargar intentos de login
    const attempts = localStorage.getItem('login_attempts');
    if (attempts) {
      this.loginAttempts = parseInt(attempts);
    }

    const lockout = localStorage.getItem('lockout_until');
    if (lockout) {
      this.lockoutUntil = parseInt(lockout);
    }
  }

  /**
   * Guarda la sesión completa
   * @param {Object} data - { access_token, refresh_token, expires_in, user }
   */
  saveSession(data) {
    if (!data) return;

    // Guardar tokens
    if (data.access_token) {
      fetchWrapper.setTokens(data.access_token, data.refresh_token);
    }

    // Calcular y guardar expiración del access token
    if (data.expires_in) {
      const expiryTs = Date.now() + (data.expires_in * 1000);
      localStorage.setItem('access_expiry_ts', expiryTs.toString());
    }

    // Guardar usuario
    if (data.user) {
      this.currentUser = data.user;
      localStorage.setItem('current_user', JSON.stringify(data.user));
    }

    // Resetear intentos de login
    this.resetLoginAttempts();
  }

  /**
   * Obtiene el access token
   */
  getAccessToken() {
    return fetchWrapper.getAccessToken();
  }

  /**
   * Obtiene el refresh token
   */
  getRefreshToken() {
    return fetchWrapper.getRefreshToken();
  }

  /**
   * Obtiene el usuario actual
   */
  getCurrentUser() {
    if (!this.currentUser) {
      const userStr = localStorage.getItem('current_user');
      if (userStr) {
        try {
          this.currentUser = JSON.parse(userStr);
        } catch (error) {
          console.error('Error parsing user data:', error);
        }
      }
    }
    return this.currentUser;
  }

  /**
   * Verifica si hay un bloqueo activo por intentos fallidos
   */
  isLockedOut() {
    if (!this.lockoutUntil) return false;
    
    if (Date.now() < this.lockoutUntil) {
      const remainingSeconds = Math.ceil((this.lockoutUntil - Date.now()) / 1000);
      return remainingSeconds;
    }

    // El bloqueo expiró
    this.lockoutUntil = null;
    localStorage.removeItem('lockout_until');
    return false;
  }

  /**
   * Incrementa el contador de intentos fallidos
   */
  incrementLoginAttempts() {
    this.loginAttempts++;
    localStorage.setItem('login_attempts', this.loginAttempts.toString());

    if (this.loginAttempts >= this.maxLoginAttempts) {
      this.lockoutUntil = Date.now() + this.lockoutDuration;
      localStorage.setItem('lockout_until', this.lockoutUntil.toString());
    }
  }

  /**
   * Resetea el contador de intentos fallidos
   */
  resetLoginAttempts() {
    this.loginAttempts = 0;
    this.lockoutUntil = null;
    localStorage.removeItem('login_attempts');
    localStorage.removeItem('lockout_until');
  }

  /**
   * Login con email y password
   * @param {string} email 
   * @param {string} password 
   * @returns {Promise<Object>} Datos de sesión
   */
  async login(email, password) {
    // Verificar bloqueo por intentos fallidos
    const lockoutRemaining = this.isLockedOut();
    if (lockoutRemaining) {
      throw {
        status: 429,
        message: `Demasiados intentos fallidos. Intenta de nuevo en ${lockoutRemaining} segundos.`,
        isLockout: true
      };
    }

    try {
      // IMPORTANTE: No almacenar la contraseña en ningún lugar
      // Solo se envía al servidor y se descarta inmediatamente
      const response = await fetchWrapper.post('/auth/login', {
        email: email,
        password: password
      });

      // Guardar sesión
      this.saveSession(response);

      return response;
    } catch (error) {
      console.error('Login error:', error);

      // Incrementar intentos fallidos
      if (error.status === 401) {
        this.incrementLoginAttempts();
        
        const remainingAttempts = this.maxLoginAttempts - this.loginAttempts;
        if (remainingAttempts > 0) {
          error.message = `Credenciales inválidas. Te quedan ${remainingAttempts} intentos.`;
        }
      }

      // Manejar rate limiting del servidor
      if (error.status === 429) {
        error.message = error.data?.detail || 'Demasiadas peticiones. Intenta más tarde.';
      }

      throw error;
    }
  }

  /**
   * Logout
   */
  async logout() {
    try {
      const refreshToken = this.getRefreshToken();
      
      if (refreshToken) {
        // Intentar notificar al servidor (no bloqueante)
        await fetchWrapper.post('/auth/logout', {
          refresh_token: refreshToken
        }).catch(err => console.warn('Logout notification failed:', err));
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Limpiar todo
      fetchWrapper.clearTokens();
      this.currentUser = null;
      
      // No resetear intentos de login en logout (solo en login exitoso)
      
      // Redirigir al login
      window.location.href = '/login.html';
    }
  }

  /**
   * Verifica si el usuario está autenticado
   * Intenta refresh automático si el token está expirado
   */
  async isAuthenticated() {
    const token = this.getAccessToken();
    const user = this.getCurrentUser();

    if (!token || !user) {
      return false;
    }

    // Verificar si el token está expirado
    if (fetchWrapper.isTokenExpired()) {
      try {
        // Intentar refresh automático
        await fetchWrapper.refreshAccessToken();
        return true;
      } catch (error) {
        console.error('Auto-refresh failed:', error);
        return false;
      }
    }

    return true;
  }

  /**
   * Verifica el token actual
   */
  async verifyToken() {
    try {
      const response = await fetchWrapper.get('/auth/verify');
      return response.valid;
    } catch (error) {
      return false;
    }
  }

  /**
   * Obtiene el perfil del usuario actual
   */
  async getProfile() {
    try {
      const response = await fetchWrapper.get('/users/me');
      
      // Actualizar usuario en sesión
      this.currentUser = response;
      localStorage.setItem('current_user', JSON.stringify(response));
      
      return response;
    } catch (error) {
      console.error('Error getting profile:', error);
      throw error;
    }
  }

  /**
   * Actualiza el perfil del usuario
   */
  async updateProfile(data) {
    try {
      const response = await fetchWrapper.put('/users/me', data);
      
      // Actualizar usuario en sesión
      this.currentUser = response;
      localStorage.setItem('current_user', JSON.stringify(response));
      
      return response;
    } catch (error) {
      console.error('Error updating profile:', error);
      throw error;
    }
  }

  /**
   * Cambia la contraseña del usuario
   * NOTA: old_password y new_password NO se almacenan, solo se envían al servidor
   */
  async changePassword(oldPassword, newPassword) {
    try {
      const response = await fetchWrapper.post('/users/me/change-password', {
        old_password: oldPassword,
        new_password: newPassword
      });
      return response;
    } catch (error) {
      console.error('Error changing password:', error);
      throw error;
    }
  }

  /**
   * Verifica si el usuario tiene un rol específico
   */
  hasRole(role) {
    return this.currentUser && this.currentUser.role === role;
  }

  /**
   * Verifica si el usuario es super admin
   */
  isSuperAdmin() {
    return this.hasRole('SUPER_ADMIN');
  }

  /**
   * Verifica si el usuario es admin de dependencia
   */
  isAdminDep() {
    return this.hasRole('ADMIN_DEP');
  }

  /**
   * Verifica si el usuario es worker
   */
  isWorker() {
    return this.hasRole('WORKER');
  }

  /**
   * Verifica si el usuario es reader
   */
  isReader() {
    return this.hasRole('READER');
  }

  /**
   * Protege una página - redirige a login si no está autenticado
   */
  requireAuth() {
    if (!this.getAccessToken() || !this.getCurrentUser()) {
      window.location.href = '/login.html';
      return false;
    }
    return true;
  }

  /**
   * Requiere un rol específico
   */
  requireRole(role) {
    if (!this.requireAuth()) {
      return false;
    }

    if (!this.hasRole(role)) {
      alert('No tienes permisos para acceder a esta página');
      window.location.href = '/dashboard.html';
      return false;
    }

    return true;
  }

  /**
   * Requiere super admin
   */
  requireSuperAdmin() {
    return this.requireRole('SUPER_ADMIN');
  }

  /**
   * Obtiene el nombre del rol en formato legible
   */
  getRoleName(role) {
    const roles = {
      'SUPER_ADMIN': 'Super Administrador',
      'ADMIN_DEP': 'Administrador de Dependencia',
      'WORKER': 'Trabajador',
      'READER': 'Lector'
    };
    return roles[role] || role;
  }

  /**
   * Actualiza el UI con la información del usuario
   * Debe llamarse después del login o cuando se carga la página
   */
  attachAuthToUI() {
    const user = this.getCurrentUser();
    if (!user) return;

    // Actualizar nombre de usuario en header
    const userNameEl = document.getElementById('userName');
    if (userNameEl) {
      userNameEl.textContent = user.full_name;
    }

    // Actualizar rol
    const userRoleEl = document.getElementById('userRole');
    if (userRoleEl) {
      userRoleEl.textContent = this.getRoleName(user.role);
    }

    // Actualizar avatar (primera letra del nombre)
    const userAvatarEl = document.getElementById('userAvatar');
    if (userAvatarEl) {
      userAvatarEl.textContent = user.full_name.charAt(0).toUpperCase();
    }

    // Actualizar email si existe elemento
    const userEmailEl = document.getElementById('userEmail');
    if (userEmailEl) {
      userEmailEl.textContent = user.email;
    }

    // Mostrar/ocultar elementos según rol
    this.updateMenuByRole(user.role);
  }

  /**
   * Actualiza el menú según el rol del usuario
   */
  updateMenuByRole(role) {
    // Ocultar opciones de super admin si no es super admin
    const superAdminOnly = document.querySelectorAll('[data-role="SUPER_ADMIN"]');
    superAdminOnly.forEach(el => {
      el.style.display = role === 'SUPER_ADMIN' ? '' : 'none';
    });

    // Ocultar opciones de admin si es worker o reader
    const adminOnly = document.querySelectorAll('[data-role="ADMIN_DEP"]');
    adminOnly.forEach(el => {
      el.style.display = (role === 'SUPER_ADMIN' || role === 'ADMIN_DEP') ? '' : 'none';
    });

    // Ocultar opciones de escritura si es reader
    const writeOnly = document.querySelectorAll('[data-permission="write"]');
    writeOnly.forEach(el => {
      el.style.display = role !== 'READER' ? '' : 'none';
    });
  }
}

// Exportar instancia singleton
export const auth = new Auth();
