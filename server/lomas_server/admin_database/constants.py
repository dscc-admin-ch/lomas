from enum import StrEnum


class BudgetDBKey(StrEnum):
    """
    Key for selecting budget values in admin db for given.

    dataset and user.
    """

    EPSILON_SPENT = "total_spent_epsilon"
    DELTA_SPENT = "total_spent_delta"
    EPSILON_INIT = "initial_epsilon"
    DELTA_INIT = "initial_delta"


WRITE_CONCERN_LEVEL = "majority"
