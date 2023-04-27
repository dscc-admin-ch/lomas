import time

from input_models import (
    BasicModel,
)


class QueryResponse(BasicModel):
    data: dict = {}
    epsilon: float = 0
    delta: float = 0


class Query(BasicModel):
    query: dict = {}
    epsilon: float = 0  # For response
    delta: float = 0  # For response
    accuracy: float = 0  # For response
    timestamp: float = 0
    response: dict = {}
    type: str = ""

    def __init__(self, steps, type):
        super().__init__()
        self.query = steps
        self.type = type
        self.timestamp = time.time()


class QueryDBInput(BasicModel):
    team_name: str = ""
    query: Query = None

    def __init__(
        self,
        name,
        query_steps,
        query_type,
    ):
        super().__init__()
        self.team_name = name
        self.query = Query(
            query_steps,
            query_type,
        )


class SubmissionDBInput(BasicModel):
    accuracy: float = 0
    timestamp: float = 0
    score: float = 0
    epsilon: float = 0
    delta: float = 0
    final_score: float = 0
    final_accuracy: float = 0
    submission_data: dict = {}

    def __init__(
        self,
        accuracy,
        score,
        final_accuracy,
        final_score,
        data,
    ):
        super().__init__()
        self.accuracy = accuracy
        self.score = score
        self.final_accuracy = final_accuracy
        self.final_score = final_score
        self.submission_data = data
        self.timestamp = time.time()
