import re
from typing import Optional, List
from pathlib import Path
import mimetypes
from email_validator import validate_email, EmailNotValidError

from ..core.config import settings

def validate_email_address(email: str) -> bool:
    """
    Validate email address format

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

def validate_username(username: str) -> bool:
    """
    Validate username format (alphanumeric, underscore, dash, 3-50 chars)

    Args:
        username: Username to validate

    Returns:
        True if valid, False otherwise
    """
    if not username or len(username) < 3 or len(username) > 50:
        return False

    # Allow alphanumeric, underscore, and dash
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, username))

def validate_password_strength(password: str) -> dict:
    """
    Validate password strength and return requirements check

    Args:
        password: Password to validate

    Returns:
        Dictionary with validation results and requirements
    """
    requirements = {
        "length": len(password) >= 8,
        "uppercase": bool(re.search(r'[A-Z]', password)),
        "lowercase": bool(re.search(r'[a-z]', password)),
        "digit": bool(re.search(r'[0-9]', password)),
        "special": bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    }

    requirements["overall"] = all(requirements.values())

    return requirements

def validate_file_mime_type(filename: str, file_content: Optional[bytes] = None) -> bool:
    """
    Validate file MIME type against allowed types

    Args:
        filename: Filename to check
        file_content: Optional file content for deeper validation

    Returns:
        True if MIME type is allowed, False otherwise
    """
    # Get MIME type from filename
    mime_type, _ = mimetypes.guess_type(filename)

    if not mime_type:
        return False

    # Check against allowed MIME types
    allowed_types = settings.allowed_mime_types_list
    return mime_type in allowed_types

def validate_file_size(file_size: int) -> bool:
    """
    Validate file size against maximum allowed size

    Args:
        file_size: File size in bytes

    Returns:
        True if size is within limits, False otherwise
    """
    return file_size <= settings.max_upload_size_bytes

def validate_path_safety(path: str) -> bool:
    """
    Validate that a path doesn't contain dangerous components

    Args:
        path: Path to validate

    Returns:
        True if path is safe, False otherwise
    """
    # Check for dangerous patterns
    dangerous_patterns = [
        r'\.\.',  # Parent directory traversal
        r'^/',    # Absolute paths
        r'^\\',   # Windows absolute paths
        r'[<>:"|?*]',  # Invalid filesystem characters
    ]

    path_obj = Path(path)

    # Check for dangerous patterns
    for pattern in dangerous_patterns:
        if re.search(pattern, path):
            return False

    # Check for reserved names on Windows
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    for part in path_obj.parts:
        if part.upper() in reserved_names:
            return False

    return True

def validate_dependency_code(code: str) -> bool:
    """
    Validate dependency code format

    Args:
        code: Dependency code to validate

    Returns:
        True if valid, False otherwise
    """
    if not code or len(code) < 2 or len(code) > 20:
        return False

    # Allow alphanumeric and underscores
    pattern = r'^[A-Z0-9_]+$'
    return bool(re.match(pattern, code.upper()))

def validate_document_number(doc_number: str) -> bool:
    """
    Validate document number format

    Args:
        doc_number: Document number to validate

    Returns:
        True if valid format, False otherwise
    """
    if not doc_number or len(doc_number) > 100:
        return False

    # Allow alphanumeric, dashes, slashes, dots, spaces
    pattern = r'^[A-Za-z0-9\-/\.\s]+$'
    return bool(re.match(pattern, doc_number))

def sanitize_string(input_str: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a string by removing potentially dangerous characters

    Args:
        input_str: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not input_str:
        return ""

    # Remove null bytes and other dangerous characters
    sanitized = input_str.replace('\x00', '').replace('\r', '').replace('\n', ' ')

    # Trim whitespace
    sanitized = sanitized.strip()

    # Apply length limit if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized

def validate_cron_expression(cron_expr: str) -> bool:
    """
    Validate cron expression format (5 fields)

    Args:
        cron_expr: Cron expression to validate

    Returns:
        True if valid, False otherwise
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        return False

    # Basic validation for each field (could be more sophisticated)
    for part in parts:
        if not re.match(r'^[\d\*\-\,\/]+$', part):
            return False

    return True
