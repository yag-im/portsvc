import logging
from collections.abc import Callable

log = logging.getLogger("portsvc")


def log_input_output[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
        # Log the function name and arguments
        log.debug("calling %s with args: %s, kwargs: %s", func.__name__, args, kwargs)

        # Call the original function
        result = func(*args, **kwargs)

        # Log the return value
        log.debug("%s returned: %s", func.__name__, repr(result))

        # Return the result
        return result

    return wrap
