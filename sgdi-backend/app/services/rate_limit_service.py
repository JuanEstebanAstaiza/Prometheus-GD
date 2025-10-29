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

    def _cleanup_expired_attempts(self, settings_override=None):
        """Clean up expired attempts"""
        current_settings = settings_override or getattr(self, '_test_settings', None) or settings

        now = datetime.utcnow()
        if (now - self._last_cleanup).seconds < self._cleanup_interval:
            return

        cutoff_time = now - timedelta(minutes=getattr(current_settings, 'lockout_minutes', 15))

        with self._lock:
            for ip in list(self._attempts.keys()):
                self._attempts[ip] = [
                    attempt_time for attempt_time in self._attempts[ip]
                    if attempt_time > cutoff_time
                ]
                if not self._attempts[ip]:
                    del self._attempts[ip]

        self._last_cleanup = now

    def record_login_attempt(self, ip_address: str, settings_override=None) -> Tuple[bool, int]:
        """
        Record a login attempt and check if rate limit exceeded

        Args:
            ip_address: Client IP address
            settings_override: Optional settings to use instead of global settings

        Returns:
            Tuple of (is_allowed: bool, attempts_remaining: int)
        """
        # Use provided settings, test settings, or fall back to global settings
        current_settings = settings_override or getattr(self, '_test_settings', None) or settings

        # Check if rate limiting is disabled
        if getattr(current_settings, 'disable_rate_limiting', False):
            return True, getattr(current_settings, 'login_attempt_limit', 5)

        self._cleanup_expired_attempts(settings_override=current_settings)

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=getattr(current_settings, 'lockout_minutes', 15))

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
            login_attempt_limit = getattr(current_settings, 'login_attempt_limit', 5)
            is_allowed = attempts_count <= login_attempt_limit

            if is_allowed:
                attempts_remaining = login_attempt_limit - attempts_count
            else:
                attempts_remaining = 0

            return is_allowed, attempts_remaining

    def is_rate_limited(self, ip_address: str, settings_override=None) -> bool:
        """
        Check if an IP address is currently rate limited

        Args:
            ip_address: Client IP address
            settings_override: Optional settings to use instead of global settings

        Returns:
            True if rate limited, False otherwise
        """
        current_settings = settings_override or getattr(self, '_test_settings', None) or settings
        self._cleanup_expired_attempts(settings_override=current_settings)

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=getattr(current_settings, 'lockout_minutes', 15))

        with self._lock:
            recent_attempts = [
                attempt_time for attempt_time in self._attempts.get(ip_address, [])
                if attempt_time > window_start
            ]

            return len(recent_attempts) >= getattr(current_settings, 'login_attempt_limit', 5)

    def get_attempts_info(self, ip_address: str, settings_override=None) -> Dict:
        """
        Get rate limiting information for an IP address

        Args:
            ip_address: Client IP address
            settings_override: Optional settings to use instead of global settings

        Returns:
            Dictionary with rate limiting info
        """
        current_settings = settings_override or getattr(self, '_test_settings', None) or settings
        self._cleanup_expired_attempts(settings_override=current_settings)

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=getattr(current_settings, 'lockout_minutes', 15))

        with self._lock:
            recent_attempts = [
                attempt_time for attempt_time in self._attempts.get(ip_address, [])
                if attempt_time > window_start
            ]

            login_attempt_limit = getattr(current_settings, 'login_attempt_limit', 5)
            lockout_minutes = getattr(current_settings, 'lockout_minutes', 15)

            return {
                "attempts_count": len(recent_attempts),
                "limit": login_attempt_limit,
                "window_minutes": lockout_minutes,
                "is_blocked": len(recent_attempts) >= login_attempt_limit,
                "next_attempt_allowed": None if len(recent_attempts) == 0 else
                    (recent_attempts[0] + timedelta(minutes=lockout_minutes)).isoformat()
            }

# Global rate limit service instance
rate_limit_service = RateLimitService()

# Function to configure the service with test settings (for testing only)
def configure_rate_limit_service_for_testing(settings_obj):
    """Configure the rate limit service with specific settings (for testing)"""
    global rate_limit_service
    # Create a new instance with the test settings
    rate_limit_service = RateLimitService()
    # Store the settings for later use in methods
    rate_limit_service._test_settings = settings_obj
