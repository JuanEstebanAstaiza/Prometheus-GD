#!/usr/bin/env python3
"""
Script para crear el usuario del sistema si no existe.
Este usuario se usa para operaciones automatizadas como la creación de carpetas mensuales.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"
SYSTEM_USER_EMAIL = "system@sgdi.internal"

db = SessionLocal()

try:
    # Verificar si el usuario del sistema ya existe
    system_user = db.query(User).filter(User.id == SYSTEM_USER_ID).first()
    
    if system_user:
        print(f"✅ Usuario del sistema ya existe:")
        print(f"   ID: {system_user.id}")
        print(f"   Email: {system_user.email}")
        print(f"   Role: {system_user.role}")
    else:
        print("🔧 Usuario del sistema no encontrado. Creando...")
        
        # Crear usuario del sistema
        system_user = User(
            id=SYSTEM_USER_ID,
            email=SYSTEM_USER_EMAIL,
            password_hash=get_password_hash("system-user-no-login"),
            full_name="Sistema SGDI",
            role="SUPER_ADMIN",
            is_active=True,
            dependency_id=None  # Sistema no pertenece a ninguna dependencia
        )
        
        db.add(system_user)
        db.commit()
        
        print(f"✅ Usuario del sistema creado exitosamente:")
        print(f"   ID: {SYSTEM_USER_ID}")
        print(f"   Email: {SYSTEM_USER_EMAIL}")
        print(f"   Role: SUPER_ADMIN")
        print()
        print("📝 Nota: Este usuario NO puede iniciar sesión. Se usa solo para operaciones automatizadas.")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()

