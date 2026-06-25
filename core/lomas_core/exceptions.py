from uuid import UUID

from lomas_core.constants import DPLibraries


class LomasAPIException(Exception):
    """Base exception for lomas server exceptions."""

    pass


class UserNotFoundException(LomasAPIException):
    """Custom exception for when the user does not exist in the database."""

    def __init__(self, user_name: str):
        super().__init__(f"User {user_name!r} does not exist.")


class DatasetNotFoundException(LomasAPIException):
    """Custom exception for when the dataset does not exist in the database."""

    def __init__(self, dataset_name: str):
        super().__init__(f"Dataset {dataset_name!r} does not exist.")


class JobNotFoundException(LomasAPIException):
    """Custom exception for when the job does not exist in the database."""

    def __init__(self, uid: UUID):
        super().__init__(f"Job {uid!r} does not exist.")


class InvalidQueryException(LomasAPIException):
    """Exception for invalid queries.

    For example if it does not contain a DP mechanism or there is not enough DP budget.
    """

    def __init__(self, message: str):
        super().__init__(f"Invalid query: {message}")


class ExternalLibraryException(LomasAPIException):
    """For exceptions from libraries external to the lomas packages."""

    def __init__(self, library: DPLibraries, message: str):
        super().__init__(f"Exception from {library!r} library: {message}")


class UnauthorizedAccessException(LomasAPIException):
    """Exception related to rights with regards to the query.

    (e.g. no user access for this dataset).
    """

    def __init__(self, message: str):
        super().__init__(f"Unauthorized: {message}")


class InternalServerException(LomasAPIException):
    """For any unforeseen internal exception."""

    def __init__(self, message: str = "Internal server error."):
        super().__init__(message)
