#!/usr/bin/env python3
"""
Script para limpiar carpetas huérfanas y datos inconsistentes.
Elimina carpetas que no tienen dependencias válidas o referencias rotas.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def cleanup_orphan_folders():
    """Limpia carpetas huérfanas y datos inconsistentes"""
    
    # Create database connection
    engine = create_engine(settings.database_url)
    
    try:
        print("=" * 60)
        print("🧹 LIMPIEZA DE CARPETAS HUÉRFANAS")
        print("=" * 60)
        print()
        
        with engine.connect() as conn:
            # PASO 1: Identificar carpetas con dependencias inexistentes
            print("📋 Paso 1: Buscando carpetas con dependencias inválidas...")
            result = conn.execute(text("""
                SELECT f.id, f.name, f.path, f.dependency_id
                FROM sgdi.folders f
                LEFT JOIN sgdi.dependencies d ON f.dependency_id = d.id
                WHERE d.id IS NULL
            """))
            
            orphan_folders = result.fetchall()
            
            if orphan_folders:
                print(f"   ⚠️  Encontradas {len(orphan_folders)} carpetas huérfanas:")
                for folder in orphan_folders:
                    print(f"      - {folder.name} (ID: {folder.id[:8]}..., Dep: {folder.dependency_id[:8] if folder.dependency_id else 'NULL'}...)")
            else:
                print("   ✅ No se encontraron carpetas huérfanas")
            
            print()
            
            # PASO 2: Identificar carpetas con parent_id inválido
            print("📋 Paso 2: Buscando carpetas con parent_id inválido...")
            result = conn.execute(text("""
                SELECT f.id, f.name, f.path, f.parent_id
                FROM sgdi.folders f
                WHERE f.parent_id IS NOT NULL
                AND f.parent_id NOT IN (SELECT id FROM sgdi.folders)
            """))
            
            invalid_parent_folders = result.fetchall()
            
            if invalid_parent_folders:
                print(f"   ⚠️  Encontradas {len(invalid_parent_folders)} carpetas con parent_id inválido:")
                for folder in invalid_parent_folders:
                    print(f"      - {folder.name} (ID: {folder.id[:8]}..., Parent: {folder.parent_id[:8] if folder.parent_id else 'NULL'}...)")
            else:
                print("   ✅ No se encontraron carpetas con parent_id inválido")
            
            print()
            
            # PASO 3: Identificar archivos con folder_id inválido
            print("📋 Paso 3: Buscando archivos con folder_id inválido...")
            result = conn.execute(text("""
                SELECT file.id, file.original_name, file.folder_id
                FROM sgdi.files file
                WHERE file.folder_id NOT IN (SELECT id FROM sgdi.folders)
            """))
            
            orphan_files = result.fetchall()
            
            if orphan_files:
                print(f"   ⚠️  Encontrados {len(orphan_files)} archivos huérfanos:")
                for file in orphan_files[:10]:  # Mostrar solo los primeros 10
                    print(f"      - {file.original_name} (ID: {file.id[:8]}..., Folder: {file.folder_id[:8] if file.folder_id else 'NULL'}...)")
                if len(orphan_files) > 10:
                    print(f"      ... y {len(orphan_files) - 10} más")
            else:
                print("   ✅ No se encontraron archivos huérfanos")
            
            print()
            
            # Contar total de problemas
            total_issues = len(orphan_folders) + len(invalid_parent_folders) + len(orphan_files)
            
            if total_issues == 0:
                print("=" * 60)
                print("✅ SISTEMA LIMPIO")
                print("=" * 60)
                print("   No se encontraron problemas de integridad")
                return
            
            print("=" * 60)
            print(f"⚠️  TOTAL DE PROBLEMAS ENCONTRADOS: {total_issues}")
            print("=" * 60)
            print()
            print("🗑️  Procediendo a limpiar...")
            print()
            
            # Start transaction
            trans = conn.begin()
            
            try:
                # LIMPIEZA 1: Eliminar archivos huérfanos
                if orphan_files:
                    print(f"   Eliminando {len(orphan_files)} archivos huérfanos...")
                    result = conn.execute(text("""
                        DELETE FROM sgdi.files
                        WHERE folder_id NOT IN (SELECT id FROM sgdi.folders)
                    """))
                    print(f"   ✓ {result.rowcount} archivos eliminados")
                
                # LIMPIEZA 2: Eliminar carpetas con parent_id inválido
                if invalid_parent_folders:
                    print(f"   Eliminando {len(invalid_parent_folders)} carpetas con parent_id inválido...")
                    result = conn.execute(text("""
                        DELETE FROM sgdi.folders
                        WHERE parent_id IS NOT NULL
                        AND parent_id NOT IN (SELECT id FROM sgdi.folders)
                    """))
                    print(f"   ✓ {result.rowcount} carpetas eliminadas")
                
                # LIMPIEZA 3: Eliminar carpetas huérfanas (sin dependencia válida)
                if orphan_folders:
                    print(f"   Eliminando {len(orphan_folders)} carpetas huérfanas...")
                    result = conn.execute(text("""
                        DELETE FROM sgdi.folders
                        WHERE dependency_id NOT IN (SELECT id FROM sgdi.dependencies)
                    """))
                    print(f"   ✓ {result.rowcount} carpetas eliminadas")
                
                # Commit transaction
                trans.commit()
                
                print()
                print("=" * 60)
                print("✅ LIMPIEZA COMPLETADA")
                print("=" * 60)
                print(f"   Total de elementos eliminados: {total_issues}")
                print()
                
                # PASO 4: Verificar integridad final
                print("📊 Verificación final de integridad...")
                print()
                
                result = conn.execute(text("""
                    SELECT 
                        (SELECT COUNT(*) FROM sgdi.dependencies) as deps,
                        (SELECT COUNT(*) FROM sgdi.folders) as folders,
                        (SELECT COUNT(*) FROM sgdi.files) as files
                """))
                
                stats = result.fetchone()
                print(f"   ✓ Dependencias: {stats.deps}")
                print(f"   ✓ Carpetas: {stats.folders}")
                print(f"   ✓ Archivos: {stats.files}")
                print()
                print("✨ Sistema limpio y listo para usar")
                
            except Exception as e:
                trans.rollback()
                raise e
        
    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        print()
        sys.exit(1)

if __name__ == "__main__":
    cleanup_orphan_folders()

