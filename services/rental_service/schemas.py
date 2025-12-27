from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Literal


class RentalBase(BaseModel):
    username: str
    payment_uid: UUID = Field(validation_alias="paymentUid")
    car_uid: UUID = Field(validation_alias="carUid")
    date_from: str = Field(validation_alias="dateFrom")
    date_to: str = Field(validation_alias="dateTo")

    class Config:
        populate_by_name = True


class RentalCreate(RentalBase):
    pass


class RentalResponse(BaseModel):
    rental_uid: UUID = Field(serialization_alias="rentalUid")
    username: str
    payment_uid: UUID = Field(serialization_alias="paymentUid")
    car_uid: UUID = Field(serialization_alias="carUid")
    date_from: str = Field(serialization_alias="dateFrom")
    date_to: str = Field(serialization_alias="dateTo")
    status: Literal["IN_PROGRESS", "FINISHED", "CANCELED"]

    class Config:
        from_attributes = True
        populate_by_name = True
