import random
import time
from typing import Callable

from fastapi import Request, Response

from utils.config import Config


async def anti_timing_att(
    request: Request, call_next: Callable, config: Config
) -> Response:
    """
    Anti-timing attack mechanism.

    Changes the response time to either a minimum or by adding
    random noïse in order to avoid timing attacks.

    Args:
        request (Request): The FastApi request.
        call_next (Callable): The FastApi endpoint to call.
        config (Config): The server config.

    Returns:
        Response: The reponse from call_next.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    if config.server.time_attack:
        if config.server.time_attack.method == "stall":
            # if stall is used slow fast callbacks
            # to a minimum response time defined by magnitude
            if process_time < config.server.time_attack.magnitude:
                time.sleep(config.server.time_attack.magnitude - process_time)
        elif config.server.time_attack.method == "jitter":
            # if jitter is used it just adds some time
            # between 0 and magnitude secs
            time.sleep(
                config.server.time_attack.magnitude * random.uniform(0, 1)
            )

    return response
