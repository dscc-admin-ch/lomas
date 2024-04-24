from pydantic import BaseModel

class ServerState(BaseModel):
    state: list
    message: list
    LIVE: bool

class State(BaseModel):
    requested_by: str
    state: ServerState

class InitialBudget(BaseModel):
    initial_epsilon: float
    initial_delta: float