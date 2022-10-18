from typing import List, Callable

from .status import PartyStatus
from .slack import post_leaders
from .metrics import acc_m_eps

class LeaderBoard():
    def __init__(self, participants: List[str], slack_path: str, metric:Callable = acc_m_eps):
        self._status = PartyStatus(participants, acc_m_eps)
        self._previous_status = self._status[:5]
        self._slack_path = slack_path

    def update_eps(self, name:str, value:float):
        self._status[name].eps += value
        if self._status[:5] != self._previous_status:
            self._previous_status = self._status[:5]
            self.post_slack(None)

    def update_acc(self, name:str, value:float):
        self._status.set_acc(name, max(
            self._status[name].acc,
            value
        ))
#        self._status[name].acc = max(
#            self._status[name].acc,
#            value
#        )
        if self._status[:5] != self._previous_status:
            self._previous_status = self._status[:5]
            self.post_slack(None)

    def get_eps(self, name:str):
        return self._status[name].eps

    def get_acc(self, name:str):
        return self._status[name].acc

    def get_score(self, name:str):
        return self._status[name].score

    def post_slack(self, no_leaders):
        post_leaders(
            self._slack_path,
            self._status[:no_leaders],            
            no_leaders
        )


    def to_fast_api_csv_str(self):
        return self._status.to_fast_api_csv_str()