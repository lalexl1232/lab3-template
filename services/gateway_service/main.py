from fastapi import FastAPI, Header, HTTPException, Query
from typing import Optional, List
import httpx
import uvicorn
from datetime import datetime
import os
import logging

from schemas import (
    PaginationResponse, RentalResponse, CreateRentalRequest,
    CreateRentalResponse, CarInfo, PaymentInfo, ErrorResponse
)
from circuit_breaker import CircuitBreakerManager
from retry_queue import retry_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gateway Service")

CARS_SERVICE_URL = os.getenv("CARS_SERVICE_URL", "http://cars:8070")
RENTAL_SERVICE_URL = os.getenv("RENTAL_SERVICE_URL", "http://rental:8060")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment:8050")

circuit_breaker_manager = CircuitBreakerManager()


@app.on_event("startup")
async def startup_event():
    await retry_queue.start()
    logger.info("Retry queue started")


@app.on_event("shutdown")
async def shutdown_event():
    await retry_queue.stop()
    logger.info("Retry queue stopped")


@app.get("/manage/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/v1/cars", response_model=PaginationResponse)
async def get_cars(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    show_all: bool = Query(False, alias="showAll")
):
    async def fetch_cars():
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{CARS_SERVICE_URL}/api/v1/cars",
                params={"page": page, "size": size, "show_all": show_all}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Cars service error")
            return response.json()

    def fallback():
        return {
            "page": page,
            "pageSize": 0,
            "totalElements": 0,
            "items": []
        }

    breaker = circuit_breaker_manager.get_breaker("cars_service")
    return await breaker.call(fetch_cars, fallback=fallback)


@app.post("/api/v1/rental", response_model=CreateRentalResponse)
async def create_rental(
    rental_request: CreateRentalRequest,
    x_user_name: str = Header(..., alias="X-User-Name")
):
    async with httpx.AsyncClient() as client:
        # Get car details
        car_response = await client.get(
            f"{CARS_SERVICE_URL}/api/v1/cars/{rental_request.car_uid}"
        )
        if car_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Car not found")

        car_data = car_response.json()

        # Calculate rental price
        date_from = datetime.fromisoformat(rental_request.date_from)
        date_to = datetime.fromisoformat(rental_request.date_to)
        days = abs((date_to - date_from).days)
        total_price = days * car_data["price"]

        # Create payment
        payment_response = await client.post(
            f"{PAYMENT_SERVICE_URL}/api/v1/payment",
            json={"price": total_price}
        )
        if payment_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Payment service error")

        payment_data = payment_response.json()

        # Reserve car
        reserve_response = await client.patch(
            f"{CARS_SERVICE_URL}/api/v1/cars/{rental_request.car_uid}/availability",
            params={"available": False}
        )
        if reserve_response.status_code != 200:
            # Rollback payment
            await client.delete(f"{PAYMENT_SERVICE_URL}/api/v1/payment/{payment_data['paymentUid']}")
            raise HTTPException(status_code=500, detail="Failed to reserve car")

        # Create rental
        rental_response = await client.post(
            f"{RENTAL_SERVICE_URL}/api/v1/rental",
            json={
                "username": x_user_name,
                "paymentUid": payment_data["paymentUid"],
                "carUid": str(rental_request.car_uid),
                "dateFrom": rental_request.date_from,
                "dateTo": rental_request.date_to
            }
        )
        if rental_response.status_code != 200:
            # Rollback car availability and payment
            await client.patch(
                f"{CARS_SERVICE_URL}/api/v1/cars/{rental_request.car_uid}/availability",
                params={"available": True}
            )
            await client.delete(f"{PAYMENT_SERVICE_URL}/api/v1/payment/{payment_data['paymentUid']}")
            raise HTTPException(status_code=500, detail="Rental service error")

        rental_data = rental_response.json()

        return CreateRentalResponse(
            rental_uid=rental_data["rentalUid"],
            status=rental_data["status"],
            car_uid=rental_request.car_uid,
            date_from=rental_request.date_from,
            date_to=rental_request.date_to,
            payment=PaymentInfo(
                payment_uid=payment_data["paymentUid"],
                status=payment_data["status"],
                price=payment_data["price"]
            )
        )


@app.get("/api/v1/rental", response_model=List[RentalResponse])
async def get_user_rentals(x_user_name: str = Header(..., alias="X-User-Name")):
    async def fetch_rentals():
        async with httpx.AsyncClient(timeout=5.0) as client:
            rentals_response = await client.get(
                f"{RENTAL_SERVICE_URL}/api/v1/rental",
                params={"username": x_user_name}
            )
            if rentals_response.status_code != 200:
                raise HTTPException(status_code=rentals_response.status_code, detail="Rental service error")
            return rentals_response.json()

    def rentals_fallback():
        return []

    rental_breaker = circuit_breaker_manager.get_breaker("rental_service")
    rentals = await rental_breaker.call(fetch_rentals, fallback=rentals_fallback)

    result = []

    for rental in rentals:
        # Get car info with fallback
        async def fetch_car():
            async with httpx.AsyncClient(timeout=5.0) as client:
                car_response = await client.get(
                    f"{CARS_SERVICE_URL}/api/v1/cars/{rental['carUid']}"
                )
                if car_response.status_code == 200:
                    return car_response.json()
                return {}

        def car_fallback():
            return {"carUid": rental["carUid"], "brand": "", "model": "", "registrationNumber": ""}

        car_breaker = circuit_breaker_manager.get_breaker("cars_service")
        car_data = await car_breaker.call(fetch_car, fallback=car_fallback)

        # Get payment info with fallback
        async def fetch_payment():
            async with httpx.AsyncClient(timeout=5.0) as client:
                payment_response = await client.get(
                    f"{PAYMENT_SERVICE_URL}/api/v1/payment/{rental['paymentUid']}"
                )
                if payment_response.status_code == 200:
                    return payment_response.json()
                return {}

        def payment_fallback():
            return {"paymentUid": rental["paymentUid"], "status": "PAID", "price": 0}

        payment_breaker = circuit_breaker_manager.get_breaker("payment_service")
        payment_data = await payment_breaker.call(fetch_payment, fallback=payment_fallback)

        result.append(RentalResponse(
            rental_uid=rental["rentalUid"],
            status=rental["status"],
            date_from=rental["dateFrom"],
            date_to=rental["dateTo"],
            car=CarInfo(
                car_uid=car_data.get("carUid", rental["carUid"]),
                brand=car_data.get("brand", ""),
                model=car_data.get("model", ""),
                registration_number=car_data.get("registrationNumber", "")
            ),
            payment=PaymentInfo(
                payment_uid=payment_data.get("paymentUid", rental["paymentUid"]),
                status=payment_data.get("status", "PAID"),
                price=payment_data.get("price", 0)
            )
        ))

    return result


@app.get("/api/v1/rental/{rental_uid}", response_model=RentalResponse)
async def get_rental(
    rental_uid: str,
    x_user_name: str = Header(..., alias="X-User-Name")
):
    async def fetch_rental():
        async with httpx.AsyncClient(timeout=5.0) as client:
            rental_response = await client.get(
                f"{RENTAL_SERVICE_URL}/api/v1/rental/{rental_uid}",
                params={"username": x_user_name}
            )
            if rental_response.status_code == 404:
                raise HTTPException(status_code=404, detail="Rental not found")
            if rental_response.status_code != 200:
                raise HTTPException(status_code=rental_response.status_code, detail="Rental service error")
            return rental_response.json()

    rental_breaker = circuit_breaker_manager.get_breaker("rental_service")
    rental = await rental_breaker.call(fetch_rental)

    # Get car info with fallback
    async def fetch_car():
        async with httpx.AsyncClient(timeout=5.0) as client:
            car_response = await client.get(
                f"{CARS_SERVICE_URL}/api/v1/cars/{rental['carUid']}"
            )
            if car_response.status_code == 200:
                return car_response.json()
            return {}

    def car_fallback():
        return {"carUid": rental["carUid"], "brand": "", "model": "", "registrationNumber": ""}

    car_breaker = circuit_breaker_manager.get_breaker("cars_service")
    car_data = await car_breaker.call(fetch_car, fallback=car_fallback)

    # Get payment info with fallback
    async def fetch_payment():
        async with httpx.AsyncClient(timeout=5.0) as client:
            payment_response = await client.get(
                f"{PAYMENT_SERVICE_URL}/api/v1/payment/{rental['paymentUid']}"
            )
            if payment_response.status_code == 200:
                return payment_response.json()
            return {}

    def payment_fallback():
        return {"paymentUid": rental["paymentUid"], "status": "PAID", "price": 0}

    payment_breaker = circuit_breaker_manager.get_breaker("payment_service")
    payment_data = await payment_breaker.call(fetch_payment, fallback=payment_fallback)

    return RentalResponse(
        rental_uid=rental["rentalUid"],
        status=rental["status"],
        date_from=rental["dateFrom"],
        date_to=rental["dateTo"],
        car=CarInfo(
            car_uid=car_data.get("carUid", rental["carUid"]),
            brand=car_data.get("brand", ""),
            model=car_data.get("model", ""),
            registration_number=car_data.get("registrationNumber", "")
        ),
        payment=PaymentInfo(
            payment_uid=payment_data.get("paymentUid", rental["paymentUid"]),
            status=payment_data.get("status", "PAID"),
            price=payment_data.get("price", 0)
        )
    )


@app.delete("/api/v1/rental/{rental_uid}", status_code=204)
async def cancel_rental(
    rental_uid: str,
    x_user_name: str = Header(..., alias="X-User-Name")
):
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Get rental to get car_uid and payment_uid
        rental_response = await client.get(
            f"{RENTAL_SERVICE_URL}/api/v1/rental/{rental_uid}",
            params={"username": x_user_name}
        )
        if rental_response.status_code == 404:
            raise HTTPException(status_code=404, detail="Rental not found")
        if rental_response.status_code != 200:
            raise HTTPException(status_code=rental_response.status_code, detail="Rental service error")

        rental = rental_response.json()

        # Try to cancel rental
        try:
            cancel_response = await client.delete(
                f"{RENTAL_SERVICE_URL}/api/v1/rental/{rental_uid}",
                params={"username": x_user_name}
            )
            if cancel_response.status_code != 204:
                raise Exception("Failed to cancel rental")

            # Release car
            try:
                await client.patch(
                    f"{CARS_SERVICE_URL}/api/v1/cars/{rental['carUid']}/availability",
                    params={"available": True}
                )
            except Exception as e:
                logger.warning(f"Failed to release car, adding to retry queue: {str(e)}")
                async def retry_release_car():
                    async with httpx.AsyncClient(timeout=5.0) as retry_client:
                        await retry_client.patch(
                            f"{CARS_SERVICE_URL}/api/v1/cars/{rental['carUid']}/availability",
                            params={"available": True}
                        )
                await retry_queue.add_task(retry_release_car)

            # Cancel payment
            try:
                await client.delete(f"{PAYMENT_SERVICE_URL}/api/v1/payment/{rental['paymentUid']}")
            except Exception as e:
                logger.warning(f"Failed to cancel payment, adding to retry queue: {str(e)}")
                async def retry_cancel_payment():
                    async with httpx.AsyncClient(timeout=5.0) as retry_client:
                        await retry_client.delete(f"{PAYMENT_SERVICE_URL}/api/v1/payment/{rental['paymentUid']}")
                await retry_queue.add_task(retry_cancel_payment)

            return None

        except Exception as e:
            logger.error(f"Failed to cancel rental: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to cancel rental")


@app.post("/api/v1/rental/{rental_uid}/finish", status_code=204)
async def finish_rental(
    rental_uid: str,
    x_user_name: str = Header(..., alias="X-User-Name")
):
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Get rental to get car_uid
        rental_response = await client.get(
            f"{RENTAL_SERVICE_URL}/api/v1/rental/{rental_uid}",
            params={"username": x_user_name}
        )
        if rental_response.status_code == 404:
            raise HTTPException(status_code=404, detail="Rental not found")
        if rental_response.status_code != 200:
            raise HTTPException(status_code=rental_response.status_code, detail="Rental service error")

        rental = rental_response.json()

        # Try to finish rental
        try:
            finish_response = await client.post(
                f"{RENTAL_SERVICE_URL}/api/v1/rental/{rental_uid}/finish",
                params={"username": x_user_name}
            )
            if finish_response.status_code != 204:
                raise Exception("Failed to finish rental")

            # Release car
            try:
                await client.patch(
                    f"{CARS_SERVICE_URL}/api/v1/cars/{rental['carUid']}/availability",
                    params={"available": True}
                )
            except Exception as e:
                logger.warning(f"Failed to release car, adding to retry queue: {str(e)}")
                async def retry_release_car():
                    async with httpx.AsyncClient(timeout=5.0) as retry_client:
                        await retry_client.patch(
                            f"{CARS_SERVICE_URL}/api/v1/cars/{rental['carUid']}/availability",
                            params={"available": True}
                        )
                await retry_queue.add_task(retry_release_car)

            return None

        except Exception as e:
            logger.error(f"Failed to finish rental: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to finish rental")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
