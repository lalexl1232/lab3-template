from pydantic import BaseModel, Field
from uuid import UUID
from typing import Literal, Optional


class CarResponse(BaseModel):
    car_uid: UUID = Field(validation_alias="carUid", serialization_alias="carUid")
    brand: str
    model: str
    registration_number: str = Field(validation_alias="registrationNumber", serialization_alias="registrationNumber")
    power: Optional[int] = None
    price: int
    type: str
    available: bool

    class Config:
        populate_by_name = True


class PaginationResponse(BaseModel):
    page: int
    page_size: int = Field(validation_alias="pageSize", serialization_alias="pageSize")
    total_elements: int = Field(validation_alias="totalElements", serialization_alias="totalElements")
    items: list[CarResponse]

    class Config:
        populate_by_name = True


class CarInfo(BaseModel):
    car_uid: UUID = Field(validation_alias="carUid", serialization_alias="carUid")
    brand: str
    model: str
    registration_number: str = Field(validation_alias="registrationNumber", serialization_alias="registrationNumber")

    class Config:
        populate_by_name = True


class PaymentInfo(BaseModel):
    payment_uid: UUID = Field(validation_alias="paymentUid", serialization_alias="paymentUid")
    status: Literal["PAID", "CANCELED"]
    price: int

    class Config:
        populate_by_name = True


class RentalResponse(BaseModel):
    rental_uid: UUID = Field(validation_alias="rentalUid", serialization_alias="rentalUid")
    status: Literal["IN_PROGRESS", "FINISHED", "CANCELED"]
    date_from: str = Field(validation_alias="dateFrom", serialization_alias="dateFrom")
    date_to: str = Field(validation_alias="dateTo", serialization_alias="dateTo")
    car: CarInfo
    payment: Optional[PaymentInfo | dict] = None

    class Config:
        populate_by_name = True


class CreateRentalRequest(BaseModel):
    car_uid: UUID = Field(validation_alias="carUid")
    date_from: str = Field(validation_alias="dateFrom")
    date_to: str = Field(validation_alias="dateTo")

    class Config:
        populate_by_name = True


class CreateRentalResponse(BaseModel):
    rental_uid: UUID = Field(validation_alias="rentalUid", serialization_alias="rentalUid")
    status: Literal["IN_PROGRESS", "FINISHED", "CANCELED"]
    car_uid: UUID = Field(validation_alias="carUid", serialization_alias="carUid")
    date_from: str = Field(validation_alias="dateFrom", serialization_alias="dateFrom")
    date_to: str = Field(validation_alias="dateTo", serialization_alias="dateTo")
    payment: PaymentInfo

    class Config:
        populate_by_name = True


class ErrorResponse(BaseModel):
    message: str
