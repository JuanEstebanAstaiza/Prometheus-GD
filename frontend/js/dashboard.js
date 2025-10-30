/**
 * SGDI - Dashboard Module
 * Lógica del dashboard principal
 */

import { auth } from './auth.js';
import { fetchWrapper } from './lib/fetch-wrapper.js';
import { ui } from './ui.js';

/**
 * Carga las estadísticas del dashboard
 */
async function loadStats() {
  const statsContainer = document.getElementById('statsContainer');
  if (!statsContainer) return;

  const user = auth.getCurrentUser();
  
  // Stats básicas
  const stats = [
    {
      title: 'Usuario Actual',
      value: user.full_name,
      subtitle: auth.getRoleName(user.role),
      icon: '👤',
      color: 'var(--color-primary-500)'
    },
    {
      title: 'Rol',
      value: auth.getRoleName(user.role),
      subtitle: 'Permisos asignados',
      icon: '🔐',
      color: 'var(--color-success)'
    }
  ];

  // Si es super admin o admin, agregar más stats
  if (auth.isSuperAdmin() || auth.isAdminDep()) {
    stats.push({
      title: 'Sistema',
      value: 'Operativo',
      subtitle: 'Todos los servicios funcionando',
      icon: '✅',
      color: 'var(--color-info)'
    });
  }

  // Renderizar stats
  statsContainer.innerHTML = stats.map(stat => `
    <div class="stat-card" style="border-left-color: ${stat.color};">
      <div class="stat-card-header">
        <div class="stat-card-icon">${stat.icon}</div>
        <div style="flex: 1;">
          <div class="stat-card-label">${stat.title}</div>
          <div class="stat-card-value">${stat.value}</div>
          <div class="stat-card-subtitle">${stat.subtitle}</div>
        </div>
      </div>
    </div>
  `).join('');
}

/**
 * Carga la actividad reciente
 */
async function loadRecentActivity() {
  const container = document.getElementById('recentActivityContainer');
  if (!container) return;

  try {
    // Obtener logs recientes
    const response = await fetchWrapper.get('/audit/logs', { limit: 10 });
    const logs = response.logs || [];

    if (!logs || logs.length === 0) {
      container.innerHTML = '<p class="text-muted">No hay actividad reciente.</p>';
      return;
    }

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: var(--space-3);">
        ${logs.map(log => `
          <div style="padding: var(--space-3); background: var(--color-gray-50); border-radius: var(--radius-md); display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="font-semibold">${log.summary || log.action_type}</div>
              <div class="text-sm text-muted">
                ${log.user_full_name || 'Usuario desconocido'} • ${ui.formatDate(log.timestamp)}
              </div>
            </div>
            <span class="badge badge-${getActionBadgeColor(log.action_type)}">${log.action_type}</span>
          </div>
        `).join('')}
      </div>
    `;
  } catch (error) {
    console.error('Error loading recent activity:', error);
    container.innerHTML = '<p class="text-muted">Error al cargar la actividad reciente.</p>';
  }
}

/**
 * Obtiene el color del badge según el tipo de acción
 */
function getActionBadgeColor(action) {
  if (action.includes('CREATE')) return 'success';
  if (action.includes('DELETE')) return 'danger';
  if (action.includes('UPDATE')) return 'warning';
  if (action.includes('LOGIN')) return 'primary';
  return 'gray';
}

// Inicializar dashboard cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', async () => {
    await loadStats();
    await loadRecentActivity();
  });
} else {
  loadStats();
  loadRecentActivity();
}

export { loadStats, loadRecentActivity };

