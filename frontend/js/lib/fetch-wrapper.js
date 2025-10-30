/**
 * SGDI - Fetch Wrapper
 * Cliente HTTP con retry, interceptors, JWT refresh automático
 */

import { generateUUID } from './validators.js';
import { config } from '../config.js';

class FetchWrapper {
  constructor() {
    this.baseURL = config.FRONTEND_API_URL;
    this.defaultTimeout = 60000; // 60 segundos
    this.maxRetries = 2; // Para peticiones idempotentes (GET)
    this.retryDelay = 1000; // 1 segundo inicial
    this.refreshPromise = null; // Para evitar múltiples refresh simultáneos
  }

  /**
   * Obtiene el access token del localStorage
   */
  getAccessToken() {
    return localStorage.getItem('access_token');
  }

  /**
   * Obtiene el refresh token del localStorage
   */
  getRefreshToken() {
    return localStorage.getItem('refresh_token');
  }

  /**
   * Guarda los tokens en localStorage
   */
  setTokens(accessToken, refreshToken) {
    if (accessToken) {
      localStorage.setItem('access_token', accessToken);
    }
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
  }

  /**
   * Limpia los tokens del localStorage
   */
  clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('access_expiry_ts');
    localStorage.removeItem('current_user');
  }

  /**
   * Verifica si el token está expirado
   */
  isTokenExpired() {
    const expiryTs = localStorage.getItem('access_expiry_ts');
    if (!expiryTs) return true;
    
    // Considerar expirado si faltan menos de 60 segundos
    return Date.now() >= (parseInt(expiryTs) - 60000);
  }

  /**
   * Refresca el access token usando el refresh token
   */
  async refreshAccessToken() {
    // Si ya hay un refresh en progreso, esperar a que termine
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      try {
        const refreshToken = this.getRefreshToken();
        
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        const response = await fetch(`${this.baseURL}/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Request-Id': generateUUID()
          },
          body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
          throw new Error('Failed to refresh token');
        }

        const data = await response.json();
        
        // Guardar nuevos tokens
        this.setTokens(data.access_token, data.refresh_token || refreshToken);
        
        // Calcular y guardar expiración
        if (data.expires_in) {
          const expiryTs = Date.now() + (data.expires_in * 1000);
          localStorage.setItem('access_expiry_ts', expiryTs.toString());
        }

        return data.access_token;
      } catch (error) {
        console.error('Token refresh failed:', error);
        
        // Limpiar todo y redirigir a login
        this.clearTokens();
        
        // Importación dinámica para evitar ciclo
        const { auth } = await import('../auth.js');
        auth.logout();
        
        throw error;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  /**
   * Construye headers con autenticación
   */
  buildHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'X-Request-Id': generateUUID(),
      ...customHeaders
    };

    const token = this.getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Maneja timeout de peticiones
   */
  withTimeout(promise, timeoutMs = this.defaultTimeout) {
    return Promise.race([
      promise,
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout')), timeoutMs)
      )
    ]);
  }

  /**
   * Sleep para backoff exponencial
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Ejecuta petición con retry y manejo de 401
   */
  async executeRequest(url, options, retryCount = 0, hasRefreshed = false) {
    try {
      const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;
      console.log('[fetch-wrapper] URL:', url);
      console.log('[fetch-wrapper] baseURL:', this.baseURL);
      console.log('[fetch-wrapper] fullUrl:', fullUrl);
      
      const response = await this.withTimeout(
        fetch(fullUrl, options)
      );

      // Si es 401 y no hemos intentado refresh, intentar refresh
      if (response.status === 401 && !hasRefreshed) {
        console.log('Received 401, attempting token refresh...');
        
        try {
          await this.refreshAccessToken();
          
          // Actualizar token en headers y reintentar
          options.headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
          
          return await this.executeRequest(url, options, retryCount, true);
        } catch (refreshError) {
          // Si el refresh falla, ya se redirigió a login en refreshAccessToken
          throw new Error('Authentication failed');
        }
      }

      // Si no es OK y no es 401, lanzar error
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
        error.status = response.status;
        error.data = errorData;
        throw error;
      }

      return response;

    } catch (error) {
      // Si es timeout o error de red y es GET, reintentar con backoff exponencial
      const isIdempotent = options.method === 'GET';
      const shouldRetry = isIdempotent && retryCount < this.maxRetries;

      if (shouldRetry && (error.message === 'Request timeout' || error.message === 'Failed to fetch')) {
        const delay = this.retryDelay * Math.pow(2, retryCount);
        console.log(`Retrying request (${retryCount + 1}/${this.maxRetries}) after ${delay}ms...`);
        
        await this.sleep(delay);
        return await this.executeRequest(url, options, retryCount + 1, hasRefreshed);
      }

      throw error;
    }
  }

  /**
   * GET request
   */
  async get(url, params = {}) {
    // Construir query string si hay params
    const queryString = Object.keys(params).length > 0
      ? '?' + new URLSearchParams(params).toString()
      : '';

    const options = {
      method: 'GET',
      headers: this.buildHeaders()
    };

    const response = await this.executeRequest(url + queryString, options);
    return await response.json();
  }

  /**
   * POST request
   */
  async post(url, body = {}, customHeaders = {}) {
    const options = {
      method: 'POST',
      headers: this.buildHeaders(customHeaders),
      body: JSON.stringify(body)
    };

    const response = await this.executeRequest(url, options);
    return await response.json();
  }

  /**
   * PUT request
   */
  async put(url, body = {}, customHeaders = {}) {
    const options = {
      method: 'PUT',
      headers: this.buildHeaders(customHeaders),
      body: JSON.stringify(body)
    };

    const response = await this.executeRequest(url, options);
    return await response.json();
  }

  /**
   * DELETE request
   */
  async delete(url, customHeaders = {}) {
    const options = {
      method: 'DELETE',
      headers: this.buildHeaders(customHeaders)
    };

    const response = await this.executeRequest(url, options);
    
    // DELETE puede no devolver contenido
    const text = await response.text();
    return text ? JSON.parse(text) : { success: true };
  }

  /**
   * PATCH request
   */
  async patch(url, body = {}, customHeaders = {}) {
    const options = {
      method: 'PATCH',
      headers: this.buildHeaders(customHeaders),
      body: JSON.stringify(body)
    };

    const response = await this.executeRequest(url, options);
    return await response.json();
  }

  /**
   * Upload con progreso usando XMLHttpRequest
   * @param {string} url - URL del endpoint
   * @param {FormData} formData - FormData con archivos
   * @param {Function} onProgress - Callback (percent) => void
   */
  upload(url, formData, onProgress = null) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;

      // Evento de progreso
      if (onProgress && xhr.upload) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            onProgress(percent);
          }
        });
      }

      // Evento de carga completada
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (error) {
            resolve({ success: true });
          }
        } else if (xhr.status === 401) {
          // Manejar 401 en upload
          this.refreshAccessToken()
            .then(() => {
              // Reintentar upload con nuevo token
              const retryFormData = formData; // FormData es reutilizable
              this.upload(url, retryFormData, onProgress)
                .then(resolve)
                .catch(reject);
            })
            .catch(() => {
              reject(new Error('Authentication failed'));
            });
        } else {
          try {
            const errorData = JSON.parse(xhr.responseText);
            const error = new Error(errorData.detail || errorData.message || `HTTP ${xhr.status}`);
            error.status = xhr.status;
            error.data = errorData;
            reject(error);
          } catch (e) {
            reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
          }
        }
      });

      // Evento de error
      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed: Network error'));
      });

      // Evento de timeout
      xhr.addEventListener('timeout', () => {
        reject(new Error('Upload timeout'));
      });

      // Configurar request
      xhr.open('POST', fullUrl);
      xhr.timeout = this.defaultTimeout;

      // Headers (sin Content-Type para que el navegador lo establezca con boundary)
      const token = this.getAccessToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }
      xhr.setRequestHeader('X-Request-Id', generateUUID());

      // Enviar
      xhr.send(formData);
    });
  }

  /**
   * Download de archivos
   * @param {string} url - URL del archivo
   * @param {string} filename - Nombre del archivo a descargar
   */
  async download(url, filename) {
    try {
      const options = {
        method: 'GET',
        headers: this.buildHeaders()
      };

      const response = await this.executeRequest(url, options);
      const blob = await response.blob();

      // Crear URL temporal y descargar
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);

      return { success: true };
    } catch (error) {
      console.error('Download error:', error);
      throw error;
    }
  }
}

// Exportar instancia singleton
export const fetchWrapper = new FetchWrapper();
