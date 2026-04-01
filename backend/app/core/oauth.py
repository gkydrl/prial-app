"""
OAuth token verification for Google and Apple Sign-In.
"""

import httpx
import jwt
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.config import settings


class OAuthError(Exception):
    pass


def _google_client_ids() -> list[str]:
    """All accepted Google client IDs (web + iOS)."""
    ids = []
    if settings.google_client_id:
        ids.append(settings.google_client_id)
    if settings.google_ios_client_id:
        ids.append(settings.google_ios_client_id)
    return ids


def verify_google_token(token: str) -> dict:
    """
    Verify a Google ID token and return user info.
    Returns: {sub, email, name, picture}
    """
    try:
        info = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            clock_skew_in_seconds=10,
        )
    except Exception as e:
        raise OAuthError(f"Google token doğrulanamadı: {e}")

    # Verify the audience (client ID) matches one of ours
    if info.get("aud") not in _google_client_ids():
        raise OAuthError("Google token geçersiz client ID içeriyor")

    if not info.get("email_verified", False):
        raise OAuthError("Google hesabının e-postası doğrulanmamış")

    return {
        "sub": info["sub"],
        "email": info["email"],
        "name": info.get("name"),
        "picture": info.get("picture"),
    }


# Apple public keys cache
_apple_keys_cache: dict | None = None


async def _get_apple_public_keys() -> dict:
    global _apple_keys_cache
    if _apple_keys_cache is not None:
        return _apple_keys_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get("https://appleid.apple.com/auth/keys", timeout=10)
        resp.raise_for_status()
        _apple_keys_cache = resp.json()
        return _apple_keys_cache


def _apple_audience_ids() -> list[str]:
    """All accepted Apple client IDs (app bundle + web services ID)."""
    ids = ["com.prial.app"]
    if settings.apple_web_client_id:
        ids.append(settings.apple_web_client_id)
    return ids


async def verify_apple_token(token: str) -> dict:
    """
    Verify an Apple ID token using Apple's public keys.
    Returns: {sub, email}
    """
    try:
        keys_data = await _get_apple_public_keys()
        # Decode header to find the right key
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # Find the matching key
        key_data = None
        for k in keys_data.get("keys", []):
            if k["kid"] == kid:
                key_data = k
                break

        if not key_data:
            # Invalidate cache and retry
            global _apple_keys_cache
            _apple_keys_cache = None
            keys_data = await _get_apple_public_keys()
            for k in keys_data.get("keys", []):
                if k["kid"] == kid:
                    key_data = k
                    break

        if not key_data:
            raise OAuthError("Apple public key bulunamadı")

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=_apple_audience_ids(),
            issuer="https://appleid.apple.com",
        )
    except OAuthError:
        raise
    except Exception as e:
        raise OAuthError(f"Apple token doğrulanamadı: {e}")

    return {
        "sub": payload["sub"],
        "email": payload.get("email"),
    }
