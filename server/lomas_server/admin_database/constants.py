from enum import StrEnum


class TopDBKey(StrEnum):
    """Key of the top level collecions."""

    ARCHIVE = "queries_archive"
    USERS = "users"
    DATASETS = "datasets"
    METADATA = "metadata"
    MISC_KEYS = "misc"


class MiscDBKeys(StrEnum):
    """Key for selecting sub elements in misc collection."""

    BOOTSTRAP_DISABLED = "bootstrap_disabled"
    BOOTSTRAP = "bootstrap"


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

# Limit each element to a max MAX_BSON_SIZE (inserted document must be < 16MB)
MAX_BSON_SIZE = 4 * 1024 * 1024  # 4 MB
