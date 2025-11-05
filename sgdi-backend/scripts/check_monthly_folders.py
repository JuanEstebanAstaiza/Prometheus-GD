#!/usr/bin/env python3
"""Script para verificar las carpetas mensuales"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.folder import Folder
from sqlalchemy import and_

db = SessionLocal()

try:
    # Buscar carpeta 2025-10 de Juridica
    folder = db.query(Folder).filter(
        and_(
            Folder.dependency_id == '9ed664d0-071f-4b66-acc2-c440b6db8dc3',
            Folder.name == '2025-10'
        )
    ).first()
    
    if folder:
        print(f"Carpeta encontrada: {folder.id}")
        print(f"  Nombre: {folder.name}")
        print(f"  Path: {folder.path}")
        print(f"  Parent ID: {folder.parent_id}")
        
        if folder.parent_id:
            parent = db.query(Folder).filter(Folder.id == folder.parent_id).first()
            if parent:
                print(f"  Parent: {parent.name}")
            else:
                print(f"  Parent: NOT FOUND (ERROR!)")
        else:
            print(f"  Parent: NULL (es raíz)")
    else:
        print("Carpeta NO encontrada")
        
finally:
    db.close()

