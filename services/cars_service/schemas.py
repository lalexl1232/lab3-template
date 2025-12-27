from pydantic import BaseModel, Field
from uuid import UUID
from typing import Literal, Optional


class CarBase(BaseModel):
    brand: str
    model: str
    registration_number: str = Field(serialization_alias="registrationNumber")
    power: Optional[int] = None
    price: int
    type: Literal["SEDAN", "SUV", "MINIVAN", "ROADSTER"]
    availability: bool = True


class CarCreate(CarBase):
    pass


class CarResponse(BaseModel):
    car_uid: UUID = Field(serialization_alias="carUid")
    brand: str
    model: str
    registration_number: str = Field(serialization_alias="registrationNumber")
    power: Optional[int] = None
    price: int
    type: str
    available: bool

    class Config:
        from_attributes = True
        populate_by_name = True


class PaginationResponse(BaseModel):
    page: int
    page_size: int = Field(serialization_alias="pageSize")
    total_elements: int = Field(serialization_alias="totalElements")
    items: list[CarResponse]

    class Config:
        populate_by_name = True
