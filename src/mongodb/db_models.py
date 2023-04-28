import time

from input_models import BasicModel


class QueryResponse(BasicModel):
    data: dict = {}
    epsilon: float = 0
    delta: float = 0


class Query(BasicModel):
    query: dict = {}
    epsilon: float = 0  #For response
    delta: float = 0    #For response
    timestamp: float = 0
    response: dict = {}
    type: str = ""

    def __init__(self, steps, type):
        super().__init__()
        self.query = steps
        self.type = type
        self.timestamp = time.time()


class QueryDBInput(BasicModel):
    user_name: str = ""
    query: Query = None

    def __init__(
        self,
        name,
        query_steps,
        query_type,
    ):
        super().__init__()
        self.user_name = name
        self.query = Query(query_steps, query_type)
