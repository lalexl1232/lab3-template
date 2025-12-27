from sqlalchemy import Column, Integer, String, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from database import Base


class Payment(Base):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True, index=True)
    payment_uid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    status = Column(String(20), nullable=False)
    price = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PAID', 'CANCELED')",
            name="payment_status_check"
        ),
    )
