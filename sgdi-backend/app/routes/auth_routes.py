from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any

from ..core.database import get_db
from ..core.security import verify_password, create_access_token, create_refresh_token, verify_token
from ..core.config import settings
from ..core.auth import get_current_user
from ..models.user import User
from ..schemas.auth import Token, TokenData, UserLogin, UserResponse, RefreshTokenRequest, ErrorResponse, RateLimitResponse
from ..services.token_service import token_service
from ..services.rate_limit_service import rate_limit_service
from ..services.audit_service import audit_service

router = APIRouter()

@router.post("/login", response_model=Token, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    429: {"model": RateLimitResponse}
})
async def login(
    request: Request,
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """
    Authenticate user and return JWT access token + refresh token

    Request body: { "email": "user@example.com", "password": "password" }
    """
    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "")

    # Check rate limiting
    is_allowed, attempts_remaining = rate_limit_service.record_login_attempt(client_ip)
    if not is_allowed:
        # Log failed login attempt due to rate limiting
        audit_service.log_action(
            db=db,
            user=None,  # System action, no user yet
            action_type="LOGIN_RATE_LIMITED",
            target_type="SYSTEM",
            target_id="rate_limit",
            details={
                "ip_address": client_ip,
                "user_agent": user_agent,
                "email_attempted": user_credentials.email
            },
            ip_address=client_ip
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(settings.lockout_minutes * 60)}
        )

    # Find user by email
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user or not verify_password(user_credentials.password, user.password_hash):
        # Log failed login attempt
        audit_service.log_action(
            db=db,
            user=user if user else None,
            action_type="LOGIN_FAILURE",
            target_type="USER",
            target_id=user.id if user else "unknown",
            details={
                "reason": "invalid_credentials",
                "ip_address": client_ip,
                "user_agent": user_agent,
                "email_attempted": user_credentials.email
            },
            ip_address=client_ip
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        # Log failed login attempt for inactive user
        audit_service.log_action(
            db=db,
            user=user,
            action_type="LOGIN_FAILURE",
            target_type="USER",
            target_id=user.id,
            details={
                "reason": "user_inactive",
                "ip_address": client_ip,
                "user_agent": user_agent
            },
            ip_address=client_ip
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user.id,
            "role": user.role,
            "dependency_id": user.dependency_id
        },
        expires_delta=access_token_expires
    )

    # Generate and store refresh token
    refresh_token_plain = token_service.generate_refresh_token()
    token_service.store_refresh_token(
        db=db,
        user=user,
        refresh_token=refresh_token_plain,
        ip_address=client_ip,
        user_agent=user_agent
    )

    # Log successful login
    audit_service.log_action(
        db=db,
        user=user,
        action_type="LOGIN",
        target_type="USER",
        target_id=user.id,
        details={
            "ip_address": client_ip,
            "user_agent": user_agent
        },
        ip_address=client_ip
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_plain,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "dependency_id": user.dependency_id
        }
    }

@router.post("/refresh", response_model=Token, responses={
    401: {"model": ErrorResponse}
})
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token

    Request body: { "refresh_token": "refresh_token_string" }
    """
    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "")

    # Validate refresh token
    refresh_token_obj = token_service.validate_refresh_token(db, refresh_data.refresh_token)
    if not refresh_token_obj:
        # Log invalid refresh token attempt
        audit_service.log_action(
            db=db,
            user=None,
            action_type="REFRESH_FAILURE",
            target_type="TOKEN",
            target_id="unknown",
            details={
                "reason": "invalid_token",
                "ip_address": client_ip,
                "user_agent": user_agent
            },
            ip_address=client_ip
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user associated with token
    user = db.query(User).filter(User.id == refresh_token_obj.user_id).first()
    if not user or not user.is_active:
        # Revoke the token if user is not found or inactive
        refresh_token_obj.revoked = True
        db.commit()

        audit_service.log_action(
            db=db,
            user=None,
            action_type="REFRESH_FAILURE",
            target_type="USER",
            target_id=refresh_token_obj.user_id,
            details={
                "reason": "user_inactive_or_deleted",
                "ip_address": client_ip,
                "user_agent": user_agent
            },
            ip_address=client_ip
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Revoke old refresh token (token rotation)
    refresh_token_obj.revoked = True
    db.commit()

    # Create new access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user.id,
            "role": user.role,
            "dependency_id": user.dependency_id
        },
        expires_delta=access_token_expires
    )

    # Generate new refresh token
    new_refresh_token_plain = token_service.generate_refresh_token()
    token_service.store_refresh_token(
        db=db,
        user=user,
        refresh_token=new_refresh_token_plain,
        ip_address=client_ip,
        user_agent=user_agent
    )

    # Log successful token refresh
    audit_service.log_action(
        db=db,
        user=user,
        action_type="TOKEN_REFRESH",
        target_type="USER",
        target_id=user.id,
        details={
            "ip_address": client_ip,
            "user_agent": user_agent
        },
        ip_address=client_ip
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token_plain,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "dependency_id": user.dependency_id
        }
    }

@router.post("/logout", responses={
    200: {"model": dict},
    401: {"model": ErrorResponse}
})
async def logout(
    request: Request,
    refresh_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Logout user by revoking refresh token

    Request body: { "refresh_token": "refresh_token_string" }
    """
    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "")

    # Revoke the refresh token
    revoked = token_service.revoke_refresh_token(db, refresh_data.refresh_token)

    if revoked:
        # Log successful logout
        audit_service.log_action(
            db=db,
            user=current_user,
            action_type="LOGOUT",
            target_type="USER",
            target_id=current_user.id,
            details={
                "ip_address": client_ip,
                "user_agent": user_agent
            },
            ip_address=client_ip
        )

        return {"message": "Successfully logged out"}

    # Token might already be invalid/expired, but we still consider it a successful logout
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="LOGOUT",
        target_type="USER",
        target_id=current_user.id,
        details={
            "ip_address": client_ip,
            "user_agent": user_agent,
            "token_already_invalid": True
        },
        ip_address=client_ip
    )

    return {"message": "Successfully logged out"}

@router.post("/verify", responses={
    200: {"model": dict},
    401: {"model": ErrorResponse}
})
async def verify_token_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Verify current access token and return user information
    """
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "dependency_id": current_user.dependency_id,
            "is_active": current_user.is_active
        }
    }
