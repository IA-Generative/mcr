from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    TokenValidationError,
)
from mcr_meeting.app.infrastructure.keycloak import (
    FRONTEND_CLIENT_ID,
    decode_and_verify,
)
from mcr_meeting.app.schemas.caller_schema import Caller
from mcr_meeting.app.schemas.keycloak_claims import TokenClaims
from mcr_meeting.app.schemas.user_schema import UserCreate
from mcr_meeting.app.use_cases.get_or_create_user_by_keycloak import (
    get_or_create_user_by_keycloak,
)

_ADMIN_ROLE = "ADMIN"

_bearer_scheme = HTTPBearer(auto_error=False)

_unauthorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_caller(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    _db: Session = Depends(router_db_session_context_manager),
) -> Caller:
    if credentials is None:
        raise _unauthorized
    try:
        claims = decode_and_verify(credentials.credentials)
    except TokenValidationError:
        raise _unauthorized

    user = get_or_create_user_by_keycloak(_to_user_create(claims))
    is_admin = claims.has_client_role(FRONTEND_CLIENT_ID, _ADMIN_ROLE)
    return Caller(user_id=user.id, keycloak_uuid=user.keycloak_uuid, is_admin=is_admin)


def require_admin(caller: Caller = Depends(get_current_caller)) -> Caller:
    if not caller.is_admin:
        raise ForbiddenAccessException("Admin role required")
    return caller


def _to_user_create(claims: TokenClaims) -> UserCreate:
    return UserCreate(
        keycloak_uuid=claims.sub,
        first_name=claims.given_name,
        last_name=claims.family_name,
        entity_name="",
        email=claims.email,
    )
