"""Shared JWT authentication helpers for tests."""

from __future__ import annotations

import time

import jwt as pyjwt

TEST_JWT_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"  # gitleaks:allow
TEST_JWT_ALGORITHM = "HS256"


def make_auth_header(*permissions: str) -> dict[str, str]:
    """Return an ``Authorization`` header with a valid JWT carrying *permissions*."""
    claims: dict = {
        "sub": "user-1",
        "username": "testuser",
        "permissions": list(permissions),
        "exp": int(time.time()) + 300,
    }
    token = pyjwt.encode(claims, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}
