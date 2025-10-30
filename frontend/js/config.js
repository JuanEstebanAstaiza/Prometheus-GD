/**
 * SGDI - Configuration
 * Variables de configuración del frontend
 * 
 * IMPORTANTE: Editar estas variables antes de desplegar en producción
 */

export const config = {
  // URL del backend API (conexión directa, CORS habilitado en backend)
  FRONTEND_API_URL: 'http://localhost:8000',
  
  // Tamaño máximo de archivos (en MB)
  MAX_UPLOAD_SIZE_MB: 50,
  
  // MIME types permitidos para upload
  ALLOWED_MIME_TYPES: [
    'application/pdf',
    'text/csv',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png',
    'image/jpg'
  ],
  
  // Tiempo de expiración del token en minutos (debe coincidir con el backend)
  ACCESS_TOKEN_EXPIRE_MINUTES: 30,
  
  // Tiempo de expiración del refresh token en días
  REFRESH_TOKEN_EXPIRE_DAYS: 7,
  
  // Número de reintentos para peticiones fallidas
  MAX_RETRIES: 3,
  
  // Tiempo de espera entre reintentos (ms)
  RETRY_DELAY: 1000,
  
  // Timeout para peticiones (ms)
  REQUEST_TIMEOUT: 30000,
  
  // Paginación por defecto
  DEFAULT_PAGE_SIZE: 50,
  
  // Formato de fecha
  DATE_FORMAT: 'es-ES'
};

// Validar configuración
if (!config.FRONTEND_API_URL) {
  console.error('FRONTEND_API_URL no está configurada');
}

// Hacer disponible globalmente para debugging
if (typeof window !== 'undefined') {
  window.SGDI_CONFIG = config;
}

