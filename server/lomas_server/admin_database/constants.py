from enum import StrEnum


class TopDBKey(StrEnum):
    """Key of the top level collecions."""

    ARCHIVE = "queries_archive"
    USERS = "users"
    DATASETS = "datasets"
    MISC_KEYS = "misc"
    JOBS = "jobs"


class MiscDBKeys(StrEnum):
    """Key for selecting sub elements in misc collection."""

    BOOTSTRAP = "bootstrap"


class BudgetDBKey(StrEnum):
    """
    Key for selecting budget values in admin db for given.

    dataset and user.
    """

    INITIAL = "initial_budget"
    SPENT = "total_spent_budget"
