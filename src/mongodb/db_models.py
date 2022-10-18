from typing import Any
from ..input_models import BasicModel
import time 
from typing import Any

class QueryEntry(BasicModel):
    team_name: str
    query: Any
    epsilon: float
    delta: float
    timestamp: float = time.time()
    response: Any
