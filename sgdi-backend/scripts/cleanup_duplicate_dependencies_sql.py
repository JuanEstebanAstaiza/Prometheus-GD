#!/usr/bin/env python3
"""
Script para eliminar dependencias duplicadas usando SQL directo.
Usa CASCADE para eliminar automáticamente todas las referencias.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def cleanup_duplicate_dependencies():
    """Elimina dependencias duplicadas usando SQL directo con CASCADE"""
    
    # Create database connection
    engine = create_engine(settings.database_url)
    
    try:
        print("=" * 60)
        print("🧹 LIMPIEZA DE DEPENDENCIAS DUPLICADAS (SQL DIRECTO)")
        print("=" * 60)
        print()
        
        with engine.connect() as conn:
            # PASO 1: Contar dependencias duplicadas
            result = conn.execute(text("""
                SELECT id, code, name 
                FROM sgdi.dependencies 
                WHERE code LIKE '%_RESTORED_%'
                ORDER BY created_at
            """))
            
            duplicates = result.fetchall()
            
            if not duplicates:
                print("✅ No se encontraron dependencias duplicadas.")
                print("   El sistema está limpio.")
                return
            
            print(f"📋 Se encontraron {len(duplicates)} dependencias duplicadas:")
            print()
            
            for dep in duplicates:
                print(f"  • {dep.code} - {dep.name}")
            
            print()
            print(f"📊 Total a eliminar: {len(duplicates)} dependencias")
            print("   (y todas sus carpetas y archivos en cascada)")
            print()
            
            # PASO 2: Eliminar usando CASCADE
            print("🗑️  Eliminando dependencias duplicadas...")
            print()
            
            # Start transaction
            trans = conn.begin()
            
            try:
                # Eliminar archivos primero
                result = conn.execute(text("""
                    DELETE FROM sgdi.files 
                    WHERE dependency_id IN (
                        SELECT id FROM sgdi.dependencies WHERE code LIKE '%_RESTORED_%'
                    )
                """))
                files_deleted = result.rowcount
                print(f"   ✓ {files_deleted} archivos eliminados")
                
                # Eliminar carpetas
                result = conn.execute(text("""
                    DELETE FROM sgdi.folders 
                    WHERE dependency_id IN (
                        SELECT id FROM sgdi.dependencies WHERE code LIKE '%_RESTORED_%'
                    )
                """))
                folders_deleted = result.rowcount
                print(f"   ✓ {folders_deleted} carpetas eliminadas")
                
                # Eliminar dependencias
                result = conn.execute(text("""
                    DELETE FROM sgdi.dependencies 
                    WHERE code LIKE '%_RESTORED_%'
                """))
                deps_deleted = result.rowcount
                print(f"   ✓ {deps_deleted} dependencias eliminadas")
                
                # Commit transaction
                trans.commit()
                
                print()
                print("=" * 60)
                print(f"✅ LIMPIEZA COMPLETADA")
                print("=" * 60)
                print(f"   {deps_deleted} dependencias eliminadas")
                print(f"   {folders_deleted} carpetas eliminadas")
                print(f"   {files_deleted} archivos eliminados")
                print()
                
            except Exception as e:
                trans.rollback()
                raise e
            
            # PASO 3: Mostrar dependencias restantes
            result = conn.execute(text("""
                SELECT code, name, 
                    (SELECT COUNT(*) FROM sgdi.folders WHERE dependency_id = d.id) as folders_count,
                    (SELECT COUNT(*) FROM sgdi.files WHERE dependency_id = d.id) as files_count
                FROM sgdi.dependencies d
                ORDER BY created_at
            """))
            
            remaining = result.fetchall()
            print(f"📊 Dependencias restantes en el sistema: {len(remaining)}")
            print()
            
            for dep in remaining:
                print(f"  ✓ {dep.code} - {dep.name}")
                print(f"    Carpetas: {dep.folders_count}, Archivos: {dep.files_count}")
            
            print()
            print("✨ Sistema limpio y listo para usar")
        
    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        print()
        sys.exit(1)

if __name__ == "__main__":
    cleanup_duplicate_dependencies()

