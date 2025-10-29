# Backup del contenido correcto para app/models/__init__.py

CONTENT = '''# This file contains model imports for the SGDI application
# Import Base from database module
from ..core.database import Base

# Import all model classes
from .user import User
from .dependency import Dependency
from .folder import Folder
from .file import File
from .action_logs import ActionLog
from .backup import BackupRecord
from .refresh_tokens import RefreshToken
from .audit import Audit

# Make sure this file has content to prevent it from being emptied
__version__ = "1.0.0"
'''

if __name__ == "__main__":
    with open('app/models/__init__.py', 'w') as f:
        f.write(CONTENT)
    print("✅ Archivo __init__.py restaurado")
