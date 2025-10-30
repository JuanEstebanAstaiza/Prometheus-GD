/**
 * SGDI - Folders Module
 * Explorador de carpetas en árbol con crear, renombrar, mover y eliminar
 */

import { fetchWrapper } from './lib/fetch-wrapper.js';
import { auth } from './auth.js';
import { ui } from './ui.js';
import { validators } from './lib/validators.js';

class FoldersManager {
  constructor() {
    this.currentDependency = null;
    this.currentFolder = null;
    this.foldersTree = null;
    this.expandedNodes = new Set();
  }

  /**
   * Inicializa el módulo de carpetas
   */
  async init() {
    await this.loadDependencies();
    this.setupEventListeners();
  }

  /**
   * Carga las dependencias disponibles
   */
  async loadDependencies() {
    try {
      console.log('[folders.js] Llamando a /dependencies...');
      const response = await fetchWrapper.get('/dependencies');
      console.log('[folders.js] Respuesta cruda:', response);
      console.log('[folders.js] Tipo de respuesta:', typeof response);
      console.log('[folders.js] Es array?', Array.isArray(response));
      console.log('[folders.js] Tiene items?', response?.items);
      
      // El endpoint devuelve { items: [...], total: N }
      let dependencies;
      if (Array.isArray(response)) {
        console.log('[folders.js] Respuesta es array directo');
        dependencies = response;
      } else if (response && Array.isArray(response.items)) {
        console.log('[folders.js] Respuesta tiene items array');
        dependencies = response.items;
      } else if (response && Array.isArray(response.dependencies)) {
        console.log('[folders.js] Respuesta tiene dependencies array');
        dependencies = response.dependencies;
      } else {
        console.warn('[folders.js] Formato de respuesta inesperado, usando array vacío');
        dependencies = [];
      }
      
      console.log('[folders.js] Dependencies finales:', dependencies);
      this.dependencies = dependencies;
      
      if (dependencies.length === 0) {
        console.warn('[folders.js] No hay dependencias disponibles');
        ui.warning('No hay dependencias disponibles');
        return;
      }
      
      this.renderDependencySelector(dependencies);
      
      // Seleccionar la primera o la del usuario
      const user = auth.getCurrentUser();
      const defaultDep = user.dependency_id 
        ? dependencies.find(d => d.id === user.dependency_id)
        : dependencies[0];
      
      if (defaultDep) {
        await this.loadFolderTree(defaultDep.id);
      }
    } catch (error) {
      console.error('[folders.js] Error loading dependencies:', error);
      ui.error('Error al cargar dependencias: ' + error.message);
    }
  }

  /**
   * Renderiza selector de dependencias
   */
  renderDependencySelector(dependencies) {
    const selector = document.getElementById('dependencySelector');
    if (!selector) return;

    selector.innerHTML = dependencies.map(dep => `
      <option value="${dep.id}">${dep.name}</option>
    `).join('');

    selector.addEventListener('change', async (e) => {
      await this.loadFolderTree(e.target.value);
    });
  }

  /**
   * Carga el árbol de carpetas de una dependencia
   */
  async loadFolderTree(dependencyId) {
    this.currentDependency = dependencyId;
    const treeContainer = document.getElementById('foldersTree');
    
    if (!treeContainer) return;

    try {
      treeContainer.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Cargando carpetas...</p></div>';

      const folders = await fetchWrapper.get(`/folders/dependencies/${dependencyId}/tree`);
      this.foldersTree = folders;

      // Renderizar árbol
      if (folders && folders.length > 0) {
        treeContainer.innerHTML = this.renderTreeNode(folders);
        this.attachTreeEventListeners();
      } else {
        treeContainer.innerHTML = `
          <div class="empty-state" style="padding: 2rem;">
            <div class="empty-state-icon">📁</div>
            <h3 class="empty-state-title">Sin carpetas</h3>
            <p class="empty-state-description">Aún no hay carpetas en esta dependencia</p>
            <button class="btn btn-primary" onclick="foldersManager.showCreateFolderModal()">
              Crear primera carpeta
            </button>
          </div>
        `;
      }
    } catch (error) {
      console.error('Error loading folder tree:', error);
      const requestId = error.headers?.get?.('x-request-id');
      ui.error(`Error al cargar carpetas${requestId ? ` (Request ID: ${requestId})` : ''}`);
      
      treeContainer.innerHTML = `
        <div class="empty-state">
          <p style="color: var(--color-danger);">Error al cargar carpetas</p>
          <button class="btn btn-secondary" onclick="location.reload()">Reintentar</button>
        </div>
      `;
    }
  }

  /**
   * Renderiza un nodo del árbol (recursivo)
   */
  renderTreeNode(nodes, level = 0) {
    if (!nodes || nodes.length === 0) return '';

    return `
      <ul class="tree-list" role="tree" style="padding-left: ${level * 20}px;">
        ${nodes.map(node => this.renderFolderItem(node, level)).join('')}
      </ul>
    `;
  }

  /**
   * Renderiza un item de carpeta
   */
  renderFolderItem(folder, level) {
    const hasChildren = folder.children && folder.children.length > 0;
    const isExpanded = this.expandedNodes.has(folder.id);
    const canWrite = !auth.isReader();

    return `
      <li class="tree-item" role="treeitem" aria-expanded="${isExpanded}" data-folder-id="${folder.id}">
        <div class="tree-item-content" data-level="${level}">
          ${hasChildren ? `
            <button class="tree-toggle" aria-label="Expandir/Contraer" data-folder-id="${folder.id}">
              <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20" style="transform: rotate(${isExpanded ? 90 : 0}deg); transition: transform 0.2s;">
                <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
              </svg>
            </button>
          ` : '<span class="tree-spacer"></span>'}
          
          <button class="tree-item-label" data-folder-id="${folder.id}">
            <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20" style="color: var(--color-primary-500);">
              <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
            </svg>
            <span class="folder-name" data-folder-id="${folder.id}">${this.escapeHtml(folder.name)}</span>
            ${folder.file_count ? `<span class="file-count">(${folder.file_count})</span>` : ''}
          </button>

          ${canWrite ? `
            <div class="tree-item-actions">
              <button class="tree-action-btn" title="Crear subcarpeta" data-action="create" data-folder-id="${folder.id}">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
                </svg>
              </button>
              <button class="tree-action-btn" title="Renombrar" data-action="rename" data-folder-id="${folder.id}">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
                </svg>
              </button>
              <button class="tree-action-btn tree-action-delete" title="Eliminar" data-action="delete" data-folder-id="${folder.id}">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
              </button>
            </div>
          ` : ''}
        </div>

        ${hasChildren && isExpanded ? this.renderTreeNode(folder.children, level + 1) : ''}
      </li>
    `;
  }

  /**
   * Configura listeners de eventos
   */
  setupEventListeners() {
    // Botón crear carpeta raíz
    const createRootBtn = document.getElementById('createRootFolderBtn');
    if (createRootBtn) {
      createRootBtn.addEventListener('click', () => {
        this.showCreateFolderModal();
      });
    }

    // Botón generar carpetas mensuales
    const monthlyBtn = document.getElementById('createMonthlyFoldersBtn');
    if (monthlyBtn && auth.isSuperAdmin()) {
      monthlyBtn.style.display = 'inline-flex';
      monthlyBtn.addEventListener('click', () => {
        this.showMonthlyFoldersModal();
      });
    }
  }

  /**
   * Adjunta event listeners al árbol
   */
  attachTreeEventListeners() {
    const treeContainer = document.getElementById('foldersTree');
    if (!treeContainer) return;

    // Delegación de eventos
    treeContainer.addEventListener('click', async (e) => {
      const target = e.target.closest('[data-action], .tree-toggle, .tree-item-label');
      if (!target) return;

      const folderId = target.dataset.folderId;
      const action = target.dataset.action;

      if (action === 'create') {
        this.showCreateFolderModal(folderId);
      } else if (action === 'rename') {
        this.showRenameFolderModal(folderId);
      } else if (action === 'delete') {
        await this.showDeleteFolderModal(folderId);
      } else if (target.classList.contains('tree-toggle')) {
        this.toggleNode(folderId);
      } else if (target.classList.contains('tree-item-label')) {
        this.selectFolder(folderId);
      }
    });

    // Double click para renombrar
    treeContainer.addEventListener('dblclick', (e) => {
      const folderName = e.target.closest('.folder-name');
      if (folderName && !auth.isReader()) {
        const folderId = folderName.dataset.folderId;
        this.showRenameFolderModal(folderId);
      }
    });

    // Teclado: Enter para expandir/contraer
    treeContainer.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const treeItem = e.target.closest('.tree-item');
        if (treeItem) {
          const folderId = treeItem.dataset.folderId;
          this.toggleNode(folderId);
        }
      }
    });
  }

  /**
   * Expande/contrae un nodo
   */
  toggleNode(folderId) {
    if (this.expandedNodes.has(folderId)) {
      this.expandedNodes.delete(folderId);
    } else {
      this.expandedNodes.add(folderId);
    }

    // Re-renderizar árbol
    this.loadFolderTree(this.currentDependency);
  }

  /**
   * Selecciona una carpeta y muestra su contenido
   */
  async selectFolder(folderId) {
    this.currentFolder = folderId;
    
    // Resaltar carpeta seleccionada
    document.querySelectorAll('.tree-item-content').forEach(el => {
      el.classList.remove('selected');
    });
    
    const selected = document.querySelector(`[data-folder-id="${folderId}"].tree-item-content`);
    if (selected) {
      selected.classList.add('selected');
    }

    // Cargar archivos de la carpeta con módulo completo
    await this.loadFilesInFolder(folderId);
  }

  /**
   * Muestra modal para crear carpeta
   */
  showCreateFolderModal(parentId = null) {
    const content = document.createElement('div');
    content.innerHTML = `
      <form id="createFolderForm">
        <div class="form-group">
          <label for="folderName" class="form-label">Nombre de la carpeta</label>
          <input
            type="text"
            id="folderName"
            class="form-input"
            placeholder="Ej: Documentos 2025"
            required
            autofocus
          >
          <div id="folderNameError" class="form-error hidden"></div>
        </div>
        ${parentId ? '<p class="text-muted" style="font-size: 0.875rem;">Se creará como subcarpeta</p>' : ''}
      </form>
    `;

    const modal = ui.showModal(
      parentId ? 'Crear Subcarpeta' : 'Crear Carpeta',
      content,
      {
        buttons: [
          {
            text: 'Cancelar',
            class: 'btn btn-secondary'
          },
          {
            text: 'Crear',
            class: 'btn btn-primary',
            onClick: async () => {
              await this.createFolder(parentId);
            },
            closeOnClick: false
          }
        ]
      }
    );

    // Submit con Enter
    content.querySelector('#createFolderForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.createFolder(parentId);
      ui.closeModal(modal.backdrop);
    });
  }

  /**
   * Crea una carpeta
   */
  async createFolder(parentId = null) {
    const nameInput = document.getElementById('folderName');
    const errorDiv = document.getElementById('folderNameError');
    const name = nameInput.value.trim();

    // Validar
    errorDiv.classList.add('hidden');
    const validation = validators.required(name, 'El nombre') || validators.maxLength(name, 255, 'El nombre');
    
    if (validation) {
      errorDiv.textContent = validation;
      errorDiv.classList.remove('hidden');
      return;
    }

    try {
      ui.showLoading('Creando carpeta...');

      const newFolder = await fetchWrapper.post('/folders', {
        name: name,
        parent_id: parentId,
        dependency_id: this.currentDependency
      });

      ui.hideLoading();
      ui.success(`Carpeta "${name}" creada correctamente`);

      // Expandir nodo padre si existe
      if (parentId) {
        this.expandedNodes.add(parentId);
      }

      // Recargar árbol
      await this.loadFolderTree(this.currentDependency);

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error creating folder:', error);
      
      const requestId = error.data?.request_id;
      let errorMessage = 'Error al crear carpeta';
      
      if (error.status === 409) {
        errorMessage = 'Ya existe una carpeta con ese nombre';
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }
      
      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Muestra modal para renombrar carpeta
   */
  async showRenameFolderModal(folderId) {
    // Obtener carpeta actual
    const folder = this.findFolderById(this.foldersTree, folderId);
    if (!folder) {
      ui.error('Carpeta no encontrada');
      return;
    }

    const content = document.createElement('div');
    content.innerHTML = `
      <form id="renameFolderForm">
        <div class="form-group">
          <label for="newFolderName" class="form-label">Nuevo nombre</label>
          <input
            type="text"
            id="newFolderName"
            class="form-input"
            value="${this.escapeHtml(folder.name)}"
            required
            autofocus
          >
          <div id="newFolderNameError" class="form-error hidden"></div>
        </div>
        <p class="text-muted" style="font-size: 0.875rem;">
          ⚠️ Al renombrar, se actualizará la ruta de todas las subcarpetas y archivos.
        </p>
      </form>
    `;

    const modal = ui.showModal('Renombrar Carpeta', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'Renombrar',
          class: 'btn btn-primary',
          onClick: async () => {
            await this.renameFolder(folderId);
          },
          closeOnClick: false
        }
      ]
    });

    // Submit con Enter
    content.querySelector('#renameFolderForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.renameFolder(folderId);
      ui.closeModal(modal.backdrop);
    });

    // Seleccionar texto
    setTimeout(() => {
      const input = document.getElementById('newFolderName');
      if (input) input.select();
    }, 100);
  }

  /**
   * Renombra una carpeta
   */
  async renameFolder(folderId) {
    const nameInput = document.getElementById('newFolderName');
    const errorDiv = document.getElementById('newFolderNameError');
    const newName = nameInput.value.trim();

    // Validar
    errorDiv.classList.add('hidden');
    const validation = validators.required(newName, 'El nombre') || validators.maxLength(newName, 255, 'El nombre');
    
    if (validation) {
      errorDiv.textContent = validation;
      errorDiv.classList.remove('hidden');
      return;
    }

    try {
      ui.showLoading('Renombrando carpeta y actualizando rutas...');

      await fetchWrapper.put(`/folders/${folderId}`, {
        name: newName
      });

      ui.hideLoading();
      ui.success('Carpeta renombrada correctamente');

      // Recargar árbol
      await this.loadFolderTree(this.currentDependency);

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error renaming folder:', error);
      
      const requestId = error.data?.request_id;
      let errorMessage = 'Error al renombrar carpeta';
      
      if (error.status === 409) {
        errorMessage = 'Conflicto de concurrencia. La carpeta fue modificada por otro usuario.';
        
        // Ofrecer refrescar
        ui.confirm(
          'Conflicto Detectado',
          '¿Deseas recargar el árbol de carpetas para ver los cambios más recientes?',
          async () => {
            await this.loadFolderTree(this.currentDependency);
          }
        );
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }
      
      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Muestra modal para eliminar carpeta
   */
  async showDeleteFolderModal(folderId) {
    const folder = this.findFolderById(this.foldersTree, folderId);
    if (!folder) {
      ui.error('Carpeta no encontrada');
      return;
    }

    const hasChildren = folder.children && folder.children.length > 0;
    const fileCount = folder.file_count || 0;

    if (hasChildren || fileCount > 0) {
      // Carpeta no vacía - mostrar advertencia
      const content = document.createElement('div');
      content.innerHTML = `
        <div style="padding: 1rem 0;">
          <p style="margin-bottom: 1rem;">
            <strong>⚠️ Advertencia:</strong> Esta carpeta no está vacía.
          </p>
          <ul style="margin-left: 1.5rem; margin-bottom: 1rem;">
            ${hasChildren ? `<li>Contiene <strong>${folder.children.length}</strong> subcarpeta(s)</li>` : ''}
            ${fileCount > 0 ? `<li>Contiene <strong>${fileCount}</strong> archivo(s)</li>` : ''}
          </ul>
          <p class="text-muted" style="font-size: 0.875rem;">
            Al eliminar con "Forzar", se eliminarán todos los archivos y subcarpetas de forma permanente.
          </p>
          <div class="form-group" style="margin-top: 1rem;">
            <label class="checkbox-label">
              <input type="checkbox" id="forceDeleteCheck">
              <span>Entiendo que esta acción es irreversible</span>
            </label>
          </div>
        </div>
      `;

      ui.showModal('Eliminar Carpeta', content, {
        buttons: [
          {
            text: 'Cancelar',
            class: 'btn btn-secondary'
          },
          {
            text: 'Forzar Eliminación',
            class: 'btn btn-danger',
            onClick: async () => {
              const checkbox = document.getElementById('forceDeleteCheck');
              if (!checkbox.checked) {
                ui.warning('Debes confirmar que entiendes que la acción es irreversible');
                return;
              }
              await this.deleteFolder(folderId, true);
            }
          }
        ]
      });
    } else {
      // Carpeta vacía - confirmación simple
      ui.confirm(
        'Eliminar Carpeta',
        `¿Estás seguro de que deseas eliminar la carpeta "${this.escapeHtml(folder.name)}"?`,
        async () => {
          await this.deleteFolder(folderId, false);
        }
      );
    }
  }

  /**
   * Elimina una carpeta
   */
  async deleteFolder(folderId, force = false) {
    try {
      ui.showLoading('Eliminando carpeta...');

      const url = force ? `/folders/${folderId}?force=true` : `/folders/${folderId}`;
      await fetchWrapper.delete(url);

      ui.hideLoading();
      ui.success('Carpeta eliminada correctamente');

      // Recargar árbol
      await this.loadFolderTree(this.currentDependency);

      // Cerrar modal si está abierto
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error deleting folder:', error);
      
      const requestId = error.data?.request_id;
      let errorMessage = 'Error al eliminar carpeta';
      
      if (error.status === 409) {
        errorMessage = 'La carpeta no está vacía. Usa la opción "Forzar" para eliminar todo el contenido.';
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }
      
      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Muestra modal para crear carpetas mensuales
   */
  showMonthlyFoldersModal() {
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

    const content = document.createElement('div');
    content.innerHTML = `
      <form id="monthlyFoldersForm">
        <div class="form-group">
          <label for="monthInput" class="form-label">Mes (YYYY-MM)</label>
          <input
            type="month"
            id="monthInput"
            class="form-input"
            value="${currentMonth}"
            required
          >
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            Se creará una carpeta con este nombre en cada dependencia que no la tenga.
          </p>
        </div>
      </form>
    `;

    const modal = ui.showModal('Crear Carpetas Mensuales', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'Crear',
          class: 'btn btn-primary',
          onClick: async () => {
            await this.createMonthlyFolders();
          },
          closeOnClick: false
        }
      ]
    });

    // Submit con Enter
    content.querySelector('#monthlyFoldersForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.createMonthlyFolders();
      ui.closeModal(modal.backdrop);
    });
  }

  /**
   * Ejecuta la creación de carpetas mensuales
   */
  async createMonthlyFolders() {
    const monthInput = document.getElementById('monthInput');
    const month = monthInput.value;

    if (!month) {
      ui.error('Selecciona un mes');
      return;
    }

    try {
      ui.showLoading('Creando carpetas mensuales...');

      const result = await fetchWrapper.post(`/admin/force-create-month-folders?month=${month}`);

      ui.hideLoading();

      if (result.folders_created && result.folders_created.length > 0) {
        const foldersList = result.folders_created.map(f => `<li>${f.dependency_name}: ${f.name}</li>`).join('');
        
        ui.showModal('Carpetas Creadas', `
          <div>
            <p style="margin-bottom: 1rem;">Se crearon <strong>${result.folders_created.length}</strong> carpeta(s):</p>
            <ul style="margin-left: 1.5rem; max-height: 300px; overflow-y: auto;">
              ${foldersList}
            </ul>
          </div>
        `, {
          buttons: [
            {
              text: 'Cerrar',
              class: 'btn btn-primary'
            }
          ]
        });

        // Recargar árbol si estamos en una de las dependencias afectadas
        await this.loadFolderTree(this.currentDependency);
      } else {
        ui.info('No se crearon carpetas. Es posible que ya existan para este mes.');
      }

      // Cerrar modal de input
      const inputModal = document.querySelector('.modal-backdrop');
      if (inputModal) ui.closeModal(inputModal);

    } catch (error) {
      ui.hideLoading();
      console.error('Error creating monthly folders:', error);
      
      const requestId = error.data?.request_id;
      ui.error(`Error al crear carpetas mensuales${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Busca una carpeta por ID en el árbol (recursivo)
   */
  findFolderById(nodes, folderId) {
    if (!nodes) return null;

    for (const node of nodes) {
      if (node.id === folderId) return node;
      
      if (node.children) {
        const found = this.findFolderById(node.children, folderId);
        if (found) return found;
      }
    }

    return null;
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
   * Carga y muestra archivos en la carpeta seleccionada
   */
  async loadFilesInFolder(folderId) {
    const filesPanel = document.getElementById('folderFiles');
    if (!filesPanel) return;

    try {
      filesPanel.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Cargando archivos...</p></div>';

      // Obtener archivos de la carpeta
      const response = await fetchWrapper.get(`/files?folder_id=${folderId}&limit=100`);
      const files = response.items || response || [];

      // Importar módulo de archivos dinámicamente
      const { filesManager } = await import('./files.js');

      // Renderizar panel de archivos
      filesPanel.innerHTML = `
        <div class="files-panel">
          <div class="files-header">
            <h3>Archivos en esta carpeta</h3>
            <button class="btn btn-primary btn-sm" id="uploadFileBtn">
              <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                <path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/>
              </svg>
              Subir archivo
            </button>
          </div>
          <div class="files-list" id="filesList"></div>
        </div>
      `;

      // Renderizar lista de archivos
      const filesList = document.getElementById('filesList');
      if (files.length === 0) {
        filesList.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">📄</div>
            <h3 class="empty-state-title">Sin archivos</h3>
            <p class="empty-state-description">Aún no hay archivos en esta carpeta</p>
          </div>
        `;
      } else {
        filesList.innerHTML = `
          <table class="table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Tipo</th>
                <th>Tamaño</th>
                <th>Subido por</th>
                <th>Fecha</th>
                <th style="width: 200px;">Acciones</th>
              </tr>
            </thead>
            <tbody>
              ${files.map(file => `
                <tr>
                  <td>
                    <strong>${this.escapeHtml(file.original_name || file.name)}</strong>
                    ${file.is_annex ? '<span class="badge badge-info">Anexo</span>' : ''}
                  </td>
                  <td>${this.escapeHtml(file.mime_type || 'N/A')}</td>
                  <td>${this.formatBytes(file.size_bytes || 0)}</td>
                  <td>${this.escapeHtml(file.uploaded_by_name || 'N/A')}</td>
                  <td>${new Date(file.created_at).toLocaleDateString()}</td>
                  <td>
                    <button class="btn btn-sm btn-secondary" onclick="foldersManager.downloadFile('${file.id}', '${this.escapeHtml(file.original_name || file.name)}')">
                      Descargar
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="foldersManager.deleteFile('${file.id}')">
                      Eliminar
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }

      // Configurar botón de upload
      const uploadBtn = document.getElementById('uploadFileBtn');
      if (uploadBtn) {
        uploadBtn.addEventListener('click', () => {
          filesManager.showUploadModal(folderId);
        });
      }

    } catch (error) {
      console.error('Error loading files:', error);
      filesPanel.innerHTML = `
        <div class="empty-state">
          <p class="text-danger">Error al cargar archivos: ${error.message}</p>
          <button class="btn btn-secondary" onclick="foldersManager.selectFolder('${folderId}')">
            Reintentar
          </button>
        </div>
      `;
    }
  }

  /**
   * Formatea bytes a tamaño legible
   */
  formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }

  /**
   * Descarga un archivo
   */
  async downloadFile(fileId, fileName) {
    try {
      ui.showLoading('Descargando archivo...');
      
      const response = await fetch(`${fetchWrapper.baseURL}/files/${fileId}/download`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Error al descargar archivo');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      ui.hideLoading();
      ui.success('Archivo descargado exitosamente');
    } catch (error) {
      console.error('Error downloading file:', error);
      ui.hideLoading();
      ui.error('Error al descargar archivo: ' + error.message);
    }
  }

  /**
   * Elimina un archivo
   */
  async deleteFile(fileId) {
    const confirmed = await ui.showConfirm(
      '¿Eliminar archivo?',
      'Esta acción no se puede deshacer.',
      'Eliminar',
      'Cancelar'
    );

    if (!confirmed) return;

    try {
      ui.showLoading('Eliminando archivo...');
      await fetchWrapper.delete(`/files/${fileId}?hard=false`);
      ui.hideLoading();
      ui.success('Archivo eliminado exitosamente');

      // Recargar archivos de la carpeta actual
      if (this.currentFolder) {
        await this.loadFilesInFolder(this.currentFolder);
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      ui.hideLoading();
      ui.error('Error al eliminar archivo: ' + error.message);
    }
  }
}

// Exportar instancia singleton
export const foldersManager = new FoldersManager();

// Hacer disponible globalmente para onclick handlers
window.foldersManager = foldersManager;
