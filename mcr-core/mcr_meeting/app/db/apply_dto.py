from pydantic import BaseModel as PydanticDTO

from mcr_meeting.app.db.db import Base as BaseORM


def apply_dto(ORMmodel: BaseORM, updateDTO: PydanticDTO) -> None:
    """
    Apply every field of a DTO onto an ORM model.
    """
    for key, value in updateDTO:
        setattr(ORMmodel, key, value)


def apply_dto_patch(ORMmodel: BaseORM, updateDTO: PydanticDTO) -> None:
    """
    Apply a DTO onto an ORM model, skipping fields left unset (None).
    """
    for key, value in updateDTO:
        if value is None:
            continue

        setattr(ORMmodel, key, value)
