/**
 * Files Manager - Módulo independiente para gestión de archivos
 * 
 * Funcionalidades:
 * - Búsqueda con autocompletado
 * - Filtros avanzados
 * - Subida de archivos con anexos
 * - Descarga y eliminación
 * - Gestión de versiones
 */

import { fetchWrapper } from './lib/fetch-wrapper.js';
import { auth } from './auth.js';
import { ui } from './ui.js';

class FilesManager {
  constructor() {
    this.files = [];
    this.dependencies = [];
    this.folders = [];
    this.users = [];
    this.currentFilters = {
      search: '',
      dependency_id: '',
      folder_id: '',
      mime_type: '',
      uploaded_by: '',
      is_deleted: false
    };
    this.currentPage = 0;
    this.pageSize = 20;
    this.total = 0;
    this.searchTimeout = null;
  }

  /**
   * Inicializa el módulo de archivos
   */
  async init() {
    console.log('[files.js] Inicializando módulo de archivos...');
    
    try {
      // Cargar datos iniciales
      await Promise.all([
        this.loadDependencies(),
        this.loadUsers(),
        this.loadFiles()
      ]);

      // Configurar event listeners
      this.setupEventListeners();

      console.log('[files.js] Módulo de archivos inicializado correctamente');
    } catch (error) {
      console.error('[files.js] Error al inicializar:', error);
      ui.error('Error al cargar el módulo de archivos');
    }
  }

  /**
   * Configura los event listeners
   */
  setupEventListeners() {
    // Buscador con autocomplete
    const searchInput = document.getElementById('fileSearch');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.handleSearch(e.target.value);
      });

      // Cerrar autocomplete al hacer clic fuera
      document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target)) {
          this.hideAutocomplete();
        }
      });
    }

    // Toggle filtros avanzados
    const toggleFiltersBtn = document.getElementById('toggleFiltersBtn');
    if (toggleFiltersBtn) {
      toggleFiltersBtn.addEventListener('click', () => {
        const advancedFilters = document.getElementById('advancedFilters');
        if (advancedFilters) {
          advancedFilters.classList.toggle('hidden');
        }
      });
    }

    // Aplicar filtros
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    if (applyFiltersBtn) {
      applyFiltersBtn.addEventListener('click', () => {
        this.applyFilters();
      });
    }

    // Limpiar filtros
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    if (clearFiltersBtn) {
      clearFiltersBtn.addEventListener('click', () => {
        this.clearFilters();
      });
    }

    // Botón de subir archivo
    const uploadFileBtn = document.getElementById('uploadFileBtn');
    if (uploadFileBtn) {
      uploadFileBtn.addEventListener('click', () => {
        this.showUploadModal();
      });
    }
  }

  /**
   * Maneja la búsqueda con debounce
   */
  handleSearch(searchTerm) {
    // Limpiar timeout anterior
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }

    // Si está vacío, ocultar autocomplete y recargar archivos
    if (!searchTerm || searchTerm.trim() === '') {
      this.hideAutocomplete();
      this.currentFilters.search = '';
      this.loadFiles();
      return;
    }

    // Debounce: esperar 300ms antes de buscar
    this.searchTimeout = setTimeout(async () => {
      this.currentFilters.search = searchTerm.trim();
      
      try {
        // Buscar archivos
        await this.loadFiles();
        
        // Mostrar resultados en autocomplete
        this.showAutocomplete(this.files);
      } catch (error) {
        console.error('[files.js] Error en búsqueda:', error);
      }
    }, 300);
  }

  /**
   * Muestra el autocomplete con los resultados
   */
  showAutocomplete(files) {
    const autocompleteResults = document.getElementById('autocompleteResults');
    if (!autocompleteResults) return;

    if (files.length === 0) {
      autocompleteResults.innerHTML = `
        <div class="autocomplete-item">
          <div class="autocomplete-item-title">No se encontraron archivos</div>
        </div>
      `;
      autocompleteResults.classList.add('show');
      return;
    }

    // Mostrar solo los primeros 5 resultados en el autocomplete
    const limitedFiles = files.slice(0, 5);
    
    autocompleteResults.innerHTML = limitedFiles.map(file => `
      <div class="autocomplete-item" data-file-id="${file.id}">
        <div class="autocomplete-item-title">${this.escapeHtml(file.original_name || file.name)}</div>
        <div class="autocomplete-item-meta">
          ${this.formatBytes(file.size_bytes || 0)} • 
          ${new Date(file.created_at).toLocaleDateString()} • 
          ${this.escapeHtml(file.folder_path || 'Sin carpeta')}
        </div>
      </div>
    `).join('');

    // Agregar event listeners a los items
    autocompleteResults.querySelectorAll('.autocomplete-item').forEach(item => {
      item.addEventListener('click', () => {
        const fileId = item.dataset.fileId;
        this.showFileDetails(fileId);
        this.hideAutocomplete();
      });
    });

    autocompleteResults.classList.add('show');
  }

  /**
   * Oculta el autocomplete
   */
  hideAutocomplete() {
    const autocompleteResults = document.getElementById('autocompleteResults');
    if (autocompleteResults) {
      autocompleteResults.classList.remove('show');
    }
  }

  /**
   * Carga las dependencias
   */
  async loadDependencies() {
    try {
      const response = await fetchWrapper.get('/dependencies');
      this.dependencies = response.items || response || [];

      // Llenar select de filtro
      const filterDependency = document.getElementById('filterDependency');
      if (filterDependency) {
        filterDependency.innerHTML = '<option value="">Todas</option>' +
          this.dependencies.map(dep => `
            <option value="${dep.id}">${this.escapeHtml(dep.name)}</option>
          `).join('');
      }
    } catch (error) {
      console.error('[files.js] Error loading dependencies:', error);
      this.dependencies = [];
    }
  }

  /**
   * Carga los usuarios
   */
  async loadUsers() {
    try {
      const response = await fetchWrapper.get('/users?limit=1000');
      if (Array.isArray(response)) {
        this.users = response;
      } else if (response && Array.isArray(response.items)) {
        this.users = response.items;
      } else if (response && Array.isArray(response.users)) {
        this.users = response.users;
      } else {
        this.users = [];
      }

      // Llenar select de filtro
      const filterUploadedBy = document.getElementById('filterUploadedBy');
      if (filterUploadedBy) {
        filterUploadedBy.innerHTML = '<option value="">Todos</option>' +
          this.users.map(user => `
            <option value="${user.id}">${this.escapeHtml(user.full_name)}</option>
          `).join('');
      }
    } catch (error) {
      console.error('[files.js] Error loading users:', error);
      this.users = [];
    }
  }

  /**
   * Carga los archivos con filtros
   */
  async loadFiles() {
    try {
      console.log('[files.js] Cargando archivos con filtros:', this.currentFilters);

      // Construir parámetros de búsqueda
      const params = new URLSearchParams({
        skip: this.currentPage * this.pageSize,
        limit: this.pageSize
      });

      if (this.currentFilters.search) {
        // Nota: El backend no tiene parámetro 'q', pero podemos buscar por nombre usando los filtros existentes
        // Por ahora, cargaremos todos y filtraremos en cliente
        params.append('limit', '1000');
      }
      if (this.currentFilters.dependency_id) {
        params.append('dependency_id', this.currentFilters.dependency_id);
      }
      if (this.currentFilters.folder_id) {
        params.append('folder_id', this.currentFilters.folder_id);
      }
      if (this.currentFilters.mime_type) {
        params.append('mime_type', this.currentFilters.mime_type);
      }
      if (this.currentFilters.uploaded_by) {
        params.append('uploaded_by', this.currentFilters.uploaded_by);
      }
      if (this.currentFilters.is_deleted) {
        params.append('is_deleted', 'true');
      }

      const response = await fetchWrapper.get(`/files?${params.toString()}`);
      
      let allFiles = response.items || response || [];
      
      // Filtrar por término de búsqueda en cliente (hasta que el backend lo soporte)
      if (this.currentFilters.search) {
        const searchLower = this.currentFilters.search.toLowerCase();
        allFiles = allFiles.filter(file => {
          const name = (file.original_name || file.name || '').toLowerCase();
          const mimeType = (file.mime_type || '').toLowerCase();
          return name.includes(searchLower) || mimeType.includes(searchLower);
        });
      }

      this.files = allFiles;
      this.total = allFiles.length;

      this.renderFilesTable();
      this.updateFilesCount();

    } catch (error) {
      console.error('[files.js] Error loading files:', error);
      ui.error('Error al cargar archivos');
      this.files = [];
      this.total = 0;
      this.renderFilesTable();
    }
  }

  /**
   * Renderiza la tabla de archivos
   */
  renderFilesTable() {
    const container = document.getElementById('filesTableContainer');
    if (!container) return;

    if (this.files.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📄</div>
          <h3 class="empty-state-title">No se encontraron archivos</h3>
          <p class="empty-state-description">
            ${this.currentFilters.search ? 
              'Intenta con otros términos de búsqueda' : 
              'Sube tu primer archivo para comenzar'}
          </p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <table class="table">
        <thead>
          <tr>
            <th style="width: 40%;">Nombre</th>
            <th style="width: 15%;">Tipo</th>
            <th style="width: 10%;">Tamaño</th>
            <th style="width: 15%;">Subido por</th>
            <th style="width: 10%;">Fecha</th>
            <th style="width: 10%;">Acciones</th>
          </tr>
        </thead>
        <tbody>
          ${this.files.map(file => this.renderFileRow(file)).join('')}
        </tbody>
      </table>
    `;
  }

  /**
   * Renderiza una fila de archivo
   */
  renderFileRow(file) {
    const isDeleted = file.is_deleted || false;
    const fileIcon = this.getFileIcon(file.mime_type);
    
    return `
      <tr class="${isDeleted ? 'text-muted' : ''}">
        <td>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            ${fileIcon}
            <div>
              <div class="font-weight-600">${this.escapeHtml(file.original_name || file.name)}</div>
              ${file.is_annex ? '<span class="badge badge-info">Anexo</span>' : ''}
              ${isDeleted ? '<span class="badge badge-danger">Eliminado</span>' : ''}
            </div>
          </div>
        </td>
        <td>${this.escapeHtml(this.getMimeTypeLabel(file.mime_type))}</td>
        <td>${this.formatBytes(file.size_bytes || 0)}</td>
        <td>${this.escapeHtml(file.uploaded_by_name || 'N/A')}</td>
        <td>${new Date(file.created_at).toLocaleDateString()}</td>
        <td>
          <div style="display: flex; gap: 0.25rem;">
            <button 
              class="btn btn-sm btn-secondary" 
              onclick="filesManager.downloadFile('${file.id}', '${this.escapeHtml(file.original_name || file.name)}')"
              title="Descargar"
            >
              ⬇
            </button>
            ${!isDeleted ? `
              <button 
                class="btn btn-sm btn-danger" 
                onclick="filesManager.deleteFile('${file.id}')"
                title="Eliminar"
              >
                🗑
              </button>
            ` : ''}
            <button 
              class="btn btn-sm btn-secondary" 
              onclick="filesManager.showFileDetails('${file.id}')"
              title="Detalles"
            >
              ℹ
            </button>
          </div>
        </td>
      </tr>
    `;
  }

  /**
   * Obtiene el icono según el tipo MIME
   */
  getFileIcon(mimeType) {
    if (!mimeType) return '📄';
    
    if (mimeType.startsWith('image/')) return '🖼️';
    if (mimeType.includes('pdf')) return '📕';
    if (mimeType.includes('word') || mimeType.includes('document')) return '📘';
    if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return '📗';
    if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return '📙';
    if (mimeType.includes('zip') || mimeType.includes('rar') || mimeType.includes('7z')) return '📦';
    if (mimeType.startsWith('video/')) return '🎬';
    if (mimeType.startsWith('audio/')) return '🎵';
    
    return '📄';
  }

  /**
   * Obtiene la etiqueta legible del tipo MIME
   */
  getMimeTypeLabel(mimeType) {
    if (!mimeType) return 'Desconocido';
    
    const labels = {
      'application/pdf': 'PDF',
      'application/msword': 'Word',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
      'application/vnd.ms-excel': 'Excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
      'image/jpeg': 'JPEG',
      'image/png': 'PNG',
      'image/gif': 'GIF',
      'text/plain': 'Texto'
    };
    
    return labels[mimeType] || mimeType.split('/')[1]?.toUpperCase() || 'Archivo';
  }

  /**
   * Actualiza el contador de archivos
   */
  updateFilesCount() {
    const filesCount = document.getElementById('filesCount');
    if (filesCount) {
      filesCount.textContent = `${this.total} archivo${this.total !== 1 ? 's' : ''}`;
    }
  }

  /**
   * Aplica los filtros seleccionados
   */
  applyFilters() {
    const filterDependency = document.getElementById('filterDependency');
    const filterFolder = document.getElementById('filterFolder');
    const filterMimeType = document.getElementById('filterMimeType');
    const filterUploadedBy = document.getElementById('filterUploadedBy');
    const filterIncludeDeleted = document.getElementById('filterIncludeDeleted');

    this.currentFilters.dependency_id = filterDependency?.value || '';
    this.currentFilters.folder_id = filterFolder?.value || '';
    this.currentFilters.mime_type = filterMimeType?.value || '';
    this.currentFilters.uploaded_by = filterUploadedBy?.value || '';
    this.currentFilters.is_deleted = filterIncludeDeleted?.checked || false;

    this.currentPage = 0;
    this.loadFiles();

    ui.success('Filtros aplicados');
  }

  /**
   * Limpia todos los filtros
   */
  clearFilters() {
    // Limpiar filtros
    this.currentFilters = {
      search: '',
      dependency_id: '',
      folder_id: '',
      mime_type: '',
      uploaded_by: '',
      is_deleted: false
    };

    // Limpiar inputs
    const searchInput = document.getElementById('fileSearch');
    if (searchInput) searchInput.value = '';

    const filterDependency = document.getElementById('filterDependency');
    if (filterDependency) filterDependency.value = '';

    const filterFolder = document.getElementById('filterFolder');
    if (filterFolder) filterFolder.value = '';

    const filterMimeType = document.getElementById('filterMimeType');
    if (filterMimeType) filterMimeType.value = '';

    const filterUploadedBy = document.getElementById('filterUploadedBy');
    if (filterUploadedBy) filterUploadedBy.value = '';

    const filterIncludeDeleted = document.getElementById('filterIncludeDeleted');
    if (filterIncludeDeleted) filterIncludeDeleted.checked = false;

    this.currentPage = 0;
    this.loadFiles();

    ui.success('Filtros limpiados');
  }

  /**
   * Muestra el modal de subida de archivo
   */
  async showUploadModal(folderId = null) {
    try {
      console.log('[files.js] showUploadModal iniciado');
      
      // Mostrar loading mientras cargamos las carpetas
      ui.showLoading('Cargando carpetas disponibles...');
      
      // Cargar carpetas para el selector ANTES de crear el modal
      await this.loadFoldersForUpload();
      
      ui.hideLoading();
      
      console.log('[files.js] Carpetas cargadas, creando modal con', this.folders.length, 'carpetas');

      const content = document.createElement('div');
      
      // Generar las opciones del selector AHORA que ya tenemos las carpetas
      let folderOptions = '<option value="">Seleccionar carpeta...</option>';
      if (this.folders && this.folders.length > 0) {
        folderOptions += this.folders.map(folder => `
          <option value="${folder.id}">${this.escapeHtml(folder.dependency_name)} → ${this.escapeHtml(folder.path)}</option>
        `).join('');
      } else {
        folderOptions = '<option value="">No hay carpetas disponibles</option>';
      }
      
      content.innerHTML = `
        <form id="uploadFileForm" enctype="multipart/form-data">
          <!-- Archivo principal -->
          <div class="form-group">
            <label class="form-label">Archivo Principal *</label>
            <input 
              type="file" 
              id="mainFile" 
              class="form-input" 
              required
              accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif"
            >
            <small class="form-help">Tamaño máximo: 200MB</small>
          </div>

          <!-- Selector de carpeta -->
          <div class="form-group">
            <label class="form-label">Carpeta Destino *</label>
            <select id="uploadFolderId" class="form-input" required>
              ${folderOptions}
            </select>
          </div>

          <!-- Checkbox para anexos -->
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" id="enableAnnexes">
              <span>Adjuntar anexos</span>
            </label>
            <small class="form-help">Los anexos se guardarán en una subcarpeta automática</small>
          </div>

          <!-- Anexos (oculto por defecto) -->
          <div id="annexesSection" class="hidden" style="margin-top: 1rem; padding: 1rem; background: #f9fafb; border-radius: 8px;">
            <div class="form-group">
              <label class="form-label">Archivos Anexos</label>
              <input 
                type="file" 
                id="annexFiles" 
                class="form-input" 
                multiple
                accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif"
              >
              <small class="form-help">Puedes seleccionar múltiples archivos</small>
            </div>

            <div class="form-group">
              <label class="form-label">Nombre de carpeta de anexos</label>
              <input 
                type="text" 
                id="annexFolderName" 
                class="form-input" 
                placeholder="Anexos-[NombreArchivo]-[Fecha]"
                readonly
              >
              <small class="form-help">Se genera automáticamente basado en el archivo principal</small>
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" id="createAnnexFolder" checked>
                <span>Crear carpeta de anexos automáticamente</span>
              </label>
            </div>
          </div>

          <!-- Metadatos -->
          <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #e5e7eb;">
            <h4 style="margin-bottom: 1rem; font-weight: 600;">Metadatos (Opcional)</h4>

            <div class="form-group">
              <label class="form-label">Número de Documento</label>
              <input 
                type="text" 
                id="docNumber" 
                class="form-input" 
                placeholder="Ej: DOC-2025-001"
              >
            </div>

            <div class="form-group">
              <label class="form-label">Etiquetas</label>
              <input 
                type="text" 
                id="tags" 
                class="form-input" 
                placeholder="Separadas por comas: contrato, proveedor, 2025"
              >
              <small class="form-help">Ayudan en la búsqueda posterior</small>
            </div>

            <div class="form-group">
              <label class="form-label">Observaciones</label>
              <textarea 
                id="observations" 
                class="form-input" 
                rows="3"
                placeholder="Notas adicionales sobre el documento..."
              ></textarea>
            </div>
          </div>

          <!-- Vista previa de archivos -->
          <div id="filePreview" class="hidden" style="margin-top: 1rem; padding: 1rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;">
            <h4 style="margin-bottom: 0.5rem; font-weight: 600; color: #1e40af;">Vista Previa</h4>
            <div id="filePreviewContent"></div>
          </div>

          <!-- Barra de progreso -->
          <div id="uploadProgress" class="hidden" style="margin-top: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
              <span id="uploadStatusText">Preparando...</span>
              <span id="uploadPercentage">0%</span>
            </div>
            <div style="width: 100%; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">
              <div id="uploadProgressBar" style="width: 0%; height: 100%; background: #3b82f6; transition: width 0.3s;"></div>
            </div>
          </div>
        </form>
      `;

      ui.showModal('Subir Archivo', content, {
        buttons: [
          {
            text: 'Subir',
            class: 'btn btn-primary',
            onClick: () => this.handleUpload()
          },
          {
            text: 'Cancelar',
            class: 'btn btn-secondary'
          }
        ],
        size: 'large'
      });

      // Configurar event listeners del formulario
      this.setupUploadFormListeners(folderId);

    } catch (error) {
      console.error('[files.js] Error showing upload modal:', error);
      ui.hideLoading();
      ui.error('Error al cargar las carpetas: ' + (error.message || 'Error desconocido'));
    }
  }

  /**
   * Carga las carpetas disponibles para subir archivos
   */
  async loadFoldersForUpload() {
    const uploadFolderId = document.getElementById('uploadFolderId');
    
    try {
      console.log('[files.js] Cargando carpetas para subida...');
      const user = auth.getCurrentUser();
      
      // Cargar dependencias primero
      if (!this.dependencies || this.dependencies.length === 0) {
        await this.loadDependencies();
      }

      console.log(`[files.js] ${this.dependencies.length} dependencias encontradas`);

      // Por cada dependencia, cargar sus carpetas
      this.folders = [];
      
      for (const dep of this.dependencies) {
        try {
          console.log(`[files.js] Cargando carpetas de ${dep.name} (${dep.id})...`);
          const tree = await fetchWrapper.get(`/folders/dependencies/${dep.id}/tree`);
          
          console.log(`[files.js] Árbol recibido para ${dep.name}:`, tree);
          
          // Aplanar el árbol de carpetas
          const flattenFolder = (folder, prefix = '') => {
            const path = prefix ? `${prefix} / ${folder.name}` : folder.name;
            this.folders.push({
              id: folder.id,
              name: folder.name,
              path: path,
              dependency_id: dep.id,
              dependency_name: dep.name
            });
            
            if (folder.children && folder.children.length > 0) {
              folder.children.forEach(child => flattenFolder(child, path));
            }
          };

          if (Array.isArray(tree) && tree.length > 0) {
            tree.forEach(root => flattenFolder(root));
            console.log(`[files.js] ${tree.length} carpetas raíz aplanadas de ${dep.name}`);
          } else if (tree && typeof tree === 'object') {
            // Si el backend devuelve un objeto único en lugar de array
            flattenFolder(tree);
            console.log(`[files.js] 1 carpeta raíz aplanada de ${dep.name}`);
          } else {
            console.warn(`[files.js] No hay carpetas en ${dep.name}`);
          }
        } catch (error) {
          console.error(`[files.js] Error cargando carpetas de ${dep.name}:`, error);
        }
      }

      console.log(`[files.js] Total de carpetas cargadas: ${this.folders.length}`);

      // No necesitamos llenar el selector aquí porque se hace en showUploadModal
      // después de que este método termine

    } catch (error) {
      console.error('[files.js] Error loading folders for upload:', error);
      this.folders = [];
      throw error; // Propagar el error para que showUploadModal lo maneje
    }
  }

  /**
   * Configura los event listeners del formulario de subida
   */
  setupUploadFormListeners(preselectedFolderId = null) {
    // Preseleccionar carpeta si se proporcionó
    if (preselectedFolderId) {
      const uploadFolderId = document.getElementById('uploadFolderId');
      if (uploadFolderId) {
        uploadFolderId.value = preselectedFolderId;
      }
    }

    // Toggle anexos
    const enableAnnexes = document.getElementById('enableAnnexes');
    const annexesSection = document.getElementById('annexesSection');
    
    if (enableAnnexes && annexesSection) {
      enableAnnexes.addEventListener('change', (e) => {
        if (e.target.checked) {
          annexesSection.classList.remove('hidden');
          this.updateAnnexFolderName();
        } else {
          annexesSection.classList.add('hidden');
        }
      });
    }

    // Actualizar nombre de carpeta de anexos cuando cambia el archivo principal
    const mainFile = document.getElementById('mainFile');
    if (mainFile) {
      mainFile.addEventListener('change', () => {
        this.updateAnnexFolderName();
        this.updateFilePreview();
      });
    }

    // Actualizar preview cuando cambian los anexos
    const annexFiles = document.getElementById('annexFiles');
    if (annexFiles) {
      annexFiles.addEventListener('change', () => {
        this.updateFilePreview();
      });
    }
  }

  /**
   * Actualiza el nombre de la carpeta de anexos
   */
  updateAnnexFolderName() {
    const mainFile = document.getElementById('mainFile');
    const annexFolderName = document.getElementById('annexFolderName');
    
    if (!mainFile || !annexFolderName) return;

    const file = mainFile.files[0];
    if (!file) {
      annexFolderName.value = '';
      return;
    }

    // Sanitizar nombre del archivo
    const fileName = file.name.replace(/\.[^/.]+$/, ''); // Quitar extensión
    const sanitized = fileName
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '') // Quitar acentos
      .replace(/[^a-zA-Z0-9_-]/g, '_')  // Solo alfanuméricos, guiones y guiones bajos
      .replace(/_+/g, '_')              // Colapsar múltiples guiones bajos
      .substring(0, 60);                // Limitar longitud

    // Formato: Anexos-[NombreArchivo]-[YYYYMMDD]
    const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
    annexFolderName.value = `Anexos-${sanitized}-${date}`;
  }

  /**
   * Actualiza la vista previa de archivos
   */
  updateFilePreview() {
    const mainFile = document.getElementById('mainFile');
    const annexFiles = document.getElementById('annexFiles');
    const filePreview = document.getElementById('filePreview');
    const filePreviewContent = document.getElementById('filePreviewContent');
    
    if (!mainFile || !filePreview || !filePreviewContent) return;

    const mainFileObj = mainFile.files[0];
    const annexFilesArray = annexFiles ? Array.from(annexFiles.files) : [];

    if (!mainFileObj && annexFilesArray.length === 0) {
      filePreview.classList.add('hidden');
      return;
    }

    let html = '';

    // Archivo principal
    if (mainFileObj) {
      html += `
        <div style="margin-bottom: 0.5rem;">
          <strong>📄 Archivo Principal:</strong>
          <div style="margin-left: 1rem; margin-top: 0.25rem;">
            ${this.escapeHtml(mainFileObj.name)} (${this.formatBytes(mainFileObj.size)})
          </div>
        </div>
      `;
    }

    // Anexos
    if (annexFilesArray.length > 0) {
      html += `
        <div style="margin-top: 0.5rem;">
          <strong>📎 Anexos (${annexFilesArray.length}):</strong>
          <ul style="margin-left: 1rem; margin-top: 0.25rem; list-style: none; padding: 0;">
            ${annexFilesArray.map(file => `
              <li style="margin-bottom: 0.25rem;">
                → ${this.escapeHtml(file.name)} (${this.formatBytes(file.size)})
              </li>
            `).join('')}
          </ul>
        </div>
      `;
    }

    filePreviewContent.innerHTML = html;
    filePreview.classList.remove('hidden');
  }

  /**
   * Maneja la subida de archivos
   */
  async handleUpload() {
    try {
      // Validar formulario
      const mainFile = document.getElementById('mainFile')?.files[0];
      const uploadFolderId = document.getElementById('uploadFolderId')?.value;

      if (!mainFile) {
        ui.error('Selecciona un archivo principal');
        return false;
      }

      if (!uploadFolderId) {
        ui.error('Selecciona una carpeta destino');
        return false;
      }

      // Recopilar datos del formulario
      const enableAnnexes = document.getElementById('enableAnnexes')?.checked;
      const annexFiles = enableAnnexes ? Array.from(document.getElementById('annexFiles')?.files || []) : [];
      const createAnnexFolder = document.getElementById('createAnnexFolder')?.checked ?? true;
      
      const metadata = {
        doc_number: document.getElementById('docNumber')?.value || null,
        tags: document.getElementById('tags')?.value?.split(',').map(t => t.trim()).filter(t => t) || [],
        observations: document.getElementById('observations')?.value || null
      };

      // Crear FormData
      const formData = new FormData();
      formData.append('file', mainFile);
      formData.append('folder_id', uploadFolderId);
      formData.append('create_annex_folder', createAnnexFolder);
      formData.append('metadata', JSON.stringify(metadata));

      // Agregar anexos
      if (annexFiles.length > 0) {
        annexFiles.forEach(file => {
          formData.append('anexos', file);
        });
      }

      // Mostrar progreso
      const uploadProgress = document.getElementById('uploadProgress');
      const uploadStatusText = document.getElementById('uploadStatusText');
      const uploadPercentage = document.getElementById('uploadPercentage');
      const uploadProgressBar = document.getElementById('uploadProgressBar');
      
      if (uploadProgress) uploadProgress.classList.remove('hidden');

      // Deshabilitar botón de subir
      const submitButton = document.querySelector('.modal-footer .btn-primary');
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = 'Subiendo...';
      }

      // Subir con XMLHttpRequest para seguir el progreso
      const result = await this.uploadWithProgress(formData, (progress) => {
        if (uploadPercentage) uploadPercentage.textContent = `${progress}%`;
        if (uploadProgressBar) uploadProgressBar.style.width = `${progress}%`;
        if (uploadStatusText) {
          if (progress < 100) {
            uploadStatusText.textContent = 'Subiendo archivos...';
          } else {
            uploadStatusText.textContent = 'Procesando...';
          }
        }
      });

      // Éxito
      ui.hideModal();
      ui.success(`Archivo subido correctamente${annexFiles.length > 0 ? ` con ${annexFiles.length} anexo(s)` : ''}`);
      
      // Recargar archivos
      await this.loadFiles();

      return true;

    } catch (error) {
      console.error('[files.js] Error uploading file:', error);
      ui.error(error.message || 'Error al subir el archivo');
      
      // Rehabilitar botón
      const submitButton = document.querySelector('.modal-footer .btn-primary');
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = 'Subir';
      }

      return false;
    }
  }

  /**
   * Sube archivos con seguimiento de progreso usando XMLHttpRequest
   */
  uploadWithProgress(formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Evento de progreso
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = Math.round((e.loaded / e.total) * 100);
          onProgress(percentComplete);
        }
      });

      // Evento de carga completa
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (error) {
            resolve(xhr.responseText);
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.detail || `Error ${xhr.status}`));
          } catch (e) {
            reject(new Error(`Error ${xhr.status}: ${xhr.statusText}`));
          }
        }
      });

      // Evento de error
      xhr.addEventListener('error', () => {
        reject(new Error('Error de red al subir el archivo'));
      });

      // Evento de cancelación
      xhr.addEventListener('abort', () => {
        reject(new Error('Subida cancelada'));
      });

      // Configurar y enviar
      xhr.open('POST', `${fetchWrapper.baseURL}/files/upload`);
      xhr.setRequestHeader('Authorization', `Bearer ${auth.getAccessToken()}`);
      
      // Agregar X-Request-Id
      const requestId = this.generateUUID();
      xhr.setRequestHeader('X-Request-Id', requestId);

      xhr.send(formData);
    });
  }

  /**
   * Genera un UUID v4
   */
  generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  /**
   * Descarga un archivo
   */
  async downloadFile(fileId, fileName) {
    try {
      ui.showLoading('Descargando archivo...');
      
      const response = await fetch(`${fetchWrapper.baseURL}/files/${fileId}/download`, {
        headers: {
          'Authorization': `Bearer ${auth.getAccessToken()}`
        }
      });

      if (!response.ok) {
        throw new Error('Error al descargar el archivo');
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
      ui.success('Archivo descargado correctamente');
    } catch (error) {
      console.error('[files.js] Error downloading file:', error);
      ui.hideLoading();
      ui.error('Error al descargar el archivo');
    }
  }

  /**
   * Elimina un archivo
   */
  async deleteFile(fileId) {
    const confirmed = await ui.confirm(
      'Eliminar archivo',
      '¿Estás seguro de que deseas eliminar este archivo? Esta acción no se puede deshacer.'
    );

    if (!confirmed) return;

    try {
      ui.showLoading('Eliminando archivo...');
      
      await fetchWrapper.delete(`/files/${fileId}?hard=false`);

      ui.hideLoading();
      ui.success('Archivo eliminado correctamente');
      
      // Recargar archivos
      await this.loadFiles();
    } catch (error) {
      console.error('[files.js] Error deleting file:', error);
      ui.hideLoading();
      ui.error('Error al eliminar el archivo');
    }
  }

  /**
   * Muestra los detalles de un archivo
   */
  async showFileDetails(fileId) {
    try {
      ui.showLoading('Cargando detalles...');
      
      const file = await fetchWrapper.get(`/files/${fileId}`);

      ui.hideLoading();

      ui.showModal('Detalles del Archivo', `
        <div class="file-details">
          <div class="detail-row">
            <strong>Nombre:</strong>
            <span>${this.escapeHtml(file.original_name || file.name)}</span>
          </div>
          <div class="detail-row">
            <strong>Tipo:</strong>
            <span>${this.escapeHtml(file.mime_type || 'Desconocido')}</span>
          </div>
          <div class="detail-row">
            <strong>Tamaño:</strong>
            <span>${this.formatBytes(file.size_bytes || 0)}</span>
          </div>
          <div class="detail-row">
            <strong>Subido por:</strong>
            <span>${this.escapeHtml(file.uploaded_by_name || 'N/A')}</span>
          </div>
          <div class="detail-row">
            <strong>Fecha de subida:</strong>
            <span>${new Date(file.created_at).toLocaleString()}</span>
          </div>
          <div class="detail-row">
            <strong>Última modificación:</strong>
            <span>${new Date(file.updated_at).toLocaleString()}</span>
          </div>
          <div class="detail-row">
            <strong>Versión:</strong>
            <span>${file.version || 1}</span>
          </div>
          ${file.checksum_sha256 ? `
            <div class="detail-row">
              <strong>Checksum (SHA256):</strong>
              <span style="font-family: monospace; font-size: 0.875rem;">${file.checksum_sha256}</span>
            </div>
          ` : ''}
        </div>
      `, {
        buttons: [
          {
            text: 'Descargar',
            class: 'btn btn-primary',
            onClick: () => this.downloadFile(fileId, file.original_name || file.name)
          },
          {
            text: 'Cerrar',
            class: 'btn btn-secondary'
          }
        ]
      });
    } catch (error) {
      console.error('[files.js] Error loading file details:', error);
      ui.hideLoading();
      ui.error('Error al cargar los detalles del archivo');
    }
  }

  /**
   * Formatea bytes a formato legible
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
   * Escapa HTML para prevenir XSS
   */
  escapeHtml(text) {
    if (!text) return '';
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
  }
}

// Exportar instancia única
export const filesManager = new FilesManager();

// Hacer global para event handlers inline
window.filesManager = filesManager;
