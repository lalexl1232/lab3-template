from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import uvicorn
import uuid

from database import engine, get_db, Base
from models import Car
from schemas import CarResponse, PaginationResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cars Service")


@app.get("/manage/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/v1/cars", response_model=PaginationResponse)
def get_cars(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    show_all: bool = Query(False),
    db: Session = Depends(get_db)
):
    query = db.query(Car)

    if not show_all:
        query = query.filter(Car.availability == True)

    total_elements = query.count()

    offset = (page - 1) * size
    cars = query.offset(offset).limit(size).all()

    items = [
        CarResponse(
            car_uid=car.car_uid,
            brand=car.brand,
            model=car.model,
            registration_number=car.registration_number,
            power=car.power,
            price=car.price,
            type=car.type,
            available=car.availability
        )
        for car in cars
    ]

    return PaginationResponse(
        page=page,
        page_size=len(items),
        total_elements=total_elements,
        items=items
    )


@app.get("/api/v1/cars/{car_uid}", response_model=CarResponse)
def get_car(car_uid: uuid.UUID, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.car_uid == car_uid).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    return CarResponse(
        car_uid=car.car_uid,
        brand=car.brand,
        model=car.model,
        registration_number=car.registration_number,
        power=car.power,
        price=car.price,
        type=car.type,
        available=car.availability
    )


@app.patch("/api/v1/cars/{car_uid}/availability")
def update_car_availability(
    car_uid: uuid.UUID,
    available: bool,
    db: Session = Depends(get_db)
):
    car = db.query(Car).filter(Car.car_uid == car_uid).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    car.availability = available
    db.commit()
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8070)
