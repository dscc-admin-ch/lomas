from collections.abc import Callable
from functools import wraps
from typing import Any

from opentelemetry import trace

tracer = trace.get_tracer("local-admin-db")


def db_span(name: str, **attrs: Any) -> Callable:
    """
    Decorator wrapping a function in an OpenTelemetry span.

    Adds the given span name and optional attributes to the span for tracing
    database-related operations.

    Args:
        name: Span name.
        **attrs: Key-value pairs added as span attributes.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(name) as span:
                for k, v in attrs.items():
                    span.set_attribute(k, v)

                return func(*args, **kwargs)

        return wrapper

    return decorator
