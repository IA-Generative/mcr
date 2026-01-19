from pydantic import BaseModel

from mcr_meeting.app.db.db import Base as BaseORM


def update_model(ORMmodel: BaseORM, updateDTO: BaseModel) -> None:
    """
    Update an ORM model with the values from a UserUpdate model.
    """
    for key, value in updateDTO:
        setattr(ORMmodel, key, value)
