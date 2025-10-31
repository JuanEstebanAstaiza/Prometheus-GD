/**
 * SGDI - Users Management Module
 * Gestión completa de usuarios y dependencias con permisos según rol
 */

import { fetchWrapper } from './lib/fetch-wrapper.js';
import { auth } from './auth.js';
import { ui } from './ui.js';
import { validators } from './lib/validators.js';

class UsersManager {
  constructor() {
    this.users = [];
    this.dependencies = [];
    this.currentFilters = {
      search: '',
      role: '',
      dependency: '',
      status: ''
    };
  }

  /**
   * Inicializa el módulo de usuarios
   */
  async init() {
    await this.loadDependencies();
    await this.loadUsers();
    this.setupEventListeners();
  }

  /**
   * Carga las dependencias
   */
  async loadDependencies() {
    try {
      const response = await fetchWrapper.get('/dependencies');
      // El endpoint devuelve { items: [...], total: N }
      this.dependencies = response.items || response || [];
    } catch (error) {
      console.error('Error loading dependencies:', error);
      ui.error('Error al cargar dependencias');
      this.dependencies = [];
    }
  }

  /**
   * Carga los usuarios
   */
  async loadUsers() {
    try {
      const user = auth.getCurrentUser();
      const isSuperAdmin = auth.isSuperAdmin();

      // Si es admin de dependencia, solo cargar usuarios de su dependencia
      const params = {};
      if (!isSuperAdmin && user.dependency_id) {
        params.dependency_id = user.dependency_id;
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
        console.warn('[users.js] Formato de respuesta inesperado:', response);
        this.users = [];
      }

      console.log('[users.js] Users loaded:', this.users.length);
      this.renderUsersTable();
    } catch (error) {
      console.error('Error loading users:', error);
      ui.error('Error al cargar usuarios');
      this.users = [];
      this.renderUsersTable();
    }
  }

  /**
   * Configura event listeners
   */
  setupEventListeners() {
    // Botón crear usuario
    const createUserBtn = document.getElementById('createUserBtn');
    if (createUserBtn) {
      createUserBtn.addEventListener('click', () => {
        this.showCreateUserModal();
      });
    }

    // Botón crear dependencia (solo super admin)
    const createDepBtn = document.getElementById('createDependencyBtn');
    if (createDepBtn && auth.isSuperAdmin()) {
      createDepBtn.style.display = 'inline-flex';
      createDepBtn.addEventListener('click', () => {
        this.showCreateDependencyModal();
      });
    }

    // Búsqueda
    const searchInput = document.getElementById('userSearch');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.currentFilters.search = e.target.value;
        this.renderUsersTable();
      });
    }

    // Filtros
    const roleFilter = document.getElementById('roleFilter');
    if (roleFilter) {
      roleFilter.addEventListener('change', (e) => {
        this.currentFilters.role = e.target.value;
        this.renderUsersTable();
      });
    }

    const depFilter = document.getElementById('dependencyFilter');
    if (depFilter) {
      depFilter.addEventListener('change', (e) => {
        this.currentFilters.dependency = e.target.value;
        this.renderUsersTable();
      });
    }

    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
      statusFilter.addEventListener('change', (e) => {
        this.currentFilters.status = e.target.value;
        this.renderUsersTable();
      });
    }
  }

  /**
   * Filtra usuarios según criterios actuales
   */
  filterUsers() {
    let filtered = [...this.users];

    // Búsqueda por texto
    if (this.currentFilters.search) {
      const search = this.currentFilters.search.toLowerCase();
      filtered = filtered.filter(u => 
        u.full_name.toLowerCase().includes(search) ||
        u.email.toLowerCase().includes(search)
      );
    }

    // Filtro por rol
    if (this.currentFilters.role) {
      filtered = filtered.filter(u => u.role === this.currentFilters.role);
    }

    // Filtro por dependencia
    if (this.currentFilters.dependency) {
      filtered = filtered.filter(u => u.dependency_id === this.currentFilters.dependency);
    }

    // Filtro por estado
    if (this.currentFilters.status) {
      const isActive = this.currentFilters.status === 'active';
      filtered = filtered.filter(u => u.is_active === isActive);
    }

    return filtered;
  }

  /**
   * Renderiza la tabla de usuarios
   */
  renderUsersTable() {
    const tableBody = document.getElementById('usersTableBody');
    if (!tableBody) return;

    const filteredUsers = this.filterUsers();
    const currentUser = auth.getCurrentUser();
    const isSuperAdmin = auth.isSuperAdmin();

    if (filteredUsers.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-state" style="text-align: center; padding: 3rem;">
            <div class="empty-state-icon" style="font-size: 3rem;">👥</div>
            <h3 class="empty-state-title">No se encontraron usuarios</h3>
            <p class="empty-state-description">
              ${this.currentFilters.search || this.currentFilters.role || this.currentFilters.dependency 
                ? 'Intenta cambiar los filtros de búsqueda' 
                : 'Aún no hay usuarios registrados'}
            </p>
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = filteredUsers.map(user => {
      // Verificar permisos para editar/eliminar este usuario
      const canEdit = isSuperAdmin || 
                     (auth.isAdminDep() && user.dependency_id === currentUser.dependency_id);
      const isCurrentUser = user.id === currentUser.id;

      const dependency = this.dependencies.find(d => d.id === user.dependency_id);

      return `
        <tr>
          <td>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <div class="user-avatar" style="width: 32px; height: 32px; border-radius: var(--radius-full); background: var(--color-primary-500); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.875rem;">
                ${user.full_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div style="font-weight: 600;">
                  ${this.escapeHtml(user.full_name)}
                  ${isCurrentUser ? '<span class="badge badge-primary" style="margin-left: 0.5rem;">Tú</span>' : ''}
                </div>
                <div style="font-size: 0.875rem; color: var(--color-gray-600);">
                  ${this.escapeHtml(user.email)}
                </div>
              </div>
            </div>
          </td>
          <td>
            <span class="badge badge-${this.getRoleBadgeColor(user.role)}">
              ${this.getRoleName(user.role)}
            </span>
          </td>
          <td>
            ${dependency ? this.escapeHtml(dependency.name) : '<span class="text-muted">Sin asignar</span>'}
          </td>
          <td>
            <span class="badge badge-${user.is_active ? 'success' : 'gray'}">
              ${user.is_active ? 'Activo' : 'Inactivo'}
            </span>
          </td>
          <td>
            <div style="font-size: 0.875rem; color: var(--color-gray-600);">
              ${ui.formatDate(user.created_at)}
            </div>
          </td>
          <td>
            <div class="table-actions">
              ${canEdit ? `
                <button 
                  class="btn btn-sm btn-secondary" 
                  onclick="usersManager.showEditUserModal('${user.id}')"
                  title="Editar usuario"
                >
                  <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
                  </svg>
                </button>
                ${!isCurrentUser ? `
                  ${user.is_active ? `
                    <button 
                      class="btn btn-sm btn-warning" 
                      onclick="usersManager.showDeactivateUserModal('${user.id}')"
                      title="Desactivar usuario"
                    >
                      <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd"/>
                      </svg>
                    </button>
                  ` : `
                    <button 
                      class="btn btn-sm btn-danger" 
                      onclick="usersManager.showPermanentDeleteUserModal('${user.id}')"
                      title="Eliminar permanentemente"
                    >
                      <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
                      </svg>
                    </button>
                  `}
                ` : ''}
              ` : `
                <span class="text-muted" style="font-size: 0.875rem;" title="No tienes permisos para editar este usuario">
                  🔒 Sin permisos
                </span>
              `}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  /**
   * Muestra modal para crear usuario
   */
  showCreateUserModal() {
    const currentUser = auth.getCurrentUser();
    const isSuperAdmin = auth.isSuperAdmin();

    // Admin dep solo puede crear en su dependencia
    const availableDeps = isSuperAdmin 
      ? this.dependencies 
      : this.dependencies.filter(d => d.id === currentUser.dependency_id);

    const content = document.createElement('div');
    content.innerHTML = `
      <form id="createUserForm">
        <div class="form-group">
          <label for="createUserFullName" class="form-label">Nombre Completo *</label>
          <input 
            type="text" 
            id="createUserFullName" 
            class="form-input" 
            placeholder="Ej: Juan Pérez"
            required
            autofocus
          >
          <div id="createUserFullNameError" class="form-error hidden"></div>
        </div>

        <div class="form-group">
          <label for="createUserEmail" class="form-label">Email *</label>
          <input 
            type="email" 
            id="createUserEmail" 
            class="form-input" 
            placeholder="usuario@empresa.com"
            required
          >
          <div id="createUserEmailError" class="form-error hidden"></div>
        </div>

        <div class="form-group">
          <label for="createUserPassword" class="form-label">Contraseña *</label>
          <input 
            type="password" 
            id="createUserPassword" 
            class="form-input" 
            placeholder="Mínimo 8 caracteres"
            required
          >
          <div id="createUserPasswordError" class="form-error hidden"></div>
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            Mínimo 8 caracteres, debe incluir mayúsculas, minúsculas y números
          </p>
        </div>

        <div class="form-group">
          <label for="createUserRole" class="form-label">Rol *</label>
          <select id="createUserRole" class="form-input" required>
            <option value="">Seleccionar...</option>
            ${isSuperAdmin ? '<option value="SUPER_ADMIN">Super Administrador</option>' : ''}
            <option value="ADMIN_DEP">Administrador de Dependencia</option>
            <option value="WORKER">Trabajador</option>
            <option value="READER">Lector</option>
          </select>
          <div id="createUserRoleError" class="form-error hidden"></div>
        </div>

        <div class="form-group">
          <label for="createUserDependency" class="form-label">Dependencia ${isSuperAdmin ? '' : '*'}</label>
          <select id="createUserDependency" class="form-input" ${!isSuperAdmin ? 'required' : ''}>
            <option value="">Seleccionar...</option>
            ${availableDeps.map(dep => `
              <option value="${dep.id}">${this.escapeHtml(dep.name)}</option>
            `).join('')}
          </select>
          <div id="createUserDependencyError" class="form-error hidden"></div>
          ${!isSuperAdmin ? '<p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">Solo puedes crear usuarios en tu dependencia</p>' : ''}
        </div>

        ${!isSuperAdmin ? `<input type="hidden" id="createUserDependencyHidden" value="${currentUser.dependency_id}">` : ''}
      </form>
    `;

    const modal = ui.showModal('Crear Usuario', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'Crear',
          class: 'btn btn-primary',
          onClick: async () => {
            await this.createUser();
          },
          closeOnClick: false
        }
      ]
    });

    // Submit con Enter
    content.querySelector('#createUserForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.createUser();
      ui.closeModal(modal.backdrop);
    });
  }

  /**
   * Crea un nuevo usuario
   */
  async createUser() {
    // Obtener elementos (prefijo 'create' para evitar conflictos con navbar)
    const fullNameEl = document.getElementById('createUserFullName');
    const emailEl = document.getElementById('createUserEmail');
    const passwordEl = document.getElementById('createUserPassword');
    const roleEl = document.getElementById('createUserRole');
    const dependencyEl = document.getElementById('createUserDependency');

    // Verificar que todos los elementos existen
    if (!fullNameEl || !emailEl || !passwordEl || !roleEl) {
      console.error('[users.js] Missing form elements:', {
        fullNameEl: !!fullNameEl,
        emailEl: !!emailEl,
        passwordEl: !!passwordEl,
        roleEl: !!roleEl,
        dependencyEl: !!dependencyEl
      });
      ui.error('Error interno: formulario no encontrado');
      return;
    }

    // Debug: verificar el select de rol
    console.log('[users.js] Role select element:', roleEl);
    console.log('[users.js] Role select HTML:', roleEl.outerHTML);
    console.log('[users.js] Role select value:', roleEl.value);
    console.log('[users.js] Role select selectedIndex:', roleEl.selectedIndex);
    console.log('[users.js] Role select options:', Array.from(roleEl.options).map(o => ({ value: o.value, text: o.text, selected: o.selected })));

    // Obtener valores
    const fullName = fullNameEl.value.trim();
    const email = emailEl.value.trim();
    const password = passwordEl.value;
    const role = roleEl.value;
    const dependencyId = dependencyEl ? dependencyEl.value : '';

    console.log('[users.js] Creating user with:', {
      fullName,
      email,
      password: '***',
      role,
      dependencyId
    });

    // Limpiar errores
    ['createUserFullName', 'createUserEmail', 'createUserPassword', 'createUserRole', 'createUserDependency'].forEach(id => {
      const errorDiv = document.getElementById(`${id}Error`);
      if (errorDiv) errorDiv.classList.add('hidden');
    });

    // Validar
    let hasErrors = false;

    const nameValidation = validators.required(fullName, 'El nombre');
    if (nameValidation) {
      console.log('[users.js] Name validation failed:', nameValidation);
      document.getElementById('createUserFullNameError').textContent = nameValidation;
      document.getElementById('createUserFullNameError').classList.remove('hidden');
      hasErrors = true;
    }

    const emailValidation = validators.required(email, 'El email') || validators.email(email);
    if (emailValidation) {
      console.log('[users.js] Email validation failed:', emailValidation);
      document.getElementById('createUserEmailError').textContent = emailValidation;
      document.getElementById('createUserEmailError').classList.remove('hidden');
      hasErrors = true;
    }

    const passwordValidation = validators.required(password, 'La contraseña') || 
                               validators.password(password);
    if (passwordValidation) {
      console.log('[users.js] Password validation failed:', passwordValidation);
      document.getElementById('createUserPasswordError').textContent = passwordValidation;
      document.getElementById('createUserPasswordError').classList.remove('hidden');
      hasErrors = true;
    }

    const roleValidation = validators.required(role, 'El rol');
    if (roleValidation) {
      console.log('[users.js] Role validation failed:', roleValidation, 'Role value:', role);
      document.getElementById('createUserRoleError').textContent = roleValidation;
      document.getElementById('createUserRoleError').classList.remove('hidden');
      hasErrors = true;
    }

    if (hasErrors) {
      console.log('[users.js] Validation errors, aborting creation');
      return;
    }

    // Crear usuario
    try {
      ui.showLoading('Creando usuario...');

      const userData = {
        full_name: fullName,
        email: email,
        password: password,
        role: role,
        dependency_id: dependencyId || null
      };

      const newUser = await fetchWrapper.post('/users', userData);

      ui.hideLoading();
      ui.success(`Usuario "${fullName}" creado correctamente`);

      // Recargar usuarios
      await this.loadUsers();

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error creating user:', error);

      const requestId = error.data?.request_id;
      let errorMessage = 'Error al crear usuario';

      if (error.status === 409) {
        errorMessage = 'Ya existe un usuario con ese email';
        document.getElementById('userEmailError').textContent = errorMessage;
        document.getElementById('userEmailError').classList.remove('hidden');
      } else if (error.status === 403) {
        errorMessage = 'No tienes permisos para crear usuarios';
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }

      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Muestra modal para editar usuario
   */
  async showEditUserModal(userId) {
    try {
      // Obtener usuario
      const user = await fetchWrapper.get(`/users/${userId}`);
      const currentUser = auth.getCurrentUser();
      const isSuperAdmin = auth.isSuperAdmin();

      const availableDeps = isSuperAdmin 
        ? this.dependencies 
        : this.dependencies.filter(d => d.id === currentUser.dependency_id);

      const content = document.createElement('div');
      content.innerHTML = `
        <form id="editUserForm">
          <div class="form-group">
            <label class="form-label">Nombre Completo</label>
            <div style="padding: 0.75rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
              ${this.escapeHtml(user.full_name)}
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Email</label>
            <div style="padding: 0.75rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
              ${this.escapeHtml(user.email)}
            </div>
          </div>

          <div class="form-group">
            <label for="editUserRole" class="form-label">Rol *</label>
            <select id="editUserRole" class="form-input" required>
              ${isSuperAdmin ? `<option value="SUPER_ADMIN" ${user.role === 'SUPER_ADMIN' ? 'selected' : ''}>Super Administrador</option>` : ''}
              <option value="ADMIN_DEP" ${user.role === 'ADMIN_DEP' ? 'selected' : ''}>Administrador de Dependencia</option>
              <option value="WORKER" ${user.role === 'WORKER' ? 'selected' : ''}>Trabajador</option>
              <option value="READER" ${user.role === 'READER' ? 'selected' : ''}>Lector</option>
            </select>
          </div>

          <div class="form-group">
            <label for="editUserDependency" class="form-label">Dependencia</label>
            <select id="editUserDependency" class="form-input">
              <option value="">Sin asignar</option>
              ${availableDeps.map(dep => `
                <option value="${dep.id}" ${user.dependency_id === dep.id ? 'selected' : ''}>
                  ${this.escapeHtml(dep.name)}
                </option>
              `).join('')}
            </select>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" id="editUserActive" ${user.is_active ? 'checked' : ''}>
              <span>Usuario activo</span>
            </label>
            <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
              Los usuarios inactivos no pueden iniciar sesión
            </p>
          </div>

          <div class="form-group">
            <label for="editUserPassword" class="form-label">Nueva Contraseña</label>
            <input 
              type="password" 
              id="editUserPassword" 
              class="form-input" 
              placeholder="Dejar vacío para mantener la actual"
            >
            <div id="editUserPasswordError" class="form-error hidden"></div>
            <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
              Solo completa si deseas cambiar la contraseña
            </p>
          </div>
        </form>
      `;

      ui.showModal('Editar Usuario', content, {
        buttons: [
          {
            text: 'Cancelar',
            class: 'btn btn-secondary'
          },
          {
            text: 'Guardar',
            class: 'btn btn-primary',
            onClick: async () => {
              await this.updateUser(userId);
            },
            closeOnClick: false
          }
        ]
      });

    } catch (error) {
      console.error('Error loading user:', error);
      ui.error('Error al cargar información del usuario');
    }
  }

  /**
   * Actualiza un usuario
   */
  async updateUser(userId) {
    const role = document.getElementById('editUserRole').value;
    const dependencyId = document.getElementById('editUserDependency').value;
    const isActive = document.getElementById('editUserActive').checked;
    const password = document.getElementById('editUserPassword').value;

    // Validar contraseña si se proporciona
    if (password) {
      const passwordValidation = validators.password(password);
      if (passwordValidation) {
        document.getElementById('editUserPasswordError').textContent = passwordValidation;
        document.getElementById('editUserPasswordError').classList.remove('hidden');
        return;
      }
    }

    try {
      ui.showLoading('Actualizando usuario...');

      const updateData = {
        role: role,
        dependency_id: dependencyId || null,
        is_active: isActive
      };

      if (password) {
        updateData.password = password;
      }

      await fetchWrapper.put(`/users/${userId}`, updateData);

      ui.hideLoading();
      ui.success('Usuario actualizado correctamente');

      // Recargar usuarios
      await this.loadUsers();

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error updating user:', error);

      const requestId = error.data?.request_id;
      let errorMessage = 'Error al actualizar usuario';

      if (error.status === 403) {
        errorMessage = 'No tienes permisos para editar este usuario';
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }

      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Muestra modal para desactivar usuario (soft delete)
   */
  async showDeactivateUserModal(userId) {
    try {
      const user = await fetchWrapper.get(`/users/${userId}`);

      const content = document.createElement('div');
      content.innerHTML = `
        <div>
          <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-warning-50); border: 1px solid var(--color-warning-200); border-radius: var(--radius-md);">
            <strong>⚠️ Desactivar Usuario</strong>
            <p style="margin-top: 0.5rem; margin-bottom: 0;">
              Esta acción desactivará al usuario. No podrá iniciar sesión, pero sus datos se mantendrán en el sistema.
            </p>
          </div>

          <div style="padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
            <div><strong>Usuario:</strong> ${this.escapeHtml(user.full_name)}</div>
            <div style="margin-top: 0.5rem;"><strong>Email:</strong> ${this.escapeHtml(user.email)}</div>
            <div style="margin-top: 0.5rem;"><strong>Rol:</strong> ${this.getRoleName(user.role)}</div>
          </div>

          <p class="text-muted" style="font-size: 0.875rem; margin-top: 1rem;">
            💡 El usuario desactivado podrá ser eliminado permanentemente después.
          </p>
        </div>
      `;

      ui.showModal('Desactivar Usuario', content, {
        buttons: [
          {
            text: 'Cancelar',
            class: 'btn btn-secondary'
          },
          {
            text: 'Desactivar',
            class: 'btn btn-warning',
            onClick: async () => {
              await this.deactivateUser(userId);
            }
          }
        ]
      });

    } catch (error) {
      console.error('Error loading user:', error);
      ui.error('Error al cargar información del usuario');
    }
  }

  /**
   * Desactiva un usuario (soft delete)
   */
  async deactivateUser(userId) {
    try {
      ui.showLoading('Desactivando usuario...');

      await fetchWrapper.delete(`/users/${userId}`);

      ui.hideLoading();
      ui.success('Usuario desactivado correctamente');

      // Recargar usuarios
      await this.loadUsers();

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error deactivating user:', error);

      const requestId = error.data?.request_id;
      let errorMessage = 'Error al desactivar usuario';

      if (error.status === 403) {
        errorMessage = 'No tienes permisos para desactivar este usuario';
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }

      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Muestra modal para eliminar usuario permanentemente (hard delete)
   */
  async showPermanentDeleteUserModal(userId) {
    try {
      const user = await fetchWrapper.get(`/users/${userId}`);

      const content = document.createElement('div');
      content.innerHTML = `
        <div>
          <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-danger-50); border: 1px solid var(--color-danger-200); border-radius: var(--radius-md);">
            <strong>🗑️ ELIMINAR PERMANENTEMENTE</strong>
            <p style="margin-top: 0.5rem; margin-bottom: 0;">
              <strong>⚠️ ESTA ACCIÓN ES IRREVERSIBLE</strong><br>
              El usuario y todos sus datos asociados serán eliminados completamente de la base de datos.
            </p>
          </div>

          <div style="padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
            <div><strong>Usuario:</strong> ${this.escapeHtml(user.full_name)}</div>
            <div style="margin-top: 0.5rem;"><strong>Email:</strong> ${this.escapeHtml(user.email)}</div>
            <div style="margin-top: 0.5rem;"><strong>Rol:</strong> ${this.getRoleName(user.role)}</div>
            <div style="margin-top: 0.5rem;">
              <span class="badge badge-gray">Inactivo</span>
            </div>
          </div>

          <div style="margin-top: 1rem; padding: 1rem; background: var(--color-gray-50); border-left: 3px solid var(--color-danger-500); border-radius: var(--radius-md);">
            <strong>⚠️ Antes de continuar:</strong>
            <ul style="margin: 0.5rem 0 0 1.25rem; padding: 0;">
              <li>Los archivos del usuario se mantendrán en el sistema</li>
              <li>No se podrá recuperar la cuenta del usuario</li>
              <li>Esta acción quedará registrada en el sistema</li>
            </ul>
          </div>

          <p style="margin-top: 1rem; font-weight: 600; color: var(--color-danger-600); text-align: center;">
            ¿Estás seguro de que deseas eliminar permanentemente este usuario?
          </p>
        </div>
      `;

      ui.showModal('Eliminar Usuario Permanentemente', content, {
        buttons: [
          {
            text: 'Cancelar',
            class: 'btn btn-secondary'
          },
          {
            text: 'ELIMINAR PERMANENTEMENTE',
            class: 'btn btn-danger',
            onClick: async () => {
              await this.deletePermanentlyUser(userId);
            }
          }
        ],
        size: 'large'
      });

    } catch (error) {
      console.error('Error loading user:', error);
      ui.error('Error al cargar información del usuario');
    }
  }

  /**
   * Elimina permanentemente un usuario (hard delete)
   */
  async deletePermanentlyUser(userId) {
    try {
      ui.showLoading('Eliminando permanentemente...');

      await fetchWrapper.delete(`/users/${userId}/permanent`);

      ui.hideLoading();
      ui.success('Usuario eliminado permanentemente');

      // Recargar usuarios
      await this.loadUsers();

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error permanently deleting user:', error);

      const requestId = error.data?.request_id;
      let errorMessage = 'Error al eliminar usuario permanentemente';

      if (error.status === 400) {
        errorMessage = 'Solo se pueden eliminar permanentemente usuarios inactivos';
      } else if (error.status === 403) {
        errorMessage = 'No tienes permisos para eliminar este usuario';
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }

      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Muestra modal para crear dependencia
   */
  showCreateDependencyModal() {
    const content = document.createElement('div');
    content.innerHTML = `
      <form id="createDependencyForm">
        <div class="form-group">
          <label for="depName" class="form-label">Nombre *</label>
          <input 
            type="text" 
            id="depName" 
            class="form-input" 
            placeholder="Ej: Departamento Legal"
            required
            autofocus
          >
          <div id="depNameError" class="form-error hidden"></div>
        </div>

        <div class="form-group">
          <label for="depCode" class="form-label">Código *</label>
          <input 
            type="text" 
            id="depCode" 
            class="form-input" 
            placeholder="Ej: DEP-LEGAL"
            required
          >
          <div id="depCodeError" class="form-error hidden"></div>
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            Código único de identificación
          </p>
        </div>

        <div class="form-group">
          <label for="depDescription" class="form-label">Descripción</label>
          <textarea 
            id="depDescription" 
            class="form-input" 
            rows="3" 
            placeholder="Descripción opcional..."
          ></textarea>
        </div>
      </form>
    `;

    const modal = ui.showModal('Crear Dependencia', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'Crear',
          class: 'btn btn-primary',
          onClick: async () => {
            await this.createDependency();
          },
          closeOnClick: false
        }
      ]
    });

    // Submit con Enter
    content.querySelector('#createDependencyForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.createDependency();
      ui.closeModal(modal.backdrop);
    });
  }

  /**
   * Crea una nueva dependencia
   */
  async createDependency() {
    const name = document.getElementById('depName').value.trim();
    const code = document.getElementById('depCode').value.trim();
    const description = document.getElementById('depDescription').value.trim();

    // Limpiar errores
    document.getElementById('depNameError').classList.add('hidden');
    document.getElementById('depCodeError').classList.add('hidden');

    // Validar
    let hasErrors = false;

    const nameValidation = validators.required(name, 'El nombre');
    if (nameValidation) {
      document.getElementById('depNameError').textContent = nameValidation;
      document.getElementById('depNameError').classList.remove('hidden');
      hasErrors = true;
    }

    const codeValidation = validators.required(code, 'El código');
    if (codeValidation) {
      document.getElementById('depCodeError').textContent = codeValidation;
      document.getElementById('depCodeError').classList.remove('hidden');
      hasErrors = true;
    }

    if (hasErrors) return;

    try {
      ui.showLoading('Creando dependencia...');

      const depData = {
        name: name,
        code: code,
        description: description || null
      };

      await fetchWrapper.post('/dependencies', depData);

      ui.hideLoading();
      ui.success(`Dependencia "${name}" creada correctamente`);

      // Recargar dependencias
      await this.loadDependencies();

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error creating dependency:', error);

      const requestId = error.data?.request_id;
      let errorMessage = 'Error al crear dependencia';

      if (error.status === 409) {
        errorMessage = 'Ya existe una dependencia con ese código';
        document.getElementById('depCodeError').textContent = errorMessage;
        document.getElementById('depCodeError').classList.remove('hidden');
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }

      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
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
   * Escapa HTML para prevenir XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Muestra modal para editar dependencia
   */
  showEditDependencyModal(dependencyId) {
    const dependency = this.dependencies.find(d => d.id === dependencyId);
    if (!dependency) {
      ui.error('Dependencia no encontrada');
      return;
    }

    const content = document.createElement('div');
    content.innerHTML = `
      <form id="editDependencyForm">
        <div class="form-group">
          <label for="editDepName" class="form-label">Nombre *</label>
          <input 
            type="text" 
            id="editDepName" 
            class="form-input" 
            value="${this.escapeHtml(dependency.name)}"
            placeholder="Ej: Dirección Jurídica"
            required
            autofocus
          >
          <div id="editDepNameError" class="form-error hidden"></div>
        </div>

        <div class="form-group">
          <label for="editDepCode" class="form-label">Código *</label>
          <input 
            type="text" 
            id="editDepCode" 
            class="form-input" 
            value="${this.escapeHtml(dependency.code)}"
            placeholder="Ej: DIR-JUR"
            required
            maxlength="20"
            disabled
            style="background-color: var(--color-gray-100); cursor: not-allowed;"
          >
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            El código no puede modificarse después de crear la dependencia
          </p>
        </div>
      </form>
    `;

    const modal = ui.showModal('Editar Dependencia', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'Guardar',
          class: 'btn btn-primary',
          onClick: async () => {
            await this.updateDependency(dependencyId);
          },
          closeOnClick: false
        }
      ]
    });

    // Submit con Enter
    content.querySelector('#editDependencyForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.updateDependency(dependencyId);
      ui.closeModal(modal.backdrop);
    });
  }

  /**
   * Actualiza una dependencia
   */
  async updateDependency(dependencyId) {
    const name = document.getElementById('editDepName').value.trim();

    // Limpiar errores
    document.getElementById('editDepNameError').classList.add('hidden');

    // Validar
    const nameValidation = validators.required(name, 'El nombre');
    if (nameValidation) {
      document.getElementById('editDepNameError').textContent = nameValidation;
      document.getElementById('editDepNameError').classList.remove('hidden');
      return;
    }

    try {
      ui.showLoading('Actualizando dependencia...');

      await fetchWrapper.put(`/dependencies/${dependencyId}`, { name });

      ui.hideLoading();
      ui.success('Dependencia actualizada correctamente');

      // Recargar dependencias
      await this.loadDependencies();

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

      // Si estamos en la página de dependencias, actualizar tabla
      if (window.location.hash === '#/dependencies') {
        window.location.reload();
      }

    } catch (error) {
      ui.hideLoading();
      console.error('Error updating dependency:', error);
      ui.error('Error al actualizar dependencia: ' + error.message);
    }
  }
}

// Exportar instancia singleton
export const usersManager = new UsersManager();

// Hacer disponible globalmente
window.usersManager = usersManager;
