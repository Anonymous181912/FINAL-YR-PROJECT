from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, verify_password, get_password_hash
from app.auth.dependencies import get_current_user
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.patient_repository import PatientRepository
from app.database.repositories.doctor_repository import DoctorRepository
from app.schemas.auth import Token, RegisterRequest
from app.auth.tokens import RefreshRequest, ForgotRequest, ResetRequest
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, payload: RegisterRequest):
    """Register via JSON body (Phase 0a).

    Password policy (min 8 chars, >=1 letter and >=1 digit) is enforced by
    the ``RegisterRequest`` schema. Only patient/doctor self-registration is
    allowed; admins are seeded from env (see scripts/seed_admin.py).
    """
    user_repo = UserRepository()
    if await user_repo.exists_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(payload.password)
    user = await user_repo.create_user(
        email=payload.email,
        hashed_password=hashed_password,
        role=payload.role,
        full_name=payload.full_name,
    )

    if payload.role == "patient":
        patient_repo = PatientRepository()
        await patient_repo.create_profile(user_id=user.id, full_name=payload.full_name)
    else:
        doctor_repo = DoctorRepository()
        await doctor_repo.create_profile(
            user_id=user.id,
            full_name=payload.full_name,
            license_number=payload.license_number,
            is_verified=False,
            verification_status="pending",
        )

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "full_name": user.full_name,
    }


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    from datetime import datetime, timezone

    from app.auth.tokens import RefreshTokenRepository

    user_repo = UserRepository()
    user = await user_repo.get_by_email(form_data.username)

    # Phase 6c: locked accounts stay locked even with the right password.
    if user is not None and user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account temporarily locked after repeated failed logins. Try again later.",
            )

    if not user or not verify_password(form_data.password, user.hashed_password):
        if user is not None:
            locked, _attempts = await user_repo.record_failed_login(user.id)
            if locked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account temporarily locked after repeated failed logins. Try again later.",
                )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    await user_repo.reset_lockout(user.id)

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = await RefreshTokenRepository().issue(user.id)

    return Token(
        access_token=access_token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
async def refresh_session(payload: RefreshRequest):
    """Rotation: a refresh token works once; each use mints a new pair."""
    from app.auth.tokens import RefreshTokenRepository

    repo = RefreshTokenRepository()
    doc = await repo.redeem(payload.refresh_token)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_repo = UserRepository()
    user = await user_repo.get_by_id(doc["user_id"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    new_refresh = await repo.issue(user.id)
    return Token(access_token=access_token, role=user.role, user_id=user.id,
                 full_name=user.full_name, refresh_token=new_refresh)


@router.post("/logout")
async def logout(payload: RefreshRequest):
    """Invalidate a refresh token (access tokens expire on their own)."""
    from app.auth.tokens import RefreshTokenRepository

    await RefreshTokenRepository().revoke(payload.refresh_token)
    return {"detail": "Logged out"}


@router.post("/forgot-password")
@limiter.limit("10/minute")
async def forgot_password(request: Request, payload: ForgotRequest):
    """Always 200 (never reveals whether an email is registered)."""
    import logging

    from app.auth.tokens import PasswordResetRepository
    from app.notifications.scheduler import send_email_best_effort

    logger = logging.getLogger("healthcare_system")
    user_repo = UserRepository()
    try:
        user = await user_repo.get_by_email(payload.email)
    except Exception:
        user = None
    if user is not None:
        token = await PasswordResetRepository().issue(user.id)
        reset_link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
        body = (f"Hello {user.full_name},\n\nUse this link within 60 minutes to reset "
                f"your password:\n{reset_link}\n\nIf you did not ask for this, ignore this email.")
        sent = send_email_best_effort(user.email, "Password reset", body)
        if not sent:
            # Dev mode: log the link instead of sending (per spec).
            logger.info(f"Password reset link for {user.email}: {reset_link}")
    return {"detail": "If the email is registered, a reset link has been sent"}


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(request: Request, payload: ResetRequest):
    from pydantic import ValidationError

    from app.auth.tokens import PasswordResetRepository, RefreshTokenRepository
    from app.schemas.auth import RegisterRequest

    # Reuse the registration password policy (min 8 + letter + digit).
    try:
        RegisterRequest(email="reset@example.com", password=payload.new_password,
                        role="patient", full_name="Reset User")
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Password must be at least 8 characters with a letter and a digit")

    doc = await PasswordResetRepository().consume(payload.token)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid or expired reset token")
    user_repo = UserRepository()
    user = await user_repo.get_by_id(doc["user_id"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid or expired reset token")
    await user_repo.set_password(user.id, get_password_hash(payload.new_password))
    await RefreshTokenRepository().revoke_all_for_user(user.id)
    return {"detail": "Password has been reset"}


@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    # Phase 0b: doctors also learn their verification state here so the
    # frontend can render the "pending approval" screen without extra calls.
    extra: dict = {}
    if current_user.role == "doctor":
        try:
            repo = DoctorRepository()
            profile = await repo.get_by_user_id(current_user.id)
            if profile is not None:
                extra = {
                    "is_verified": profile.is_verified,
                    "verification_status": profile.verification_status,
                    "license_number": profile.license_number,
                }
        except Exception:
            extra = {}
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        **extra,
    }
