from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field


class ClientRoles(BaseModel):
    roles: list[str] = []


class TokenClaims(BaseModel):
    model_config = ConfigDict(frozen=True)

    sub: UUID4
    email: EmailStr
    given_name: str = ""
    family_name: str = ""
    azp: str | None = None
    resource_access: dict[str, ClientRoles] = Field(default_factory=dict)

    def has_client_role(self, client_id: str, role: str) -> bool:
        client = self.resource_access.get(client_id)
        if client is None:
            return False
        return role.upper() in {r.upper() for r in client.roles}
