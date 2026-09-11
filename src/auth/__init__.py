"""Authentication module for OmniSupport AI."""
from src.auth.database import (
    default_auth_db,
    AuthDatabase,
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    DEMO_ADMIN_NAME,
    DEMO_AGENT_EMAIL,
    DEMO_AGENT_PASSWORD,
    hash_password,
    verify_password,
)

__all__ = [
    "default_auth_db",
    "AuthDatabase",
    "DEMO_ADMIN_EMAIL",
    "DEMO_ADMIN_PASSWORD",
    "DEMO_ADMIN_NAME",
    "DEMO_AGENT_EMAIL",
    "DEMO_AGENT_PASSWORD",
    "hash_password",
    "verify_password",
]
