import random
import time
from typing import Callable

from fastapi import Request, Response
from utils.config import Config


async def anti_timing_att(
    request: Request, call_next: Callable, config: Config
) -> Response:
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
