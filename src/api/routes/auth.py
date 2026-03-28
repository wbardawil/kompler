"""Auth API — signup, login, JWT tokens.

Simple auth for MVP. No OAuth, no SSO, no magic links.
Email + password → JWT token → use in all API calls.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.core.config import get_settings

settings = get_settings()
router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    company_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str
    company_name: str
    expires_in: int


@router.post("/auth/signup", response_model=TokenResponse)
async def signup(
    request: SignupRequest,
    session: AsyncSession = Depends(get_db),
):
    """Create a new account (tenant + user).

    Creates:
    - New tenant (company) on Starter plan
    - New user as owner
    - Returns JWT token for immediate use
    """
    # Check if email already exists
    existing = await session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": request.email.lower()},
    )
    if existing.first():
        raise HTTPException(400, "An account with this email already exists")

    # Create tenant
    tenant_id = str(uuid.uuid4())
    slug = request.company_name.lower().replace(" ", "-")[:50]

    # Ensure unique slug
    slug_check = await session.execute(
        text("SELECT id FROM tenants WHERE slug = :slug"),
        {"slug": slug},
    )
    if slug_check.first():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    await session.execute(
        text("""
            INSERT INTO tenants (id, name, slug, tier, credits_included, storage_limit_gb, max_connectors)
            VALUES (:id, :name, :slug, 'starter', 2000, 10, 1)
        """),
        {"id": tenant_id, "name": request.company_name, "slug": slug},
    )

    # Create user
    user_id = str(uuid.uuid4())
    password_hash = bcrypt.hash(request.password)

    await session.execute(
        text("""
            INSERT INTO users (id, tenant_id, email, name, password_hash, role)
            VALUES (:id, :tid, :email, :name, :hash, 'owner')
        """),
        {
            "id": user_id,
            "tid": tenant_id,
            "email": request.email.lower(),
            "name": request.name,
            "hash": password_hash,
        },
    )

    # Create default compliance profile
    await session.execute(
        text("""
            INSERT INTO compliance_profiles (tenant_id, frameworks, industry)
            VALUES (:tid, '["iso_9001"]', 'manufacturing')
        """),
        {"tid": tenant_id},
    )

    await session.commit()

    # Generate JWT
    token = _create_token(tenant_id, user_id)

    return TokenResponse(
        access_token=token,
        tenant_id=tenant_id,
        user_id=user_id,
        company_name=request.company_name,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """Login with email + password. Returns JWT token."""
    result = await session.execute(
        text("""
            SELECT u.id as user_id, u.tenant_id, u.password_hash, u.name,
                   t.name as company_name
            FROM users u
            JOIN tenants t ON t.id = u.tenant_id
            WHERE u.email = :email AND u.is_active = true AND t.active = true
        """),
        {"email": request.email.lower()},
    )
    user = result.mappings().first()

    if not user or not bcrypt.verify(request.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    token = _create_token(str(user["tenant_id"]), str(user["user_id"]))

    return TokenResponse(
        access_token=token,
        tenant_id=str(user["tenant_id"]),
        user_id=str(user["user_id"]),
        company_name=user["company_name"],
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/auth/me")
async def get_me(
    session: AsyncSession = Depends(get_db),
    authorization: str = None,
):
    """Get current user info from JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")

    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        raise HTTPException(401, "Invalid token")

    result = await session.execute(
        text("""
            SELECT u.id, u.email, u.name, u.role,
                   t.id as tenant_id, t.name as company_name, t.tier
            FROM users u
            JOIN tenants t ON t.id = u.tenant_id
            WHERE u.id = :uid
        """),
        {"uid": payload.get("user_id")},
    )
    user = result.mappings().first()

    if not user:
        raise HTTPException(404, "User not found")

    return {
        "user_id": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "tenant_id": str(user["tenant_id"]),
        "company_name": user["company_name"],
        "tier": user["tier"],
    }


def _create_token(tenant_id: str, user_id: str) -> str:
    """Create a JWT token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
