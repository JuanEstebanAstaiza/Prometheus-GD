#!/usr/bin/env python3
"""
Script para eliminar una carpeta de forma segura usando SQL directo.
Elimina archivos y subcarpetas en el orden correcto para evitar violaciones de FK.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def delete_folder_safe(folder_id: str):
    """Elimina una carpeta y todo su contenido de forma segura"""
    
    # Create database connection
    engine = create_engine(settings.database_url)
    
    try:
        print("=" * 60)
        print(f"🗑️  ELIMINANDO CARPETA: {folder_id}")
        print("=" * 60)
        print()
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # 1. Obtener info de la carpeta
                result = conn.execute(text("""
                    SELECT name, path FROM sgdi.folders WHERE id = :folder_id
                """), {"folder_id": folder_id})
                
                folder = result.fetchone()
                if not folder:
                    print(f"❌ Carpeta {folder_id} no encontrada")
                    return
                
                print(f"📁 Carpeta: {folder.name}")
                print(f"📍 Ruta: {folder.path}")
                print()
                
                # 2. Eliminar archivos deprecados que referencien a archivos en esta carpeta
                # (pueden estar en cualquier carpeta, incluyendo "deprecados")
                result = conn.execute(text("""
                    DELETE FROM sgdi.files 
                    WHERE main_file_id IN (
                        SELECT id FROM sgdi.files
                        WHERE folder_id IN (
                            SELECT id FROM sgdi.folders 
                            WHERE path LIKE :path || '%'
                            OR id = :folder_id
                        )
                    )
                """), {"folder_id": folder_id, "path": folder.path})
                deprecated_count = result.rowcount
                print(f"   ✓ {deprecated_count} archivos deprecados eliminados (desde cualquier ubicación)")
                
                # 3. Eliminar archivos principales
                result = conn.execute(text("""
                    DELETE FROM sgdi.files 
                    WHERE folder_id IN (
                        SELECT id FROM sgdi.folders 
                        WHERE path LIKE :path || '%'
                        OR id = :folder_id
                    )
                    AND main_file_id IS NULL
                """), {"folder_id": folder_id, "path": folder.path})
                files_count = result.rowcount
                print(f"   ✓ {files_count} archivos principales eliminados")
                
                # 4. Eliminar subcarpetas (ordenadas por profundidad inversa)
                result = conn.execute(text("""
                    DELETE FROM sgdi.folders 
                    WHERE path LIKE :path || '%'
                    AND id != :folder_id
                """), {"folder_id": folder_id, "path": folder.path})
                subfolders_count = result.rowcount
                print(f"   ✓ {subfolders_count} subcarpetas eliminadas")
                
                # 5. Eliminar la carpeta principal
                result = conn.execute(text("""
                    DELETE FROM sgdi.folders 
                    WHERE id = :folder_id
                """), {"folder_id": folder_id})
                print(f"   ✓ Carpeta principal eliminada")
                
                # Commit transaction
                trans.commit()
                
                print()
                print("=" * 60)
                print("✅ CARPETA ELIMINADA EXITOSAMENTE")
                print("=" * 60)
                print(f"   Archivos deprecados: {deprecated_count}")
                print(f"   Archivos principales: {files_count}")
                print(f"   Subcarpetas: {subfolders_count}")
                print()
                
            except Exception as e:
                trans.rollback()
                raise e
        
    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        print()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python delete_folder_safe.py <folder_id>")
        sys.exit(1)
    
    folder_id = sys.argv[1]
    delete_folder_safe(folder_id)

