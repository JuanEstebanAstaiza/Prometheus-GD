#!/usr/bin/env python3
"""
Script para eliminar dependencias duplicadas creadas por restauraciones de backup.
Elimina todas las dependencias con sufijo '_RESTORED_' en su código.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
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
        
        for dep in duplicates:
            # Contar carpetas y archivos asociados
            folders_count = db.query(Folder).filter(Folder.dependency_id == dep.id).count()
            files_count = db.query(File).filter(File.dependency_id == dep.id).count()
            
            print(f"  • {dep.code}")
            print(f"    Nombre: {dep.name}")
            print(f"    ID: {dep.id}")
            print(f"    Carpetas: {folders_count}")
            print(f"    Archivos: {files_count}")
            print(f"    Creado: {dep.created_at}")
            print()
        
        # PASO 2: Confirmar eliminación
        print("⚠️  ADVERTENCIA: Esta operación eliminará:")
        print("   - Las dependencias duplicadas")
        print("   - Todas sus carpetas asociadas")
        print("   - Todos sus archivos asociados")
        print("   - Los archivos físicos del sistema de almacenamiento")
        print()
        
        response = input("¿Deseas continuar? (escribe 'SI' para confirmar): ")
        
        if response.strip().upper() != 'SI':
            print()
            print("❌ Operación cancelada por el usuario.")
            return
        
        print()
        print("🗑️  Eliminando dependencias duplicadas...")
        print()
        
        # PASO 3: Eliminar dependencias (en cascada eliminará carpetas y archivos)
        deleted_count = 0
        for dep in duplicates:
            print(f"   Eliminando: {dep.code}...")
            db.delete(dep)
            deleted_count += 1
        
        # Commit changes
        db.commit()
        
        print()
        print("=" * 60)
        print(f"✅ LIMPIEZA COMPLETADA")
        print("=" * 60)
        print(f"   {deleted_count} dependencias eliminadas exitosamente")
        print()
        
        # PASO 4: Mostrar dependencias restantes
        remaining = db.query(Dependency).order_by(Dependency.created_at).all()
        print(f"📊 Dependencias restantes en el sistema: {len(remaining)}")
        print()
        
        for dep in remaining:
            folders_count = db.query(Folder).filter(Folder.dependency_id == dep.id).count()
            files_count = db.query(File).filter(File.dependency_id == dep.id).count()
            print(f"  • {dep.code} - {dep.name}")
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

