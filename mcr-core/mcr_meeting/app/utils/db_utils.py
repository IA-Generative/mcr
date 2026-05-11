from pydantic import BaseModel as PydanticDTO

from mcr_meeting.app.db.db import Base as BaseORM


def update_model(ORMmodel: BaseORM, updateDTO: PydanticDTO) -> None:
    """
    Update an ORM model with the values from a UserUpdate model.
    """
    for key, value in updateDTO:
        setattr(ORMmodel, key, value)


def patch_model(ORMmodel: BaseORM, updateDTO: PydanticDTO) -> None:
    """
    Update an ORM model with the values from a UserUpdate model.
    """
    for key, value in updateDTO:
        if value is None:
            continue

        setattr(ORMmodel, key, value)
