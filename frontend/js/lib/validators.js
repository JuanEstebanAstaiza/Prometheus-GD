/**
 * SGDI - Validators
 * Funciones de validación de formularios
 */

export const validators = {
  /**
   * Valida que un campo no esté vacío
   */
  required(value, fieldName = 'Este campo') {
    if (!value || value.toString().trim() === '') {
      return `${fieldName} es requerido`;
    }
    return null;
  },

  /**
   * Valida formato de email
   */
  email(value) {
    if (!value) return null;
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      return 'Email inválido';
    }
    return null;
  },

  /**
   * Valida longitud mínima
   */
  minLength(value, min, fieldName = 'Este campo') {
    if (!value) return null;
    
    if (value.length < min) {
      return `${fieldName} debe tener al menos ${min} caracteres`;
    }
    return null;
  },

  /**
   * Valida longitud máxima
   */
  maxLength(value, max, fieldName = 'Este campo') {
    if (!value) return null;
    
    if (value.length > max) {
      return `${fieldName} no puede tener más de ${max} caracteres`;
    }
    return null;
  },

  /**
   * Valida contraseña fuerte
   */
  password(value) {
    if (!value) return null;
    
    if (value.length < 8) {
      return 'La contraseña debe tener al menos 8 caracteres';
    }
    
    if (!/[A-Z]/.test(value)) {
      return 'La contraseña debe contener al menos una mayúscula';
    }
    
    if (!/[a-z]/.test(value)) {
      return 'La contraseña debe contener al menos una minúscula';
    }
    
    if (!/[0-9]/.test(value)) {
      return 'La contraseña debe contener al menos un número';
    }
    
    return null;
  },

  /**
   * Valida que dos valores coincidan
   */
  matches(value, otherValue, fieldName = 'Los campos') {
    if (value !== otherValue) {
      return `${fieldName} no coinciden`;
    }
    return null;
  },

  /**
   * Valida número
   */
  number(value, fieldName = 'Este campo') {
    if (!value) return null;
    
    if (isNaN(value)) {
      return `${fieldName} debe ser un número`;
    }
    return null;
  },

  /**
   * Valida número positivo
   */
  positive(value, fieldName = 'Este campo') {
    const numError = validators.number(value, fieldName);
    if (numError) return numError;
    
    if (parseFloat(value) <= 0) {
      return `${fieldName} debe ser un número positivo`;
    }
    return null;
  },

  /**
   * Valida rango numérico
   */
  range(value, min, max, fieldName = 'Este campo') {
    const numError = validators.number(value, fieldName);
    if (numError) return numError;
    
    const num = parseFloat(value);
    if (num < min || num > max) {
      return `${fieldName} debe estar entre ${min} y ${max}`;
    }
    return null;
  },

  /**
   * Valida que el valor esté en una lista
   */
  oneOf(value, options, fieldName = 'Este campo') {
    if (!value) return null;
    
    if (!options.includes(value)) {
      return `${fieldName} debe ser uno de: ${options.join(', ')}`;
    }
    return null;
  },

  /**
   * Valida formato de fecha (YYYY-MM-DD)
   */
  date(value, fieldName = 'La fecha') {
    if (!value) return null;
    
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(value)) {
      return `${fieldName} debe estar en formato YYYY-MM-DD`;
    }
    
    const date = new Date(value);
    if (isNaN(date.getTime())) {
      return `${fieldName} no es válida`;
    }
    
    return null;
  },

  /**
   * Valida URL
   */
  url(value, fieldName = 'La URL') {
    if (!value) return null;
    
    try {
      new URL(value);
      return null;
    } catch {
      return `${fieldName} no es válida`;
    }
  },

  /**
   * Valida extensión de archivo
   */
  fileExtension(filename, allowedExtensions) {
    if (!filename) return null;
    
    const ext = filename.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      return `Solo se permiten archivos: ${allowedExtensions.join(', ')}`;
    }
    return null;
  },

  /**
   * Valida tamaño de archivo
   */
  fileSize(file, maxSizeMB) {
    if (!file) return null;
    
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > maxSizeMB) {
      return `El archivo no puede ser mayor a ${maxSizeMB}MB`;
    }
    return null;
  },

  /**
   * Valida MIME type
   */
  fileMimeType(file, allowedTypes) {
    if (!file) return null;
    
    if (!allowedTypes.includes(file.type)) {
      return 'Tipo de archivo no permitido';
    }
    return null;
  }
};

/**
 * Genera un UUID v4
 */
export function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

