-- Script para eliminar dependencias duplicadas creadas por backups
-- Ejecutar este script desde psql o pgAdmin

-- PASO 1: Ver las dependencias duplicadas antes de eliminar
SELECT id, code, name, created_at 
FROM sgdi.dependencies 
WHERE code LIKE '%_RESTORED_%'
ORDER BY created_at DESC;

-- PASO 2: Eliminar las dependencias duplicadas
-- Esto eliminará en cascada todas las carpetas, archivos y referencias asociadas

BEGIN;

-- Eliminar dependencias con sufijo _RESTORED_
DELETE FROM sgdi.dependencies 
WHERE code LIKE '%_RESTORED_%';

-- Verificar cuántas se eliminaron
SELECT 
    'Dependencias eliminadas' as operacion,
    COUNT(*) as total
FROM sgdi.dependencies 
WHERE code LIKE '%_RESTORED_%';

-- Si todo está bien, confirmar los cambios
COMMIT;

-- Si algo salió mal, deshacer con: ROLLBACK;

-- PASO 3: Verificar las dependencias restantes
SELECT id, code, name, created_at 
FROM sgdi.dependencies 
ORDER BY created_at;

