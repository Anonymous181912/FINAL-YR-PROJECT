from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from app.core.config import settings
from app.core.security import decode_access_token
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.doctor_repository import DoctorRepository
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user_repo = UserRepository()
    db_user = await user_repo.get_by_id(user_id)
    if db_user is None:
        raise credentials_exception

    return User(
        id=db_user.id,
        email=db_user.email,
        role=db_user.role,
        full_name=db_user.full_name,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at,
    )


async def get_current_doctor(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Doctor role required.",
        )
    return current_user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required.",
        )
    return current_user


async def get_current_verified_doctor(
    current_user: User = Depends(get_current_doctor),
) -> User:
    """Doctor endpoints touching patient data require admin verification.

    Phase 0: verified doctors only (Phase 3 adds per-patient consent grants).
    Returns 403 with a clear message for pending/rejected doctors so the
    frontend can render the "pending approval" screen.
    """
    repo = DoctorRepository()
    profile = await repo.get_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor profile not found. Please contact support.",
        )
    if not profile.is_verified or profile.verification_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor account pending approval. Please wait for admin verification.",
        )
    return current_user


async def get_current_patient(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Patient role required.",
        )
    return current_user
