from pydantic import UUID4, BaseModel, ConfigDict


class Caller(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: int
    keycloak_uuid: UUID4
    is_admin: bool
