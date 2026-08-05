from abc import ABC, abstractmethod
from uuid import UUID

from csvw_eo.metadata_structure import TableMetadata

from lomas_core.models.collections import DSInfo
from lomas_core.models.constants import get_lomas_logger
from lomas_core.models.responses import Job
from lomas_server.admin_database.constants import BudgetDBKey

logger = get_lomas_logger(__name__)


class AdminDatabase(ABC):
    """Overall database management for server state."""

    @abstractmethod
    def does_user_exist(self, user_name: str) -> bool:
        """
        Checks if user exist in the database.

        Args:
            user_name (str): name of the user to check

        Returns:
            bool: True if the user exists, False otherwise.
        """

    @abstractmethod
    def does_dataset_exist(self, dataset_name: str) -> bool:
        """
        Checks if dataset exists in the database.

        Args:
            dataset_name (str): name of the dataset to check

        Returns:
            bool: True if the dataset exists, False otherwise.
        """

    @abstractmethod
    def does_job_exist(self, uid: UUID) -> bool:
        """Returns true only if the job exists.

        Args:
            uid (UUID): The uid of the job.

        Returns:
            bool: True only if the job exists
        """

    @abstractmethod
    def get_job(self, uid: UUID) -> Job:
        """
        Gets the job with given uid from the database.

        Args:
            uid (UUID): The uid of the job.

        Returns:
            Job: The job.
        """

    @abstractmethod
    def put_job(self, job: Job) -> None:
        """
        Puts the job in the database.

        Args:
            job (Job): The job to put in the database.
        """

    @abstractmethod
    def update_job(self, updated_job: Job) -> None:
        """
        Updates the job.

        All fields are taken from updated_job, except those that are None.

        Args:
            updated_job (Job): The updated job
        """

    @abstractmethod
    def archive_job(self, uid: UUID) -> None:
        """
        Adds the job into the archives, ignores dummy and cost queries.

        Args:
            uid (UUID): The job uid to archive
        """

    @abstractmethod
    def get_dataset_metadata(self, dataset_name: str) -> TableMetadata:
        """
        Returns the metadata dictionnary of the dataset.

        Wrapped by [dataset_must_exist][lomas_server.admin_database.admin_database.dataset_must_exist].

        Args:
            dataset_name (str): name of the dataset to get the metadata

        Returns:
            TableMetadata: The metadata object.
        """

    @abstractmethod
    def is_user_admin(self, user_name: str) -> bool:
        """
        Returns true if the user is an admin.

        Args:
            user_name (str): name of the user

        Returns:
            bool: True if the user is a lomas admin.
        """

    @abstractmethod
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str) -> bool:
        """
        Checks if a user may access a particular dataset.

        Wrapped by [user_must_exist][lomas_server.admin_database.admin_database.user_must_exist].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            bool: True if the user has access, False otherwise.
        """

    @abstractmethod
    def get_epsilon_or_delta(self, user_name: str, dataset_name: str, parameter: BudgetDBKey) -> float:
        """
        Get the total spent epsilon or delta by user on dataset.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (str): Member of BudgetDBKey.

        Returns:
            float: The requested budget value.
        """

    def get_total_spent_budget(self, user_name: str, dataset_name: str) -> list[float]:
        """
        Get the total spent epsilon and delta spent by user on dataset.

        Wrapped by [user_must_have_access_to_dataset][lomas_server.admin_database.admin_database.user_must_have_access_to_dataset].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[float]: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        return [
            self.get_epsilon_or_delta(user_name, dataset_name, BudgetDBKey.EPSILON_SPENT),
            self.get_epsilon_or_delta(user_name, dataset_name, BudgetDBKey.DELTA_SPENT),
        ]

    def get_initial_budget(self, user_name: str, dataset_name: str) -> list[float]:
        """
        Get the initial epsilon and delta budget.

        Wrapped by [user_must_have_access_to_dataset][lomas_server.admin_database.admin_database.user_must_have_access_to_dataset].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[float]: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        return [
            self.get_epsilon_or_delta(user_name, dataset_name, BudgetDBKey.EPSILON_INIT),
            self.get_epsilon_or_delta(user_name, dataset_name, BudgetDBKey.DELTA_INIT),
        ]

    def get_remaining_budget(self, user_name: str, dataset_name: str) -> list[float]:
        """
        Get the remaining epsilon and delta budget (initial - total spent).

        Wrapped by [user_must_have_access_to_dataset][lomas_server.admin_database.admin_database.user_must_have_access_to_dataset].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[float]: The first value of the list is the epsilon value,
                the second value is the delta value.
        """
        init_eps, init_delta = self.get_initial_budget(user_name, dataset_name)
        spent_eps, spent_delta = self.get_total_spent_budget(user_name, dataset_name)
        return [init_eps - spent_eps, init_delta - spent_delta]

    @abstractmethod
    def update_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: BudgetDBKey,
        spent_value: float,
    ) -> None:
        """
        Update current budget spent by user with spent budget.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (str): One of BudgetDBKey
            spent_value (float): spending of epsilon or delta on last query
        """

    def update_epsilon(self, user_name: str, dataset_name: str, spent_epsilon: float) -> None:
        """
        Update spent epsilon by user with total spent epsilon.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            spent_epsilon (float): value of epsilon spent on last query
        """
        return self.update_epsilon_or_delta(user_name, dataset_name, BudgetDBKey.EPSILON_SPENT, spent_epsilon)

    def update_delta(self, user_name: str, dataset_name: str, spent_delta: float) -> None:
        """
        Update spent delta spent by user with spent delta of the user.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            spent_delta (float): value of delta spent on last query
        """
        self.update_epsilon_or_delta(user_name, dataset_name, BudgetDBKey.DELTA_SPENT, spent_delta)

    def update_budget(
        self,
        user_name: str,
        dataset_name: str,
        spent_epsilon: float,
        spent_delta: float,
    ) -> None:
        """
        Update current epsilon and delta delta spent by user.

        Wrapped by [user_must_have_access_to_dataset][lomas_server.admin_database.admin_database.user_must_have_access_to_dataset].

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            spent_epsilon (float): value of epsilon spent on last query
            spent_delta (float): value of delta spent on last query
        """
        self.update_epsilon(user_name, dataset_name, spent_epsilon)
        self.update_delta(user_name, dataset_name, spent_delta)

    @abstractmethod
    def get_dataset(self, dataset_name: str) -> DSInfo:
        """
        Get dataset access info based on dataset_name.

        Wrapped by [dataset_must_exist][lomas_server.admin_database.admin_database.dataset_must_exist].

        Args:
            dataset_name (str): Name of the dataset.

        Returns:
            Dataset: The dataset model.
        """

    @abstractmethod
    def get_user_dataset_queries(
        self,
        user_name: str,
        dataset_name: str,
    ) -> list[dict]:
        """
        Retrieves and return the queries already done by a user for a particular dataset.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[dict]: List of previous queries.
        """

    @abstractmethod
    def get_user_queries(self, username: str) -> list[Job]:
        """
        Retrieves and return the queries already done by a user.

        Args:
            user_name (str): name of the user

        Returns:
            List[dict]: List of previous queries.
        """

    @abstractmethod
    def wipe(self) -> None:
        """Wipe the entire Database."""

    @abstractmethod
    def set_bootstrap(self, bootstrap: str) -> None:
        """Sets the bootstrap value.

        Also sets the bootstrap disabled value to False.

        Args:
            bootstrap (str): Bootstrap creds to set.
        """

    @abstractmethod
    def get_bootstrap(self) -> str | None:
        """Returns the bootstrap credential value or None if it has not been set.

        Returns:
            str | None: The bootstrap credential value or None if it has not been set.
        """

    @abstractmethod
    def set_bootstrap_disabled(self, bootstrap_disabled: bool = True) -> None:
        """Sets the bootstrap disabled value."""

    @abstractmethod
    def get_bootstrap_disabled(self) -> bool:
        """Get the bootstrap disabled value.

        Returns:
            bool: The bootstrap disabled value. False by default if not set in the DB.
        """
