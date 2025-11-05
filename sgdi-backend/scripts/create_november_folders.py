#!/usr/bin/env python3
"""Script para crear carpetas de noviembre 2025"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tasks.monthly_folders import create_monthly_folders_for_month

print("Creando carpetas mensuales para noviembre 2025...")
print()

result = create_monthly_folders_for_month(2025, 11)

print()
print(f"✅ Carpetas creadas: {len(result)}")
for folder in result:
    print(f"   - {folder['name']} en {folder['dependency_code']} ({folder['dependency_name']})")
    print(f"     Path: {folder['path']}")

