from collections.abc import Callable
from functools import wraps

from opentelemetry import trace
from opentelemetry.util.types import AttributeValue

tracer = trace.get_tracer("local-admin-db")


def db_span[**Q, R](name: str, **attrs: AttributeValue) -> Callable[[Callable[Q, R]], Callable[Q, R]]:
    """
    Decorator wrapping a function in an OpenTelemetry span.

    Adds the given span name and optional attributes to the span for tracing
    database-related operations.

    Args:
        name: Span name.
        **attrs: Key-value pairs added as span attributes.
    """

    def decorator(func: Callable[Q, R]) -> Callable[Q, R]:
        @wraps(func)
        def wrapper(*args: Q.args, **kwargs: Q.kwargs) -> R:
            with tracer.start_as_current_span(name) as span:
                for k, v in attrs.items():
                    span.set_attribute(k, v)

                return func(*args, **kwargs)

        return wrapper

    return decorator
