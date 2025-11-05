#!/usr/bin/env python3
"""
Script para eliminar dependencias duplicadas creadas por restauraciones de backup.
Elimina todas las dependencias con sufijo '_RESTORED_' en su código.
VERSIÓN AUTOMÁTICA - No pide confirmación
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.dependency import Dependency
from app.models.folder import Folder
from app.models.file import File

def cleanup_duplicate_dependencies():
    """Elimina dependencias duplicadas con sufijo _RESTORED_"""
    
    # Create database connection
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("🧹 LIMPIEZA DE DEPENDENCIAS DUPLICADAS")
        print("=" * 60)
        print()
        
        # PASO 1: Mostrar dependencias que se van a eliminar
        duplicates = db.query(Dependency).filter(
            Dependency.code.like('%_RESTORED_%')
        ).all()
        
        if not duplicates:
            print("✅ No se encontraron dependencias duplicadas.")
            print("   El sistema está limpio.")
            return
        
        print(f"📋 Se encontraron {len(duplicates)} dependencias duplicadas:")
        print()
        
        total_folders = 0
        total_files = 0
        
        for dep in duplicates:
            # Contar carpetas y archivos asociados
            folders_count = db.query(Folder).filter(Folder.dependency_id == dep.id).count()
            files_count = db.query(File).filter(File.dependency_id == dep.id).count()
            
            total_folders += folders_count
            total_files += files_count
            
            print(f"  • {dep.code}")
            print(f"    Nombre: {dep.name}")
            print(f"    Carpetas: {folders_count}, Archivos: {files_count}")
        
        print()
        print(f"📊 Total a eliminar:")
        print(f"   - {len(duplicates)} dependencias")
        print(f"   - {total_folders} carpetas")
        print(f"   - {total_files} archivos")
        print()
        
        # PASO 2: Eliminar archivos, carpetas y dependencias en orden correcto
        print("🗑️  Eliminando dependencias duplicadas...")
        print()
        
        deleted_deps = 0
        deleted_folders = 0
        deleted_files = 0
        
        # Disable autoflush to avoid premature constraint checks
        with db.no_autoflush:
            for dep in duplicates:
                print(f"   Procesando: {dep.code}...")
                
                # 2.1: Eliminar archivos de esta dependencia
                files = db.query(File).filter(File.dependency_id == dep.id).all()
                for file in files:
                    db.delete(file)
                    deleted_files += 1
                print(f"      - {len(files)} archivos eliminados")
                
                # 2.2: Eliminar carpetas de esta dependencia (ordenadas por profundidad inversa)
                folders = db.query(Folder).filter(Folder.dependency_id == dep.id).order_by(
                    Folder.path.desc()  # Eliminar carpetas más profundas primero
                ).all()
                for folder in folders:
                    db.delete(folder)
                    deleted_folders += 1
                print(f"      - {len(folders)} carpetas eliminadas")
                
                # 2.3: Eliminar la dependencia
                db.delete(dep)
                deleted_deps += 1
                print(f"      ✓ Dependencia eliminada")
                print()
        
        # Commit all changes at once
        print("   Guardando cambios en la base de datos...")
        db.commit()
        
        print()
        print("=" * 60)
        print(f"✅ LIMPIEZA COMPLETADA")
        print("=" * 60)
        print(f"   {deleted_deps} dependencias eliminadas")
        print(f"   {deleted_folders} carpetas eliminadas")
        print(f"   {deleted_files} archivos eliminados")
        print()
        
        # PASO 3: Mostrar dependencias restantes
        remaining = db.query(Dependency).order_by(Dependency.created_at).all()
        print(f"📊 Dependencias restantes en el sistema: {len(remaining)}")
        print()
        
        for dep in remaining:
            folders_count = db.query(Folder).filter(Folder.dependency_id == dep.id).count()
            files_count = db.query(File).filter(File.dependency_id == dep.id).count()
            print(f"  ✓ {dep.code} - {dep.name}")
            print(f"    Carpetas: {folders_count}, Archivos: {files_count}")
        
        print()
        print("✨ Sistema limpio y listo para usar")
        
    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        print()
        print("Revertiendo cambios...")
        db.rollback()
        print("Cambios revertidos. No se eliminó nada.")
        sys.exit(1)
        
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_duplicate_dependencies()

