import uuid

from factory import Faker, LazyFunction, Trait

from mcr_meeting.app.models.user_model import Role, User

from .base import BaseFactory


class UserFactory(BaseFactory[User]):
    """
    Factory for creating User instances with realistic test data.

    By default, creates a regular user with fake data.
    Use traits for common variations (admin).

    Examples:
        user = UserFactory()
        admin = UserFactory(admin=True)
        custom = UserFactory(email="specific@example.com")
    """

    class Meta:
        model = User

    first_name = Faker("first_name")
    last_name = Faker("last_name")
    entity_name = Faker("company")
    email = Faker("email")
    role = Role.USER
    keycloak_uuid = LazyFunction(uuid.uuid4)

    class Params:
        # Trait for admin users
        admin = Trait(
            role=Role.ADMIN,
            entity_name="Admin Team",
        )
