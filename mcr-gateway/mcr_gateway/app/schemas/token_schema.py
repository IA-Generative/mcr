from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class RealmAccess(BaseModel):
    roles: List[str] = []


class ResourceRoles(BaseModel):
    roles: List[str] = []


class ResourceAccess(BaseModel):
    mcr: Optional[ResourceRoles] = None


class TokenRoles(BaseModel):
    realm_access: RealmAccess
    resource_access: ResourceAccess

    @property
    def realm_roles(self) -> List[str]:
        return self.realm_access.roles

    @property
    def resource_roles(self) -> List[str]:
        if self.resource_access.mcr is not None:
            return self.resource_access.mcr.roles
        else:
            return []

    def get_all_roles(self) -> List[str]:
        return self.realm_roles + self.resource_roles

    model_config = ConfigDict(extra="allow")
