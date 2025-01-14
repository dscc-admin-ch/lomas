import time
from typing import Tuple

from lomas_core.constants import SERVICE_NAME
from opentelemetry import metrics
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.types import ASGIApp

# Create a meter for the application
meter = metrics.get_meter(__name__)

# Define the metrics using OpenTelemetry API
requests_counter = meter.create_counter(
    "fastapi_requests_total",
    description="Total count of requests by method and path",
)

responses_counter = meter.create_counter(
    "fastapi_responses_total",
    description="Total count of responses by method, path, and status code",
)

exceptions_counter = meter.create_counter(
    "fastapi_exceptions_total",
    description="Total count of exceptions raised by path and exception type",
)

requests_processing_histogram = meter.create_histogram(
    "fastapi_requests_duration_seconds",
    description="Histogram of requests processing time by path",
)

requests_in_progress_gauge = meter.create_up_down_counter(
    "fastapi_requests_in_progress",
    description="Gauge of requests currently being processed",
)


class MetricMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect and expose Prometheus metrics for a FastAPI application.

    This middleware tracks various metrics related to HTTP requests, including:
    - Total requests (`fastapi_requests_total`)
    - Total responses (`fastapi_responses_total`)
    - Exceptions raised (`fastapi_exceptions_total`)
    - Request processing duration (`fastapi_requests_duration_seconds`)
    - Current requests in progress (`fastapi_requests_in_progress`)

    It also supports integration with an OpenTelemetry exporter for exporting metrics
    to a metrics collector (e.g., Prometheus or any other OTLP-compatible collector).
    """

    def __init__(self, app: ASGIApp, app_name: str = SERVICE_NAME) -> None:
        """
        Initializes the MetricMiddleware.

        Args:
            app (ASGIApp): The FastAPI application instance.
            app_name (str): The name of the application used for metric labeling.
        """
        super().__init__(app)
        self.app_name = app_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Processes the incoming HTTP request, records metrics,.

        and returns the HTTP response.

        This method performs the following steps:
        1. Tracks the current request in progress using the
            `fastapi_requests_in_progress` gauge.
        2. Records the request count with the `fastapi_requests_total` counter.
        3. Records the time taken to process the request using the
            `fastapi_requests_duration_seconds` histogram.
        4. Handles exceptions, if raised, and records the exception details using the
            `fastapi_exceptions_total` counter.
        5. Records the response status code with the `fastapi_responses_total` counter.
        6. Decrements the in-progress request gauge after processing.

        Args:
            request (Request): The incoming HTTP request to be processed.
            call_next (RequestResponseEndpoint): The endpoint function that processes
                                                 the request and returns a response.

        Returns:
            Response: The HTTP response after processing the request.

        Raises:
            BaseException: If an exception occurs during request processing, it is
                           raised after logging it.
        """
        method = request.method
        path, is_handled_path = self.get_path(request)

        if not is_handled_path:
            return await call_next(request)

        # Track requests being processed
        requests_in_progress_gauge.add(
            1, {"method": method, "path": path, "app_name": self.app_name}
        )
        requests_counter.add(
            1, {"method": method, "path": path, "app_name": self.app_name}
        )

        before_time = time.perf_counter()

        try:
            response = await call_next(request)
        except BaseException as e:
            exceptions_counter.add(
                1,
                {
                    "method": method,
                    "path": path,
                    "exception_type": type(e).__name__,
                    "app_name": self.app_name,
                },
            )
            raise e from None
        else:
            status_code = response.status_code
            after_time = time.perf_counter()

            # Record request processing time
            requests_processing_histogram.record(
                after_time - before_time,
                {"method": method, "path": path, "app_name": self.app_name},
            )

        finally:
            responses_counter.add(
                1,
                {
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "app_name": self.app_name,
                },
            )
            requests_in_progress_gauge.add(
                -1, {"method": method, "path": path, "app_name": self.app_name}
            )

        return response

    @staticmethod
    def get_path(request: Request) -> Tuple[str, bool]:
        """
        Attempts to match the request' route to a defined route.

        Args:
            request (Request): The HTTP request to check for a matching path.

        Returns:
            Tuple[str, bool]: A tuple containing:
                - The matched path (str) from the request URL.
                - Boolean (True if the path was handled by one of the routes).
        """
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path, True

        return request.url.path, False
