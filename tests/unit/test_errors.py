import pytest
from fastapi import status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.errors import (
    format_error_payload,
    http_exception_handler,
    validation_exception_handler,
)


def test_format_error_payload() -> None:
    without_details = format_error_payload(code="test_code", message="test message")
    assert without_details == {"code": "test_code", "message": "test message"}
    assert "details" not in without_details

    with_details = format_error_payload(
        code="test_code", message="test message", details={"key": "val"}
    )
    assert with_details == {
        "code": "test_code",
        "message": "test message",
        "details": {"key": "val"},
    }


@pytest.mark.anyio
async def test_http_exception_handler_branches() -> None:
    # 1. String detail with 401
    exc_401 = StarletteHTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Custom 401 text"
    )
    res_401 = await http_exception_handler(None, exc_401)  # type: ignore[arg-type]
    data_401 = res_401.body.decode()
    assert '"code":"unauthorized"' in data_401
    assert '"message":"Custom 401 text"' in data_401

    # 2. String detail with other status (e.g. 500)
    exc_500 = StarletteHTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=""
    )
    res_500 = await http_exception_handler(None, exc_500)  # type: ignore[arg-type]
    data_500 = res_500.body.decode()
    assert '"code":"http_error"' in data_500
    assert '"message":"An error occurred"' in data_500

    # 3. Dict detail with custom code, message and details
    exc_dict = StarletteHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "bad_request",
            "message": "Malformed input",
            "details": {"reason": "missing_token"},
        },
    )
    res_dict = await http_exception_handler(None, exc_dict)  # type: ignore[arg-type]
    data_dict = res_dict.body.decode()
    assert '"code":"bad_request"' in data_dict
    assert '"details":{"reason":"missing_token"}' in data_dict


@pytest.mark.anyio
async def test_validation_exception_handler_edge_locations() -> None:
    # Empty loc
    err_empty_loc = RequestValidationError(
        errors=[{"loc": (), "msg": "general error", "type": "value_error"}]
    )
    res_empty = await validation_exception_handler(None, err_empty_loc)  # type: ignore[arg-type]
    data_empty = res_empty.body.decode()
    assert '"field":"body"' in data_empty

    # Top-level single item loc
    err_single_loc = RequestValidationError(
        errors=[{"loc": ("custom",), "msg": "custom error", "type": "value_error"}]
    )
    res_single = await validation_exception_handler(None, err_single_loc)  # type: ignore[arg-type]
    data_single = res_single.body.decode()
    assert '"field":"custom"' in data_single
