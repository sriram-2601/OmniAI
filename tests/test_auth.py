"""Test Suite for Authentication, SQLite Credential Storage, and Social Login."""
from __future__ import annotations

import uuid
import tempfile
from pathlib import Path
import pytest

from src.auth.database import (
    AuthDatabase,
    hash_password,
    verify_password,
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    DEMO_AGENT_EMAIL,
)


@pytest.fixture
def temp_db():
    db_path = Path(tempfile.gettempdir()) / f"test_auth_{uuid.uuid4().hex[:12]}.db"
    auth_db = AuthDatabase(db_path=db_path)
    yield auth_db
    try:
        if db_path.exists():
            db_path.unlink(missing_ok=True)
    except OSError:
        pass


def test_password_hashing_and_salting():
    """Verify salted PBKDF2 hashing generates distinct hashes and verifies correctly."""
    pwd = "MySecretPassword123!"
    hash1, salt1 = hash_password(pwd)
    hash2, salt2 = hash_password(pwd)

    # Different salts must yield different hashes
    assert salt1 != salt2
    assert hash1 != hash2

    # Verification must succeed with matching salt
    assert verify_password(pwd, salt1, hash1) is True
    assert verify_password(pwd, salt2, hash2) is True

    # Verification must fail with wrong password
    assert verify_password("WrongPassword", salt1, hash1) is False


def test_demo_accounts_seeded(temp_db):
    """Verify demo admin and agent accounts are initialized out-of-the-box."""
    admin = temp_db.get_user_by_email(DEMO_ADMIN_EMAIL)
    assert admin is not None
    assert admin["role"] == "admin"
    assert admin["auth_provider"] == "local"

    agent = temp_db.get_user_by_email(DEMO_AGENT_EMAIL)
    assert agent is not None
    assert agent["role"] == "agent"


def test_authenticate_demo_admin(temp_db):
    """Verify successful authentication with demo admin credentials."""
    user = temp_db.authenticate_user(DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD)
    assert user is not None
    assert user["email"] == DEMO_ADMIN_EMAIL
    assert user["role"] == "admin"

    # Verify invalid password rejected
    bad_auth = temp_db.authenticate_user(DEMO_ADMIN_EMAIL, "WrongPass123!")
    assert bad_auth is None


def test_create_and_authenticate_new_user(temp_db):
    """Verify user registration and authentication flow."""
    email = "new_user@example.com"
    pwd = "SecureUser2026@"
    name = "Alice Support"

    user = temp_db.create_user(email=email, password=pwd, name=name, role="agent")
    assert user["email"] == email
    assert user["name"] == name

    # Authenticate new user
    auth_user = temp_db.authenticate_user(email, pwd)
    assert auth_user is not None
    assert auth_user["email"] == email

    # Re-registering existing email must raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        temp_db.create_user(email=email, password=pwd, name=name)


def test_social_logins_provisioning(temp_db):
    """Verify social logins (Google, Twitter/X, Facebook) auto-provision user profiles."""
    providers = [("google", "admin"), ("twitter", "agent"), ("facebook", "analyst")]
    for prov, role in providers:
        social_email = f"user_{prov}@social.com"
        user = temp_db.social_login(
            email=social_email,
            name=f"Social User {prov.capitalize()}",
            provider=prov,
            role=role,
        )
        assert user is not None
        assert user["email"] == social_email
        assert user["auth_provider"] == prov
        assert user["role"] == role

        # Verify second login updates existing user
        user_repeat = temp_db.social_login(
            email=social_email,
            name=f"Social User {prov.capitalize()}",
            provider=prov,
        )
        assert user_repeat["id"] == user["id"]
        assert user_repeat["role"] == role


def test_audit_logging_and_summary(temp_db):
    """Verify immutable audit log trail and diagnostic summary."""
    logs = temp_db.get_audit_logs(limit=20)
    assert len(logs) >= 2  # Seed accounts generated logs

    summary = temp_db.get_database_summary()
    assert summary["db_type"].startswith("SQLite")
    assert summary["total_users"] >= 2
    assert "PBKDF2" in summary["hashing_algorithm"]
