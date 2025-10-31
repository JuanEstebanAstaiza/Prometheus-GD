/**
 * SGDI - UI Module
 * Utilidades UI (modales, toasts, loading)
 */

class UI {
  constructor() {
    this.toastContainer = null;
    this.init();
  }

  /**
   * Inicializa el contenedor de toasts
   */
  init() {
    // Crear contenedor si no existe
    if (!document.getElementById('toastContainer')) {
      const container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    this.toastContainer = document.getElementById('toastContainer');
  }

  /**
   * Muestra un toast
   */
  showToast(message, type = 'info', duration = 5000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const content = document.createElement('div');
    content.textContent = message;
    content.style.flex = '1';

    const closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => this.removeToast(toast);

    toast.appendChild(content);
    toast.appendChild(closeBtn);
    this.toastContainer.appendChild(toast);

    // Auto-cerrar
    if (duration > 0) {
      setTimeout(() => this.removeToast(toast), duration);
    }

    return toast;
  }

  /**
   * Remueve un toast
   */
  removeToast(toast) {
    toast.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }

  /**
   * Toast de éxito
   */
  success(message, duration) {
    return this.showToast(message, 'success', duration);
  }

  /**
   * Toast de error
   */
  error(message, duration) {
    return this.showToast(message, 'error', duration);
  }

  /**
   * Toast de advertencia
   */
  warning(message, duration) {
    return this.showToast(message, 'warning', duration);
  }

  /**
   * Toast de información
   */
  info(message, duration) {
    return this.showToast(message, 'info', duration);
  }

  /**
   * Muestra un modal
   */
  showModal(title, content, options = {}) {
    // Crear backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';

    // Crear modal
    const modal = document.createElement('div');
    if (options.size === 'fullscreen') {
      modal.className = 'modal modal-fullscreen';
    } else if (options.size === 'large') {
      modal.className = 'modal modal-large';
    } else {
      modal.className = 'modal';
    }

    // Header
    const header = document.createElement('div');
    header.className = 'modal-header';
    
    const titleEl = document.createElement('h3');
    titleEl.className = 'modal-title';
    titleEl.textContent = title;
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => this.closeModal(backdrop);
    
    header.appendChild(titleEl);
    header.appendChild(closeBtn);

    // Body
    const body = document.createElement('div');
    body.className = 'modal-body';
    if (typeof content === 'string') {
      body.innerHTML = content;
    } else {
      body.appendChild(content);
    }

    // Footer (si hay botones)
    if (options.buttons) {
      const footer = document.createElement('div');
      footer.className = 'modal-footer';
      
      options.buttons.forEach(btn => {
        const button = document.createElement('button');
        button.className = btn.class || 'btn btn-secondary';
        button.textContent = btn.text;
        button.onclick = () => {
          if (btn.onClick) btn.onClick();
          if (btn.closeOnClick !== false) this.closeModal(backdrop);
        };
        footer.appendChild(button);
      });
      
      modal.appendChild(header);
      modal.appendChild(body);
      modal.appendChild(footer);
    } else {
      modal.appendChild(header);
      modal.appendChild(body);
    }

    backdrop.appendChild(modal);
    document.body.appendChild(backdrop);

    // Cerrar al hacer click en el backdrop
    backdrop.onclick = (e) => {
      if (e.target === backdrop) {
        this.closeModal(backdrop);
      }
    };

    return { backdrop, modal };
  }

  /**
   * Cierra un modal
   */
  closeModal(backdrop) {
    backdrop.style.animation = 'fadeOut 0.2s ease-out';
    setTimeout(() => {
      if (backdrop.parentNode) {
        backdrop.parentNode.removeChild(backdrop);
      }
    }, 200);
  }

  /**
   * Cierra el modal actual (el más reciente)
   */
  hideModal() {
    const backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) {
      this.closeModal(backdrop);
    }
  }

  /**
   * Modal de confirmación
   */
  confirm(title, message) {
    return new Promise((resolve) => {
      this.showModal(title, `<p>${message}</p>`, {
        buttons: [
          {
            text: 'Cancelar',
            class: 'btn btn-secondary',
            onClick: () => resolve(false)
          },
          {
            text: 'Confirmar',
            class: 'btn btn-primary',
            onClick: () => resolve(true)
          }
        ]
      });
    });
  }

  /**
   * Alias para confirm
   */
  showConfirm(title, message) {
    return this.confirm(title, message);
  }

  /**
   * Muestra loading
   */
  showLoading(message = 'Cargando...') {
    const loading = document.createElement('div');
    loading.id = 'loadingOverlay';
    loading.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
      background: white;
      padding: 2rem;
      border-radius: 0.5rem;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
    `;

    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.style.width = '2rem';
    spinner.style.height = '2rem';

    const text = document.createElement('p');
    text.textContent = message;
    text.style.margin = '0';

    content.appendChild(spinner);
    content.appendChild(text);
    loading.appendChild(content);
    document.body.appendChild(loading);

    return loading;
  }

  /**
   * Oculta loading
   */
  hideLoading() {
    const loading = document.getElementById('loadingOverlay');
    if (loading) {
      loading.parentNode.removeChild(loading);
    }
  }

  /**
   * Formatea una fecha
   */
  formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    // Menos de 1 minuto
    if (diff < 60000) {
      return 'Hace un momento';
    }
    
    // Menos de 1 hora
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000);
      return `Hace ${minutes} minuto${minutes > 1 ? 's' : ''}`;
    }
    
    // Menos de 1 día
    if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000);
      return `Hace ${hours} hora${hours > 1 ? 's' : ''}`;
    }
    
    // Fecha completa
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
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
}

// Exportar instancia singleton
export const ui = new UI();

