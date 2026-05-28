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

# Admin db query
ADMINDB_QUERY_COUNTER = meter.create_counter(
    name="admindb_query_count",
    description="Number of admindb queries executed",
    unit="queries",
)

ADMINDB_INSERT_COUNTER = meter.create_counter(
    name="admindb_insert_count",
    description="Number of AdminDB insert operations executed",
    unit="inserts",
)

ADMINDB_UPDATE_COUNTER = meter.create_counter(
    name="admindb_update_count",
    description="Number of AdminDB update operations executed",
    unit="updates",
)

ADMINDB_ERROR_COUNTER = meter.create_counter(
    name="admindb_error_count",
    description="Number of AdminDB errors encountered",
    unit="errors",
)

ADMINDB_DELETE_COUNTER = meter.create_counter(
    name="admindb_delete_count",
    description="Number of AdminDB deletes encountered",
    unit="deletes",
)
