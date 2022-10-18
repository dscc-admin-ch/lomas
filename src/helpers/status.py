from fastapi import HTTPException
from typing import List, Callable
from datetime import datetime

class IndividualStatus():
    name: str
    metric: Callable
    _acc: float = 0
    _eps: float = 0
    score: float = 0
    last_submision: datetime = None

    def __init__(self, name, metric):
        self.name = name
        self.metric = metric

    @property
    def acc(self):
        return self._acc

    @acc.setter
    def acc(self, value):
        self._acc = value
        self.score = self.metric(self._acc, self._eps)

    @property
    def eps(self):
        return self._eps

    @eps.setter
    def eps(self, value):
        self._eps = value
        self.score = self.metric(self._acc, self._eps)

    def __lt__(self, other):
        if not isinstance(other, IndividualStatus):
            raise ValueError(f"{other} is not a key in PartyStatus.")

        return self.score < other.score

    def to_fast_api_csv_row(self):
        return ", ".join(map(str, [self.name, self._acc, self._eps, self.score, self.last_submision]))

class PartyStatus():
    _status: List[IndividualStatus]

    def __init__(self, party_list: List[str], ranking_method: Callable):
        self._status = [IndividualStatus(name=p, metric=ranking_method) for p in party_list]

    def __getitem__(self, key):
        if isinstance(key, str):
            # don't use this method outside of this class
            for status in self._status:
                if status.name == key:
                    return status

            raise HTTPException(400, f"{key} is not a key in PartyStatus.")

        else:
            # sort based on score
            self.sort()

            if isinstance(key, slice):
                # used to create leaderboards easily
                return {s.name:s.score for s in self._status[key]}
            elif isinstance(key, int):
                return {self._status[key].name:self._status[key].score}

    def set_acc(self, name, value):
        self[name].acc = value
        self[name].last_submision = datetime.now()

    def get_acc(self, name):
        return self[name].acc.copy()

    def set_eps(self, name, value):
        self[name].eps = value

    def get_eps(self, name):
        return self[name].eps.copy()

    def sort(self):
        self._status.sort(reverse=True)

    def to_fast_api_csv_str(self):
        return '\n'.join(map(lambda individual_status: individual_status.to_fast_api_csv_row(), self._status))


    