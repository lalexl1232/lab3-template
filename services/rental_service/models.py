from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from database import Base


class Rental(Base):
    __tablename__ = "rental"

    id = Column(Integer, primary_key=True, index=True)
    rental_uid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    username = Column(String(80), nullable=False)
    payment_uid = Column(UUID(as_uuid=True), nullable=False)
    car_uid = Column(UUID(as_uuid=True), nullable=False)
    date_from = Column(DateTime(timezone=True), nullable=False)
    date_to = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'FINISHED', 'CANCELED')",
            name="rental_status_check"
        ),
    )
