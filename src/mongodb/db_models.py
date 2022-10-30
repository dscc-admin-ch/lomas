import time
from datetime import datetime
from typing import Any

from input_models import BasicModel


class QueryResponse(BasicModel):
    data: dict = {}
    epsilon: float = 0
    delta: float = 0

class Query(BasicModel):
    query: dict = {}
    epsilon: float = 0  #For response
    delta: float = 0    #For response
    accuracy: float = 0 #For response
    timestamp: float = time.time()
    response: dict = {}
    type: str = ""
    
    def __init__(self,steps,type):
        super().__init__()
        self.query = steps
        self.type = type

class QueryDBInput(BasicModel):
    team_name: str = ""
    query: Query = None
    
    def __init__(self,name,query_steps,query_type):
        super().__init__()
        self.team_name = name
        self.query = Query(query_steps, query_type)


class SubmissionDBInput(BasicModel):
    accuracy: float = 0
    timestamp: float = time.time()
    score: float = 0
    
    def __init__(self,accuracy,score):
        super().__init__()
        self.accuracy = accuracy
        self.score = score