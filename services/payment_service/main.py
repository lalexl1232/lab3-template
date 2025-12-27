from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uvicorn
import uuid

from database import engine, get_db, Base
from models import Payment
from schemas import PaymentCreate, PaymentResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Payment Service")


@app.get("/manage/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/v1/payment", response_model=PaymentResponse)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    db_payment = Payment(
        payment_uid=uuid.uuid4(),
        status="PAID",
        price=payment.price
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@app.get("/api/v1/payment/{payment_uid}", response_model=PaymentResponse)
def get_payment(payment_uid: uuid.UUID, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.payment_uid == payment_uid).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@app.delete("/api/v1/payment/{payment_uid}", status_code=204)
def cancel_payment(payment_uid: uuid.UUID, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.payment_uid == payment_uid).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.status = "CANCELED"
    db.commit()
    return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8050)
