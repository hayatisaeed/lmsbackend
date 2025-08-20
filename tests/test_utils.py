from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from config.utils import exception_handler


def test_exception_handler_server_error():
    factory = APIRequestFactory()
    request = Request(factory.get("/"))
    response = exception_handler(Exception("boom"), {"request": request})
    assert response.status_code == 500
    assert response.data["error"]["code"] == "server_error"


def test_exception_handler_validation_error():
    factory = APIRequestFactory()
    request = Request(factory.get("/"))
    exc = ValidationError("bad")
    response = exception_handler(exc, {"request": request})
    assert response.status_code == 400
    assert "bad" in response.data["error"]["message"]
