/**
 * SGDI - Backups Module
 * Gestión de backups y restauración con medidas de seguridad
 */

import { fetchWrapper } from './lib/fetch-wrapper.js';
import { auth } from './auth.js';
import { ui } from './ui.js';

class BackupsManager {
  constructor() {
    this.backups = [];
    this.dependencies = [];
  }

  /**
   * Inicializa el módulo de backups
   */
  async init() {
    await this.loadDependencies();
    await this.loadBackups();
    this.setupEventListeners();
  }

  /**
   * Carga dependencias para backup parcial
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
   * Carga lista de backups
   */
  async loadBackups() {
    const tableBody = document.getElementById('backupsTableBody');
    if (!tableBody) return;

    try {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="loading-state" style="text-align: center; padding: 3rem;">
            <div class="spinner"></div>
            <p style="margin-top: 1rem;">Cargando backups...</p>
          </td>
        </tr>
      `;

      this.backups = await fetchWrapper.get('/admin/backups');
      this.renderBackupsTable();

    } catch (error) {
      console.error('Error loading backups:', error);
      ui.error('Error al cargar lista de backups');
      
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="empty-state" style="text-align: center; padding: 3rem;">
            <div class="empty-state-icon" style="color: var(--color-danger);">⚠️</div>
            <h3 class="empty-state-title">Error al cargar backups</h3>
            <button class="btn btn-primary" onclick="backupsManager.loadBackups()">Reintentar</button>
          </td>
        </tr>
      `;
    }
  }

  /**
   * Renderiza tabla de backups
   */
  renderBackupsTable() {
    const tableBody = document.getElementById('backupsTableBody');
    if (!tableBody) return;

    if (this.backups.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="empty-state" style="text-align: center; padding: 3rem;">
            <div class="empty-state-icon">💾</div>
            <h3 class="empty-state-title">No hay backups</h3>
            <p class="empty-state-description">Aún no se han creado respaldos del sistema</p>
            <button class="btn btn-primary" onclick="backupsManager.showCreateBackupModal()">
              Crear Primer Backup
            </button>
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = this.backups.map(backup => `
      <tr>
        <td data-label="Archivo">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg width="24" height="24" fill="currentColor" viewBox="0 0 20 20" style="color: var(--color-primary-500); flex-shrink: 0;">
              <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z"/>
              <path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z"/>
              <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z"/>
            </svg>
            <div style="min-width: 0;">
              <div style="font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                ${this.escapeHtml(backup.filename)}
              </div>
              <div style="font-size: 0.75rem; color: var(--color-gray-600);">
                ID: ${backup.id.substring(0, 8)}...
              </div>
            </div>
          </div>
        </td>
        <td data-label="Tipo">
          <span class="badge badge-${backup.dependency_id ? 'warning' : 'primary'}">
            ${backup.dependency_id ? 'Parcial' : 'Completo'}
          </span>
        </td>
        <td data-label="Fecha">
          <div style="font-size: 0.875rem;">
            ${ui.formatDate(backup.created_at)}
          </div>
        </td>
        <td data-label="Tamaño">
          <div style="font-size: 0.875rem; font-weight: 500;">
            ${ui.formatBytes(backup.size_bytes)}
          </div>
        </td>
        <td data-label="Acciones">
          <div class="table-actions">
            <button 
              class="btn btn-sm btn-secondary" 
              onclick="backupsManager.downloadBackup('${backup.id}', '${this.escapeHtml(backup.filename)}')"
              title="Descargar backup"
            >
              <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
              Descargar
            </button>
            <button 
              class="btn btn-sm btn-warning" 
              onclick="backupsManager.showRestoreModal('${backup.id}', '${this.escapeHtml(backup.filename)}')"
              title="Restaurar backup"
            >
              <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
              </svg>
              Restaurar
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  /**
   * Configura event listeners
   */
  setupEventListeners() {
    // Botón crear backup completo
    const createFullBackupBtn = document.getElementById('createFullBackupBtn');
    if (createFullBackupBtn) {
      createFullBackupBtn.addEventListener('click', () => {
        this.showCreateBackupModal();
      });
    }

    // Botón crear backup parcial
    const createPartialBackupBtn = document.getElementById('createPartialBackupBtn');
    if (createPartialBackupBtn) {
      createPartialBackupBtn.addEventListener('click', () => {
        this.showCreateBackupModal(true);
      });
    }
  }

  /**
   * Muestra modal para crear backup
   */
  showCreateBackupModal(partial = false) {
    const content = document.createElement('div');
    content.innerHTML = `
      <div>
        <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-info-50); border: 1px solid var(--color-info-200); border-radius: var(--radius-md);">
          <strong>ℹ️ Información</strong>
          <p style="margin-top: 0.5rem; margin-bottom: 0;">
            ${partial 
              ? 'Se creará un backup de una dependencia específica (carpetas y archivos).' 
              : 'Se creará un backup completo del sistema (dependencias, carpetas, archivos y logs).'}
          </p>
        </div>

        ${partial ? `
          <div class="form-group">
            <label for="backupDependency" class="form-label">Dependencia *</label>
            <select id="backupDependency" class="form-input" required>
              <option value="">Seleccionar...</option>
              ${this.dependencies.map(dep => `
                <option value="${dep.id}">${this.escapeHtml(dep.name)}</option>
              `).join('')}
            </select>
          </div>
        ` : ''}

        <div style="margin-top: 1rem; padding: 1rem; background: var(--color-warning-50); border: 1px solid var(--color-warning-200); border-radius: var(--radius-md);">
          <strong>⚠️ Advertencia</strong>
          <ul style="margin-top: 0.5rem; margin-bottom: 0; margin-left: 1.5rem;">
            <li>El proceso puede tardar varios minutos</li>
            <li>Se recomienda realizar backups en horarios de baja actividad</li>
            <li>El archivo generado será grande y ocupará espacio en disco</li>
          </ul>
        </div>
      </div>
    `;

    ui.showModal(partial ? 'Crear Backup Parcial' : 'Crear Backup Completo', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'Crear Backup',
          class: 'btn btn-primary',
          onClick: async () => {
            await this.createBackup(partial);
          },
          closeOnClick: false
        }
      ]
    });
  }

  /**
   * Crea un backup
   */
  async createBackup(partial = false) {
    let dependencyId = null;

    if (partial) {
      const select = document.getElementById('backupDependency');
      dependencyId = select ? select.value : null;

      if (!dependencyId) {
        ui.error('Selecciona una dependencia');
        return;
      }
    }

    try {
      // Cerrar modal de confirmación
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

      // Mostrar progress spinner
      ui.showLoading('Generando backup... Esto puede tardar varios minutos.');

      const body = dependencyId ? { dependency_id: dependencyId } : {};
      const result = await fetchWrapper.post('/admin/backups/create', body);

      ui.hideLoading();

      // Mostrar éxito con opción de descarga
      const successContent = document.createElement('div');
      successContent.innerHTML = `
        <div>
          <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-success-50); border: 1px solid var(--color-success-200); border-radius: var(--radius-md);">
            <strong>✅ Backup creado exitosamente</strong>
          </div>

          <div style="padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
            <div><strong>Archivo:</strong> ${this.escapeHtml(result.filename)}</div>
            <div style="margin-top: 0.5rem;"><strong>Tamaño:</strong> ${ui.formatBytes(result.size_bytes)}</div>
            <div style="margin-top: 0.5rem;"><strong>ID:</strong> ${result.id}</div>
            ${result.checksum ? `<div style="margin-top: 0.5rem;"><strong>Checksum:</strong> <code style="font-size: 0.75rem;">${result.checksum.substring(0, 16)}...</code></div>` : ''}
          </div>

          <p style="margin-top: 1rem; font-size: 0.875rem; color: var(--color-gray-600);">
            El backup está disponible para descarga en la lista.
          </p>
        </div>
      `;

      ui.showModal('Backup Creado', successContent, {
        buttons: [
          {
            text: 'Descargar Ahora',
            class: 'btn btn-primary',
            onClick: async () => {
              await this.downloadBackup(result.id, result.filename);
            }
          },
          {
            text: 'Cerrar',
            class: 'btn btn-secondary'
          }
        ]
      });

      // Recargar lista
      await this.loadBackups();

    } catch (error) {
      ui.hideLoading();
      console.error('Error creating backup:', error);

      const requestId = error.data?.request_id;
      let errorMessage = 'Error al crear backup';

      if (error.data?.detail) {
        errorMessage = error.data.detail;
      }

      ui.error(`${errorMessage}${requestId ? ` (ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Descarga un backup
   */
  async downloadBackup(backupId, filename) {
    try {
      await fetchWrapper.download(`/admin/backups/${backupId}/download`, filename);
    } catch (error) {
      console.error('Download backup error:', error);
      ui.error('Error al descargar backup');
    }
  }

  /**
   * Muestra modal de restauración
   */
  showRestoreModal(backupId = null, filename = null) {
    const content = document.createElement('div');
    content.innerHTML = `
      <div>
        <!-- Advertencias de seguridad -->
        <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-danger-50); border: 1px solid var(--color-danger-200); border-radius: var(--radius-md);">
          <strong>🚨 ADVERTENCIA CRÍTICA</strong>
          <p style="margin-top: 0.5rem; margin-bottom: 0;">
            Restaurar un backup puede <strong>sobrescribir o eliminar datos actuales</strong>.
          </p>
        </div>

        <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-info-50); border: 1px solid var(--color-info-200); border-radius: var(--radius-md);">
          <strong>📋 Recomendaciones:</strong>
          <ol style="margin-top: 0.5rem; margin-bottom: 0; margin-left: 1.5rem;">
            <li><strong>Ejecuta primero en modo SIMULATE</strong> para ver qué cambios se realizarán</li>
            <li>Haz un <strong>backup de la base de datos actual</strong> antes de restaurar (pg_dump)</li>
            <li>Verifica que el archivo .tar.gz sea válido</li>
            <li>Realiza la restauración en <strong>horarios de baja actividad</strong></li>
          </ol>
        </div>

        ${backupId ? `
          <div class="form-group">
            <label class="form-label">Archivo de Backup</label>
            <div style="padding: 0.75rem; background: var(--color-gray-50); border-radius: var(--radius-md); font-family: monospace; font-size: 0.875rem;">
              ${this.escapeHtml(filename)}
            </div>
            <input type="hidden" id="restoreBackupId" value="${backupId}">
          </div>
        ` : `
          <div class="form-group">
            <label for="restoreFile" class="form-label">Archivo de Backup (.tar.gz) *</label>
            <input 
              type="file" 
              id="restoreFile" 
              class="form-input" 
              accept=".tar.gz,.tgz"
              required
            >
            <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
              Solo archivos .tar.gz generados por el sistema
            </p>
          </div>
        `}

        <div class="form-group">
          <label for="restoreStrategy" class="form-label">Estrategia de Restauración *</label>
          <select id="restoreStrategy" class="form-input" required>
            <option value="create_new_ids">Crear Nuevos IDs (recomendado)</option>
            <option value="overwrite">Sobrescribir Existentes (⚠️ peligroso)</option>
          </select>
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            <strong>create_new_ids:</strong> Crea nuevas entradas con IDs diferentes, no afecta datos existentes<br>
            <strong>overwrite:</strong> Sobrescribe entradas con el mismo ID (puede causar pérdida de datos)
          </p>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" id="simulateOnly" checked>
            <span><strong>Solo simular (recomendado)</strong></span>
          </label>
          <p class="text-muted" style="font-size: 0.875rem; margin-top: 0.5rem;">
            Muestra un reporte de los cambios sin aplicarlos. Desmarcar para ejecutar la restauración real.
          </p>
        </div>

        <div class="form-group" id="confirmSection" style="display: none;">
          <label class="checkbox-label">
            <input type="checkbox" id="confirmRestore">
            <span style="color: var(--color-danger);"><strong>Confirmo que he hecho backup de la BD actual y entiendo los riesgos</strong></span>
          </label>
        </div>
      </div>
    `;

    const modal = ui.showModal('Restaurar Backup', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'Continuar',
          class: 'btn btn-warning',
          onClick: async () => {
            await this.executeRestore(backupId);
          },
          closeOnClick: false
        }
      ]
    });

    // Mostrar confirmación si no es simulación
    const simulateCheck = document.getElementById('simulateOnly');
    const confirmSection = document.getElementById('confirmSection');

    if (simulateCheck && confirmSection) {
      simulateCheck.addEventListener('change', () => {
        if (simulateCheck.checked) {
          confirmSection.style.display = 'none';
        } else {
          confirmSection.style.display = 'block';
        }
      });
    }
  }

  /**
   * Ejecuta la restauración o simulación
   */
  async executeRestore(backupId = null) {
    const strategy = document.getElementById('restoreStrategy').value;
    const simulateOnly = document.getElementById('simulateOnly').checked;
    const confirmRestore = document.getElementById('confirmRestore');
    const fileInput = document.getElementById('restoreFile');

    // Validar confirmación si no es simulación
    if (!simulateOnly && confirmRestore && !confirmRestore.checked) {
      ui.error('Debes confirmar que has realizado un backup de la BD actual');
      return;
    }

    // Validar archivo si no hay backupId
    if (!backupId && (!fileInput || !fileInput.files || fileInput.files.length === 0)) {
      ui.error('Selecciona un archivo de backup');
      return;
    }

    try {
      // Cerrar modal actual
      const modal = document.querySelector('.modal-backdrop');
      if (modal) ui.closeModal(modal);

      // Mostrar loading
      ui.showLoading(simulateOnly ? 'Simulando restauración...' : 'Restaurando backup... NO INTERRUMPAS EL PROCESO.');

      // Preparar FormData
      const formData = new FormData();
      
      if (backupId) {
        formData.append('backup_id', backupId);
      } else {
        formData.append('file', fileInput.files[0]);
      }
      
      formData.append('strategy', strategy);
      formData.append('simulate', simulateOnly.toString());

      const result = await fetchWrapper.upload('/admin/backups/restore', formData);

      ui.hideLoading();

      // Mostrar resultado
      if (simulateOnly) {
        this.showSimulationReport(result);
      } else {
        this.showRestoreResult(result);
      }

    } catch (error) {
      ui.hideLoading();
      console.error('Restore error:', error);

      const requestId = error.data?.request_id;
      let errorMessage = 'Error al restaurar backup';

      if (error.status === 400) {
        errorMessage = 'Archivo de backup inválido o corrupto';
      } else if (error.status === 409) {
        errorMessage = 'Conflicto de datos. Verifica la estrategia seleccionada.';
      } else if (error.data?.detail) {
        errorMessage = error.data.detail;
      }

      ui.error(`${errorMessage}${requestId ? ` (Request ID: ${requestId})` : ''}`);
    }
  }

  /**
   * Muestra reporte de simulación
   */
  showSimulationReport(report) {
    const content = document.createElement('div');
    content.innerHTML = `
      <div>
        <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-info-50); border: 1px solid var(--color-info-200); border-radius: var(--radius-md);">
          <strong>📊 Reporte de Simulación</strong>
          <p style="margin-top: 0.5rem; margin-bottom: 0;">
            Esta es una simulación. No se han aplicado cambios al sistema.
          </p>
        </div>

        <div style="padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
          <h4 style="margin-bottom: 1rem;">Resumen de Acciones</h4>
          
          ${report.dependencies_to_create ? `
            <div style="margin-bottom: 0.75rem;">
              <strong>📁 Dependencias a crear:</strong> ${report.dependencies_to_create}
            </div>
          ` : ''}

          ${report.folders_to_create ? `
            <div style="margin-bottom: 0.75rem;">
              <strong>📂 Carpetas a crear:</strong> ${report.folders_to_create}
            </div>
          ` : ''}

          ${report.files_to_create ? `
            <div style="margin-bottom: 0.75rem;">
              <strong>📄 Archivos a restaurar:</strong> ${report.files_to_create}
            </div>
          ` : ''}

          ${report.conflicts && report.conflicts.length > 0 ? `
            <div style="margin-top: 1rem; padding: 1rem; background: var(--color-warning-50); border: 1px solid var(--color-warning-200); border-radius: var(--radius-md);">
              <strong>⚠️ Conflictos Detectados (${report.conflicts.length}):</strong>
              <ul style="margin-top: 0.5rem; margin-bottom: 0; margin-left: 1.5rem; max-height: 200px; overflow-y: auto;">
                ${report.conflicts.slice(0, 10).map(conflict => `
                  <li style="font-size: 0.875rem;">${this.escapeHtml(conflict)}</li>
                `).join('')}
                ${report.conflicts.length > 10 ? `<li style="font-size: 0.875rem;">... y ${report.conflicts.length - 10} más</li>` : ''}
              </ul>
            </div>
          ` : `
            <div style="margin-top: 1rem; padding: 1rem; background: var(--color-success-50); border: 1px solid var(--color-success-200); border-radius: var(--radius-md);">
              <strong>✅ No se detectaron conflictos</strong>
            </div>
          `}

          ${report.request_id ? `
            <div style="margin-top: 1rem; font-size: 0.75rem; color: var(--color-gray-600);">
              Request ID: ${report.request_id}
            </div>
          ` : ''}
        </div>

        <p style="margin-top: 1rem; font-size: 0.875rem; color: var(--color-gray-600);">
          ¿Deseas proceder con la restauración real?
        </p>
      </div>
    `;

    ui.showModal('Reporte de Simulación', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'Ejecutar Restauración Real',
          class: 'btn btn-danger',
          onClick: () => {
            // Volver a mostrar modal pero sin simulate
            const simulateCheck = document.getElementById('simulateOnly');
            if (simulateCheck) {
              simulateCheck.checked = false;
              simulateCheck.dispatchEvent(new Event('change'));
            }
            
            // Cerrar reporte
            const reportModal = document.querySelector('.modal-backdrop');
            if (reportModal) ui.closeModal(reportModal);
            
            // Mostrar confirmación final
            this.showFinalConfirmation(report);
          }
        }
      ]
    });
  }

  /**
   * Muestra confirmación final antes de restaurar
   */
  showFinalConfirmation(simulationReport) {
    const content = document.createElement('div');
    content.innerHTML = `
      <div>
        <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-danger-50); border: 1px solid var(--color-danger-200); border-radius: var(--radius-md);">
          <strong>🚨 CONFIRMACIÓN FINAL</strong>
          <p style="margin-top: 0.5rem; margin-bottom: 0;">
            Esta acción <strong>no se puede deshacer</strong> y puede causar <strong>pérdida de datos</strong>.
          </p>
        </div>

        <div style="padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md); margin-bottom: 1rem;">
          <p style="margin-bottom: 0.5rem;"><strong>Se aplicarán los siguientes cambios:</strong></p>
          <ul style="margin-left: 1.5rem;">
            ${simulationReport.dependencies_to_create ? `<li>Crear ${simulationReport.dependencies_to_create} dependencias</li>` : ''}
            ${simulationReport.folders_to_create ? `<li>Crear ${simulationReport.folders_to_create} carpetas</li>` : ''}
            ${simulationReport.files_to_create ? `<li>Restaurar ${simulationReport.files_to_create} archivos</li>` : ''}
            ${simulationReport.conflicts && simulationReport.conflicts.length > 0 ? `<li style="color: var(--color-danger);">⚠️ ${simulationReport.conflicts.length} conflictos detectados</li>` : ''}
          </ul>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" id="finalConfirm1">
            <span><strong>He realizado un backup de la base de datos actual (pg_dump)</strong></span>
          </label>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" id="finalConfirm2">
            <span><strong>Entiendo que esta acción puede causar pérdida de datos</strong></span>
          </label>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" id="finalConfirm3">
            <span><strong>Confirmo que deseo proceder con la restauración</strong></span>
          </label>
        </div>
      </div>
    `;

    ui.showModal('⚠️ Confirmación Final', content, {
      buttons: [
        {
          text: 'Cancelar',
          class: 'btn btn-secondary'
        },
        {
          text: 'RESTAURAR AHORA',
          class: 'btn btn-danger',
          onClick: async () => {
            const confirm1 = document.getElementById('finalConfirm1');
            const confirm2 = document.getElementById('finalConfirm2');
            const confirm3 = document.getElementById('finalConfirm3');

            if (!confirm1.checked || !confirm2.checked || !confirm3.checked) {
              ui.error('Debes confirmar todas las opciones para continuar');
              return false; // No cerrar modal
            }

            // Ejecutar restauración real
            // TODO: Aquí deberíamos pasar los datos del backup original
            // Por ahora, mostrar que necesitamos volver a solicitar el archivo
            ui.info('Para continuar, vuelve a abrir el modal de restauración y desmarca "Solo simular"');
          }
        }
      ]
    });
  }

  /**
   * Muestra resultado de restauración
   */
  showRestoreResult(result) {
    const content = document.createElement('div');
    content.innerHTML = `
      <div>
        <div style="margin-bottom: 1rem; padding: 1rem; background: var(--color-success-50); border: 1px solid var(--color-success-200); border-radius: var(--radius-md);">
          <strong>✅ Restauración Completada</strong>
          <p style="margin-top: 0.5rem; margin-bottom: 0;">
            El backup se ha restaurado exitosamente.
          </p>
        </div>

        <div style="padding: 1rem; background: var(--color-gray-50); border-radius: var(--radius-md);">
          <h4 style="margin-bottom: 1rem;">Resumen</h4>
          
          ${result.dependencies_created ? `
            <div style="margin-bottom: 0.75rem;">
              <strong>📁 Dependencias creadas:</strong> ${result.dependencies_created}
            </div>
          ` : ''}

          ${result.folders_created ? `
            <div style="margin-bottom: 0.75rem;">
              <strong>📂 Carpetas creadas:</strong> ${result.folders_created}
            </div>
          ` : ''}

          ${result.files_created ? `
            <div style="margin-bottom: 0.75rem;">
              <strong>📄 Archivos restaurados:</strong> ${result.files_created}
            </div>
          ` : ''}

          ${result.errors && result.errors.length > 0 ? `
            <div style="margin-top: 1rem; padding: 1rem; background: var(--color-danger-50); border: 1px solid var(--color-danger-200); border-radius: var(--radius-md);">
              <strong>❌ Errores (${result.errors.length}):</strong>
              <ul style="margin-top: 0.5rem; margin-bottom: 0; margin-left: 1.5rem; max-height: 200px; overflow-y: auto;">
                ${result.errors.map(error => `
                  <li style="font-size: 0.875rem;">${this.escapeHtml(error)}</li>
                `).join('')}
              </ul>
            </div>
          ` : ''}

          ${result.request_id ? `
            <div style="margin-top: 1rem; font-size: 0.75rem; color: var(--color-gray-600);">
              Request ID: ${result.request_id}
            </div>
          ` : ''}
        </div>

        <p style="margin-top: 1rem; font-size: 0.875rem; color: var(--color-gray-600);">
          Se recomienda verificar que todos los datos se hayan restaurado correctamente.
        </p>
      </div>
    `;

    ui.showModal('Restauración Completada', content, {
      buttons: [
        {
          text: 'Cerrar',
          class: 'btn btn-primary'
        }
      ]
    });

    // Recargar lista de backups
    this.loadBackups();
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
export const backupsManager = new BackupsManager();

// Hacer disponible globalmente
window.backupsManager = backupsManager;
