from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uvicorn
import uuid
from datetime import datetime

from database import engine, get_db, Base
from models import Rental
from schemas import RentalCreate, RentalResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rental Service")


@app.get("/manage/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/v1/rental", response_model=RentalResponse)
def create_rental(rental: RentalCreate, db: Session = Depends(get_db)):
    date_from = datetime.fromisoformat(rental.date_from)
    date_to = datetime.fromisoformat(rental.date_to)

    db_rental = Rental(
        rental_uid=uuid.uuid4(),
        username=rental.username,
        payment_uid=rental.payment_uid,
        car_uid=rental.car_uid,
        date_from=date_from,
        date_to=date_to,
        status="IN_PROGRESS"
    )
    db.add(db_rental)
    db.commit()
    db.refresh(db_rental)

    return RentalResponse(
        rental_uid=db_rental.rental_uid,
        username=db_rental.username,
        payment_uid=db_rental.payment_uid,
        car_uid=db_rental.car_uid,
        date_from=rental.date_from,
        date_to=rental.date_to,
        status=db_rental.status
    )


@app.get("/api/v1/rental", response_model=List[RentalResponse])
def get_rentals_by_username(username: str, db: Session = Depends(get_db)):
    rentals = db.query(Rental).filter(Rental.username == username).all()

    return [
        RentalResponse(
            rental_uid=rental.rental_uid,
            username=rental.username,
            payment_uid=rental.payment_uid,
            car_uid=rental.car_uid,
            date_from=rental.date_from.strftime("%Y-%m-%d"),
            date_to=rental.date_to.strftime("%Y-%m-%d"),
            status=rental.status
        )
        for rental in rentals
    ]


@app.get("/api/v1/rental/{rental_uid}", response_model=RentalResponse)
def get_rental(rental_uid: uuid.UUID, username: str, db: Session = Depends(get_db)):
    rental = db.query(Rental).filter(
        Rental.rental_uid == rental_uid,
        Rental.username == username
    ).first()

    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")

    return RentalResponse(
        rental_uid=rental.rental_uid,
        username=rental.username,
        payment_uid=rental.payment_uid,
        car_uid=rental.car_uid,
        date_from=rental.date_from.strftime("%Y-%m-%d"),
        date_to=rental.date_to.strftime("%Y-%m-%d"),
        status=rental.status
    )


@app.delete("/api/v1/rental/{rental_uid}", status_code=204)
def cancel_rental(rental_uid: uuid.UUID, username: str, db: Session = Depends(get_db)):
    rental = db.query(Rental).filter(
        Rental.rental_uid == rental_uid,
        Rental.username == username
    ).first()

    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")

    rental.status = "CANCELED"
    db.commit()
    return None


@app.post("/api/v1/rental/{rental_uid}/finish", status_code=204)
def finish_rental(rental_uid: uuid.UUID, username: str, db: Session = Depends(get_db)):
    rental = db.query(Rental).filter(
        Rental.rental_uid == rental_uid,
        Rental.username == username
    ).first()

    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")

    rental.status = "FINISHED"
    db.commit()
    return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8060)
