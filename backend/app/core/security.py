"""
Security utilities for authentication and authorization.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Token subject (usually user ID)
        expires_delta: Token expiration time
        extra_claims: Additional claims to include

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
    }

    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: Token subject (usually user ID)
        expires_delta: Token expiration time

    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


def generate_otp(length: int | None = None) -> str:
    """
    Generate a numeric OTP.

    Args:
        length: OTP length (default from settings)

    Returns:
        OTP string
    """
    length = length or settings.otp_length
    return "".join(secrets.choice("0123456789") for _ in range(length))


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify webhook signature using HMAC.

    Args:
        payload: Raw request body bytes
        signature: Signature from webhook header
        secret: Webhook secret key
        algorithm: Hash algorithm (default: sha256)

    Returns:
        True if signature is valid
    """
    try:
        import hashlib
        import hmac

        if algorithm == "sha1":
            hash_func = hashlib.sha1
        elif algorithm == "sha256":
            hash_func = hashlib.sha256
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hash_func,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


def verify_meta_webhook_signature(
    payload: bytes,
    signature_header: str,
    app_secret: str,
) -> bool:
    """
    Verify Meta (Facebook/WhatsApp) webhook signature.

    Meta sends: X-Hub-Signature-256: sha256=<signature>

    Args:
        payload: Raw request body bytes
        signature_header: Full signature header value (e.g., "sha256=abc123")
        app_secret: Meta App Secret

    Returns:
        True if signature is valid
    """
    try:
        import hashlib
        import hmac

        # Extract signature from header (format: "sha256=<signature>")
        if not signature_header or "=" not in signature_header:
            return False

        algorithm, signature = signature_header.split("=", 1)

        if algorithm != "sha256":
            return False

        # Calculate expected signature
        expected_signature = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


def verify_twilio_signature(
    url: str,
    params: dict[str, str],
    signature: str,
    auth_token: str,
) -> bool:
    """
    Verify Twilio webhook signature.

    Twilio computes signature as: base64(hmac-sha1(url + sorted params))

    Args:
        url: Full webhook URL (including protocol and domain)
        params: POST parameters as dict
        signature: X-Twilio-Signature header value
        auth_token: Twilio Auth Token

    Returns:
        True if signature is valid
    """
    try:
        import base64
        import hashlib
        import hmac

        # Sort params and concatenate to URL
        data = url
        for key in sorted(params.keys()):
            data += key + params[key]

        # Calculate expected signature
        expected_signature = base64.b64encode(
            hmac.new(
                auth_token.encode("utf-8"),
                data.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("utf-8")

        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and injection attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem operations
    """
    import os
    import re

    # Remove any path components
    filename = os.path.basename(filename)

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Remove control characters and dangerous characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f\x7f]', '', filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext

    # Fallback if filename becomes empty
    if not filename:
        filename = "unnamed_file"

    return filename


def validate_file_magic_bytes(content: bytes, expected_type: str) -> bool:
    """
    Validate file type by checking magic bytes (file signature).

    Args:
        content: File content bytes
        expected_type: Expected file type (pdf, jpg, png, etc.)

    Returns:
        True if magic bytes match expected type
    """
    if not content:
        return False

    # Magic bytes for common file types
    magic_bytes = {
        "pdf": [b"%PDF"],
        "jpg": [b"\xff\xd8\xff"],
        "jpeg": [b"\xff\xd8\xff"],
        "png": [b"\x89PNG\r\n\x1a\n"],
        "gif": [b"GIF87a", b"GIF89a"],
        "bmp": [b"BM"],
        "tiff": [b"II*\x00", b"MM\x00*"],
        "webp": [b"RIFF"],
        "svg": [b"<svg", b"<?xml"],
        "doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
        "docx": [b"PK\x03\x04"],
        "xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
        "xlsx": [b"PK\x03\x04"],
        "zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    }

    expected_type = expected_type.lower().lstrip(".")

    if expected_type not in magic_bytes:
        # Unknown type, allow (but log warning)
        return True

    for magic in magic_bytes[expected_type]:
        if content.startswith(magic):
            return True

    return False


def is_safe_path(basedir: str, path: str) -> bool:
    """
    Check if path is within basedir (prevents path traversal).

    Args:
        basedir: Base directory path
        path: Path to check

    Returns:
        True if path is safe
    """
    import os

    # Resolve to absolute paths
    basedir = os.path.abspath(basedir)
    path = os.path.abspath(path)

    # Check if path starts with basedir
    return path.startswith(basedir)
