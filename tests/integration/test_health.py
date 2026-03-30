from fastapi import FastAPI
from fastapi.testclient import TestClient

from payment_service.interfaces.api.routes.v1.payments import router as payments_router


def test_openapi_available():
    app = FastAPI()
    app.include_router(payments_router, prefix="/api/v1")
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
