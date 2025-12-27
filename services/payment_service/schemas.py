from pydantic import BaseModel, Field
from uuid import UUID
from typing import Literal


class PaymentBase(BaseModel):
    price: int


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(BaseModel):
    payment_uid: UUID = Field(serialization_alias="paymentUid")
    status: Literal["PAID", "CANCELED"]
    price: int

    class Config:
        from_attributes = True
        populate_by_name = True
