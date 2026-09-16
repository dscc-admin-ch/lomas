from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from lomas_core.exceptions import LomasAPIException
from lomas_core.models.constants import get_lomas_logger
from lomas_core.models.exceptions import LomasAPIErrorModel, model_from_lomas_exception

logger = get_lomas_logger(__name__)


# Custom exception handlers
def add_exception_handlers(app: FastAPI) -> None:
    """
    Translates custom exceptions to JSONResponses.

    Args:
        app (FastAPI): A fastapi App.
    """

    @app.exception_handler(LomasAPIException)
    async def lomas_exception_handler(_: Request, exc: LomasAPIException) -> JSONResponse:
        # Log exception
        if not isinstance(exc, LomasAPIException):
            logger.exception(f"Unforseen exception occured: {exc}")  # noqa:LOG004
        else:
            logger.exception(exc)  # noqa:LOG004
        model, status_code = model_from_lomas_exception(exc)
        return JSONResponse(status_code=status_code, content=jsonable_encoder(model))


# Server error responses for API queries (can only put one model per status code)
API_ERROR_RESPONSES: dict[int, dict[str, type[LomasAPIErrorModel]]] = {
    status.HTTP_400_BAD_REQUEST: {"model": LomasAPIErrorModel},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": LomasAPIErrorModel},
    status.HTTP_403_FORBIDDEN: {"model": LomasAPIErrorModel},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": LomasAPIErrorModel},
    status.HTTP_404_NOT_FOUND: {"model": LomasAPIErrorModel},
}
