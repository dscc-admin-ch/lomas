from opentelemetry import metrics

meter = metrics.get_meter(__name__)

# FastAPI metrics
FAST_API_REQUESTS_COUNTER = meter.create_counter(
    "requests_total",
    description="Total count of requests by method and path",
)

FAST_API_RESPONSES_COUNTER = meter.create_counter(
    "responses_total",
    description="Total count of responses by method, path, and status code",
)

FAST_API_EXCEPTION_COUNTER = meter.create_counter(
    "exceptions_total",
    description="Total count of exceptions raised by path and exception type",
)

FAST_API_REQUESTS_PROCESSING_HISTOGRAM = meter.create_histogram(
    "requests_duration_seconds",
    description="Histogram of requests processing time by path",
)

FAST_API_REQUESTS_IN_PROGRESS_GAUGE = meter.create_up_down_counter(
    "requests_in_progress",
    description="Gauge of requests currently being processed",
)
