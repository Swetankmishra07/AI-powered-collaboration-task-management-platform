from fastapi import Request, FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(app: FastAPI):
    """
    Registers custom global exception handlers for standardized JSON responses.
    Prevents unhandled 500 internal server error stack trace leaks.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": exc.detail
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "status_code": 422,
                "detail": "Input validation error",
                "errors": exc.errors()
            }
        )
