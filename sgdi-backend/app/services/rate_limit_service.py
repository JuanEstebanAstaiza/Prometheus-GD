from datetime import datetime, timedelta
from collections import defaultdict
import threading
from typing import Dict, Tuple

from ..core.config import settings

class RateLimitService:
    """Simple in-memory rate limiting service"""

    def __init__(self):
        self._attempts: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = datetime.utcnow()

    def _cleanup_expired_attempts(self):
        """Clean up expired attempts"""
        now = datetime.utcnow()
        if (now - self._last_cleanup).seconds < self._cleanup_interval:
            return

        cutoff_time = now - timedelta(minutes=settings.lockout_minutes)

        with self._lock:
            for ip in list(self._attempts.keys()):
                self._attempts[ip] = [
                    attempt_time for attempt_time in self._attempts[ip]
                    if attempt_time > cutoff_time
                ]
                if not self._attempts[ip]:
                    del self._attempts[ip]

        self._last_cleanup = now

    def record_login_attempt(self, ip_address: str) -> Tuple[bool, int]:
        """
        Record a login attempt and check if rate limit exceeded

        Args:
            ip_address: Client IP address

        Returns:
            Tuple of (is_allowed: bool, attempts_remaining: int)
        """
        self._cleanup_expired_attempts()

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=settings.lockout_minutes)

        with self._lock:
            # Filter attempts within the time window
            recent_attempts = [
                attempt_time for attempt_time in self._attempts[ip_address]
                if attempt_time > window_start
            ]

            # Add current attempt
            recent_attempts.append(now)
            self._attempts[ip_address] = recent_attempts

            attempts_count = len(recent_attempts)
            is_allowed = attempts_count <= settings.login_attempt_limit

            if is_allowed:
                attempts_remaining = settings.login_attempt_limit - attempts_count
            else:
                attempts_remaining = 0

            return is_allowed, attempts_remaining

    def is_rate_limited(self, ip_address: str) -> bool:
        """
        Check if an IP address is currently rate limited

        Args:
            ip_address: Client IP address

        Returns:
            True if rate limited, False otherwise
        """
        self._cleanup_expired_attempts()

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=settings.lockout_minutes)

        with self._lock:
            recent_attempts = [
                attempt_time for attempt_time in self._attempts.get(ip_address, [])
                if attempt_time > window_start
            ]

            return len(recent_attempts) >= settings.login_attempt_limit

    def get_attempts_info(self, ip_address: str) -> Dict:
        """
        Get rate limiting information for an IP address

        Args:
            ip_address: Client IP address

        Returns:
            Dictionary with rate limiting info
        """
        self._cleanup_expired_attempts()

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=settings.lockout_minutes)

        with self._lock:
            recent_attempts = [
                attempt_time for attempt_time in self._attempts.get(ip_address, [])
                if attempt_time > window_start
            ]

            return {
                "attempts_count": len(recent_attempts),
                "limit": settings.login_attempt_limit,
                "window_minutes": settings.lockout_minutes,
                "is_blocked": len(recent_attempts) >= settings.login_attempt_limit,
                "next_attempt_allowed": None if len(recent_attempts) == 0 else
                    (recent_attempts[0] + timedelta(minutes=settings.lockout_minutes)).isoformat()
            }

# Global rate limit service instance
rate_limit_service = RateLimitService()
