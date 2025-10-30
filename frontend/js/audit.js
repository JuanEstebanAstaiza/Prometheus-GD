/**
 * SGDI - Audit Module
 * Visualización y exportación de logs de auditoría
 */

import { fetchWrapper } from './lib/fetch-wrapper.js';
import { auth } from './auth.js';
import { ui } from './ui.js';
import { validators } from './lib/validators.js';

class AuditManager {
  constructor() {
    this.logs = [];
    this.users = [];
    this.dependencies = [];
    this.currentPage = 1;
    this.pageSize = 50;
    this.totalCount = 0;
    this.currentFilters = {
      start_date: '',
      end_date: '',
      user_id: '',
      dependency_id: '',
      action_type: '',
      search: ''
    };
    this.actionTypes = [
      'LOGIN',
      'LOGOUT',
      'CREATE_FOLDER',
      'UPDATE_FOLDER',
      'DELETE_FOLDER',
      'UPLOAD_FILE',
      'DOWNLOAD_FILE',
      'UPDATE_FILE',
      'DELETE_FILE',
      'CREATE_USER',
      'UPDATE_USER',
      'DELETE_USER',
      'BACKUP',
      'RESTORE'
    ];
  }

  /**
   * Inicializa el módulo de auditoría
   */
  async init() {
    this.setupDefaultDates();
    await this.loadUsers();
    await this.loadDependencies();
    await this.loadLogs();
    this.setupEventListeners();
  }

  /**
   * Configura fechas por defecto (últimos 30 días)
   */
  setupDefaultDates() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    const startInput = document.getElementById('startDate');
    const endInput = document.getElementById('endDate');

    if (startInput) {
      startInput.value = startDate.toISOString().split('T')[0];
      this.currentFilters.start_date = startInput.value;
    }

    if (endInput) {
      endInput.value = endDate.toISOString().split('T')[0];
      this.currentFilters.end_date = endInput.value;
    }
  }

  /**
   * Carga usuarios para filtro
   */
  async loadUsers() {
    try {
      const currentUser = auth.getCurrentUser();
      const isSuperAdmin = auth.isSuperAdmin();

      const params = {};
      if (!isSuperAdmin && currentUser.dependency_id) {
        params.dependency_id = currentUser.dependency_id;
      }

      const response = await fetchWrapper.get('/users', params);
      
      // Manejar respuesta paginada o array directo
      if (Array.isArray(response)) {
        this.users = response;
      } else if (response && Array.isArray(response.items)) {
        this.users = response.items;
      } else if (response && Array.isArray(response.users)) {
        this.users = response.users;
      } else {
        console.warn('[audit.js] Formato de respuesta inesperado:', response);
        this.users = [];
      }
    } catch (error) {
      console.error('Error loading users:', error);
      this.users = [];
    }
  }

  /**
   * Carga dependencias para filtro
   */
  async loadDependencies() {
    try {
      const response = await fetchWrapper.get('/dependencies');
      // El endpoint devuelve { items: [...], total: N }
      this.dependencies = response.items || response || [];
    } catch (error) {
      console.error('Error loading dependencies:', error);
      this.dependencies = [];
    }
  }

  /**
   * Carga los logs de auditoría
   */
  async loadLogs() {
    const tableBody = document.getElementById('auditTableBody');
    if (!tableBody) return;

    // Mostrar loading
    tableBody.innerHTML = `
      <tr>
        <td colspan="7" class="loading-state" style="text-align: center; padding: 3rem;">
          <div class="spinner"></div>
          <p style="margin-top: 1rem;">Cargando logs...</p>
        </td>
      </tr>
    `;

    try {
      // Construir params
      const params = {
        limit: this.pageSize,
        offset: (this.currentPage - 1) * this.pageSize,
        format: 'json'
      };

      // Agregar filtros
      if (this.currentFilters.start_date) {
        params.start_date = this.currentFilters.start_date;
      }
      if (this.currentFilters.end_date) {
        params.end_date = this.currentFilters.end_date;
      }
      if (this.currentFilters.user_id) {
        params.user_id = this.currentFilters.user_id;
      }
      if (this.currentFilters.dependency_id) {
        params.dependency_id = this.currentFilters.dependency_id;
      }
      if (this.currentFilters.action_type) {
        params.action_type = this.currentFilters.action_type;
      }
      if (this.currentFilters.search) {
        params.q = this.currentFilters.search;
      }

      const response = await fetchWrapper.get('/audit/logs', params);

      // Si el backend devuelve paginación
      if (response.logs) {
        this.logs = response.logs;
        this.totalCount = response.total || response.logs.length;
      } else if (response.items) {
        this.logs = response.items;
        this.totalCount = response.total || response.items.length;
      } else if (Array.isArray(response)) {
        this.logs = response;
        this.totalCount = response.length;
      } else {
        this.logs = [];
        this.totalCount = 0;
      }

      // Filtrar por búsqueda en cliente si backend no soporta 'q'
      if (this.currentFilters.search && !params.q) {
        this.logs = this.filterLogsBySearch(this.logs);
      }

      this.renderLogsTable();
      this.renderPagination();

    } catch (error) {
      console.error('Error loading logs:', error);
      ui.error('Error al cargar logs de auditoría');
      
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state" style="text-align: center; padding: 3rem;">
            <div class="empty-state-icon" style="color: var(--color-danger);">⚠️</div>
            <h3 class="empty-state-title">Error al cargar logs</h3>
            <p class="empty-state-description">${error.message || 'Error desconocido'}</p>
            <button class="btn btn-primary" onclick="auditManager.loadLogs()">Reintentar</button>
          </td>
        </tr>
      `;
    }
  }

  /**
   * Filtra logs por búsqueda en cliente
   */
  filterLogsBySearch(logs) {
    if (!this.currentFilters.search) return logs;

    const search = this.currentFilters.search.toLowerCase();
    return logs.filter(log => {
      const summary = (log.summary || '').toLowerCase();
      const details = JSON.stringify(log.details || {}).toLowerCase();
      const userName = (log.user_full_name || '').toLowerCase();
      
      return summary.includes(search) || 
             details.includes(search) || 
             userName.includes(search);
    });
  }

  /**
   * Configura event listeners
   */
  setupEventListeners() {
    // Filtros
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const userFilter = document.getElementById('userFilter');
    const depFilter = document.getElementById('dependencyFilter');
    const actionFilter = document.getElementById('actionTypeFilter');
    const searchInput = document.getElementById('auditSearch');
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    const exportBtn = document.getElementById('exportCsvBtn');

    if (startDate) {
      startDate.addEventListener('change', () => {
        this.currentFilters.start_date = startDate.value;
      });
    }

    if (endDate) {
      endDate.addEventListener('change', () => {
        this.currentFilters.end_date = endDate.value;
      });
    }

    if (userFilter) {
      userFilter.addEventListener('change', () => {
        this.currentFilters.user_id = userFilter.value;
      });
    }

    if (depFilter) {
      depFilter.addEventListener('change', () => {
        this.currentFilters.dependency_id = depFilter.value;
      });
    }

    if (actionFilter) {
      actionFilter.addEventListener('change', () => {
        this.currentFilters.action_type = actionFilter.value;
      });
    }

    if (searchInput) {
      // Búsqueda con debounce
      let searchTimeout;
      searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
          this.currentFilters.search = searchInput.value.trim();
          this.currentPage = 1;
          this.loadLogs();
        }, 500);
      });
    }

    if (applyFiltersBtn) {
      applyFiltersBtn.addEventListener('click', () => {
        this.currentPage = 1;
        this.loadLogs();
      });
    }

    if (clearFiltersBtn) {
      clearFiltersBtn.addEventListener('click', () => {
        this.clearFilters();
      });
    }

    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        this.exportCSV();
      });
    }
  }

  /**
   * Renderiza la tabla de logs
   */
  renderLogsTable() {
    const tableBody = document.getElementById('auditTableBody');
    if (!tableBody) return;

    if (this.logs.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state" style="text-align: center; padding: 3rem;">
            <div class="empty-state-icon">🔍</div>
            <h3 class="empty-state-title">No se encontraron logs</h3>
            <p class="empty-state-description">
              ${Object.values(this.currentFilters).some(v => v) 
                ? 'Intenta cambiar los filtros de búsqueda' 
                : 'Aún no hay logs de auditoría'}
            </p>
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = this.logs.map(log => `
      <tr>
        <td data-label="Fecha/Hora">
          <div style="font-weight: 500;">
            ${new Date(log.timestamp).toLocaleDateString('es-ES', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric'
            })}
          </div>
          <div style="font-size: 0.875rem; color: var(--color-gray-600);">
            ${new Date(log.timestamp).toLocaleTimeString('es-ES', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            })}
          </div>
        </td>
        <td data-label="Usuario">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div class="user-avatar" style="width: 24px; height: 24px; font-size: 0.75rem;">
              ${(log.user_full_name || '?').charAt(0).toUpperCase()}
            </div>
            <div>
              <div style="font-weight: 500; font-size: 0.875rem;">
                ${this.escapeHtml(log.user_full_name || 'Usuario desconocido')}
              </div>
              <div style="font-size: 0.75rem; color: var(--color-gray-600);">
                ${log.user_email || ''}
              </div>
            </div>
          </div>
        </td>
        <td data-label="Rol">
          <span class="badge badge-${this.getRoleBadgeColor(log.user_role)}">
            ${this.getRoleName(log.user_role)}
          </span>
        </td>
        <td data-label="Acción">
          <span class="badge badge-${this.getActionBadgeColor(log.action_type)}">
            ${this.formatActionType(log.action_type)}
          </span>
        </td>
        <td data-label="Recurso">
          ${this.renderTargetInfo(log)}
        </td>
        <td data-label="Resumen">
          <div style="max-width: 300px;">
            ${this.escapeHtml(log.summary || this.generateSummary(log))}
          </div>
        </td>
        <td data-label="IP">
          <span style="font-family: monospace; font-size: 0.875rem; color: var(--color-gray-600);">
            ${log.ip_address || 'N/A'}
          </span>
        </td>
      </tr>
    `).join('');
  }

  /**
   * Renderiza información del recurso target
   */
  renderTargetInfo(log) {
    if (!log.target_type) {
      return '<span class="text-muted">—</span>';
    }

    const icons = {
      'file': '📄',
      'folder': '📁',
      'user': '👤',
      'dependency': '🏢',
      'backup': '💾'
    };

    const icon = icons[log.target_type] || '📦';
    const targetId = log.target_id ? `<div style="font-size: 0.75rem; color: var(--color-gray-500); font-family: monospace;">${log.target_id.substring(0, 8)}...</div>` : '';

    return `
      <div>
        <div style="font-size: 0.875rem;">
          ${icon} ${this.escapeHtml(log.target_type)}
        </div>
        ${targetId}
      </div>
    `;
  }

  /**
   * Genera resumen si no existe
   */
  generateSummary(log) {
    const user = log.user_full_name || 'Usuario';
    const action = this.formatActionType(log.action_type);
    const target = log.target_type || 'recurso';
    
    return `${user} realizó ${action} en ${target}`;
  }

  /**
   * Renderiza paginación
   */
  renderPagination() {
    const paginationContainer = document.getElementById('paginationContainer');
    if (!paginationContainer) return;

    const totalPages = Math.ceil(this.totalCount / this.pageSize);

    if (totalPages <= 1) {
      paginationContainer.innerHTML = '';
      return;
    }

    const maxButtons = 7;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);

    if (endPage - startPage < maxButtons - 1) {
      startPage = Math.max(1, endPage - maxButtons + 1);
    }

    const buttons = [];

    // Botón anterior
    buttons.push(`
      <button 
        class="btn btn-sm btn-secondary" 
        ${this.currentPage === 1 ? 'disabled' : ''}
        onclick="auditManager.goToPage(${this.currentPage - 1})"
      >
        ‹ Anterior
      </button>
    `);

    // Primera página
    if (startPage > 1) {
      buttons.push(`
        <button class="btn btn-sm btn-secondary" onclick="auditManager.goToPage(1)">1</button>
      `);
      if (startPage > 2) {
        buttons.push('<span style="padding: 0 0.5rem;">...</span>');
      }
    }

    // Páginas numeradas
    for (let i = startPage; i <= endPage; i++) {
      buttons.push(`
        <button 
          class="btn btn-sm ${i === this.currentPage ? 'btn-primary' : 'btn-secondary'}" 
          onclick="auditManager.goToPage(${i})"
        >
          ${i}
        </button>
      `);
    }

    // Última página
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        buttons.push('<span style="padding: 0 0.5rem;">...</span>');
      }
      buttons.push(`
        <button class="btn btn-sm btn-secondary" onclick="auditManager.goToPage(${totalPages})">${totalPages}</button>
      `);
    }

    // Botón siguiente
    buttons.push(`
      <button 
        class="btn btn-sm btn-secondary" 
        ${this.currentPage === totalPages ? 'disabled' : ''}
        onclick="auditManager.goToPage(${this.currentPage + 1})"
      >
        Siguiente ›
      </button>
    `);

    paginationContainer.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
        ${buttons.join('')}
      </div>
      <div style="font-size: 0.875rem; color: var(--color-gray-600); margin-top: 0.5rem;">
        Mostrando ${((this.currentPage - 1) * this.pageSize) + 1} - ${Math.min(this.currentPage * this.pageSize, this.totalCount)} de ${this.totalCount} registros
      </div>
    `;
  }

  /**
   * Navega a una página
   */
  goToPage(page) {
    if (page < 1 || page > Math.ceil(this.totalCount / this.pageSize)) {
      return;
    }

    this.currentPage = page;
    this.loadLogs();

    // Scroll al inicio de la tabla
    const table = document.getElementById('auditTableBody');
    if (table) {
      table.closest('.card').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  /**
   * Limpia todos los filtros
   */
  clearFilters() {
    // Resetear filtros
    this.currentFilters = {
      start_date: '',
      end_date: '',
      user_id: '',
      dependency_id: '',
      action_type: '',
      search: ''
    };

    // Limpiar inputs
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const userFilter = document.getElementById('userFilter');
    const depFilter = document.getElementById('dependencyFilter');
    const actionFilter = document.getElementById('actionTypeFilter');
    const searchInput = document.getElementById('auditSearch');

    if (startDate) startDate.value = '';
    if (endDate) endDate.value = '';
    if (userFilter) userFilter.value = '';
    if (depFilter) depFilter.value = '';
    if (actionFilter) actionFilter.value = '';
    if (searchInput) searchInput.value = '';

    // Reestablecer fechas por defecto
    this.setupDefaultDates();

    // Recargar
    this.currentPage = 1;
    this.loadLogs();
  }

  /**
   * Exporta logs a CSV
   */
  async exportCSV() {
    try {
      ui.showLoading('Generando CSV...');

      // Construir params (sin limit/offset para obtener todos)
      const params = {
        format: 'csv'
      };

      if (this.currentFilters.start_date) {
        params.start_date = this.currentFilters.start_date;
      }
      if (this.currentFilters.end_date) {
        params.end_date = this.currentFilters.end_date;
      }
      if (this.currentFilters.user_id) {
        params.user_id = this.currentFilters.user_id;
      }
      if (this.currentFilters.dependency_id) {
        params.dependency_id = this.currentFilters.dependency_id;
      }
      if (this.currentFilters.action_type) {
        params.action_type = this.currentFilters.action_type;
      }
      if (this.currentFilters.search) {
        params.q = this.currentFilters.search;
      }

      // Construir query string
      const queryString = new URLSearchParams(params).toString();
      
      // Descargar usando fetch directo
      const token = auth.getAccessToken();
      const response = await fetch(
        `${fetchWrapper.baseURL}/audit/logs?${queryString}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Request-Id': this.generateUUID()
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to export CSV');
      }

      // Obtener filename del header si existe
      const disposition = response.headers.get('Content-Disposition');
      let filename = 'audit-logs.csv';
      
      if (disposition && disposition.includes('filename=')) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
        if (matches && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }

      // Descargar
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      ui.hideLoading();
      ui.success('CSV exportado correctamente');

    } catch (error) {
      ui.hideLoading();
      console.error('Export CSV error:', error);
      ui.error('Error al exportar CSV');
    }
  }

  /**
   * Formatea tipo de acción
   */
  formatActionType(action) {
    return action.replace(/_/g, ' ');
  }

  /**
   * Obtiene color de badge para acción
   */
  getActionBadgeColor(action) {
    if (!action) return 'gray';
    
    if (action.includes('CREATE')) return 'success';
    if (action.includes('DELETE')) return 'danger';
    if (action.includes('UPDATE')) return 'warning';
    if (action.includes('LOGIN')) return 'primary';
    if (action.includes('DOWNLOAD')) return 'info';
    
    return 'gray';
  }

  /**
   * Obtiene nombre del rol
   */
  getRoleName(role) {
    return auth.getRoleName(role);
  }

  /**
   * Obtiene color de badge para rol
   */
  getRoleBadgeColor(role) {
    const colors = {
      'SUPER_ADMIN': 'danger',
      'ADMIN_DEP': 'warning',
      'WORKER': 'primary',
      'READER': 'gray'
    };
    return colors[role] || 'gray';
  }

  /**
   * Genera UUID v4
   */
  generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  /**
   * Escapa HTML para prevenir XSS
   */
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Exportar instancia singleton
export const auditManager = new AuditManager();

// Hacer disponible globalmente
window.auditManager = auditManager;
