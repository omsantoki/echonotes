"""Server-side Google ID-token verification (feature 002, Strong — FR-26).

We verify the token's signature **against Google's published certs** (never trust
the client): PyJWT's `PyJWKClient` fetches and caches Google's JWKS, and we check
the RS256 signature, the audience (our OAuth client id), and the issuer. No
`google-auth` dependency is needed — PyJWT (already used for sessions) covers it.

`verify_google_id_token` is intentionally a single, easily-monkeypatched function
so tests can stub it without hitting the network.
"""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

from app.config import get_settings

_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

_jwk_client: PyJWKClient | None = None


class GoogleNotConfigured(Exception):
    """No GOOGLE_OAUTH_CLIENT_ID set on the server."""


class GoogleAuthError(Exception):
    """The presented Google ID token is invalid (bad signature/audience/issuer/claims)."""


def _client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(_GOOGLE_CERTS_URL)  # caches signing keys across calls
    return _jwk_client


def verify_google_id_token(id_token: str) -> dict:
    """Verify a Google ID token and return `{sub, email, email_verified}`.

    Raises GoogleNotConfigured if the server has no client id, or GoogleAuthError
    if the token fails verification.
    """
    client_id = get_settings().google_oauth_client_id.strip()
    if not client_id:
        raise GoogleNotConfigured()
    if not id_token:
        raise GoogleAuthError("Missing id_token.")
    try:
        signing_key = _client().get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token, signing_key.key, algorithms=["RS256"], audience=client_id,
        )
    except Exception as exc:  # signature/audience/expiry/parse failures
        raise GoogleAuthError(str(exc)) from exc

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise GoogleAuthError("Unexpected token issuer.")
    email = (claims.get("email") or "").strip().lower()
    sub = claims.get("sub")
    if not email or not sub:
        raise GoogleAuthError("Token is missing email or subject.")
    return {"sub": sub, "email": email, "email_verified": bool(claims.get("email_verified"))}
