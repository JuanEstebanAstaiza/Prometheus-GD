from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import secrets
import hashlib
import hmac
from typing import Optional

from ..core.config import settings
from ..models.refresh_tokens import RefreshToken
from ..models.user import User

class TokenService:
    """Service for managing refresh tokens"""

    @staticmethod
    def generate_refresh_token() -> str:
        """Generate a secure random refresh token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Hash refresh token using HMAC-SHA256"""
        secret = settings.jwt_secret_key.encode()
        return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def store_refresh_token(
        db: Session,
        user: User,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> RefreshToken:
        """
        Store a hashed refresh token in the database

        Args:
            db: Database session
            user: User object
            refresh_token: Plain refresh token string
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created RefreshToken object
        """
        token_hash = TokenService.hash_refresh_token(refresh_token)
        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        db.add(refresh_token_obj)
        db.commit()
        db.refresh(refresh_token_obj)

        return refresh_token_obj

    @staticmethod
    def validate_refresh_token(db: Session, refresh_token: str) -> Optional[RefreshToken]:
        """
        Validate a refresh token and return the token object if valid

        Args:
            db: Database session
            refresh_token: Plain refresh token string

        Returns:
            RefreshToken object if valid, None otherwise
        """
        token_hash = TokenService.hash_refresh_token(refresh_token)

        token_obj = db.query(RefreshToken).filter(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False
            )
        ).first()

        if token_obj and token_obj.is_valid:
            return token_obj

        return None

    @staticmethod
    def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
        """
        Revoke a refresh token

        Args:
            db: Database session
            refresh_token: Plain refresh token string

        Returns:
            True if token was revoked, False if not found
        """
        token_hash = TokenService.hash_refresh_token(refresh_token)

        token_obj = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash
        ).first()

        if token_obj:
            token_obj.revoked = True
            db.commit()
            return True

        return False

    @staticmethod
    def revoke_all_user_tokens(db: Session, user_id: str) -> int:
        """
        Revoke all refresh tokens for a user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of tokens revoked
        """
        tokens = db.query(RefreshToken).filter(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False
            )
        ).all()

        revoked_count = 0
        for token in tokens:
            token.revoked = True
            revoked_count += 1

        if revoked_count > 0:
            db.commit()

        return revoked_count

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """
        Clean up expired tokens from database

        Args:
            db: Database session

        Returns:
            Number of tokens cleaned up
        """
        expired_tokens = db.query(RefreshToken).filter(
            and_(
                RefreshToken.expires_at < datetime.utcnow(),
                RefreshToken.revoked == False
            )
        ).all()

        cleaned_count = 0
        for token in expired_tokens:
            token.revoked = True
            cleaned_count += 1

        if cleaned_count > 0:
            db.commit()

        return cleaned_count

# Global token service instance
token_service = TokenService()
