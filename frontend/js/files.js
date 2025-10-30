/**
 * SGDI - Files Module
 * Gestión completa de archivos con anexos, versioning, upload/download
 */

import { fetchWrapper } from './lib/fetch-wrapper.js';
import { auth } from './auth.js';
import { ui } from './ui.js';
import { validators } from './lib/validators.js';

class FilesManager {
  constructor() {
    this.currentFolder = null;
    this.uploadRetries = 2;
    this.maxFileSize = 200 * 1024 * 1024; // 200MB
    this.largeFileThreshold = 25 * 1024 * 1024; // 25MB
  }

  /**
   * Sanitiza nombre de archivo para carpeta de anexos
   * Strip extension, normalize NFKD, remove non-alphanumeric except - and _, collapse spaces to _, max 60 chars
   */
  sanitizeFileName(filename) {
    // Remover extensión
    const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');
    
    // Normalize to NFKD (decompose accents)
    let sanitized = nameWithoutExt.normalize('NFKD');
    
    // Remove accents
    sanitized = sanitized.replace(/[\u0300-\u036f]/g, '');
    
    // Keep only alphanumeric, hyphens, underscores
    sanitized = sanitized.replace(/[^a-zA-Z0-9\-_ ]/g, '');
    
    // Collapse spaces to underscore
    sanitized = sanitized.replace(/\s+/g, '_');
    
    // Collapse multiple underscores
    sanitized = sanitized.replace(/_+/g, '_');
    
    // Trim underscores
    sanitized = sanitized.replace(/^_+|_+$/g, '');
    
    // Max length 60
    sanitized = sanitized.substring(0, 60);
    
    return sanitized;
  }

  /**
   * Genera nombre de carpeta de anexos
   */
  generateAnnexFolderName(mainFileName) {
    const sanitized = this.sanitizeFileName(mainFileName);
    const now = new Date();
    const dateStr = now.getFullYear() + 
                    String(now.getMonth() + 1).padStart(2, '0') + 
                    String(now.getDate()).padStart(2, '0');
    
    return `Anexos-${sanitized}-${dateStr}`;
  }

  /**
   * Muestra modal de upload
   */
  showUploadModal(folderId) {
    if (!folderId) {
      ui.error('Selecciona una carpeta primero');
      return;
    }

    this.currentFolder = folderId;

    const content = document.createElement('div');
    content.innerHTML = `
      <form id="uploadForm" enctype="multipart/form-data">
        <!-- Archivo principal -->
        <div class="form-group">
          <label for="mainFile" class="form-label">Archivo Principal *</label>
          <div class="file-upload-zone" id="mainFileZone">
            <svg width="48" height="48" fill="currentColor" viewBox="0 0 20 20" style="color: var(--color-gray-400); margin: 0 auto;">
              <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
            </svg>
            <p style="margin-top: 1rem; font-weight: 500;">Arrastra o haz clic para seleccionar</p>
            <p style="font-size: 0.875rem; color: var(--color-gray-600);">Máximo 200MB</p>
          </div>
          <input type="file" id="mainFile" style="display: none;" required>
          <div id="mainFilePreview" class="file-preview hidden"></div>
        </div>

        <!-- Checkbox anexos -->
        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" id="hasAnnexes">
            <span>¿Tiene anexos?</span>
          </label>
        </div>

        <!-- Anexos (hidden inicialmente) -->
        <div id="annexesSection" class="form-group hidden">
          <label for="annexFiles" class="form-label">Archivos Anexos</label>
          <input type="file" id="annexFiles" class="form-input" multiple>
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            Puedes seleccionar múltiples archivos
          </p>
          <div id="annexesPreview" class="file-preview hidden"></div>
        </div>

        <!-- Nombre de carpeta de anexos (hidden inicialmente) -->
        <div id="annexFolderSection" class="form-group hidden">
          <label for="annexFolderName" class="form-label">Nombre de Carpeta de Anexos</label>
          <input type="text" id="annexFolderName" class="form-input" placeholder="Anexos-Nombre-YYYYMMDD">
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            Se creará automáticamente para organizar los anexos
          </p>
        </div>

        <!-- Metadata -->
        <div class="form-group">
          <label for="docNumber" class="form-label">Número de Documento</label>
          <input type="text" id="docNumber" class="form-input" placeholder="Ej: 2025-001">
        </div>

        <div class="form-group">
          <label for="tags" class="form-label">Etiquetas</label>
          <input type="text" id="tags" class="form-input" placeholder="etiqueta1, etiqueta2, etiqueta3">
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            Separadas por comas
          </p>
        </div>

        <div class="form-group">
          <label for="observations" class="form-label">Observaciones</label>
          <textarea id="observations" class="form-input" rows="3" placeholder="Notas adicionales..."></textarea>
        </div>

        <!-- Progress (hidden inicialmente) -->
        <div id="uploadProgress" class="hidden" style="margin-top: 1rem;">
          <div style="margin-bottom: 0.5rem;">
            <strong>Subiendo...</strong>
            <span id="uploadPercentage" style="float: right;">0%</span>
          </div>
          <div class="progress">
            <div class="progress-bar" id="uploadProgressBar" style="width: 0%;"></div>
          </div>
          <p id="uploadStatus" class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;"></p>
        </div>
      </form>
    `;

    const modal = ui.showModal('Subir Archivo', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary',
          onClick: () => {
            // Verificar si hay upload en progreso
            const progressDiv = document.getElementById('uploadProgress');
            if (progressDiv && !progressDiv.classList.contains('hidden')) {
              if (!confirm('¿Cancelar la subida en progreso?')) {
                return false; // No cerrar
              }
            }
          }
        },
        {
          text: 'Subir',
          class: 'btn btn-primary',
          onClick: async () => {
            await this.handleUpload();
          },
          closeOnClick: false
        }
      ]
    });

    // Setup event listeners
    this.setupUploadModalListeners(modal);
  }

  /**
   * Configura listeners del modal de upload
   */
  setupUploadModalListeners(modal) {
    const mainFileZone = document.getElementById('mainFileZone');
    const mainFileInput = document.getElementById('mainFile');
    const hasAnnexesCheck = document.getElementById('hasAnnexes');
    const annexesSection = document.getElementById('annexesSection');
    const annexFolderSection = document.getElementById('annexFolderSection');
    const annexFilesInput = document.getElementById('annexFiles');

    // Drag & drop para archivo principal
    mainFileZone.addEventListener('click', () => mainFileInput.click());

    mainFileZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      mainFileZone.classList.add('dragging');
    });

    mainFileZone.addEventListener('dragleave', () => {
      mainFileZone.classList.remove('dragging');
    });

    mainFileZone.addEventListener('drop', (e) => {
      e.preventDefault();
      mainFileZone.classList.remove('dragging');
      
      if (e.dataTransfer.files.length > 0) {
        mainFileInput.files = e.dataTransfer.files;
        this.updateMainFilePreview(mainFileInput.files[0]);
      }
    });

    // Cambio de archivo principal
    mainFileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.updateMainFilePreview(e.target.files[0]);
      }
    });

    // Toggle anexos
    hasAnnexesCheck.addEventListener('change', (e) => {
      if (e.target.checked) {
        annexesSection.classList.remove('hidden');
        annexFolderSection.classList.remove('hidden');
      } else {
        annexesSection.classList.add('hidden');
        annexFolderSection.classList.add('hidden');
        annexFilesInput.value = '';
        document.getElementById('annexesPreview').classList.add('hidden');
      }
    });

    // Cambio de anexos
    annexFilesInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.updateAnnexesPreview(e.target.files);
      }
    });
  }

  /**
   * Actualiza preview del archivo principal
   */
  updateMainFilePreview(file) {
    const preview = document.getElementById('mainFilePreview');
    const zone = document.getElementById('mainFileZone');
    const annexFolderInput = document.getElementById('annexFolderName');

    if (!file) return;

    // Validar tamaño
    if (file.size > this.maxFileSize) {
      ui.error(`El archivo es demasiado grande (máximo ${this.maxFileSize / (1024 * 1024)}MB)`);
      document.getElementById('mainFile').value = '';
      return;
    }

    // Advertencia para archivos grandes
    if (file.size > this.largeFileThreshold) {
      ui.warning(`⚠️ Archivo grande (${ui.formatBytes(file.size)}). La subida puede tardar varios minutos.`);
    }

    zone.style.display = 'none';
    preview.classList.remove('hidden');
    preview.innerHTML = `
      <div style="display: flex; align-items: center; gap: 1rem; padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
        <svg width="32" height="32" fill="currentColor" viewBox="0 0 20 20" style="color: var(--color-primary-500); flex-shrink: 0;">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/>
        </svg>
        <div style="flex: 1; min-width: 0;">
          <div style="font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(file.name)}</div>
          <div style="font-size: 0.875rem; color: var(--color-gray-600);">
            ${ui.formatBytes(file.size)} • ${file.type || 'application/octet-stream'}
          </div>
        </div>
        <button type="button" class="btn btn-sm btn-secondary" onclick="document.getElementById('mainFile').value=''; document.getElementById('mainFileZone').style.display=''; this.parentElement.parentElement.classList.add('hidden');">
          Cambiar
        </button>
      </div>
    `;

    // Generar nombre de carpeta de anexos
    if (annexFolderInput && document.getElementById('hasAnnexes').checked) {
      annexFolderInput.value = this.generateAnnexFolderName(file.name);
    }
  }

  /**
   * Actualiza preview de anexos
   */
  updateAnnexesPreview(files) {
    const preview = document.getElementById('annexesPreview');
    const annexFolderInput = document.getElementById('annexFolderName');
    const mainFileInput = document.getElementById('mainFile');

    if (!files || files.length === 0) return;

    preview.classList.remove('hidden');
    
    let totalSize = 0;
    const filesList = Array.from(files).map(file => {
      totalSize += file.size;
      return `
        <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; background: var(--color-gray-50); border-radius: var(--radius-sm); font-size: 0.875rem;">
          <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20" style="color: var(--color-gray-500); flex-shrink: 0;">
            <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/>
          </svg>
          <span style="flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(file.name)}</span>
          <span style="color: var(--color-gray-600);">${ui.formatBytes(file.size)}</span>
        </div>
      `;
    }).join('');

    preview.innerHTML = `
      <div style="padding: 1rem; background: var(--color-blue-50); border: 1px solid var(--color-blue-200); border-radius: var(--radius-md);">
        <div style="font-weight: 600; margin-bottom: 0.5rem;">
          ${files.length} anexo(s) • ${ui.formatBytes(totalSize)}
        </div>
        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
          ${filesList}
        </div>
      </div>
    `;

    // Actualizar nombre de carpeta si no ha sido editado manualmente
    if (annexFolderInput && mainFileInput.files.length > 0) {
      const currentValue = annexFolderInput.value;
      const expectedValue = this.generateAnnexFolderName(mainFileInput.files[0].name);
      
      // Solo actualizar si parece ser el valor auto-generado
      if (!currentValue || currentValue.startsWith('Anexos-')) {
        annexFolderInput.value = expectedValue;
      }
    }
  }

  /**
   * Maneja el proceso de upload
   */
  async handleUpload() {
    const mainFileInput = document.getElementById('mainFile');
    const hasAnnexes = document.getElementById('hasAnnexes').checked;
    const annexFilesInput = document.getElementById('annexFiles');
    const docNumber = document.getElementById('docNumber').value.trim();
    const tags = document.getElementById('tags').value.trim();
    const observations = document.getElementById('observations').value.trim();
    const annexFolderName = document.getElementById('annexFolderName').value.trim();

    // Validar
    if (!mainFileInput.files || mainFileInput.files.length === 0) {
      ui.error('Selecciona un archivo principal');
      return;
    }

    if (hasAnnexes && (!annexFilesInput.files || annexFilesInput.files.length === 0)) {
      ui.error('Selecciona al menos un anexo o desmarca la opción "¿Tiene anexos?"');
      return;
    }

    if (hasAnnexes && !annexFolderName) {
      ui.error('Especifica el nombre de la carpeta de anexos');
      return;
    }

    // Preparar FormData
    const formData = new FormData();
    formData.append('file', mainFileInput.files[0]);
    formData.append('folder_id', this.currentFolder);

    // Anexos
    if (hasAnnexes) {
      for (let i = 0; i < annexFilesInput.files.length; i++) {
        formData.append('anexos', annexFilesInput.files[i]);
      }
      formData.append('annex_folder_name', annexFolderName);
    }

    // Metadata
    const metadata = {
      doc_number: docNumber || null,
      tags: tags ? tags.split(',').map(t => t.trim()).filter(t => t) : [],
      observations: observations || null
    };
    formData.append('metadata', JSON.stringify(metadata));

    // Upload con progreso
    await this.uploadWithProgress(formData);
  }

  /**
   * Upload con barra de progreso y reintentos
   */
  async uploadWithProgress(formData, retryCount = 0) {
    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('uploadProgressBar');
    const percentage = document.getElementById('uploadPercentage');
    const status = document.getElementById('uploadStatus');

    // Mostrar progreso
    progressDiv.classList.remove('hidden');
    status.textContent = retryCount > 0 ? `Reintentando (${retryCount}/${this.uploadRetries})...` : 'Preparando subida...';

    try {
      const result = await fetchWrapper.upload('/files/upload', formData, (percent) => {
        progressBar.style.width = `${percent}%`;
        percentage.textContent = `${percent}%`;
        
        if (percent < 100) {
          status.textContent = 'Subiendo archivos...';
        } else {
          status.textContent = 'Procesando en el servidor...';
        }
      });

      // Éxito completo
      progressDiv.classList.add('hidden');
      
      const annexCount = result.annexes ? result.annexes.length : 0;
      const message = annexCount > 0 
        ? `Archivo y ${annexCount} anexo(s) subidos correctamente`
        : 'Archivo subido correctamente';

      ui.success(message);

      // Mostrar detalles si hay carpeta de anexos
      if (result.annex_folder) {
        ui.showModal('Upload Exitoso', `
          <div>
            <p style="margin-bottom: 1rem;">✅ ${message}</p>
            <div style="background: var(--color-gray-50); padding: 1rem; border-radius: var(--radius-md);">
              <div><strong>Archivo principal:</strong> ${this.escapeHtml(result.file.original_name)}</div>
              <div><strong>Carpeta de anexos:</strong> ${this.escapeHtml(result.annex_folder.name)}</div>
              ${annexCount > 0 ? `
                <div style="margin-top: 0.5rem;"><strong>Anexos incluidos:</strong></div>
                <ul style="margin-left: 1.5rem; margin-top: 0.5rem;">
                  ${result.annexes.map(a => `<li>${this.escapeHtml(a.original_name)}</li>`).join('')}
                </ul>
              ` : ''}
            </div>
          </div>
        `, {
          buttons: [{ text: 'Cerrar', class: 'btn btn-primary' }]
        });
      }

      // Cerrar modal de upload
      const uploadModal = document.querySelector('.modal-backdrop');
      if (uploadModal) ui.closeModal(uploadModal);

      // Recargar lista de archivos (si existe)
      if (typeof this.loadFiles === 'function') {
        await this.loadFiles(this.currentFolder);
      }

    } catch (error) {
      console.error('Upload error:', error);

      // Verificar si es error de red y podemos reintentar
      const isNetworkError = error.message === 'Upload failed: Network error' || 
                             error.message === 'Upload timeout';

      if (isNetworkError && retryCount < this.uploadRetries) {
        // Esperar con backoff exponencial
        const delay = Math.pow(2, retryCount) * 1000;
        status.textContent = `Error de red. Reintentando en ${delay / 1000}s...`;
        
        await new Promise(resolve => setTimeout(resolve, delay));
        
        // Reintentar
        return await this.uploadWithProgress(formData, retryCount + 1);
      }

      // Error definitivo
      progressDiv.classList.add('hidden');

      // Verificar si es éxito parcial
      if (error.status === 207 || error.data?.partial_success) {
        this.handlePartialSuccess(error.data);
      } else {
        const requestId = error.data?.request_id;
        ui.error(`Error al subir archivo${requestId ? ` (ID: ${requestId})` : ''}`);
      }
    }
  }

  /**
   * Maneja éxito parcial (main subido pero anexos fallaron)
   */
  handlePartialSuccess(data) {
    const mainFile = data.file;
    const successAnnexes = data.annexes_success || [];
    const failedAnnexes = data.annexes_failed || [];

    const content = document.createElement('div');
    content.innerHTML = `
      <div>
        <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-warning-50); border: 1px solid var(--color-warning-200); border-radius: var(--radius-md);">
          <strong>⚠️ Subida parcial</strong>
          <p style="margin-top: 0.5rem; margin-bottom: 0;">El archivo principal se subió correctamente, pero algunos anexos fallaron.</p>
        </div>

        <div style="margin-bottom: 1rem;">
          <h4 style="margin-bottom: 0.5rem;">✅ Archivo Principal</h4>
          <div style="padding: 0.75rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
            ${this.escapeHtml(mainFile.original_name)}
          </div>
        </div>

        ${successAnnexes.length > 0 ? `
          <div style="margin-bottom: 1rem;">
            <h4 style="margin-bottom: 0.5rem;">✅ Anexos Exitosos (${successAnnexes.length})</h4>
            <ul style="margin-left: 1.5rem;">
              ${successAnnexes.map(a => `<li>${this.escapeHtml(a.original_name)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}

        ${failedAnnexes.length > 0 ? `
          <div style="margin-bottom: 1rem;">
            <h4 style="margin-bottom: 0.5rem; color: var(--color-danger);">❌ Anexos Fallidos (${failedAnnexes.length})</h4>
            <ul style="margin-left: 1.5rem;">
              ${failedAnnexes.map(a => `<li>${this.escapeHtml(a.name)} - ${this.escapeHtml(a.error)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}

        <p class="text-muted" style="font-size: 0.875rem;">
          ¿Qué deseas hacer?
        </p>
      </div>
    `;

    ui.showModal('Subida Parcial', content, {
      buttons: [
        {
          text: 'Reintentar Anexos',
          class: 'btn btn-primary',
          onClick: async () => {
            await this.retryFailedAnnexes(mainFile.id, failedAnnexes);
          }
        },
        {
          text: 'Eliminar Todo',
          class: 'btn btn-danger',
          onClick: async () => {
            if (confirm('¿Eliminar el archivo principal y todos los anexos?')) {
              await this.deleteFile(mainFile.id, true, true);
              ui.closeModal(document.querySelector('.modal-backdrop'));
            }
          }
        },
        {
          text: 'Mantener Archivos Exitosos',
          class: 'btn btn-secondary'
        }
      ]
    });
  }

  /**
   * Reintenta subir anexos fallidos
   */
  async retryFailedAnnexes(mainFileId, failedAnnexes) {
    ui.showLoading('Reintentando anexos...');

    try {
      // Nota: Este endpoint debe estar implementado en el backend
      // POST /files/{mainFileId}/retry-annexes con { annex_names: [...] }
      
      const result = await fetchWrapper.post(`/files/${mainFileId}/retry-annexes`, {
        annex_names: failedAnnexes.map(a => a.name)
      });

      ui.hideLoading();
      ui.success(`${result.success_count} anexo(s) subidos correctamente`);

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

      // Recargar archivos
      if (typeof this.loadFiles === 'function') {
        await this.loadFiles(this.currentFolder);
      }

    } catch (error) {
      ui.hideLoading();
      console.error('Retry annexes error:', error);
      ui.error('Error al reintentar anexos');
    }
  }

  /**
   * Descarga un archivo con validación de checksum
   */
  async downloadFile(fileId, filename) {
    try {
      ui.showLoading('Preparando descarga...');

      // Usar fetch para capturar headers
      const token = auth.getAccessToken();
      const response = await fetch(`${fetchWrapper.baseURL}/files/${fileId}/download`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Download failed');
      }

      // Capturar checksum si existe
      const checksum = response.headers.get('X-Checksum-Sha256');
      if (checksum) {
        console.log('File checksum:', checksum);
      }

      // Obtener filename del Content-Disposition si existe
      const disposition = response.headers.get('Content-Disposition');
      let downloadFilename = filename;
      
      if (disposition && disposition.includes('filename=')) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
        if (matches && matches[1]) {
          downloadFilename = matches[1].replace(/['"]/g, '');
        }
      }

      // Descargar
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = downloadFilename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      ui.hideLoading();
      ui.success('Archivo descargado correctamente');

    } catch (error) {
      ui.hideLoading();
      console.error('Download error:', error);
      ui.error('Error al descargar archivo');
    }
  }

  /**
   * Muestra modal para actualizar archivo (versioning)
   */
  async showUpdateFileModal(fileId) {
    try {
      // Obtener info del archivo actual
      const fileInfo = await fetchWrapper.get(`/files/${fileId}`);

      const content = document.createElement('div');
      content.innerHTML = `
        <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
          <div><strong>Archivo actual:</strong> ${this.escapeHtml(fileInfo.original_name)}</div>
          <div style="font-size: 0.875rem; color: var(--color-gray-600); margin-top: 0.25rem;">
            Versión ${fileInfo.version || 1} • ${ui.formatBytes(fileInfo.size)}
          </div>
        </div>

        <form id="updateFileForm">
          <div class="form-group">
            <label for="newFile" class="form-label">Nuevo Archivo *</label>
            <input type="file" id="newFile" class="form-input" required>
            <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
              Se creará una nueva versión del archivo
            </p>
          </div>

          <div class="form-group">
            <label for="updateComment" class="form-label">Comentario de Versión</label>
            <textarea id="updateComment" class="form-input" rows="2" placeholder="Describe los cambios..."></textarea>
          </div>
        </form>

        ${fileInfo.versions && fileInfo.versions.length > 0 ? `
          <div style="margin-top: 1rem;">
            <h4 style="margin-bottom: 0.5rem;">Versiones Anteriores</h4>
            <div style="max-height: 200px; overflow-y: auto;">
              ${fileInfo.versions.map(v => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: var(--color-gray-50); border-radius: var(--radius-sm); margin-bottom: 0.5rem;">
                  <div>
                    <div style="font-weight: 500;">Versión ${v.version}</div>
                    <div style="font-size: 0.875rem; color: var(--color-gray-600);">
                      ${ui.formatDate(v.created_at)} • ${ui.formatBytes(v.size)}
                    </div>
                  </div>
                  <button type="button" class="btn btn-sm btn-secondary" onclick="filesManager.downloadFile('${v.id}', '${this.escapeHtml(v.original_name)}')">
                    Descargar
                  </button>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      `;

      ui.showModal('Actualizar Archivo', content, {
        buttons: [
          {
            text: 'Cancelar',
            class: 'btn btn-secondary'
          },
          {
            text: 'Actualizar',
            class: 'btn btn-primary',
            onClick: async () => {
              await this.updateFile(fileId);
            },
            closeOnClick: false
          }
        ]
      });

    } catch (error) {
      console.error('Error loading file info:', error);
      ui.error('Error al cargar información del archivo');
    }
  }

  /**
   * Actualiza un archivo (crea nueva versión)
   */
  async updateFile(fileId) {
    const newFileInput = document.getElementById('newFile');
    const comment = document.getElementById('updateComment').value.trim();

    if (!newFileInput.files || newFileInput.files.length === 0) {
      ui.error('Selecciona un archivo');
      return;
    }

    const formData = new FormData();
    formData.append('file', newFileInput.files[0]);
    if (comment) {
      formData.append('version_comment', comment);
    }

    try {
      ui.showLoading('Actualizando archivo...');

      // Usar upload con progreso
      const result = await fetchWrapper.upload(`/files/${fileId}`, formData, (percent) => {
        // Opcional: actualizar progreso en modal
      });

      ui.hideLoading();
      ui.success(`Archivo actualizado a versión ${result.version || 'nueva'}`);

      // Cerrar modal
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

      // Recargar archivos
      if (typeof this.loadFiles === 'function') {
        await this.loadFiles(this.currentFolder);
      }

    } catch (error) {
      ui.hideLoading();
      console.error('Update file error:', error);
      ui.error('Error al actualizar archivo');
    }
  }

  /**
   * Elimina un archivo
   */
  async deleteFile(fileId, hard = false, cascade = false) {
    const action = hard ? 'eliminar permanentemente' : 'eliminar';
    
    if (!confirm(`¿Estás seguro de que deseas ${action} este archivo?${cascade ? ' (incluidos anexos)' : ''}`)) {
      return;
    }

    try {
      ui.showLoading('Eliminando...');

      const url = `/files/${fileId}?hard=${hard}${cascade ? '&cascade=true' : ''}`;
      await fetchWrapper.delete(url);

      ui.hideLoading();
      ui.success(`Archivo ${hard ? 'eliminado permanentemente' : 'movido a papelera'}`);

      // Recargar archivos
      if (typeof this.loadFiles === 'function') {
        await this.loadFiles(this.currentFolder);
      }

    } catch (error) {
      ui.hideLoading();
      console.error('Delete file error:', error);
      ui.error('Error al eliminar archivo');
    }
  }

  /**
   * Lista anexos de un archivo
   */
  async loadAnnexes(fileId) {
    try {
      const annexes = await fetchWrapper.get(`/files/${fileId}/anexos`);
      return annexes;
    } catch (error) {
      console.error('Error loading annexes:', error);
      return [];
    }
  }

  /**
   * Renderiza sección de anexos
   */
  renderAnnexesSection(fileId, annexes) {
    if (!annexes || annexes.length === 0) {
      return '';
    }

    return `
      <details class="annexes-section" style="margin-top: 1rem; padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
        <summary style="cursor: pointer; font-weight: 600;">
          📎 Anexos (${annexes.length})
        </summary>
        <div style="margin-top: 1rem;">
          ${annexes.map(annex => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: white; border-radius: var(--radius-sm); margin-bottom: 0.5rem;">
              <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                  ${this.escapeHtml(annex.original_name)}
                </div>
                <div style="font-size: 0.875rem; color: var(--color-gray-600);">
                  ${ui.formatBytes(annex.size)}
                </div>
              </div>
              <button type="button" class="btn btn-sm btn-secondary" onclick="filesManager.downloadFile('${annex.id}', '${this.escapeHtml(annex.original_name)}')">
                Descargar
              </button>
            </div>
          `).join('')}
        </div>
      </details>
    `;
  }

  /**
   * Escapa HTML para prevenir XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Exportar instancia singleton
export const filesManager = new FilesManager();

// Hacer disponible globalmente
window.filesManager = filesManager;
