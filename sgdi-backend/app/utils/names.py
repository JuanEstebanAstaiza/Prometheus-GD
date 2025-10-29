import re
import unicodedata
from typing import Optional
from datetime import datetime

def normalize_filename(filename: str) -> str:
    """
    Normalize a filename by removing special characters and replacing spaces

    Args:
        filename: Original filename

    Returns:
        Normalized filename safe for filesystem
    """
    # Remove file extension temporarily
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        name, ext = name_parts
    else:
        name = filename
        ext = ""

    # Normalize unicode characters
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')

    # Replace spaces and special characters with underscores
    name = re.sub(r'[^\w\-_\.]', '_', name)

    # Remove multiple consecutive underscores
    name = re.sub(r'_+', '_', name)

    # Remove leading/trailing underscores and spaces
    name = name.strip('_ ')

    # Rejoin extension if it existed
    if ext:
        return f"{name}.{ext}"
    return name

def generate_folder_name(year: int, month: int) -> str:
    """
    Generate a folder name for monthly organization

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        Folder name in format YYYY_MM
    """
    return "03d"

def generate_backup_name(prefix: str = "backup") -> str:
    """
    Generate a timestamped backup name

    Args:
        prefix: Prefix for the backup name

    Returns:
        Backup name with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}"

def sanitize_path_component(component: str) -> str:
    """
    Sanitize a path component to be filesystem-safe

    Args:
        component: Path component to sanitize

    Returns:
        Sanitized path component
    """
    # Remove or replace dangerous characters
    component = re.sub(r'[<>:"/\\|?*]', '_', component)

    # Normalize unicode
    component = unicodedata.normalize('NFKD', component).encode('ASCII', 'ignore').decode('ASCII')

    # Replace spaces with underscores
    component = component.replace(' ', '_')

    # Remove leading/trailing dots and spaces
    component = component.strip('. ')

    # Ensure it's not empty and not a reserved name
    if not component or component.lower() in ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9']:
        component = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return component

def truncate_filename(filename: str, max_length: int = 255) -> str:
    """
    Truncate filename if it exceeds maximum length, preserving extension

    Args:
        filename: Original filename
        max_length: Maximum allowed length

    Returns:
        Truncated filename
    """
    if len(filename) <= max_length:
        return filename

    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        name, ext = name_parts
        ext = f".{ext}"
        max_name_length = max_length - len(ext)

        if max_name_length > 0:
            return f"{name[:max_name_length]}{ext}"
        else:
            # If extension is too long, truncate it too
            return filename[:max_length]
    else:
        return filename[:max_length]

def generate_unique_name(base_name: str, existing_names: list) -> str:
    """
    Generate a unique name by appending a number if the base name already exists

    Args:
        base_name: Base name to make unique
        existing_names: List of existing names to check against

    Returns:
        Unique name
    """
    if base_name not in existing_names:
        return base_name

    # Split name and extension
    name_parts = base_name.rsplit('.', 1)
    if len(name_parts) == 2:
        name, ext = name_parts
        ext = f".{ext}"
    else:
        name = base_name
        ext = ""

    counter = 1
    while True:
        candidate = f"{name}_{counter}{ext}"
        if candidate not in existing_names:
            return candidate
        counter += 1

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    size = float(size_bytes)

    while size >= 1024 and size_index < len(size_names) - 1:
        size /= 1024
        size_index += 1

    if size_index == 0:
        return ".0f"
    else:
        return ".1f"
