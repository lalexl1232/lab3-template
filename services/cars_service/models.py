from sqlalchemy import Column, Integer, String, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from database import Base


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    car_uid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    brand = Column(String(80), nullable=False)
    model = Column(String(80), nullable=False)
    registration_number = Column(String(20), nullable=False)
    power = Column(Integer)
    price = Column(Integer, nullable=False)
    type = Column(String(20))
    availability = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint(
            "type IN ('SEDAN', 'SUV', 'MINIVAN', 'ROADSTER')",
            name="car_type_check"
        ),
    )
