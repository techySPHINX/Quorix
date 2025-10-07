"""
Advanced Security Middleware
Provides comprehensive security features including CORS, CSP, security headers, and threat detection.
"""
import re
import time
import logging
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urlparse
import hashlib
import secrets

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware

from app.core.cache import cache
from app.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityHeaders:
    """Security headers configuration and management"""

    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        """Get default security headers"""
        return {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",

            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",

            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Permissions policy
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",

            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),

            # HSTS (if HTTPS)
            # "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        }


class ThreatDetector:
    """Detect and mitigate security threats"""

    def __init__(self):
        self.suspicious_patterns = [
            # SQL injection patterns
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+.*\s+(from|into|table)",
            r"(?i)'.*;\s*(drop|delete|update|insert)",

            # XSS patterns
            r"(?i)<script[^>]*>.*?</script>",
            r"(?i)javascript:",
            r"(?i)on(load|error|click|mouseover)\s*=",

            # Path traversal
            r"\.\./",
            r"\.\.\\",

            # Command injection
            r"[;&|`]",
            r"\$\([^)]*\)",

            # LDAP injection
            r"(?i)\(\|\(",

            # NoSQL injection
            r"(?i)\$where",
            r"(?i)\$ne",
        ]

        self.compiled_patterns = [re.compile(pattern) for pattern in self.suspicious_patterns]

    def is_suspicious_request(self, request: Request) -> tuple[bool, str]:
        """Check if request contains suspicious patterns"""
        # Check URL path
        if self._contains_suspicious_pattern(request.url.path):
            return True, "Suspicious pattern in URL path"

        # Check query parameters
        for key, value in request.query_params.items():
            if self._contains_suspicious_pattern(value):
                return True, f"Suspicious pattern in query parameter: {key}"

        # Check headers (but be careful not to block legitimate content)
        for header_name, header_value in request.headers.items():
            if header_name.lower() in ['user-agent', 'referer', 'cookie']:
                if self._contains_suspicious_pattern(header_value):
                    return True, f"Suspicious pattern in header: {header_name}"

        return False, ""

    def _contains_suspicious_pattern(self, text: str) -> bool:
        """Check if text contains any suspicious patterns"""
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True
        return False


class IPBlocklist:
    """Manage IP address blocklist"""

    def __init__(self):
        self.blocked_ips: Set[str] = set()
        self.blocked_subnets: List[str] = []
        self._load_blocklist()

    def _load_blocklist(self):
        """Load IP blocklist from configuration"""
        # Load from configuration or database
        blocked_ips = getattr(settings, 'SECURITY_BLOCKED_IPS', [])
        self.blocked_ips.update(blocked_ips)

        # Load blocked subnets
        self.blocked_subnets = getattr(settings, 'SECURITY_BLOCKED_SUBNETS', [])

    def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        # Check exact IP match
        if ip in self.blocked_ips:
            return True

        # Check subnet matches (simplified implementation)
        for subnet in self.blocked_subnets:
            if ip.startswith(subnet.split('/')[0]):
                return True

        return False

    async def add_ip(self, ip: str, duration: int = 3600):
        """Add IP to temporary blocklist"""
        self.blocked_ips.add(ip)

        # Store in cache for distributed systems
        await cache.set(f"blocked_ip:{ip}", True, duration)

    def remove_ip(self, ip: str):
        """Remove IP from blocklist"""
        self.blocked_ips.discard(ip)


class RequestValidator:
    """Validate and sanitize HTTP requests"""

    @staticmethod
    def validate_content_length(request: Request, max_size: Optional[int] = None) -> bool:
        """Validate request content length"""
        max_size = max_size or settings.scalability.MAX_REQUEST_SIZE
        content_length = request.headers.get('content-length')

        if content_length:
            try:
                size = int(content_length)
                return size <= max_size
            except ValueError:
                return False

        return True

    @staticmethod
    def validate_content_type(request: Request, allowed_types: Optional[List[str]] = None) -> bool:
        """Validate request content type"""
        if not allowed_types:
            allowed_types = [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data',
                'text/plain'
            ]

        content_type = request.headers.get('content-type', '').split(';')[0].strip()

        if request.method in ['POST', 'PUT', 'PATCH'] and content_type:
            return content_type.lower() in [ct.lower() for ct in allowed_types]

        return True

    @staticmethod
    def validate_headers(request: Request) -> bool:
        """Validate request headers"""
        # Check for excessively long headers
        for name, value in request.headers.items():
            if len(name) > 256 or len(value) > 4096:
                return False

        # Check for suspicious header patterns
        suspicious_headers = ['x-real-ip', 'x-forwarded-for', 'x-originating-ip']
        for header in suspicious_headers:
            if header in request.headers:
                # Basic validation for IP headers
                ip_value = request.headers[header]
                if not re.match(r'^[\d.,\s:]+$', ip_value):
                    return False

        return True


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware providing:
    - Security headers
    - Threat detection
    - IP blocking
    - Request validation
    - Attack monitoring
    """

    def __init__(self, app):
        super().__init__(app)
        self.threat_detector = ThreatDetector()
        self.ip_blocklist = IPBlocklist()
        self.request_validator = RequestValidator()
        self.security_headers = SecurityHeaders()

        # Attack monitoring
        self.attack_threshold = 10  # Max suspicious requests per IP per hour

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"

    async def _log_security_event(self, event_type: str, request: Request, details: str):
        """Log security events for monitoring"""
        client_ip = self._get_client_ip(request)

        security_event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", ""),
            "method": request.method,
            "url": str(request.url),
            "details": details
        }

        logger.warning(f"Security event: {event_type} from {client_ip} - {details}")

        # Store in cache for analysis
        event_key = f"security_event:{client_ip}:{int(time.time())}"
        await cache.set(event_key, security_event, 3600)

        # Track attack frequency
        await self._track_attack_frequency(client_ip)

    async def _track_attack_frequency(self, ip: str):
        """Track attack frequency per IP"""
        attack_key = f"attack_count:{ip}"
        current_count = await cache.get(attack_key, 0)

        new_count = current_count + 1
        await cache.set(attack_key, new_count, 3600)  # 1 hour window

        # Auto-block if threshold exceeded
        if new_count >= self.attack_threshold:
            await self.ip_blocklist.add_ip(ip, 3600)  # Block for 1 hour
            # If request is None, skip logging request details, just log IP
            logger.warning(f"Security event: auto_block for IP {ip} - auto-blocked due to {new_count} suspicious requests")
            event_key = f"security_event:{ip}:{int(time.time())}"
            security_event = {
                "timestamp": time.time(),
                "event_type": "auto_block",
                "client_ip": ip,
                "details": f"IP {ip} auto-blocked due to {new_count} suspicious requests"
            }
            await cache.set(event_key, security_event, 3600)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with security checks"""
        client_ip = self._get_client_ip(request)

        # 1. Check IP blocklist
        if self.ip_blocklist.is_blocked(client_ip):
            await self._log_security_event("blocked_ip", request, f"Blocked IP {client_ip} attempted access")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # 2. Validate request structure
        if not self.request_validator.validate_content_length(request):
            await self._log_security_event("request_too_large", request, "Request exceeds maximum size")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )

        if not self.request_validator.validate_content_type(request):
            await self._log_security_event("invalid_content_type", request, "Invalid content type")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported media type"
            )

        if not self.request_validator.validate_headers(request):
            await self._log_security_event("invalid_headers", request, "Invalid or suspicious headers")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request headers"
            )

        # 3. Threat detection
        is_suspicious, threat_details = self.threat_detector.is_suspicious_request(request)
        if is_suspicious:
            await self._log_security_event("threat_detected", request, threat_details)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Suspicious request detected"
            )

        # 4. Process request
        try:
            response = await call_next(request)

            # 5. Add security headers
            security_headers = self.security_headers.get_default_headers()

            # Add HSTS if HTTPS
            if request.url.scheme == "https":
                security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

            for header, value in security_headers.items():
                response.headers[header] = value

            # Add server identification
            response.headers["Server"] = f"{settings.PROJECT_NAME}/{settings.VERSION}"

            return response

        except Exception as e:
            await self._log_security_event("request_error", request, f"Request processing error: {str(e)}")
            raise


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""

    def __init__(self, app, exempt_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or ['/api/v1/auth/login', '/api/v1/auth/register']
        self.safe_methods = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}

    def _generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection"""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with CSRF protection"""
        # Skip CSRF protection for safe methods and exempt paths
        if request.method in self.safe_methods or self._is_exempt(request.url.path):
            response = await call_next(request)

            # Generate CSRF token for future requests
            csrf_token = self._generate_csrf_token()
            response.headers["X-CSRF-Token"] = csrf_token

            return response

        # Check CSRF token for unsafe methods
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing"
            )

        # In a real implementation, you would validate the token
        # against a stored value (session, database, etc.)

        response = await call_next(request)

        # Regenerate CSRF token
        new_csrf_token = self._generate_csrf_token()
        response.headers["X-CSRF-Token"] = new_csrf_token

        return response
