from typing import List, Optional

from loguru import logger
from pydantic import UUID4

from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models import User

from ..db.db import get_db_session_ctx


def save_user(user: User) -> User:
    """
    Create a new user in the database.

    Args:
        user_data (UserCreate): The Pydantic model containing the user data.

    Returns:
        User: The created user object.
    """
    db = get_db_session_ctx()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(user_id: int) -> User:
    """
    Retrieve a user by ID.
    """
    db = get_db_session_ctx()
    user = db.get(User, user_id)

    if not user:
        logger.error("User not found: {}", user_id)
        raise NotFoundException(f"User not found: id={user_id}")

    return user


def update_user(updated_user: User) -> User:
    """
    Update an existing user instance in the database.
    """
    db = get_db_session_ctx()

    db.merge(updated_user)
    db.commit()
    db.refresh(updated_user)
    return updated_user


def delete_user(user: User) -> None:
    """
    Delete a user from the database.
    """
    db = get_db_session_ctx()
    db.delete(user)
    db.commit()


def get_users(search: Optional[str]) -> List[User]:
    """
    Récupère une liste de utilisateurs filtrés depuis la base de données.

    Args:
        search (str): Terme de recherche optionnel pour filtrer les utilisateurs.

    Returns:
        List[User]: Liste des utilisateurs correspondant aux critères.
    """
    db = get_db_session_ctx()
    query = db.query(User)
    if search:
        query = query.filter(User.first_name.contains(search))
    return query.order_by(User.id.asc()).all()


def get_user_by_keycloak_uuid(keycloak_uuid: UUID4) -> User:
    """
    Retrieve a user by keycloak_uuid.
    """
    db = get_db_session_ctx()
    user = db.query(User).filter(User.keycloak_uuid == keycloak_uuid).first()

    if not user:
        logger.error("User not found: {}", keycloak_uuid)
        raise NotFoundException(f"User not found: keycloak_uuid={keycloak_uuid}")

    return user
