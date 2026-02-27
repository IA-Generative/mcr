from pydantic import BaseModel, ConfigDict


class RealmAccess(BaseModel):
    roles: list[str] = []


class ResourceRoles(BaseModel):
    roles: list[str] = []


class ResourceAccess(BaseModel):
    mcr: ResourceRoles | None = None


class TokenRoles(BaseModel):
    realm_access: RealmAccess
    resource_access: ResourceAccess

    @property
    def realm_roles(self) -> list[str]:
        return self.realm_access.roles

    @property
    def resource_roles(self) -> list[str]:
        if self.resource_access.mcr is not None:
            return self.resource_access.mcr.roles
        else:
            return []

    def get_all_roles(self) -> list[str]:
        return self.realm_roles + self.resource_roles

    model_config = ConfigDict(extra="allow")
